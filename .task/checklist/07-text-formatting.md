# Feature: Complete Text & Formatting

## Status: DONE ✅

## Goal
Extend the WYSIWYG editor with a full set of formatting tools matching
Bear / Notes-Up quality: richer toolbar, insert helpers, find & replace,
and a live word/character count in the status bar.

---

## Checklist

### Toolbar — Additional Format Buttons
- [x] Strikethrough button (`S̶`) → `execCmd('strike')`  `Ctrl+Shift+S`
- [x] Highlight button (`H̲`) → `highlightSelection()` JS  `Ctrl+Shift+H`
- [x] H3 button → `execCmd('heading', {"level":3})`
- [x] Ordered list button (`1.`) → `execCmd('orderedList')`
- [x] Unordered list button (`•`) → `execCmd('bulletList')`
- [x] Task list (checkbox) button (`☑`) → `execCmd('taskList')`
- [x] Horizontal rule button (`—`) → `execCmd('hr')`
- [x] Dividers `|` between button groups (inline / headings / lists / insert)

### Insert Helpers
- [x] **Insert Link** (`Ctrl+K`): `InsertLinkDialog` (URL + text inputs, OK disabled until URL non-empty)
  → `insertLink(url, text)` JS (tries `addLink`, fallback to raw markdown)
- [x] **Insert Image** (`Ctrl+Shift+I`): `QFileDialog` → copies to `~/NotesUp/<nb>/.attachments/<slug>/`
  → `insertImage(url, alt)` JS
- [x] **Insert Table**: `InsertTableDialog` (rows × cols spinboxes)
  → `insertTable(rows, cols)` JS (tries `addTable`, fallback to markdown skeleton)
- [x] **Insert Code Block** (`Ctrl+Shift+C`): `InsertCodeBlockDialog` language combo
  → `insertCodeBlock(lang)` JS (`editor.insertText`)

### Find & Replace
- [x] `Ctrl+F` opens find bar (slim bar above WYSIWYG view)
- [x] Find input: `QWebEnginePage.findText()` highlights all matches live
- [x] Next (`F3` / `Enter`) / Previous (`Shift+F3`) match navigation
- [x] `Ctrl+H` expands bar to show Replace input
- [x] Replace one → `replaceInEditor(find, replace, false)` JS
- [x] Replace All → `replaceInEditor(find, replace, true)` JS
- [x] Escape closes bar and clears highlights
- [x] Bar auto-closes when note is cleared

### Word / Character Count
- [x] JS `getStats()` → `{words, chars}` derived from cleaned markdown
- [x] `EditorPanel` polls every 2 s via `QTimer` (`_word_count_timer`)
- [x] `word_count_updated` signal → permanent `QLabel` on right of status bar
- [x] Counter resets to empty when no note is open

### Highlight CSS (editor.html)
- [x] `<mark>` CSS uses `var(--mark-bg)` / `var(--mark-text)`
- [x] Dark theme `--mark-bg: #2A4A1A`, Light theme `--mark-bg: #FFF176`
- [x] Variables included in `setTheme()` THEMES palettes

### Keyboard Shortcuts
| Action            | Shortcut          |
|-------------------|-------------------|
| Bold              | Ctrl+B            |
| Italic            | Ctrl+I            |
| Strikethrough     | Ctrl+Shift+S      |
| Highlight         | Ctrl+Shift+H      |
| Insert Link       | Ctrl+K            |
| Insert Image      | Ctrl+Shift+I      |
| Insert Code Block | Ctrl+Shift+C      |
| Find              | Ctrl+F            |
| Find & Replace    | Ctrl+H            |
| Next match        | F3 / Enter        |
| Prev match        | Shift+F3          |
| Close Find bar    | Escape            |

### Edge Cases
- [x] Insert Image: attachment dir creation failure → fallback to original path
- [x] Insert Link: OK button disabled when URL empty
- [x] Find bar hidden when note is cleared (`EditorPanel.clear()`)
- [x] Word count timer stopped on clear, restarted on `load_note()`
- [x] `getStats()` returns `{words:0, chars:0}` if editor not ready
