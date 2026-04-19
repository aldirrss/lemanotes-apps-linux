# Feature: Bookmark (Priority), Filter & Sort

## Status: TODO

## Goal
Tambahkan sistem bookmark/priority pada note, filter cepat berdasarkan
bookmark/tag, dan kontrol urutan tampilan untuk notebook (sidebar) maupun
note list — semuanya persisten di settings.

---

## Checklist

### Data Layer (`storage.py`)
- [ ] Tambah field `"pinned": false` dan `"priority": 0` ke `.meta.json`
  - `pinned`: bool — note dipin ke atas list
  - `priority`: int 0–3 (0=normal, 1=low, 2=medium, 3=high)
- [ ] `toggle_pin(notebook, slug, section=None)` → bool baru
- [ ] `set_priority(notebook, slug, priority, section=None)` → bool
- [ ] `list_notes()` kembalikan field `pinned` dan `priority`
- [ ] Default `pinned=False`, `priority=0` jika field tidak ada di meta

### Settings (`settings.py`)
- [ ] Tambah ke `_DEFAULTS`:
  ```json
  {
    "note_sort":     "updated_desc",
    "notebook_sort": "name_asc",
    "filter_pinned": false
  }
  ```
- [ ] `note_sort` options: `"updated_desc"`, `"updated_asc"`, `"title_asc"`,
  `"title_desc"`, `"priority_desc"`, `"created_desc"`
- [ ] `notebook_sort` options: `"name_asc"`, `"name_desc"`, `"manual"`
  (manual = urutan drag-and-drop, disimpan sebagai list di settings)

### NoteListPanel — Sort & Filter UI
- [ ] Tambah sort/filter bar di bawah search bar:
  - Tombol **★ Pinned** (toggle filter: tampilkan hanya note ter-pin)
  - Tombol **↕ Sort** → `QMenu` dengan opsi sort
- [ ] `_sort_order: str` state, default dari settings
- [ ] `_filter_pinned: bool` state, default dari settings
- [ ] `_apply_sort_filter(notes)` — terapkan sort + pin-first + filter ke list
  - Note pinned selalu di atas, sorted by priority desc, lalu by sort_order
- [ ] Save perubahan sort/filter ke settings.json saat berubah
- [ ] Sort menu options:
  - Updated (newest first) ✓ default
  - Updated (oldest first)
  - Title A→Z
  - Title Z→A
  - Priority (highest first)
  - Created (newest first)

### Note Card — Pin & Priority Indicator
- [ ] Pin indicator: ikon 📌 kecil di kanan atas card jika `pinned=True`
- [ ] Priority badge warna di kiri card:
  - 0 = tidak ada badge
  - 1 = kuning (low)
  - 2 = oranye (medium)
  - 3 = merah (high)
- [ ] Context menu note list: tambah item:
  - **Pin / Unpin** (toggle)
  - **Priority** → sub-menu: None / Low / Medium / High

### SidebarPanel — Notebook Sort
- [ ] Tambah tombol `↕` kecil di header sidebar notebook section
- [ ] `QMenu`: Sort A→Z, Sort Z→A, Manual (drag order)
- [ ] Untuk manual sort: simpan urutan notebook ke `settings["notebook_order"]`
- [ ] `load_notebooks()` menghormati urutan dari settings jika mode manual

### EditorPanel — Bookmark Button
- [ ] Tambah tombol 🔖 / ★ di top-bar sebelah kanan judul
- [ ] Klik toggle `pinned` state → simpan langsung via `storage.toggle_pin()`
- [ ] Icon berubah (filled ★ jika pinned, outline ☆ jika tidak)
- [ ] Update tampilan card di NoteListPanel setelah toggle

### Filter Pinned di Sidebar (opsional, nice-to-have)
- [ ] Di sidebar tags section, tambah item khusus **★ Pinned Notes**
- [ ] Klik → NoteListPanel filter hanya note pinned lintas semua notebook

### Integrasi
- [ ] `_on_note_saved` di MainWindow refresh note list agar pin/priority update
- [ ] `load_note()` di EditorPanel set state tombol pin sesuai note yang dibuka
- [ ] Saat note pinned/unpinned, NoteListPanel.refresh() dipanggil

### Edge Cases
- [ ] Note baru default: `pinned=False`, `priority=0`
- [ ] Sort + filter_pinned berjalan bersamaan (filter dulu, baru sort)
- [ ] `filter_pinned=True` + tidak ada note pinned → tampilkan empty state
- [ ] Priority badge tidak muncul jika tidak ada note yang memakai priority
- [ ] Notebook sort manual persisten antar restart
