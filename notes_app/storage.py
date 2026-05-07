"""
Storage layer: folder-based .md files + JSON metadata sidecar per note.
Structure:
  ~/LemaNotes/
    <notebook_name>/
      <note_slug>.md              ← note at notebook root (section=None)
      <note_slug>.meta.json
      <section_name>/
        <note_slug>.md            ← note inside a section
        <note_slug>.meta.json
"""

import json
import re
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path


NOTES_ROOT = Path.home() / "LemaNotes"


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text[:64] or "untitled"


def ensure_root():
    NOTES_ROOT.mkdir(parents=True, exist_ok=True)


def _base_path(notebook: str, section: str | None) -> Path:
    if section:
        return NOTES_ROOT / notebook / section
    return NOTES_ROOT / notebook


def _meta_path(notebook: str, slug: str, section: str | None = None) -> Path:
    return _base_path(notebook, section) / f"{slug}.meta.json"


def _md_path(notebook: str, slug: str, section: str | None = None) -> Path:
    return _base_path(notebook, section) / f"{slug}.md"


def _load_meta(notebook: str, slug: str, section: str | None = None) -> dict:
    mp = _meta_path(notebook, slug, section)
    if mp.exists():
        with open(mp, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_meta(notebook: str, slug: str, meta: dict, section: str | None = None):
    mp = _meta_path(notebook, slug, section)
    with open(mp, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


# ─── Notebooks ────────────────────────────────────────────────────────────────

def _has_active_note_in_dir(path: Path) -> bool:
    """Return True if `path` contains at least one .md with no trashed_at."""
    for md in path.glob("*.md"):
        meta_p = md.with_suffix(".meta.json")
        try:
            if meta_p.exists() and json.loads(meta_p.read_text()).get("trashed_at"):
                continue
        except Exception:
            pass
        return True
    return False


def list_notebooks() -> list[str]:
    ensure_root()
    return sorted(
        d.name for d in NOTES_ROOT.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def create_notebook(name: str) -> bool:
    nb_path = NOTES_ROOT / name
    if nb_path.exists():
        return False
    nb_path.mkdir(parents=True)
    return True


def rename_notebook(old_name: str, new_name: str) -> bool:
    old_path = NOTES_ROOT / old_name
    new_path = NOTES_ROOT / new_name
    if not old_path.exists() or new_path.exists():
        return False
    old_path.rename(new_path)
    return True


def delete_notebook(name: str) -> bool:
    nb_path = NOTES_ROOT / name
    if not nb_path.exists():
        return False
    shutil.rmtree(nb_path)
    return True


# ─── Sections ─────────────────────────────────────────────────────────────────

def list_sections(notebook: str) -> list[str]:
    nb_path = NOTES_ROOT / notebook
    if not nb_path.exists():
        return []
    return sorted(
        d.name for d in nb_path.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    )


def create_section(notebook: str, name: str) -> bool:
    sec_path = NOTES_ROOT / notebook / name
    if sec_path.exists():
        return False
    sec_path.mkdir(parents=True)
    return True


def rename_section(notebook: str, old: str, new: str) -> bool:
    old_path = NOTES_ROOT / notebook / old
    new_path = NOTES_ROOT / notebook / new
    if not old_path.exists() or new_path.exists():
        return False
    old_path.rename(new_path)
    return True


def delete_section(notebook: str, section: str) -> bool:
    sec_path = NOTES_ROOT / notebook / section
    if not sec_path.exists():
        return False
    shutil.rmtree(sec_path)
    return True


# ─── Notes ────────────────────────────────────────────────────────────────────

def list_notes(notebook: str, section: str | None = None,
               include_trashed: bool = False) -> list[dict]:
    base = _base_path(notebook, section)
    if not base.exists():
        return []
    notes = []
    for md_file in sorted(base.glob("*.md")):
        slug = md_file.stem
        meta = _load_meta(notebook, slug, section)
        if not include_trashed and meta.get("trashed_at"):
            continue
        notes.append({
            "slug":       slug,
            "notebook":   notebook,
            "section":    section,
            "title":      meta.get("title", slug),
            "tags":       meta.get("tags", []),
            "created_at": meta.get("created_at", ""),
            "updated_at": meta.get("updated_at", ""),
            "pinned":     meta.get("pinned", False),
            "priority":   meta.get("priority", 0),
            "trashed_at": meta.get("trashed_at"),
        })
    return sorted(notes, key=lambda n: n["updated_at"], reverse=True)


def create_note(notebook: str, title: str, content: str = "",
                tags: list[str] = None,
                section: str | None = None) -> dict:
    slug = slugify(title)
    base_slug = slug
    counter = 1
    while _md_path(notebook, slug, section).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    _base_path(notebook, section).mkdir(parents=True, exist_ok=True)

    now = datetime.now().isoformat()
    meta = {
        "title":      title,
        "tags":       tags or [],
        "created_at": now,
        "updated_at": now,
    }
    with open(_md_path(notebook, slug, section), "w", encoding="utf-8") as f:
        f.write(content)
    _save_meta(notebook, slug, meta, section)
    return {"slug": slug, "notebook": notebook, "section": section, **meta}


def load_note(notebook: str, slug: str,
              section: str | None = None) -> dict | None:
    md_file = _md_path(notebook, slug, section)
    if not md_file.exists():
        return None
    meta = _load_meta(notebook, slug, section)
    with open(md_file, "r", encoding="utf-8") as f:
        content = f.read()
    return {
        "slug": slug, "notebook": notebook, "section": section,
        "content": content, **meta,
    }


def rename_note(notebook: str, slug: str, new_title: str,
                section: str | None = None) -> bool:
    if not _md_path(notebook, slug, section).exists():
        return False
    meta = _load_meta(notebook, slug, section)
    meta["title"] = new_title
    meta["updated_at"] = datetime.now().isoformat()
    _save_meta(notebook, slug, meta, section)
    return True


def save_note(notebook: str, slug: str, content: str,
              title: str = None, tags: list[str] = None,
              section: str | None = None) -> bool:
    md_file = _md_path(notebook, slug, section)
    if not md_file.exists():
        return False
    meta = _load_meta(notebook, slug, section)
    if title is not None:
        meta["title"] = title
    if tags is not None:
        meta["tags"] = tags
    meta["updated_at"] = datetime.now().isoformat()
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(content)
    _save_meta(notebook, slug, meta, section)
    return True


def move_note(src_notebook: str, slug: str, dst_notebook: str,
              src_section: str | None = None,
              dst_section: str | None = None) -> bool:
    src_md   = _md_path(src_notebook, slug, src_section)
    src_meta = _meta_path(src_notebook, slug, src_section)
    if not src_md.exists():
        return False
    dst_slug  = slug
    base_slug = slug
    counter   = 1
    while _md_path(dst_notebook, dst_slug, dst_section).exists():
        dst_slug = f"{base_slug}-{counter}"
        counter += 1
    _base_path(dst_notebook, dst_section).mkdir(parents=True, exist_ok=True)
    src_md.rename(_md_path(dst_notebook, dst_slug, dst_section))
    if src_meta.exists():
        src_meta.rename(_meta_path(dst_notebook, dst_slug, dst_section))
    return True


def delete_note(notebook: str, slug: str,
                section: str | None = None) -> bool:
    md_file = _md_path(notebook, slug, section)
    mp      = _meta_path(notebook, slug, section)
    if not md_file.exists():
        return False
    md_file.unlink()
    if mp.exists():
        mp.unlink()
    return True


# ─── Trash ────────────────────────────────────────────────────────────────────

TRASH_TTL_DAYS = 7


def trash_note(notebook: str, slug: str, section: str | None = None) -> bool:
    """Soft-delete: mark note with trashed_at timestamp."""
    meta = _load_meta(notebook, slug, section)
    if not meta and not _md_path(notebook, slug, section).exists():
        return False
    meta["trashed_at"] = datetime.now(timezone.utc).isoformat()
    _save_meta(notebook, slug, meta, section)
    return True


def restore_note(notebook: str, slug: str, section: str | None = None) -> bool:
    """Remove trashed_at to bring a note back from trash."""
    meta = _load_meta(notebook, slug, section)
    if "trashed_at" not in meta:
        return False
    meta.pop("trashed_at")
    _save_meta(notebook, slug, meta, section)
    return True


def purge_note(notebook: str, slug: str, section: str | None = None) -> bool:
    """Permanently delete a note's files from disk."""
    md = _md_path(notebook, slug, section)
    mt = _meta_path(notebook, slug, section)
    if not md.exists():
        return False
    md.unlink()
    if mt.exists():
        mt.unlink()
    return True


def list_trash() -> list[dict]:
    """Return all notes that have a trashed_at timestamp, newest-trashed first."""
    result = []
    for nb in _all_notebook_dirs():
        for note in list_notes(nb, include_trashed=True):
            if note.get("trashed_at"):
                result.append(note)
        for sec in _all_section_dirs(nb):
            for note in list_notes(nb, sec, include_trashed=True):
                if note.get("trashed_at"):
                    result.append(note)
    return sorted(result, key=lambda n: n.get("trashed_at", ""), reverse=True)


def cleanup_expired_trash(days: int = TRASH_TTL_DAYS) -> int:
    """Permanently purge notes trashed more than `days` ago. Returns count."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    count = 0
    for note in list_trash():
        try:
            ts = datetime.fromisoformat(note["trashed_at"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts < cutoff:
                purge_note(note["notebook"], note["slug"], note.get("section"))
                count += 1
        except Exception:
            pass
    return count


def trash_section(notebook: str, section: str) -> list[dict]:
    """Trash all notes in a section. Returns list of trashed note dicts."""
    trashed = []
    for note in list_notes(notebook, section):
        if trash_note(notebook, note["slug"], section):
            trashed.append(note)
    return trashed


def trash_notebook(notebook: str) -> list[dict]:
    """Trash all notes in a notebook (root + all sections). Returns list of trashed note dicts."""
    trashed = []
    for note in list_notes(notebook):
        if trash_note(notebook, note["slug"]):
            trashed.append(note)
    for sec in _all_section_dirs(notebook):
        trashed.extend(trash_section(notebook, sec))
    return trashed


def _all_notebook_dirs() -> list[str]:
    ensure_root()
    return sorted(d.name for d in NOTES_ROOT.iterdir()
                  if d.is_dir() and not d.name.startswith("."))


def _all_section_dirs(notebook: str) -> list[str]:
    nb_path = NOTES_ROOT / notebook
    if not nb_path.exists():
        return []
    return sorted(d.name for d in nb_path.iterdir()
                  if d.is_dir() and not d.name.startswith("."))


# ─── Pin & Priority ───────────────────────────────────────────────────────────

def toggle_pin(notebook: str, slug: str, section: str | None = None) -> bool:
    if not _md_path(notebook, slug, section).exists():
        return False
    meta = _load_meta(notebook, slug, section)
    meta["pinned"] = not meta.get("pinned", False)
    _save_meta(notebook, slug, meta, section)
    return meta["pinned"]


def set_priority(notebook: str, slug: str, priority: int,
                 section: str | None = None) -> bool:
    if not _md_path(notebook, slug, section).exists():
        return False
    meta = _load_meta(notebook, slug, section)
    meta["priority"] = max(0, min(3, priority))
    _save_meta(notebook, slug, meta, section)
    return True


# ─── Search ───────────────────────────────────────────────────────────────────

def _search_in(nb: str, section: str | None, query_lower: str) -> list[dict]:
    results = []
    for note in list_notes(nb, section):
        note_data = load_note(nb, note["slug"], section)
        if not note_data:
            continue
        content_lower = note_data["content"].lower()
        title_lower   = note_data["title"].lower()
        tags_lower    = [t.lower() for t in note_data.get("tags", [])]
        if (query_lower in title_lower or
                query_lower in content_lower or
                any(query_lower in t for t in tags_lower)):
            idx     = content_lower.find(query_lower)
            snippet = ""
            if idx >= 0:
                start   = max(0, idx - 40)
                end     = min(len(note_data["content"]), idx + 80)
                snippet = "..." + note_data["content"][start:end].strip() + "..."
            results.append({**note, "snippet": snippet})
    return results


def search_notes(query: str, notebook: str = None) -> list[dict]:
    query_lower = query.lower()
    results     = []
    notebooks   = [notebook] if notebook else list_notebooks()
    for nb in notebooks:
        results.extend(_search_in(nb, None, query_lower))
        for sec in list_sections(nb):
            results.extend(_search_in(nb, sec, query_lower))
    return results


def get_all_tags() -> list[str]:
    tags = set()
    for nb in list_notebooks():
        for note in list_notes(nb):
            tags.update(note.get("tags", []))
        for sec in list_sections(nb):
            for note in list_notes(nb, sec):
                tags.update(note.get("tags", []))
    return sorted(tags)


def remove_tag_from_all(tag: str) -> int:
    """Remove a tag from every note that has it. Returns count of modified notes."""
    count = 0
    for nb in list_notebooks():
        for note in list_notes(nb):
            if tag in note.get("tags", []):
                meta = _load_meta(nb, note["slug"])
                meta["tags"] = [t for t in meta.get("tags", []) if t != tag]
                meta["updated_at"] = datetime.now().isoformat()
                _save_meta(nb, note["slug"], meta)
                count += 1
        for sec in list_sections(nb):
            for note in list_notes(nb, sec):
                if tag in note.get("tags", []):
                    meta = _load_meta(nb, note["slug"], sec)
                    meta["tags"] = [t for t in meta.get("tags", []) if t != tag]
                    meta["updated_at"] = datetime.now().isoformat()
                    _save_meta(nb, note["slug"], meta, sec)
                    count += 1
    return count


def filter_by_tag(tag: str) -> list[dict]:
    tag_lower = tag.lower()
    results   = []
    for nb in list_notebooks():
        for note in list_notes(nb):
            if any(t.lower() == tag_lower for t in note.get("tags", [])):
                results.append(note)
        for sec in list_sections(nb):
            for note in list_notes(nb, sec):
                if any(t.lower() == tag_lower for t in note.get("tags", [])):
                    results.append(note)
    return sorted(results, key=lambda n: n["updated_at"], reverse=True)
