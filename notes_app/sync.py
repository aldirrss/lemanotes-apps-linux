"""Supabase sync manager — offline-first, auto-sync when logged in."""

import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import webbrowser

from notes_app.settings import load_settings, save_settings
from notes_app import storage


class SyncManager:
    def __init__(self):
        self._client = None
        self._ready = False
        self._load_config()

    # ── Config / init ────────────────────────────────────────────────────────────

    def _load_config(self):
        s = load_settings()
        url = s.get("supabase_url", "")
        key = s.get("supabase_key", "")
        if url and key:
            self._init_client(url, key, s.get("supabase_session"))

    def _init_client(self, url: str, key: str, session_data: dict | None = None):
        try:
            from supabase import create_client
            self._client = create_client(url, key)
            if session_data:
                try:
                    self._client.auth.set_session(
                        session_data["access_token"],
                        session_data["refresh_token"],
                    )
                except Exception:
                    pass
            self._ready = True
        except Exception:
            self._ready = False

    def configure(self, url: str, key: str) -> tuple[bool, str]:
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

    def is_logged_in(self) -> bool:
        if not self._client:
            return False
        try:
            user = self._client.auth.get_user()
            return user is not None and user.user is not None
        except Exception:
            return False

    def get_user_email(self) -> str | None:
        if not self._client:
            return None
        try:
            user = self._client.auth.get_user()
            return user.user.email if user and user.user else None
        except Exception:
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
        s = load_settings()
        s.pop("supabase_session", None)
        save_settings(s)

    def _save_session(self, session):
        s = load_settings()
        s["supabase_session"] = {
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
        }
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

    def pull_all(self) -> int:
        """Pull cloud notes newer than local. Returns count of notes written."""
        if not self.is_logged_in():
            return 0
        try:
            uid = self._client.auth.get_user().user.id
            res = (self._client.table("notes")
                   .select("*")
                   .eq("user_id", uid)
                   .eq("is_deleted", False)
                   .execute())
            count = 0
            for row in res.data:
                nb  = row["notebook"]
                sec = row["section"] or None
                slug = row["slug"]

                if nb not in storage.list_notebooks():
                    storage.create_notebook(nb)
                if sec and sec not in storage.list_sections(nb):
                    storage.create_section(nb, sec)

                existing = storage.load_note(nb, slug, sec)
                remote_ts = row.get("updated_at", "")
                local_ts  = existing.get("updated_at", "") if existing else ""

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
            return count
        except Exception as e:
            print(f"[Sync] pull_all error: {e}")
            return 0

    def push_all(self):
        """Push all local notes to cloud."""
        if not self.is_logged_in():
            return
        for nb in storage.list_notebooks():
            for note in storage.list_notes(nb):
                self.push_note(nb, note["slug"])
            for sec in storage.list_sections(nb):
                for note in storage.list_notes(nb, sec):
                    self.push_note(nb, note["slug"], sec)


sync_manager = SyncManager()
