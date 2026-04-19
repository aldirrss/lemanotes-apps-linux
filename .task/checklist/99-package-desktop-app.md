# Feature: Package as Linux Desktop App

## Goal
Distribute NotesUp as a standalone Linux desktop application with a `.desktop` launcher, app icon, and optional AppImage bundle.

## Checklist

### App Icon
- [ ] Create `assets/icon.png` (512x512 recommended) as the app icon
- [ ] Reference icon in `.desktop` file and in `QApplication.setWindowIcon()`

### .desktop Entry
- [ ] Create `notesup.desktop`:
  ```ini
  [Desktop Entry]
  Name=NotesUp
  Comment=Markdown notes app
  Exec=/opt/notesup/notesup
  Icon=/opt/notesup/assets/icon.png
  Terminal=false
  Type=Application
  Categories=Office;TextEditor;
  ```
- [ ] Add `install.sh` script that copies files to `/opt/notesup/` and installs the `.desktop` file to `~/.local/share/applications/`

### PyInstaller Bundle (single-folder)
- [ ] Add `PyInstaller` to `requirements-dev.txt` (keep separate from runtime deps)
- [ ] Create `notesup.spec` with:
  - `datas`: include `assets/` folder
  - `hiddenimports`: `["markdown2", "PyQt6.QtWebEngineWidgets"]`
  - `icon`: `assets/icon.png`
- [ ] Build command: `pyinstaller notesup.spec --distpath dist/`
- [ ] Test the built binary runs without Python installed

### AppImage (optional, portable)
- [ ] Use `appimagetool` to wrap the PyInstaller `dist/notesup/` folder
- [ ] Add `AppRun` entry point script
- [ ] Output: `NotesUp-x86_64.AppImage` — single executable, runs on any modern Linux distro

### install.sh
- [ ] Script steps:
  1. Copy `dist/notesup/` → `/opt/notesup/`
  2. Copy `notesup.desktop` → `~/.local/share/applications/`
  3. Run `update-desktop-database ~/.local/share/applications/` (if available)
  4. Print success message with launch instructions
- [ ] Add `uninstall.sh` that reverses the above

### CI / Build Script
- [ ] Add `build.sh` that runs PyInstaller then optionally packages AppImage
- [ ] Document build steps in `README.md` under a new "Build & Distribute" section

## Dependencies
```
# requirements-dev.txt
pyinstaller>=6.0
```
- `appimagetool` binary from https://github.com/AppImage/AppImageKit (download separately)
