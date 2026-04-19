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
from datetime import datetime
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

def list_notes(notebook: str, section: str | None = None) -> list[dict]:
    base = _base_path(notebook, section)
    if not base.exists():
        return []
    notes = []
    for md_file in sorted(base.glob("*.md")):
        slug = md_file.stem
        meta = _load_meta(notebook, slug, section)
        notes.append({
            "slug":       slug,
            "notebook":   notebook,
            "section":    section,
            "title":      meta.get("title", slug),
            "tags":       meta.get("tags", []),
            "created_at": meta.get("created_at", ""),
            "updated_at": meta.get("updated_at", ""),
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
