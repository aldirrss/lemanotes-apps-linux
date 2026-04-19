# Feature: Full Sidebar Tag Filter

## Status: DONE ✅

## Goal
Add a tag list section to `SidebarPanel`. Clicking a tag filters notes across all notebooks.

## Checklist

### Backend / Storage
- [x] `storage.get_all_tags()` already existed — returns sorted list of all tags
- [x] `storage.filter_by_tag(tag)` added — scans all notebooks, returns notes where tag matches (exact, case-insensitive), sorted by `updated_at`

### SidebarPanel
- [x] "Tags" collapsible section added below notebook list with separator, header row, and scroll area
- [x] `refresh_tags()` repopulates tag buttons from `storage.get_all_tags()`
- [x] `tag_selected = pyqtSignal(str)` emitted on tag click
- [x] `tag_cleared = pyqtSignal()` emitted when active tag is clicked again (toggle off)
- [x] `clear_tag_selection()` public method for external deselection
- [x] `_toggle_tags_section()` shows/hides the scroll area (▾/▸ button)
- [x] Style: teal pill buttons (`#132530` bg, `#7FDBCA` text), checked state inverts colors, scrollable at max 180px

### NoteListPanel
- [x] `_tag_filter: str | None` state added
- [x] `filter_by_tag(tag)` sets filter, updates header label to `"Tag: <tag>"`, renders filtered results
- [x] `clear_tag_filter()` resets filter, restores notebook label and note list
- [x] `refresh()` re-renders based on active state: tag filter if active, else current notebook
- [x] `load_notes()` always clears `_tag_filter` (fresh notebook selection)

### MainWindow
- [x] `sidebar.tag_selected` → `_on_tag_selected()`: calls `note_list.filter_by_tag()` + clears editor
- [x] `sidebar.tag_cleared` → `_on_tag_cleared()`: calls `note_list.clear_tag_filter()` + clears editor
- [x] `_on_notebook_selected()`: calls `sidebar.clear_tag_selection()` before loading notes
- [x] `_on_note_saved()`: uses `note_list.refresh()` instead of `load_notes()` to preserve active tag filter; also calls `sidebar.refresh_tags()`
- [x] `sidebar.refresh_tags()` called on startup (after `_load_notebooks`)

### Edge Cases
- [x] Tags auto-refresh after save via `_on_note_saved → sidebar.refresh_tags()`
- [x] Empty tag filter results show empty list (no special empty-state widget needed — existing behavior)
- [x] Clicking a notebook while tag filter is active clears tag selection via `_on_notebook_selected`

## Dependencies
- No new pip packages needed

## Implementation Notes
- `refresh()` on `NoteListPanel` replaces direct `load_notes()` calls from `_on_note_saved` to keep tag filter alive across saves
- Tag toggle logic in `_on_tag_clicked`: same tag → deselect + `tag_cleared`; different tag → swap selection + `tag_selected`
- Tags section uses `QScrollArea` max 180px with a `QVBoxLayout` of `QPushButton` (checkable) — no custom layout needed
