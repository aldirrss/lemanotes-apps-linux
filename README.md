# LemaNotes Clone

A Linux desktop notes app built with PyQt6, inspired by Notes-Up.

## Features
- 📁 Notebook/folder grouping
- 🏷 Tags per note
- 🔍 Full-text search (title, content, tags)
- 🌙 Dark mode toggle (Ctrl+Shift+D)
- ✏ Markdown editor with syntax highlighting
- 👁 Toggle Editor / Preview (HTML render)
- 💾 Auto-save (800ms after typing stops)
- Storage: `.md` file per note + `.meta.json` sidecar

## File Structure
```
~/LemaNotes/
  <NotebookName>/
    <note-title>.md
    <note-title>.meta.json
```

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# On Ubuntu/Debian, PyQt6-WebEngine may require:
sudo apt install python3-pyqt6.qtwebengine

# Run
python run.py
```

## Shortcuts
| Shortcut | Action |
|---|---|
| `Ctrl+N` | New Note |
| `Ctrl+Shift+N` | New Notebook |
| `Ctrl+Shift+D` | Toggle Dark Mode |

## Project Structure
```
notesup-clone/
├── run.py                  # Entry point
├── requirements.txt
└── notes_app/
    ├── __init__.py
    ├── storage.py          # File-based storage layer
    └── main_window.py      # UI: sidebar, note list, editor, preview
```
