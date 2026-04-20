# LemaNotes

A Linux desktop notes app built with PyQt6, with optional cloud sync via Supabase.

## Features

- **Notebooks & Sections** — hierarchical note organization (notebook → section → note)
- **Tags** — label notes and filter by tag
- **WYSIWYG Editor** — powered by Toast UI Editor (Markdown under the hood)
- **8 Themes** — 4 dark (Dark, Deep Sea, Midnight, Night Forest) + 4 light (Classic, Ocean, Forest, Rose)
- **Auto-save** — saves automatically 800ms after you stop typing
- **Full-text search** — search by title, content, and tags
- **Pin & Priority** — pin important notes, mark priority (Low / Medium / High)
- **Export PDF** — export any note to a PDF file
- **Cloud Sync** — auto-sync across devices via Supabase (optional)
- **Offline-first** — all features work without an internet connection

---

## Installation

### 1. System Dependencies (Ubuntu / Debian)

```bash
sudo apt install -y libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 \
                    libxcb-image0 libxcb-keysyms1 libxcb-render-util0

# WebEngine (if the pip version does not bundle it)
sudo apt install -y python3-pyqt6.qtwebengine
```

### 2. Python Dependencies

```bash
# Conda (recommended)
conda activate python3.11
pip install -r requirements.txt

# Or with plain pip
pip install -r requirements.txt
```

`requirements.txt`:
```
PyQt6>=6.6.0
PyQt6-WebEngine>=6.6.0
supabase>=2.0.0
```

### 3. Run

```bash
cd lemanotes-apps
python run.py
```

### Troubleshooting

| Error | Fix |
|---|---|
| `Could not load the Qt platform plugin "xcb"` | `sudo apt install -y libxcb-cursor0` |
| `PyQt6-WebEngine` not found | `sudo apt install -y python3-pyqt6.qtwebengine` |
| Editor area is blank | Make sure `assets/tui/` contains the Toast UI Editor files |
| `ModuleNotFoundError: supabase` | `pip install supabase` |

---

## Cloud Sync Setup (Supabase)

Sync is **optional**. The app runs fully offline without this setup.

### 1. Create a Supabase Account & Project

