# Feature: Toolbar Formatting Buttons

## Status: DONE ✅

## Goal
Add a formatting toolbar to `EditorPanel` with buttons for Bold, Italic, and Heading. Buttons wrap the current selection in the appropriate Markdown syntax.

## Checklist

### EditorPanel — Toolbar Widget
- [x] `_fmt_toolbar` QWidget added between tag bar and `QStackedWidget`, height 34px
- [x] Buttons: **B** (bold `**`), *I* (italic `*`), **H1** (`# `), **H2** (`## `), `</>` (inline code `` ` ``), `"` (blockquote `> `)
- [x] Toolbar hidden when preview mode active (`_toggle_view` calls `_fmt_toolbar.hide()/show()`)
- [x] Style: `#1A3A4A` bg, `#7FDBCA` text, hover `#2A5A6A`, pressed inverts to teal — matches dark theme

### Formatting Logic
- [x] `_wrap_selection(prefix, suffix)` — inline wrap helper:
  - Selected text already wrapped → unwrap (strip prefix/suffix)
  - Selected text → wrap with prefix + selected + suffix
  - No selection → insert `prefix+suffix` and position cursor between them
- [x] `_prefix_line(prefix)` — line-start helper for H1, H2, blockquote:
  - Line already starts with prefix → remove it (toggle off)
  - Otherwise → insert prefix at start of block
- [x] Button wiring:
  - **B** → `_wrap_selection("**", "**")`
  - **I** → `_wrap_selection("*", "*")`
  - **H1** → `_prefix_line("# ")`
  - **H2** → `_prefix_line("## ")`
  - `</>` → `_wrap_selection("`", "`")`
  - `"` → `_prefix_line("> ")`

### Keyboard Shortcuts
- [x] `Ctrl+B` → Bold via `QShortcut`
- [x] `Ctrl+I` → Italic via `QShortcut`

### Edge Cases
- [x] All toolbar buttons use `setFocusPolicy(Qt.FocusPolicy.NoFocus)` — editor keeps focus after click
- [x] Both `_wrap_selection` and `_prefix_line` call `self.editor.setFocus()` at end
- [x] Toggle behavior implemented: unwrap bold/italic/code if already wrapped; remove heading/quote prefix if already present
- [x] `_fmt_toolbar.setEnabled(False)` by default; enabled in `load_note()`, disabled in `clear()`

## Dependencies
- No new pip packages needed

## Implementation Notes
- `QTextCursor` and `QShortcut` added to `PyQt6.QtGui` imports
- `_fmt_btn()` helper closure inside `__init__` keeps button creation DRY
- `_prefix_line` uses `cursor.block().text()` to check line content before moving to `StartOfBlock`
