# Feature: Nested Folders (2 Levels)

## Status: DONE ✅

## Goal
Tambahkan dukungan sub-folder satu tingkat di dalam notebook (maksimal 2 level:
Notebook → Section). Note tetap tersimpan sebagai file `.md` + `.meta.json`,
hanya diorganisir dalam sub-direktori di dalam notebook.

---

## Checklist

### Data Layer (`storage.py`)
- [ ] Struktur direktori: `~/NotesUp/<notebook>/<section>/<slug>.md`
  - Notes di root notebook (tanpa section) tetap didukung
  - Section adalah sub-direktori langsung di dalam notebook (tidak rekursif)
- [ ] `list_sections(notebook)` → `sorted(list[str])` — scan sub-dir bukan `.attachments`
- [ ] `create_section(notebook, name)` → bool
- [ ] `rename_section(notebook, old, new)` → bool
- [ ] `delete_section(notebook, section)` → bool (rekursif hapus isi)
- [ ] `list_notes(notebook, section=None)` — update: jika `section=None` kembalikan
  notes di root notebook saja; jika `section` diisi kembalikan notes di sub-dir tersebut
- [ ] `create_note(notebook, title, ..., section=None)` — tulis ke sub-dir jika section diisi
- [ ] `load_note`, `save_note`, `delete_note`, `move_note` — semua terima `section=None`
  parameter untuk path resolution
- [ ] `_md_path` / `_meta_path` — update untuk mendukung optional section
- [ ] `search_notes` — scan root + semua sections

### SidebarPanel — Tampilan Bertingkat
- [ ] Ganti `NotebookListWidget (QListWidget)` dengan `QTreeWidget` bernama `_tree`
- [ ] Level 0 item: notebook (ikon 📁, bold)
- [ ] Level 1 item: section di bawah notebook (ikon 📄, indent)
- [ ] Notebook yang tidak punya section langsung bisa dipilih untuk melihat note di root-nya
- [ ] Expand/collapse notebook node dengan klik panah atau double-click
- [ ] `SidebarPanel.load_notebooks()` → rebuild tree (notebook + sections)
- [ ] Signal `notebook_selected(notebook, section_or_None)` — update signature
- [ ] Context menu pada notebook: Rename, Delete, **Add Section**
- [ ] Context menu pada section: Rename, Delete
- [ ] Drag-and-drop note ke section (update `_NOTE_MIME` handling)

### NoteListPanel
- [ ] Update `load_notes(notebook, section=None)` — pass section ke `storage.list_notes()`
- [ ] Judul panel: `"<Notebook>"` jika root, `"<Notebook> / <Section>"` jika di section
- [ ] Note card tetap sama

### EditorPanel
- [ ] `load_note(notebook, slug, section=None)` — teruskan section ke storage
- [ ] `_auto_save` / `_do_save` — sertakan section
- [ ] Attachment dir: `~/NotesUp/<nb>/<section>/.attachments/<slug>/` jika ada section

### MainWindow
- [ ] `_on_notebook_selected(notebook, section)` — update handler
- [ ] `_create_note()` — sertakan section aktif saat ini
- [ ] `_delete_note(notebook, slug, section)` — update
- [ ] `_on_note_moved` — update untuk mendukung move ke notebook/section lain
- [ ] Simpan state `_current_section` selain `_current_notebook`

### Drag & Drop
- [ ] `_NOTE_MIME` payload: `"<nb>\x00<section_or_empty>\x00<slug>"`
- [ ] `NotebookListWidget` (sekarang tree) terima drop ke section node maupun notebook node
- [ ] Drop ke notebook root → `section=None`

### Edge Cases
- [ ] Rename section: update path semua notes di dalamnya (rename dir)
- [ ] Delete section yang berisi notes → konfirmasi dialog
- [ ] Nama section tidak boleh dimulai dengan `.`
- [ ] Move note antar section dalam notebook yang sama tetap didukung
- [ ] `search_notes` tetap mencari di semua sections
- [ ] Tag filter di sidebar tetap bekerja lintas section
