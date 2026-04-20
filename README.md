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

## Installation

### 1. System Dependencies (Ubuntu/Debian)

Install required system libraries before running the app:

```bash
# Required: Qt XCB platform plugin dependencies
sudo apt install -y libxcb-cursor0

# Required: Qt WebEngine (if pip version doesn't bundle it)
sudo apt install -y python3-pyqt6.qtwebengine

# Optional but recommended: additional Qt XCB libraries
sudo apt install -y libxcb-xinerama0 libxcb-icccm4 libxcb-image0 \
                    libxcb-keysyms1 libxcb-render-util0
```

### 2. Python Dependencies

```bash
pip install -r requirements.txt
```

Using conda:

```bash
conda activate python3.11
pip install -r requirements.txt
```

### 3. Run

```bash
python run.py
```

### Troubleshooting

| Error | Fix |
|---|---|
| `Could not load the Qt platform plugin "xcb"` | `sudo apt install -y libxcb-cursor0` |
| `PyQt6-WebEngine` not found | `sudo apt install -y python3-pyqt6.qtwebengine` |
| Blank white editor area | Ensure `assets/tui/` contains Toast UI Editor files |

## Shortcuts
| Shortcut | Action |
|---|---|
| `Ctrl+N` | New Note |
| `Ctrl+Shift+N` | New Notebook |
| `Ctrl+Shift+D` | Toggle Dark Mode |

## Project Structure
```
lemanotes-app/
├── run.py                  # Entry point
├── requirements.txt
└── notes_app/
    ├── __init__.py
    ├── storage.py          # File-based storage layer
    └── main_window.py      # UI: sidebar, note list, editor, preview
```
