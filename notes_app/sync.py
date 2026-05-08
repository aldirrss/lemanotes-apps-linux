"""Supabase sync manager — offline-first, auto-sync when logged in."""

import json
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import webbrowser

from notes_app.settings import load_settings, save_settings
from notes_app import storage

# Resolve .env relative to this package's parent directory (project root)
_ENV_FILE = Path(__file__).parent.parent / ".env"


def _load_env_file():
    """Load .env file if present. Returns dict of key→value."""
    if not _ENV_FILE.exists():
        return {}
    try:
        from dotenv import dotenv_values
        return dotenv_values(_ENV_FILE)
    except ImportError:
        # Fallback: manual parse
        values = {}
        for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            values[k.strip()] = v.strip()
        return values


_KEYRING_SERVICE = "lemanotes"
_KEYRING_KEY = "supabase_session"


def _keyring_save(data: dict) -> bool:
    """Persist session dict in the OS keyring. Returns False if keyring unavailable."""
    try:
        import keyring
        keyring.set_password(_KEYRING_SERVICE, _KEYRING_KEY, json.dumps(data))
        return True
    except Exception:
        return False


def _keyring_load() -> "dict | None":
    """Read session dict from the OS keyring. Returns None if missing or unavailable."""
    try:
        import keyring
        raw = keyring.get_password(_KEYRING_SERVICE, _KEYRING_KEY)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def _keyring_clear() -> None:
    """Remove session entry from the OS keyring, silently ignoring errors."""
    try:
        import keyring
        keyring.delete_password(_KEYRING_SERVICE, _KEYRING_KEY)
    except Exception:
        pass


