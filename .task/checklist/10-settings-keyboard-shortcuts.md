# Feature: Settings — Keyboard Shortcut Dictionary & Toggle

## Status: TODO

## Goal
Tambahkan panel "Shortcuts" di `SettingsDialog` yang menampilkan seluruh
keyboard shortcut yang tersedia dalam bentuk tabel, lengkap dengan toggle
untuk mengaktifkan / menonaktifkan shortcut tertentu per-kategori.

---

## Checklist

### Data Layer (`settings.py`)
- [ ] Tambah `"disabled_shortcuts": []` ke `_DEFAULTS`
  — list berisi nama shortcut yang dinonaktifkan (e.g. `["Ctrl+K", "Ctrl+H"]`)
- [ ] `load_settings()` / `save_settings()` sudah ada, cukup tambah key baru

### Shortcut Registry (`main_window.py`)
- [ ] Definisikan `SHORTCUTS` dict/list di level modul — satu sumber kebenaran:
  ```
  [
    {"key": "Ctrl+B",       "label": "Bold",              "category": "Format"},
    {"key": "Ctrl+I",       "label": "Italic",            "category": "Format"},
    {"key": "Ctrl+Shift+S", "label": "Strikethrough",     "category": "Format"},
    {"key": "Ctrl+Shift+H", "label": "Highlight",         "category": "Format"},
    {"key": "Ctrl+K",       "label": "Insert Link",       "category": "Insert"},
    {"key": "Ctrl+Shift+I", "label": "Insert Image",      "category": "Insert"},
    {"key": "Ctrl+Shift+C", "label": "Insert Code Block", "category": "Insert"},
    {"key": "Ctrl+F",       "label": "Find",              "category": "Find"},
    {"key": "Ctrl+H",       "label": "Find & Replace",    "category": "Find"},
    {"key": "Ctrl+Z",       "label": "Undo",              "category": "Edit"},
    {"key": "Ctrl+Shift+Z", "label": "Redo",              "category": "Edit"},
    {"key": "Ctrl+N",       "label": "New Note",          "category": "App"},
    {"key": "Ctrl+Shift+N", "label": "New Notebook",      "category": "App"},
    {"key": "Ctrl+E",       "label": "Export PDF",        "category": "App"},
    {"key": "Ctrl+,",       "label": "Settings",          "category": "App"},
    {"key": "Ctrl+Shift+D", "label": "Cycle Theme",       "category": "App"},
  ]
  ```
- [ ] `EditorPanel._register_shortcuts(disabled: list[str])` — buat semua
  `QShortcut` dari `SHORTCUTS`, skip yang ada di `disabled`
- [ ] `EditorPanel.apply_shortcuts(disabled: list[str])` — hapus shortcut lama,
  buat ulang dengan daftar disabled baru (tanpa restart)
- [ ] `MainWindow._register_menu_shortcuts(disabled: list[str])` — sama untuk
  shortcut di menu (Ctrl+N, Ctrl+E, dll.)

### SettingsDialog — Tab / Panel Shortcuts
- [ ] `SettingsDialog` jadi multi-section menggunakan `QTabWidget` atau
  `QStackedWidget` + sidebar list:
  - Tab 1: **Appearance** (theme combo + font size — sudah ada)
  - Tab 2: **Shortcuts**
- [ ] Tab Shortcuts menampilkan `QTreeWidget` dengan kolom:
  | # | Category | Action | Shortcut | Enabled |
- [ ] Kolom **Enabled**: `QCheckBox` per baris, default checked
- [ ] Group by category (category sebagai parent node, tidak bisa di-toggle)
- [ ] Checkbox dinonaktifkan untuk shortcut yang tidak boleh dimatikan
  (bebas tentukan mana yang "wajib", e.g. Ctrl+Z Undo)
- [ ] Live preview: unchecking langsung menonaktifkan shortcut di app
- [ ] Cancel: revert ke state sebelum dialog dibuka
- [ ] OK: simpan `disabled_shortcuts` ke settings.json

### Integrasi saat startup
- [ ] `MainWindow.__init__` load `disabled_shortcuts` dari settings
- [ ] Teruskan ke `editor_panel.apply_shortcuts(disabled)` dan
  `_register_menu_shortcuts(disabled)` saat startup

### Edge Cases
- [ ] Shortcut yang dinonaktifkan tidak muncul sebagai konflik dengan shortcut lain
- [ ] Jika settings.json tidak punya `disabled_shortcuts` key → semua aktif
- [ ] Shortcut `Ctrl+,` (Settings) tidak bisa dinonaktifkan (selalu enabled)
- [ ] Mengaktifkan kembali shortcut yang sebelumnya disabled langsung efektif
