"""
Main window — LemaNotes
Wires together SidebarPanel, NoteListPanel, and EditorPanel.
"""

import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter,
    QHBoxLayout, QStatusBar, QLabel,
    QDialog, QInputDialog, QMessageBox, QFileDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont, QKeySequence

from notes_app.themes import THEMES, _THEME_CYCLE  # noqa: F401
from notes_app.shortcuts import _MANDATORY_SHORTCUTS
from notes_app.dialogs import SettingsDialog
from notes_app.sidebar import SidebarPanel
from notes_app.note_list import NoteListPanel
from notes_app.editor import EditorPanel
from notes_app import storage
from notes_app.settings import load_settings, save_settings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LemaNotes")
        self.resize(1200, 780)
        self.setMinimumSize(800, 500)
        self._current_notebook = None
        self._current_section: str | None = None

        settings = load_settings()
        saved = settings.get("theme", "dark")
        self._theme_name = saved if saved in THEMES else "dark"
        self._font_size = settings.get("font_size", 15)
        self._disabled_shortcuts: list[str] = settings.get("disabled_shortcuts", [])
        self._notebook_sort: str = settings.get("notebook_sort", "name_asc")

        self._build_ui()
        self._build_menu()
        self.editor_panel.note_loaded.connect(self._export_pdf_act.setEnabled)
        self.editor_panel.note_loaded.connect(self._on_note_load_state)
        self.editor_panel.pdf_export_done.connect(self._on_pdf_exported)
        self.editor_panel.word_count_updated.connect(self._word_count_lbl.setText)
        self.editor_panel.title_input.textChanged.connect(
            lambda t: self.setWindowTitle(f"{t.strip()} \u2014 LemaNotes" if t.strip() else "LemaNotes")
        )
        self.editor_panel.apply_shortcuts(self._disabled_shortcuts)
        self._register_menu_shortcuts(self._disabled_shortcuts)
        self._load_notebooks()
        self._apply_theme(self._theme_name)
        self.editor_panel.set_font_size(self._font_size)
        self.sidebar.refresh_tags()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = SidebarPanel()
        self.sidebar.notebook_selected.connect(self._on_notebook_selected)
        self.sidebar.new_notebook_requested.connect(self._create_notebook)
        self.sidebar.note_moved.connect(self._on_note_moved)
        self.sidebar.tag_selected.connect(self._on_tag_selected)
        self.sidebar.tag_cleared.connect(self._on_tag_cleared)
        self.sidebar.theme_toggle_requested.connect(self._toggle_theme)
        self.sidebar.pinned_all_requested.connect(self._on_pinned_all_requested)
        self.sidebar.pinned_all_cleared.connect(self._on_pinned_all_cleared)
        self.sidebar.notebook_sort_changed.connect(self._on_notebook_sort_changed)
        main_layout.addWidget(self.sidebar)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(1)

        self.note_list = NoteListPanel()
        self.note_list.note_selected.connect(self._on_note_selected)
        self.note_list.new_note_requested.connect(self._create_note)
        self.note_list.delete_note_requested.connect(self._delete_note)
        self.note_list.pin_note_requested.connect(self._on_pin_requested)
        self.note_list.priority_changed.connect(self._on_priority_changed)
        self._splitter.addWidget(self.note_list)

        self.editor_panel = EditorPanel()
        self.editor_panel.note_saved.connect(self._on_note_saved)
        self.editor_panel.pin_toggled.connect(self._on_note_pin_toggled)
        self._splitter.addWidget(self.editor_panel)

        self._splitter.setSizes([250, 950])
        main_layout.addWidget(self._splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        self._word_count_lbl = QLabel("")
        self._word_count_lbl.setContentsMargins(0, 0, 8, 0)
        self.status_bar.addPermanentWidget(self._word_count_lbl)

    def _build_menu(self):
        self._menubar = self.menuBar()

        file_menu = self._menubar.addMenu("File")
        self._new_note_act = QAction("New Note", self)
        self._new_note_act.setShortcut(QKeySequence("Ctrl+N"))
        self._new_note_act.triggered.connect(self._create_note)
        file_menu.addAction(self._new_note_act)

        self._new_nb_act = QAction("New Notebook", self)
        self._new_nb_act.setShortcut(QKeySequence("Ctrl+Shift+N"))
        self._new_nb_act.triggered.connect(self._create_notebook)
        file_menu.addAction(self._new_nb_act)

        file_menu.addSeparator()
        self._export_pdf_act = QAction("Export as PDF\u2026", self)
        self._export_pdf_act.setShortcut(QKeySequence("Ctrl+E"))
        self._export_pdf_act.triggered.connect(self._export_pdf)
        self._export_pdf_act.setEnabled(False)
        file_menu.addAction(self._export_pdf_act)

        view_menu = self._menubar.addMenu("View")
        self._refresh_act = QAction("Refresh Notes", self)
        self._refresh_act.setShortcut(QKeySequence("Ctrl+R"))
        self._refresh_act.triggered.connect(self._refresh_notes)
        view_menu.addAction(self._refresh_act)
        view_menu.addSeparator()
        self._toggle_theme_act = QAction("Cycle Theme", self)
        self._toggle_theme_act.setShortcut(QKeySequence("Ctrl+Shift+D"))
        self._toggle_theme_act.triggered.connect(self._toggle_theme)
        view_menu.addAction(self._toggle_theme_act)

        self._settings_act = QAction("Settings\u2026", self)
        self._settings_act.setShortcut(QKeySequence("Ctrl+,"))
        self._settings_act.triggered.connect(self._open_settings)
        view_menu.addAction(self._settings_act)

        self._update_menu_style()

    def _update_menu_style(self):
        t = THEMES[self._theme_name]
        self._menubar.setStyleSheet(f"""
            QMenuBar {{ background: {t['bg2']}; color: {t['muted']}; }}
            QMenuBar::item:selected {{ background: {t['item_sel']}; color: {t['accent']}; }}
            QMenu {{ background: {t['bg3']}; color: {t['text']}; border: 1px solid {t['border']}; }}
            QMenu::item:selected {{ background: {t['item_sel']}; }}
        """)
        self.status_bar.setStyleSheet(
            f"background: {t['bg2']}; color: {t['muted2']}; font-size: 11px;"
        )
        self._word_count_lbl.setStyleSheet(f"color: {t['muted2']}; font-size: 11px;")
        self._splitter.setStyleSheet(f"QSplitter::handle {{ background: {t['border']}; }}")
        self.setStyleSheet(f"QMainWindow {{ background: {t['bg']}; }}")

    def _apply_theme(self, name: str, save: bool = True):
        self._theme_name = name
        t = THEMES[name]
        self.sidebar.apply_theme(t)
        self.note_list.apply_theme(t)
        self.editor_panel.apply_theme(t, name)
        self._update_menu_style()
        if save:
            s = load_settings()
            s["theme"] = name
            save_settings(s)

    def _toggle_theme(self):
        idx = _THEME_CYCLE.index(self._theme_name) if self._theme_name in _THEME_CYCLE else 0
        self._apply_theme(_THEME_CYCLE[(idx + 1) % len(_THEME_CYCLE)])

    def _register_menu_shortcuts(self, disabled: list[str]):
        disabled_set = set(disabled)
        menu_map = {
            "Ctrl+N":       self._new_note_act,
            "Ctrl+Shift+N": self._new_nb_act,
            "Ctrl+E":       self._export_pdf_act,
            "Ctrl+Shift+D": self._toggle_theme_act,
            "Ctrl+,":       self._settings_act,
            "Ctrl+R":       self._refresh_act,
        }
        for key, act in menu_map.items():
            if key in disabled_set and key not in _MANDATORY_SHORTCUTS:
                act.setShortcut(QKeySequence())
            else:
                act.setShortcut(QKeySequence(key))

    def _open_settings(self):
        s = load_settings()
        dlg = SettingsDialog(
            self,
            t=THEMES[self._theme_name],
            current_theme=self._theme_name,
            current_font_size=s.get("font_size", 15),
            disabled_shortcuts=s.get("disabled_shortcuts", []),
        )
        dlg.set_preview_callback(self._preview_settings)
        dlg.set_shortcuts_callback(self._preview_shortcuts)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            theme, font_size, disabled_sc = dlg.values()
            self._apply_theme(theme)
            self.editor_panel.set_font_size(font_size)
            self._font_size = font_size
            self._disabled_shortcuts = disabled_sc
            self.editor_panel.apply_shortcuts(disabled_sc)
            self._register_menu_shortcuts(disabled_sc)
            s = load_settings()
            s["font_size"] = font_size
            s["disabled_shortcuts"] = disabled_sc
            save_settings(s)

    def _preview_settings(self, theme: str, font_size: int):
        self._apply_theme(theme, save=False)
        self.editor_panel.set_font_size(font_size)

    def _preview_shortcuts(self, disabled: list[str]):
        self.editor_panel.apply_shortcuts(disabled)
        self._register_menu_shortcuts(disabled)

    def _load_notebooks(self):
        nbs = storage.list_notebooks()
        if not nbs:
            storage.create_notebook("Personal")
            nbs = ["Personal"]
        if self._notebook_sort == "name_desc":
            nbs = sorted(nbs, reverse=True)
        elif self._notebook_sort == "manual":
            s = load_settings()
            order = s.get("notebook_order", [])
            ordered   = [nb for nb in order if nb in nbs]
            remaining = [nb for nb in nbs if nb not in order]
            nbs = ordered + remaining
        self.sidebar.load_notebooks(nbs)
        self.sidebar.select_first()

    # ── Notebook / Note handlers ───────────────────────────────────────────────

    def _on_notebook_selected(self, notebook: str, section: str):
        self._current_notebook = notebook
        self._current_section = section or None
        self.sidebar.clear_tag_selection()
        self.note_list.load_notes(notebook, self._current_section)
        self.editor_panel.clear()

    def _on_note_selected(self, notebook: str, section: str, slug: str):
        self.editor_panel.load_note(notebook, slug, section or None)

    def _on_note_saved(self):
        self.status_bar.showMessage("Saved", 1500)
        self.sidebar.refresh_tags()
        current_item = self.note_list.list_widget.currentItem()
        current_data = current_item.data(Qt.ItemDataRole.UserRole) if current_item else None
        self.note_list.refresh()
        if current_data:
            for i in range(self.note_list.list_widget.count()):
                item = self.note_list.list_widget.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == current_data:
                    self.note_list.list_widget.blockSignals(True)
                    self.note_list.list_widget.setCurrentRow(i)
                    self.note_list.list_widget.blockSignals(False)
                    break

    def _create_notebook(self):
        name, ok = QInputDialog.getText(self, "New Notebook", "Notebook name:")
        if ok and name.strip():
            storage.create_notebook(name.strip())
            nbs = storage.list_notebooks()
            self.sidebar.load_notebooks(nbs)
            self.sidebar.select_notebook(name.strip())
            self.status_bar.showMessage(f"Notebook '{name.strip()}' created", 2000)

    def _create_note(self):
        if not self._current_notebook:
            QMessageBox.information(self, "Info", "Select a notebook first.")
            return
        title, ok = QInputDialog.getText(self, "New Note", "Note title:")
        if ok and title.strip():
            note = storage.create_note(
                self._current_notebook, title.strip(),
                content=f"# {title.strip()}\n\n",
                section=self._current_section,
            )
            self.status_bar.showMessage(f"Note '{title.strip()}' created", 2000)
            self.note_list.load_notes(self._current_notebook, self._current_section)
            target = (self._current_notebook, self._current_section or "", note["slug"])
            for i in range(self.note_list.list_widget.count()):
                item = self.note_list.list_widget.item(i)
                if item and item.data(Qt.ItemDataRole.UserRole) == target:
                    self.note_list.list_widget.setCurrentRow(i)
                    break

    def _delete_note(self, notebook: str, section: str, slug: str):
        storage.delete_note(notebook, slug, section or None)
        self.note_list.load_notes(notebook, section or None)
        self.editor_panel.clear()
        self.status_bar.showMessage("Note deleted", 2000)

    def _on_tag_selected(self, tag: str):
        self.note_list.filter_by_tag(tag)
        self.editor_panel.clear()

    def _on_tag_cleared(self):
        self.note_list.clear_tag_filter()
        self.editor_panel.clear()

    def _on_note_moved(self, src_nb: str, src_sec: str, slug: str,
                       dst_nb: str, dst_sec: str):
        moved = storage.move_note(src_nb, slug, dst_nb,
                                  src_section=src_sec or None,
                                  dst_section=dst_sec or None)
        if not moved:
            dst_label = f"{dst_nb}/{dst_sec}" if dst_sec else dst_nb
            QMessageBox.warning(self, "Move Failed",
                                f"Could not move note to '{dst_label}'.")
            return
        if (self._current_notebook == src_nb and
                (self._current_section or "") == src_sec):
            self.note_list.load_notes(src_nb, src_sec or None)
        if (self.editor_panel._notebook == src_nb
                and self.editor_panel._slug == slug
                and (self.editor_panel._section or "") == src_sec):
            self.editor_panel.clear()
        dst_label = f"{dst_nb} / {dst_sec}" if dst_sec else dst_nb
        self.status_bar.showMessage(f"Note moved to '{dst_label}'", 2000)

    # ── Pin / Priority handlers ────────────────────────────────────────────────

    def _on_pin_requested(self, notebook: str, section: str, slug: str):
        new_pinned = storage.toggle_pin(notebook, slug, section or None)
        self.status_bar.showMessage("Note pinned" if new_pinned else "Note unpinned", 1500)
        self.note_list.refresh()
        if (self.editor_panel._notebook == notebook and
                self.editor_panel._slug == slug and
                (self.editor_panel._section or "") == section):
            note = storage.load_note(notebook, slug, section or None)
            if note:
                pinned = note.get("pinned", False)
                self.editor_panel._pinned = pinned
                self.editor_panel._pin_btn.setText("\u2605" if pinned else "\u2606")
                self.editor_panel._pin_btn.setToolTip(
                    "Unpin note" if pinned else "Pin note"
                )

    def _on_priority_changed(self, notebook: str, section: str, slug: str, priority: int):
        storage.set_priority(notebook, slug, priority, section or None)
        labels = {0: "cleared", 1: "set to Low", 2: "set to Medium", 3: "set to High"}
        self.status_bar.showMessage(f"Priority {labels.get(priority, 'updated')}", 1500)
        self.note_list.refresh()

    def _on_note_pin_toggled(self, *_):
        self.note_list.refresh()

    def _on_pinned_all_requested(self):
        self.note_list.filter_pinned_all()
        self.editor_panel.clear()

    def _on_pinned_all_cleared(self):
        if self._current_notebook:
            self.note_list.load_notes(self._current_notebook, self._current_section)
        self.editor_panel.clear()

    def _on_notebook_sort_changed(self, sort: str):
        self._notebook_sort = sort
        s = load_settings()
        s["notebook_sort"] = sort
        save_settings(s)
        self._load_notebooks()

    # ── PDF export ────────────────────────────────────────────────────────────

    def _export_pdf(self):
        if not self.editor_panel._slug:
            return
        title = self.editor_panel.title_input.text().strip() or "note"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export as PDF", str(Path.home() / f"{title}.pdf"), "PDF Files (*.pdf)"
        )
        if path:
            self.editor_panel.export_pdf(path)

    def _refresh_notes(self):
        self.note_list.refresh()
        self.sidebar.refresh_tags()
        self.status_bar.showMessage("Refreshed", 1500)

    def _on_note_load_state(self, loaded: bool):
        if not loaded:
            self.setWindowTitle("LemaNotes")

    def _on_pdf_exported(self, path: str, success: bool):
        if success:
            self.status_bar.showMessage(f"Exported to {path}", 4000)
        else:
            QMessageBox.warning(self, "Export Failed", f"Could not write PDF to:\n{path}")


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("LemaNotes")
    app.setOrganizationName("Lemacore")
    app.setFont(QFont("Segoe UI", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
