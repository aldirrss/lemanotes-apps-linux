# Feature: Custom Themes & Font Size Setting

## Status: DONE ✅

## Goal
Let users choose a color theme (Dark / Light / Sepia) and adjust editor font size from a Settings dialog.

## Checklist

### Settings Storage
- [ ] Create `settings.py` with `load_settings()` / `save_settings()` using `~/.config/notesup/settings.json`
- [ ] Schema: `{ "theme": "dark", "font_size": 14 }`
- [ ] Provide defaults if file missing

### Theme System
- [ ] Define theme palettes as dicts in `settings.py`:
  - `dark`: current hardcoded colors (`#0D1B22`, `#7FDBCA`, `#C8DDE8`)
  - `light`: white/gray background, dark text
  - `sepia`: `#F4ECD8` background, `#5B4636` text
- [ ] Refactor all hardcoded color strings in `main_window.py` to read from active theme dict
- [ ] Add `apply_theme(theme_name)` function that rebuilds stylesheets for all panels
- [ ] Update `PREVIEW_CSS` dynamically based on active theme

### Font Size
- [ ] Read `font_size` from settings and apply to `EditorPanel.editor` stylesheet
- [ ] Changing font size re-applies only the editor stylesheet (no full reload needed)

### Settings Dialog
- [ ] Add `SettingsDialog(QDialog)` in `main_window.py`
  - Theme selector: `QComboBox` with options Dark / Light / Sepia
  - Font size: `QSpinBox` range 10–24, step 1
  - OK / Cancel buttons
- [ ] Preview changes live as user adjusts (apply on change, revert on Cancel)
- [ ] Add "Settings…" action to `View` menu with shortcut `Ctrl+,`

### Edge Cases
- [ ] Settings saved on OK, reverted on Cancel
- [ ] Settings loaded on app startup before UI is built
- [ ] Remove `Ctrl+Shift+D` dark mode toggle or repurpose it to cycle themes

## Dependencies
- No new pip packages needed
