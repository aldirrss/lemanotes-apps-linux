# Feature: Dark / Light Theme Toggle

## Status: DONE ✅

## Goal
Add a toggle button (or menu action) to switch between dark and light themes.
Both the Qt widgets (sidebar, note list, top bar) and the WYSIWYG editor
(TUI Editor inside QWebEngineView) must update together.

---

## Checklist

### Theme Definition
- [x] Define two theme dicts in `THEMES` at top of `main_window.py`:
  - Dark: bg #0D1B22, accent #7FDBCA, text #C8DDE8 …
  - Light: bg #F5F7FA, accent #1A7A6A, text #1A2B35 …

### Qt Widget Stylesheets
- [x] `TagPill.apply_theme(t)` — updates pill bg/fg from theme dict
- [x] `TagBar.apply_theme(t)` — propagates to input + pills
- [x] `SidebarPanel.apply_theme(t)` — rebuilds all widget stylesheets;
  calls `refresh_tags()` which uses `self._theme` for tag button colors
- [x] `NoteListPanel.apply_theme(t)` — rebuilds toolbar, search, list stylesheets;
  re-renders note cards with themed colors via `_make_note_card()`
- [x] `EditorPanel.apply_theme(t, name)` — rebuilds topbar/tag_wrap/fmt_toolbar;
  calls `set_theme(name)` if editor is ready
- [x] `MainWindow._apply_theme(name)` — orchestrates all panels, updates menubar/statusbar/splitter

### WYSIWYG Editor Theme (editor.html)
- [x] CSS rewritten to use CSS custom properties (`--bg`, `--text`, `--accent`, etc.) on `:root`
- [x] All color rules use `var(--bg)` etc.
- [x] `window.setTheme(name)` JS function: updates `:root` CSS variables from `THEMES` dict
- [x] Light palette defined in `THEMES.light` JS object

### EditorPanel bridge
- [x] `EditorPanel.set_theme(name)` — runs `setTheme(name)` via `runJavaScript`
- [x] `EditorPanel._on_editor_ready()` calls `set_theme(self._theme_name)` to sync on load

### UI — Toggle control
- [x] ☀/🌙 icon button in `SidebarPanel` header (next to `+` notebook button)
- [x] Emits `theme_toggle_requested` signal → `MainWindow._toggle_theme()`
- [x] `View > Toggle Theme` menu action with `Ctrl+Shift+D` shortcut

### Persistence
- [x] `notes_app/settings.py` — `load_settings()` / `save_settings()` (JSON read/write)
- [x] Theme saved to `~/.config/notesup/settings.json` on each change
- [x] Theme loaded from settings on startup (fallback to `"dark"`)

### Edge Cases
- [x] `setTheme` called on `editor_ready` to sync editor when app starts with saved theme
- [x] New notes created in light theme open in light theme (EditorPanel stores `_theme_name`)
- [x] Theme persists across app restarts
