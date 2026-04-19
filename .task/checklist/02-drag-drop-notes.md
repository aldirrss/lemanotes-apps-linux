# Feature: Drag & Drop Notes Between Notebooks

## Status: DONE ✅

## Goal
Allow users to drag a note from `NoteListPanel` and drop it onto a notebook in `SidebarPanel` to move it.

## Checklist

### Backend / Storage
- [x] `move_note(src_notebook, slug, dst_notebook)` added to `storage.py`
  - Moves `<slug>.md` and `<slug>.meta.json` to the destination notebook directory
  - Handles slug collision by appending `-1`, `-2`, etc.

### NoteListPanel (drag source)
- [x] `NoteListWidget(QListWidget)` subclass created with `setDragEnabled(True)`
- [x] `startDrag` encodes `(notebook, slug)` into MIME type `application/x-notesup-note`
- [x] `NoteListPanel.list_widget` replaced with `NoteListWidget`

### SidebarPanel (drop target)
- [x] `NotebookListWidget(QListWidget)` subclass created with `setAcceptDrops(True)` and `setDropIndicatorShown(True)`
- [x] `dragEnterEvent` and `dragMoveEvent` accept `application/x-notesup-note` MIME type
- [x] `dropEvent` decodes MIME data, resolves target notebook, emits `note_dropped(src_nb, slug, dst_nb)`
- [x] `SidebarPanel.list_widget` replaced with `NotebookListWidget`
- [x] `SidebarPanel.note_moved` signal forwards `note_dropped` to `MainWindow`

### MainWindow
- [x] `sidebar.note_moved` connected to `_on_note_moved(src_nb, slug, dst_nb)`
- [x] `_on_note_moved` calls `storage.move_note()`, reloads `NoteListPanel`, clears editor if moved note was open
- [x] Status bar shows `"Note moved to '<notebook>'"` on success

### Edge Cases
- [x] Drop onto same notebook is rejected (`dst_nb == src_nb` → `e.ignore()`)
- [x] Slug collision handled in `storage.move_note()` with counter suffix
- [x] Visual feedback via `setDropIndicatorShown(True)` on hover

## Dependencies
- No new pip packages needed

## Implementation Notes
- MIME constant `_NOTE_MIME = "application/x-notesup-note"` defined as module-level string
- Both custom list widgets live in the new `# Drag & Drop Widgets` section above `SidebarPanel`
- `_on_note_moved` only reloads `NoteListPanel` when the source notebook is currently selected — avoids unnecessary reloads