Sign up for free at [supabase.com](https://supabase.com) and create a new project.

### 2. Create the `notes` Table

Open the **SQL Editor** in the Supabase Dashboard and run:

```sql
CREATE TABLE notes (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  notebook    TEXT NOT NULL,
  section     TEXT NOT NULL DEFAULT '',
  slug        TEXT NOT NULL,
  title       TEXT NOT NULL DEFAULT '',
  content     TEXT NOT NULL DEFAULT '',
  tags        TEXT[] NOT NULL DEFAULT '{}',
  pinned      BOOLEAN NOT NULL DEFAULT FALSE,
  priority    INTEGER NOT NULL DEFAULT 0,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  is_deleted  BOOLEAN NOT NULL DEFAULT FALSE,
  UNIQUE(user_id, notebook, section, slug)
);

ALTER TABLE notes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users manage own notes"
  ON notes FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
```

### 3. Configure OAuth (for Google / GitHub login)

#### Add Redirect URL

In the Supabase Dashboard → **Authentication → URL Configuration**, add the following to **Redirect URLs**:

```
http://localhost:54321/callback
```

#### Google OAuth

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create or select a project.
2. Navigate to **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
3. Set **Application type** to **Web application**.
4. Under **Authorized redirect URIs**, add your Supabase callback URL:
   ```
   https://<your-project-ref>.supabase.co/auth/v1/callback
   ```
   *(Copy the exact URL from Supabase Dashboard → Authentication → Providers → Google → Callback URL)*
5. Click **Create**. Google will give you a **Client ID** and **Client Secret**.
   - Client ID format: `123456789012-xxxxxxxxxxxxxxxx.apps.googleusercontent.com`
6. In Supabase Dashboard → **Authentication → Providers → Google**, paste the **Client ID** and **Client Secret**, then click **Save**.

#### GitHub OAuth

1. Go to [github.com](https://github.com) → **Settings → Developer settings → OAuth Apps → New OAuth App**.
2. Fill in the form:
   ```
   Application name        : LemaNotes
   Homepage URL            : https://<your-project-ref>.supabase.co
   Authorization callback URL : https://<your-project-ref>.supabase.co/auth/v1/callback
   ```
3. Click **Register application**, then click **Generate a new client secret**.
4. Copy the **Client ID** and **Client Secret**.
5. In Supabase Dashboard → **Authentication → Providers → GitHub**, paste both values and click **Save**.

### 4. Get Your URL & Anon Key

Go to **Project Settings → API** and copy:
- **Project URL** — `https://xxxx.supabase.co`
- **Anon (public) Key** — `eyJhbGciOiJIUzI1NiIs...`

### 5. Connect to the App

In LemaNotes: **Account → Setup Supabase…**, enter the URL and Anon Key, then click **Save & Connect**.

---

## User Guide

### Layout

```
┌──────────────┬──────────────────┬────────────────────────────┐
│   Sidebar    │   Note List      │         Editor             │
│              │                  │                            │
│  Notebooks   │  [Search]        │  [Title input]             │
│  Sections    │  ─────────────   │  [Tag bar]                 │
│  ─────────   │  Note cards      │  [Toolbar]                 │
│  Tags        │  (title, tags,   │                            │
│              │   date)          │  [Editor area]             │
│              │                  │                            │
└──────────────┴──────────────────┴────────────────────────────┘
```

### Managing Notebooks

| Action | How |
|---|---|
| New notebook | `Ctrl+Shift+N` or click **＋** in the sidebar |
| New section | Right-click a notebook → **New Section** |
| Rename / Delete | Right-click a notebook or section |
| Sort notebooks | Right-click the notebook area → choose sort order |

### Managing Notes

| Action | How |
|---|---|
| New note | `Ctrl+N` or the **＋ Note** button in the note list |
| Search notes | Type in the search box (searches title, content, and tags) |
| Pin a note | Right-click → **Pin**, or use the pin button in the editor |
| Set priority | Right-click → **Priority** → Low / Medium / High |
| Delete a note | Right-click → **Delete Note** |
| Move a note | Drag & drop onto another notebook or section in the sidebar |

### Editor Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+B` | Bold |
| `Ctrl+I` | Italic |
| `Ctrl+Shift+S` | Strikethrough |
| `Ctrl+Shift+H` | Highlight |
| `Ctrl+K` | Insert Link |
| `Ctrl+Shift+I` | Insert Image |
| `Ctrl+Shift+C` | Insert Code Block |
| `Ctrl+F` | Find |
| `Ctrl+H` | Find & Replace |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |

### Tags

- Click **+ tag** below the title to add a tag
- Click **×** on a tag to remove it
- Click a tag in the sidebar to filter all notes by that tag

### Themes

Switch themes via:
- `Ctrl+Shift+D` — cycle through all themes (Dark → Deep Sea → Midnight → Night Forest → Classic → Ocean → Forest → Rose)
- `Ctrl+,` → **Appearance** tab → pick a theme from the dropdown

### Exporting to PDF

Open a note → `Ctrl+E` or **File → Export as PDF…**

### Cloud Sync

| Action | How |
|---|---|
| Login (email) | **Account → Sign in…** → enter email & password |
| Login (OAuth) | **Account → Sign in…** → click **GitHub** or **Google** |
| Register | **Account → Sign in…** → click **Register** |
| Manual sync | **Account → Sync Now** |
| Logout | **Account → Sign out** |

Once logged in:
- **Auto pull** — cloud data is pulled to local storage on first login
- **Auto push** — every time a note is saved, it is pushed to the cloud in the background
- **Delete sync** — deleting a note locally marks it as deleted in the cloud
- Sync status is shown in the bottom-right corner of the status bar

> Notes are always stored locally in `~/LemaNotes/`. Cloud sync adds a backup layer and does not replace local storage.

### All Keyboard Shortcuts

| Shortcut | Action | Category |
|---|---|---|
| `Ctrl+B` | Bold | Format |
| `Ctrl+I` | Italic | Format |
| `Ctrl+Shift+S` | Strikethrough | Format |
| `Ctrl+Shift+H` | Highlight | Format |
| `Ctrl+K` | Insert Link | Insert |
| `Ctrl+Shift+I` | Insert Image | Insert |
| `Ctrl+Shift+C` | Insert Code Block | Insert |
| `Ctrl+F` | Find | Find |
| `Ctrl+H` | Find & Replace | Find |
| `Ctrl+Z` | Undo | Edit |
| `Ctrl+Shift+Z` | Redo | Edit |
| `Ctrl+N` | New Note | App |
| `Ctrl+Shift+N` | New Notebook | App |
| `Ctrl+E` | Export PDF | App |
| `Ctrl+,` | Settings | App |
| `Ctrl+Shift+D` | Cycle Theme | App |
| `Ctrl+R` | Refresh Notes | App |

Individual shortcuts can be disabled under **Settings → Shortcuts**.

---

## Local Storage Structure

```
~/LemaNotes/
  <NotebookName>/
    <note-slug>.md
    <note-slug>.meta.json
    <SectionName>/
      <note-slug>.md
      <note-slug>.meta.json

~/.config/notesup/
  settings.json        # theme, font size, shortcuts, Supabase config
```

## Project Structure

```
lemanotes-apps/
├── run.py
├── requirements.txt
├── assets/
│   ├── editor.html          # Toast UI Editor wrapper
│   └── tui/                 # Toast UI Editor static files
└── notes_app/
    ├── storage.py           # File-based storage (CRUD, search, tags)
    ├── sync.py              # Supabase sync manager
    ├── settings.py          # Load/save settings.json
    ├── themes.py            # 8 color themes
    ├── shortcuts.py         # Shortcut definitions
    ├── widgets.py           # TagPill, NoteListWidget, etc.
    ├── dialogs.py           # Settings, Login, Supabase Setup dialogs
    ├── sidebar.py           # Left panel: notebook tree + tag list
    ├── note_list.py         # Center panel: note list + search
    ├── editor.py            # Right panel: editor + tag bar + toolbar
    └── main_window.py       # Main window, wires all panels together
```
