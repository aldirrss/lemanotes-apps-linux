# Feature: Export Note to PDF

## Status: DONE ✅

## Goal
Allow users to export the current note as a PDF file via menu or toolbar button.

## Checklist

### Backend / Storage
- [x] No storage changes needed — reads existing note content via `storage.load_note()`

### Core Implementation
- [x] `export_pdf(output_path)` added to `EditorPanel` — renders preview then calls `page().printToPdf()`
- [x] Use `QWebEngineView.page().printToPdf()` to render the preview HTML and save as PDF
- [x] Apply `PREVIEW_CSS` so the exported PDF matches the in-app preview style

### UI
- [x] "Export as PDF…" action added under `File` menu with shortcut `Ctrl+E`
- [x] `QFileDialog.getSaveFileName` opens with default path `~/note-title.pdf`
- [x] Action disabled when no note loaded; enabled via `note_loaded` signal from `EditorPanel`
- [x] Status bar shows `"Exported to <path>"` on success (4s)

### Edge Cases
- [x] Action is disabled (no-op guard) when `_slug is None`
- [x] `pdfPrintingFinished` async signal connected — shows `QMessageBox.warning` on failure

## Dependencies
- No new pip packages needed (`QWebEngineView.page().printToPdf` is part of PyQt6-WebEngine)

## Implementation Notes
- `EditorPanel` gained two new signals: `note_loaded(bool)` and `pdf_export_done(str, bool)`
- `export_pdf()` always calls `_render_preview()` first to ensure latest content is used, even when editor view is active
- `pdfPrintingFinished` connected via lambda in `__init__` after `QWebEngineView` is created
