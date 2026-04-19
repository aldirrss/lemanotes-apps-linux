# Feature: WYSIWYG Markdown Editor (Typora / Bear style)

## Status: DONE ✅

## Approach
Replace `QTextEdit` with `QWebEngineView` loading a local HTML page that embeds
**Toast UI Editor** (WYSIWYG Markdown). Python ↔ JS via `QWebChannel`.
Storage stays `.md` — no changes to `storage.py`.

---

## Checklist

### 1. Assets
- [x] `assets/tui/toastui-editor-all.min.js` downloaded (534 KB)
- [x] `assets/tui/toastui-editor.min.css` downloaded (165 KB)
- [x] `qwebchannel.js` served via `qrc:///qtwebchannel/qwebchannel.js` (built into Qt — no file needed)
- [x] `assets/editor.html` created

### 2. assets/editor.html
- [x] Loads TUI + qwebchannel.js from local/qrc paths
- [x] TUI Editor initialized in `wysiwyg` mode, full viewport height, toolbar hidden
- [x] QWebChannel connected on load; `bridge` registered
- [x] `change` event → `bridge.on_content_change(editor.getMarkdown())`
- [x] `window.setContent(md)` — sets editor content (queues if editor not ready)
- [x] `window.getContent()` → returns `editor.getMarkdown()`
- [x] `window.execCmd(cmd, payload)` — wraps `editor.exec()`
- [x] `window.notifyReady()` — calls `bridge.on_editor_ready()` after init
- [x] Full dark theme CSS overrides (bg #0D1B22, teal headings, dark code blocks, scrollbar)

### 3. EditorBridge class
- [x] `EditorBridge(QObject)` added to `main_window.py`
- [x] `content_changed = pyqtSignal(str)` + `@pyqtSlot(str) on_content_change`
- [x] `editor_ready = pyqtSignal()` + `@pyqtSlot() on_editor_ready`

### 4. EditorPanel refactor
- [x] `QTextEdit` + `MarkdownHighlighter` removed
- [x] `QStackedWidget` (editor/preview stack) removed
- [x] `toggle_btn` (Preview toggle) removed
- [x] `QWebEngineView` (wysiwyg) added with `QWebChannel` + `EditorBridge`
- [x] `_editor_ready` flag + `_pending_content` queue for pre-ready load
- [x] `load_note()` — injects content immediately if ready, else queues
- [x] `_on_editor_ready()` — flushes pending content
- [x] `_inject_content(md)` — `runJavaScript("setContent(...)")`
- [x] `_auto_save()` — async: `runJavaScript("getContent()", callback)`
- [x] `_do_save()` — callback that calls `storage.save_note()` with snapshot of nb/slug/title/tags
- [x] `export_pdf()` — uses `_wysiwyg.page().printToPdf()` directly
- [x] `clear()` — injects empty string, hides view, disables toolbar

### 5. Formatting toolbar rewired to JS
- [x] B → `execCmd('bold')`
- [x] I → `execCmd('italic')`
- [x] H1 → `execCmd('heading', {"level":1})`
- [x] H2 → `execCmd('heading', {"level":2})`
- [x] `</>` → `execCmd('code')`
- [x] `"` → `execCmd('blockQuote')`
- [x] Ctrl+B / Ctrl+I shortcuts rewired to same JS commands

### 6. Cleanup
- [x] `MarkdownHighlighter` class deleted
- [x] `PREVIEW_CSS` constant deleted
- [x] `markdown2` import removed
- [x] `markdown2` removed from `requirements.txt`
- [x] `QTextEdit`, `QStackedWidget`, `QTextCharFormat`, `QSyntaxHighlighter`, `QTextCursor` removed from imports

## Dependencies
- `PyQt6-WebEngine` (already required) — includes `QtWebChannel`
- `markdown2` removed
- TUI Editor bundled locally under `assets/tui/`