class SyncManager:
    def __init__(self):
        self._client = None
        self._ready = False
        self._env_locked = False
        self._optimistic_logged_in = False
        self._on_session_refresh: "callable | None" = None
        self._stored_refresh_token: "str | None" = None  # kept for network-error retry
        self._load_config()

    # ── Config / init ────────────────────────────────────────────────────────────

    def _load_config(self):
        env = _load_env_file()
        from_env = env.get("LEMANOTES_SYNC_FROM_ENV", "false").lower() == "true"

        if from_env:
            url = env.get("LEMANOTES_SUPABASE_URL", "").strip()
            key = env.get("LEMANOTES_SUPABASE_ANON_KEY", "").strip()
            self._env_locked = True
        else:
            s = load_settings()
            url = s.get("supabase_url", "")
            key = s.get("supabase_key", "")
            self._env_locked = False

        if url and key:
            # Keyring is the primary store; fall back to legacy JSON entry and
            # migrate it to keyring on the first successful read.
            session_data = _keyring_load()
            if session_data is None:
                s = load_settings()
                session_data = s.get("supabase_session")
                if session_data:
                    if _keyring_save(session_data):
                        s.pop("supabase_session", None)
                        save_settings(s)
            self._init_client(url, key, session_data)

    def set_session_refresh_callback(self, cb: "callable") -> None:
        """Register a UI callback invoked (from background thread) after session refresh."""
        self._on_session_refresh = cb

    def _init_client(self, url: str, key: str, session_data: dict | None = None):
        try:
            from supabase import create_client
            self._client = create_client(url, key)
            if session_data and session_data.get("refresh_token"):
                # Keep refresh_token for network-error retry on next startup.
                self._stored_refresh_token = session_data["refresh_token"]
                # Mark optimistic so is_logged_in() returns True while background
                # refresh is in flight (access_token may be expired).
                self._optimistic_logged_in = True
                try:
                    res = self._client.auth.set_session(
                        session_data["access_token"],
                        session_data["refresh_token"],
                    )
                    # set_session() auto-refreshes when access_token is expired.
                    # If the refresh_token rotated, update our copy NOW to avoid
                    # Scenario B: _refresh_session_bg() calling refresh with stale token.
                    if (res and res.session and res.session.refresh_token
                            and res.session.refresh_token != session_data["refresh_token"]):
                        self._stored_refresh_token = res.session.refresh_token
                        self._save_session(res.session)
                except Exception:
                    # Network down or token completely invalid — keep stored_refresh_token
                    # so _refresh_session_bg() can retry with it explicitly.
                    pass
                threading.Thread(target=self._refresh_session_bg, daemon=True).start()
            self._ready = True
        except Exception:
            self._ready = False

    def _refresh_session_bg(self):
        """Refresh access token in background.

        Always passes stored_refresh_token explicitly to refresh_session() so the
        call succeeds even when set_session() failed (Scenario A: network not yet
        ready at startup → client internal storage is empty).

        Only clears the stored session on definitive server-side auth errors
        (token revoked / invalid). Network/transient errors keep the token so
        the next startup can retry.
        """
        try:
            # Pass stored_refresh_token explicitly — bypasses the client's internal
            # session state which may be empty if set_session() failed at startup.
            res = self._client.auth.refresh_session(self._stored_refresh_token)
            if res and res.session:
                self._save_session(res.session)
                self._stored_refresh_token = None
                self._optimistic_logged_in = False
            else:
                # Null response = token definitively rejected by server
                self._optimistic_logged_in = False
                self._clear_stored_session()
        except Exception as exc:
            exc_name = type(exc).__name__.lower()
            exc_str  = str(exc).lower()
            # Server-side auth rejection → must clear (user needs to re-login)
            # Network / transient errors → keep token, retry on next startup
            is_auth_error = (
                "authapiexception"        in exc_name
                or "authinvalidcredentials" in exc_name
                or "invalid_grant"         in exc_str
                or "token_revoked"         in exc_str
                or "token_expired"         in exc_str
                or "refresh_token_not_found" in exc_str
                or "user_not_found"        in exc_str
            )
            self._optimistic_logged_in = False
            if is_auth_error:
                self._clear_stored_session()
            # Network/timeout errors: keep refresh_token, retry on next startup
        if self._on_session_refresh:
            self._on_session_refresh()

    def retry_refresh_if_needed(self):
        """Re-attempt token refresh if the startup refresh failed (network error).

        Call this before any sync operation that requires auth.
        Runs synchronously — intended for background threads only.
        """
        if self.is_logged_in() or not self._client:
            return
        if not self._stored_refresh_token:
            return
        try:
            self._client.auth.set_session("", self._stored_refresh_token)
            res = self._client.auth.refresh_session()
            if res and res.session:
                self._save_session(res.session)
                self._stored_refresh_token = None
                if self._on_session_refresh:
                    self._on_session_refresh()
        except Exception:
            pass

    def _clear_stored_session(self):
        _keyring_clear()
        s = load_settings()
        s.pop("supabase_session", None)
        save_settings(s)

    def configure(self, url: str, key: str) -> tuple[bool, str]:
        """Configure Supabase via UI. Not available when env-locked."""
        if self._env_locked:
            return False, "Configuration is locked by .env file."
        try:
            from supabase import create_client
            client = create_client(url, key)
            self._client = client
            self._ready = True
            s = load_settings()
            s["supabase_url"] = url
            s["supabase_key"] = key
            save_settings(s)
            return True, ""
        except ImportError:
            return False, "Package 'supabase' is not installed.\nRun: pip install supabase"
        except Exception as e:
            return False, str(e)

    # ── Auth state ───────────────────────────────────────────────────────────────

    def is_configured(self) -> bool:
        return self._ready and self._client is not None

    def is_env_locked(self) -> bool:
        """True when Supabase config is loaded from .env (UI setup is read-only)."""
        return self._env_locked

    def is_logged_in(self) -> bool:
        if not self._client:
            return False
        if self._optimistic_logged_in:
            return True
        try:
            session = self._client.auth.get_session()
            return session is not None and session.user is not None
        except Exception:
            return False

    def get_user_email(self) -> str | None:
        if not self._client:
            return None
        try:
            session = self._client.auth.get_session()
            if session and session.user:
                return session.user.email
        except Exception:
            pass
        # Fallback to stored email during optimistic phase (access_token still pending refresh)
        if self._optimistic_logged_in:
            stored = _keyring_load() or load_settings().get("supabase_session", {})
            return stored.get("user_email")
        return None

    # ── Login methods ────────────────────────────────────────────────────────────

    def login_email(self, email: str, password: str) -> tuple[bool, str]:
        if not self._client:
            return False, "Supabase is not configured"
        try:
            res = self._client.auth.sign_in_with_password({"email": email, "password": password})
            if res.session:
                self._save_session(res.session)
            return True, ""
        except Exception as e:
            return False, str(e)

    def register_email(self, email: str, password: str) -> tuple[bool, str]:
        if not self._client:
            return False, "Supabase is not configured"
        try:
            res = self._client.auth.sign_up({"email": email, "password": password})
            if res.session:
                self._save_session(res.session)
                return True, ""
            return True, "confirm_email"
        except Exception as e:
            return False, str(e)

    def login_oauth(self, provider: str, on_done):
        """
        Open browser for OAuth. on_done(success: bool, error: str) called from background thread.
        Caller must marshal UI updates to main thread (via signal).
        """
        if not self._client:
            on_done(False, "Supabase is not configured")
            return

        result: dict = {"code": None}
        server_done = threading.Event()

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                params = parse_qs(urlparse(self.path).query)
                code = params.get("code", [None])[0]
                if code:
                    result["code"] = code
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"<html><body style='font-family:sans-serif;text-align:center;padding-top:80px'>"
                    b"<h2>&#10003; Login successful</h2>"
                    b"<p>You can return to LemaNotes.</p>"
                    b"<script>setTimeout(()=>window.close(),2000)</script>"
                    b"</body></html>"
                )
                server_done.set()

            def log_message(self, *_):
                pass

        try:
            srv = HTTPServer(("localhost", 54321), _Handler)
        except OSError as e:
            on_done(False, f"Port 54321 is already in use: {e}")
            return

        def _serve():
            while not server_done.is_set():
                srv.handle_request()
            srv.server_close()

        threading.Thread(target=_serve, daemon=True).start()

        try:
            res = self._client.auth.sign_in_with_oauth({
                "provider": provider,
                "options": {"redirect_to": "http://localhost:54321/callback"},
            })
            webbrowser.open(res.url)
        except Exception as e:
            on_done(False, str(e))
            server_done.set()
            return

        def _wait():
            server_done.wait(timeout=120)
            code = result.get("code")
            if code:
                try:
                    r = self._client.auth.exchange_code_for_session({"auth_code": code})
                    if r.session:
                        self._save_session(r.session)
                    on_done(True, "")
                except Exception as e:
                    on_done(False, str(e))
            else:
                on_done(False, "Login timed out or was cancelled")

        threading.Thread(target=_wait, daemon=True).start()

    def logout(self):
        if self._client:
            try:
                self._client.auth.sign_out()
            except Exception:
                pass
        _keyring_clear()
        s = load_settings()
        s.pop("supabase_session", None)
        save_settings(s)

    def _save_session(self, session):
        data = {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "user_email": session.user.email if session.user else None,
        }
        if not _keyring_save(data):
            # Keyring unavailable (headless / no daemon) — fall back to JSON.
            s = load_settings()
            s["supabase_session"] = data
            save_settings(s)

    # ── Sync operations ──────────────────────────────────────────────────────────

    def push_note(self, notebook: str, slug: str, section: str | None = None):
        if not self.is_logged_in():
            return
        note = storage.load_note(notebook, slug, section)
        if not note:
            return
        try:
            uid = self._client.auth.get_user().user.id
            now = datetime.now(timezone.utc).isoformat()
            self._client.table("notes").upsert({
                "user_id":   uid,
                "notebook":  notebook,
                "section":   section or "",
                "slug":      slug,
                "title":     note.get("title", ""),
                "content":   note.get("content", ""),
                "tags":      note.get("tags", []),
                "pinned":    note.get("pinned", False),
                "priority":  note.get("priority", 0),
                "created_at": note.get("created_at", now),
                "updated_at": note.get("updated_at", now),
                "is_deleted": False,
                "trashed_at": note.get("trashed_at"),
            }, on_conflict="user_id,notebook,section,slug").execute()
        except Exception as e:
            print(f"[Sync] push_note error: {e}")

    def delete_note_remote(self, notebook: str, slug: str, section: str | None = None):
        if not self.is_logged_in():
            return
        try:
            uid = self._client.auth.get_user().user.id
            (self._client.table("notes")
             .update({"is_deleted": True})
             .eq("user_id", uid)
             .eq("notebook", notebook)
             .eq("section", section or "")
             .eq("slug", slug)
             .execute())
        except Exception as e:
            print(f"[Sync] delete_note error: {e}")

    def trash_note_remote(self, notebook: str, slug: str,
                          section: str | None = None, trashed_at: str = "") -> None:
        """Mark a note as trashed in Supabase (sets trashed_at)."""
        if not self.is_logged_in():
            return
        try:
            from datetime import datetime, timezone
            uid = self._client.auth.get_user().user.id
            ts = trashed_at or datetime.now(timezone.utc).isoformat()
            (self._client.table("notes")
             .update({"trashed_at": ts})
             .eq("user_id", uid)
             .eq("notebook", notebook)
             .eq("section", section or "")
             .eq("slug", slug)
             .execute())
        except Exception as e:
            print(f"[Sync] trash_note error: {e}")

    def restore_note_remote(self, notebook: str, slug: str,
                            section: str | None = None) -> None:
        """Clear trashed_at in Supabase to restore a note."""
        if not self.is_logged_in():
            return
        try:
            uid = self._client.auth.get_user().user.id
            (self._client.table("notes")
             .update({"trashed_at": None})
             .eq("user_id", uid)
             .eq("notebook", notebook)
             .eq("section", section or "")
             .eq("slug", slug)
             .execute())
        except Exception as e:
            print(f"[Sync] restore_note error: {e}")

    def delete_section_remote(self, notebook: str, section: str) -> None:
        """Mark all notes in a section as permanently deleted in Supabase."""
        if not self.is_logged_in():
            return
        try:
            uid = self._client.auth.get_user().user.id
            (self._client.table("notes")
             .update({"is_deleted": True})
             .eq("user_id", uid)
             .eq("notebook", notebook)
             .eq("section", section)
             .execute())
        except Exception as e:
            print(f"[Sync] delete_section error: {e}")

    def delete_notebook_remote(self, notebook: str) -> None:
        """Mark all notes in a notebook as permanently deleted in Supabase."""
        if not self.is_logged_in():
            return
        try:
            uid = self._client.auth.get_user().user.id
            (self._client.table("notes")
             .update({"is_deleted": True})
             .eq("user_id", uid)
             .eq("notebook", notebook)
             .execute())
        except Exception as e:
            print(f"[Sync] delete_notebook error: {e}")

    def pull_all(self) -> tuple[int, str]:
        """Pull cloud notes newer than local.

        Returns (count_written, error_message).
        error_message is empty string on success.
        """
        self.retry_refresh_if_needed()
        if not self.is_logged_in():
            return 0, "Not logged in"
        try:
            session = self._client.auth.get_session()
            uid = session.user.id
            res = (self._client.table("notes")
                   .select("*")
                   .eq("user_id", uid)
                   .eq("is_deleted", False)
                   .execute())
            count = 0
            for row in res.data:
                nb   = row["notebook"]
                sec  = row["section"] or None
                slug = row["slug"]

                if nb not in storage.list_notebooks():
                    storage.create_notebook(nb)
                if sec and sec not in storage.list_sections(nb):
                    storage.create_section(nb, sec)

                existing  = storage.load_note(nb, slug, sec)
                remote_ts = row.get("updated_at", "")
                local_ts  = existing.get("updated_at", "") if existing else ""

                remote_trashed = row.get("trashed_at")

                # If remote marks note as trashed and local copy is active, trash it locally
                if remote_trashed and existing and not existing.get("trashed_at"):
                    storage.trash_note(nb, slug, sec)
                    count += 1
                    continue

                # Skip notes that are trashed on remote (don't recreate them locally)
                if remote_trashed:
                    continue

                if not existing or remote_ts > local_ts:
                    base = storage._base_path(nb, sec)
                    base.mkdir(parents=True, exist_ok=True)
                    storage._md_path(nb, slug, sec).write_text(
                        row.get("content", ""), encoding="utf-8"
                    )
                    meta = {
                        "title":      row["title"],
                        "tags":       row.get("tags", []),
                        "pinned":     row.get("pinned", False),
                        "priority":   row.get("priority", 0),
                        "created_at": row.get("created_at", ""),
                        "updated_at": row.get("updated_at", ""),
                    }
                    storage._meta_path(nb, slug, sec).write_text(
                        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
                    )
                    count += 1
            return count, ""
        except Exception as e:
            return 0, str(e)

    def push_all(self) -> str:
        """Push all local notes (active + trashed) to cloud. Returns error string or empty."""
        self.retry_refresh_if_needed()
        if not self.is_logged_in():
            return "Not logged in"
        try:
            for nb in storage._all_notebook_dirs():
                for note in storage.list_notes(nb, include_trashed=True):
                    self.push_note(nb, note["slug"])
                for sec in storage._all_section_dirs(nb):
                    for note in storage.list_notes(nb, sec, include_trashed=True):
                        self.push_note(nb, note["slug"], sec)
            return ""
        except Exception as e:
            return str(e)

    def upload_attachment(self, notebook: str, slug: str, section: str | None,
                          file_path) -> str:
        """Upload a local attachment file to Supabase Storage.

        Returns the public URL on success, or empty string on failure.
        """
        from pathlib import Path as _Path
        if not self.is_logged_in() or not self._client:
            return ""
        try:
            file_path = _Path(file_path)
            # Storage path: <user_id>/<notebook>[/<section>]/<slug>/<filename>
            user_id = self._client.auth.get_user().user.id
            parts = [user_id, notebook]
            if section:
                parts.append(section)
            parts += [slug, file_path.name]
            storage_path = "/".join(parts)
            with open(file_path, "rb") as f:
                data = f.read()
            mime = _guess_mime(file_path.suffix)
            self._client.storage.from_("note-attachments").upload(
                storage_path, data,
                {"content-type": mime, "upsert": "true"},
            )
            public = self._client.storage.from_("note-attachments").get_public_url(storage_path)
            return public
        except Exception:
            return ""


def _guess_mime(suffix: str) -> str:
    return {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
    }.get(suffix.lower(), "application/octet-stream")


sync_manager = SyncManager()
