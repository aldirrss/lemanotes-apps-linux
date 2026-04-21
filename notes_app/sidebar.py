from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea,
    QPushButton, QLabel, QMenu, QInputDialog, QMessageBox,
    QTreeWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSignal

from notes_app.themes import THEMES
from notes_app.widgets import NotebookTreeWidget
from notes_app.dialogs import PromptDialog
from notes_app import storage


class SidebarPanel(QWidget):
    notebook_selected = pyqtSignal(str, str)   # (notebook, section) — section="" means root
    new_notebook_requested = pyqtSignal()
    note_moved = pyqtSignal(str, str, str, str, str)  # (src_nb, src_sec, slug, dst_nb, dst_sec)
    tag_selected = pyqtSignal(str)
    tag_cleared = pyqtSignal()
    theme_toggle_requested = pyqtSignal()
    notebook_sort_changed = pyqtSignal(str)   # sort mode
    pinned_all_requested = pyqtSignal()
    pinned_all_cleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = THEMES["dark"]
        self.setMinimumWidth(190)
        self.setMaximumWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self._header = QWidget()
        self._header.setFixedHeight(56)
        hl = QHBoxLayout(self._header)
        hl.setContentsMargins(16, 0, 8, 0)
        self._header_title = QLabel("\U0001f4d3  LemaNotes")
        hl.addWidget(self._header_title)
        hl.addStretch()
        self._theme_btn = QPushButton("\u2600")
        self._theme_btn.setFixedSize(24, 24)
        self._theme_btn.setToolTip("Cycle theme (Ctrl+Shift+D)")
        self._theme_btn.clicked.connect(self.theme_toggle_requested)
        hl.addWidget(self._theme_btn)
        self._nb_sort_btn = QPushButton("\u21c5")
        self._nb_sort_btn.setFixedSize(24, 24)
        self._nb_sort_btn.setToolTip("Sort notebooks")
        self._nb_sort_btn.clicked.connect(self._show_notebook_sort_menu)
        hl.addWidget(self._nb_sort_btn)
        self._add_btn = QPushButton("+")
        self._add_btn.setFixedSize(24, 24)
        self._add_btn.setToolTip("New notebook")
        self._add_btn.clicked.connect(self.new_notebook_requested)
        hl.addWidget(self._add_btn)
        layout.addWidget(self._header)

        self._active_pinned_filter = False

        self._sep = QFrame()
        self._sep.setFrameShape(QFrame.Shape.HLine)
        self._sep.setFixedHeight(1)
        layout.addWidget(self._sep)

        # Notebook / Section tree
        self._tree = NotebookTreeWidget()
        self._tree.currentItemChanged.connect(self._on_tree_item_changed)
        self._tree.note_dropped.connect(self.note_moved)
        layout.addWidget(self._tree)

        # Tags section
        self._tags_sep = QFrame()
        self._tags_sep.setFrameShape(QFrame.Shape.HLine)
        self._tags_sep.setFixedHeight(1)
        layout.addWidget(self._tags_sep)

        self._tags_header = QWidget()
        self._tags_header.setFixedHeight(30)
        thl = QHBoxLayout(self._tags_header)
        thl.setContentsMargins(16, 0, 8, 0)
        self._tags_lbl = QLabel("\U0001f3f7  Tags")
        thl.addWidget(self._tags_lbl)
        thl.addStretch()
        self._tags_toggle_btn = QPushButton("\u25be")
        self._tags_toggle_btn.setFixedSize(20, 20)
        self._tags_toggle_btn.clicked.connect(self._toggle_tags_section)
        thl.addWidget(self._tags_toggle_btn)
        layout.addWidget(self._tags_header)

        self._tags_scroll = QScrollArea()
        self._tags_scroll.setWidgetResizable(True)
        self._tags_scroll.setMaximumHeight(160)
        self._tags_container = QWidget()
        self._tags_layout = QVBoxLayout(self._tags_container)
        self._tags_layout.setContentsMargins(8, 4, 8, 4)
        self._tags_layout.setSpacing(2)
        self._tags_scroll.setWidget(self._tags_container)
        layout.addWidget(self._tags_scroll)

        self._active_tag: str | None = None
        self._tag_buttons: dict[str, QPushButton] = {}
        self._apply_styles()

    # ── Theme ──────────────────────────────────────────────────────────────────

    def _apply_styles(self):
        t = self._theme
        self.setStyleSheet(f"background: {t['bg']};")
        self._header.setStyleSheet(f"background: {t['bg3']};")
        self._header_title.setStyleSheet(
            f"color: {t['accent']}; font-weight: 700; font-size: 15px;"
        )
        _icon_btn = f"""
            QPushButton {{
                background: {t['border']}; color: {t['accent']};
                border-radius: 12px; font-size: 13px; font-weight: bold; border: none;
            }}
            QPushButton:hover {{ background: {t['item_sel']}; }}
        """
        self._theme_btn.setStyleSheet(_icon_btn)
        self._nb_sort_btn.setStyleSheet(_icon_btn)
        self._add_btn.setStyleSheet(_icon_btn.replace("13px", "16px"))
        self._theme_btn.setText(t["theme_icon"])
        self._sep.setStyleSheet(f"background: {t['border']};")
        self._tree.setStyleSheet(f"""
            QTreeWidget {{
                background: {t['bg']}; border: none; padding: 4px 0;
                outline: none;
            }}
            QTreeWidget::item {{
                color: {t['muted']}; padding: 5px 8px; font-size: 13px;
                border: none; white-space: nowrap;
            }}
            QTreeWidget::item:selected {{
                background: {t['item_sel']}; color: {t['accent']};
                border-left: 3px solid {t['accent']};
            }}
            QTreeWidget::item:hover:!selected {{
                background: {t['item_hover']}; color: {t['text']};
            }}
            QTreeWidget::branch {{
                background: {t['bg']};
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                image: none;
                border-image: none;
                color: {t['muted2']};
            }}
            QScrollBar:vertical {{ background: {t['bg']}; width: 4px; }}
            QScrollBar::handle:vertical {{ background: {t['border']}; border-radius: 2px; }}
        """)
        self._tags_sep.setStyleSheet(f"background: {t['border']};")
        self._tags_header.setStyleSheet(f"background: {t['bg']};")
        self._tags_lbl.setStyleSheet(
            f"color: {t['tag_lbl']}; font-size: 11px; font-weight: 600;"
        )
        self._tags_toggle_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; color: {t['tag_lbl']}; border: none; font-size: 12px; }}
            QPushButton:hover {{ color: {t['accent']}; }}
        """)
        self._tags_scroll.setStyleSheet(f"""
            QScrollArea {{ border: none; background: {t['bg']}; }}
            QScrollBar:vertical {{ background: {t['bg']}; width: 4px; }}
            QScrollBar::handle:vertical {{ background: {t['border']}; border-radius: 2px; }}
        """)
        self._tags_container.setStyleSheet(f"background: {t['bg']};")

    def apply_theme(self, t: dict):
        self._theme = t
        self._apply_styles()
        self.refresh_tags()

    # ── Notebooks / Sections ───────────────────────────────────────────────────

    def load_notebooks(self, notebooks: list[str]):
        self._tree.blockSignals(True)
        self._tree.clear()
        for nb in notebooks:
            nb_item = QTreeWidgetItem(self._tree, [f"  \U0001f4c1  {nb}"])
            nb_item.setData(0, Qt.ItemDataRole.UserRole, (nb, ""))
            nb_item.setExpanded(True)
            for sec in storage.list_sections(nb):
                sec_item = QTreeWidgetItem(nb_item, [f"  \U0001f4c4  {sec}"])
                sec_item.setData(0, Qt.ItemDataRole.UserRole, (nb, sec))
        self._tree.blockSignals(False)

    def select_first(self):
        if self._tree.topLevelItemCount():
            self._tree.setCurrentItem(self._tree.topLevelItem(0))

    def select_notebook(self, nb: str, section: str = ""):
        for i in range(self._tree.topLevelItemCount()):
            nb_item = self._tree.topLevelItem(i)
            nb_data = nb_item.data(0, Qt.ItemDataRole.UserRole)
            if nb_data and nb_data[0] == nb:
                if not section:
                    self._tree.blockSignals(True)
                    self._tree.setCurrentItem(nb_item)
                    self._tree.blockSignals(False)
                    return
                for j in range(nb_item.childCount()):
                    sec_item = nb_item.child(j)
                    sec_data = sec_item.data(0, Qt.ItemDataRole.UserRole)
                    if sec_data and sec_data[1] == section:
                        self._tree.blockSignals(True)
                        self._tree.setCurrentItem(sec_item)
                        self._tree.blockSignals(False)
                        return

    def _on_tree_item_changed(self, current, previous):
        if not current:
            return
        data = current.data(0, Qt.ItemDataRole.UserRole)
        if data:
            nb, sec = data
            self.notebook_selected.emit(nb, sec)

    # ── Tags ───────────────────────────────────────────────────────────────────

    def refresh_tags(self):
        t = self._theme
        while self._tags_layout.count():
            item = self._tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._tag_buttons.clear()

        pin_btn = QPushButton("  \u2605 Pinned Notes")
        pin_btn.setCheckable(True)
        pin_btn.setChecked(self._active_pinned_filter)
        pin_btn.setStyleSheet(self._tag_btn_style(t, special=True))
        pin_btn.clicked.connect(self._on_pinned_filter_clicked)
        self._tags_layout.addWidget(pin_btn)
        self._pin_filter_btn_ref = pin_btn

        all_tags = storage.get_all_tags()
        if not all_tags:
            no_tags_lbl = QLabel("No tags yet")
            no_tags_lbl.setStyleSheet(
                f"color: {t['muted2']}; font-size: 11px; padding: 4px 16px;"
            )
            self._tags_layout.addWidget(no_tags_lbl)
        for tag in all_tags:
            btn = QPushButton(f"  {tag}")
            btn.setCheckable(True)
            btn.setChecked(tag == self._active_tag)
            btn.setStyleSheet(self._tag_btn_style(t))
            btn.clicked.connect(lambda _, tg=tag: self._on_tag_clicked(tg))
            self._tags_layout.addWidget(btn)
            self._tag_buttons[tag] = btn
        self._tags_layout.addStretch()

    def _tag_btn_style(self, t: dict, special: bool = False) -> str:
        fg = t["accent"] if not special else "#FFD700"
        return f"""
            QPushButton {{
                background: {t['code_bg']}; color: {fg};
                border: 1px solid {t['border']}; border-radius: 10px;
                font-size: 11px; padding: 2px 8px; text-align: left;
            }}
            QPushButton:checked {{
                background: {t['accent']}; color: {t['accent_fg']};
                border-color: {t['accent']};
            }}
            QPushButton:hover:!checked {{ background: {t['item_sel']}; }}
        """

    def _on_pinned_filter_clicked(self):
        self._active_pinned_filter = not self._active_pinned_filter
        if self._active_pinned_filter:
            self.clear_tag_selection()
            self.pinned_all_requested.emit()
        else:
            self.pinned_all_cleared.emit()

    def clear_tag_selection(self):
        if self._active_tag and self._active_tag in self._tag_buttons:
            self._tag_buttons[self._active_tag].setChecked(False)
        self._active_tag = None

    def _on_tag_clicked(self, tag: str):
        if self._active_tag == tag:
            self.clear_tag_selection()
            self.tag_cleared.emit()
        else:
            if self._active_tag and self._active_tag in self._tag_buttons:
                self._tag_buttons[self._active_tag].setChecked(False)
            self._active_tag = tag
            if tag in self._tag_buttons:
                self._tag_buttons[tag].setChecked(True)
            self.tag_selected.emit(tag)

    def clear_pinned_filter(self):
        self._active_pinned_filter = False
        if hasattr(self, "_pin_filter_btn_ref"):
            self._pin_filter_btn_ref.setChecked(False)

    def _toggle_tags_section(self):
        visible = not self._tags_scroll.isVisible()
        self._tags_scroll.setVisible(visible)
        self._tags_toggle_btn.setText("\u25be" if visible else "\u25b8")

    def _show_notebook_sort_menu(self):
        t = self._theme
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {t['bg3']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 4px; }}
            QMenu::item {{ padding: 6px 16px 6px 12px; border-radius: 5px; color: {t['text']}; margin: 1px 0; }}
            QMenu::item:selected {{ background: {t['item_sel']}; color: {t['text']}; }}
            QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 8px; }}
        """)
        a_z    = menu.addAction("Sort A \u2192 Z")
        z_a    = menu.addAction("Sort Z \u2192 A")
        manual = menu.addAction("Manual order")
        act = menu.exec(self._nb_sort_btn.mapToGlobal(
            self._nb_sort_btn.rect().bottomLeft()))
        if act == a_z:
            self.notebook_sort_changed.emit("name_asc")
        elif act == z_a:
            self.notebook_sort_changed.emit("name_desc")
        elif act == manual:
            self.notebook_sort_changed.emit("manual")

    # ── Context Menu ───────────────────────────────────────────────────────────

    def contextMenuEvent(self, e):
        pos = self._tree.mapFrom(self, e.pos())
        item = self._tree.itemAt(pos)
        if not item:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        nb, sec = data
        t = self._theme
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {t['bg3']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 4px; }}
            QMenu::item {{ padding: 6px 16px 6px 12px; border-radius: 5px; color: {t['text']}; margin: 1px 0; }}
            QMenu::item:selected {{ background: {t['item_sel']}; color: {t['text']}; }}
            QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 8px; }}
        """)

        if not sec:
            add_sec_act = menu.addAction("\U0001f4c4  Add Section")
            menu.addSeparator()
            rename_act = menu.addAction("Rename Notebook")
            delete_act = menu.addAction("Delete Notebook")
            act = menu.exec(e.globalPos())
            if act == add_sec_act:
                name, ok = PromptDialog.get_text(
                    self, "New Section", "Section name",
                    icon="📄", theme=self._theme,
                )
                if ok and name.strip() and not name.strip().startswith("."):
                    if storage.create_section(nb, name.strip()):
                        sec_item = QTreeWidgetItem(item, [f"  \U0001f4c4  {name.strip()}"])
                        sec_item.setData(0, Qt.ItemDataRole.UserRole, (nb, name.strip()))
                        item.setExpanded(True)
            elif act == rename_act:
                new_name, ok = PromptDialog.get_text(
                    self, "Rename Notebook", "New name",
                    icon="✏️", text=nb, theme=self._theme,
                )
                if ok and new_name.strip():
                    if storage.rename_notebook(nb, new_name.strip()):
                        item.setText(0, f"  \U0001f4c1  {new_name.strip()}")
                        item.setData(0, Qt.ItemDataRole.UserRole, (new_name.strip(), ""))
                        for ci in range(item.childCount()):
                            child = item.child(ci)
                            child_sec = child.data(0, Qt.ItemDataRole.UserRole)[1]
                            child.setData(0, Qt.ItemDataRole.UserRole, (new_name.strip(), child_sec))
            elif act == delete_act:
                if QMessageBox.question(
                    self, "Delete", f"Delete notebook '{nb}' and all its notes?"
                ) == QMessageBox.StandardButton.Yes:
                    storage.delete_notebook(nb)
                    idx = self._tree.indexOfTopLevelItem(item)
                    self._tree.takeTopLevelItem(idx)
        else:
            rename_act = menu.addAction("Rename Section")
            delete_act = menu.addAction("Delete Section")
            act = menu.exec(e.globalPos())
            if act == rename_act:
                new_name, ok = PromptDialog.get_text(
                    self, "Rename Section", "New name",
                    icon="✏️", text=sec, theme=self._theme,
                )
                if ok and new_name.strip() and not new_name.strip().startswith("."):
                    if storage.rename_section(nb, sec, new_name.strip()):
                        item.setText(0, f"  \U0001f4c4  {new_name.strip()}")
                        item.setData(0, Qt.ItemDataRole.UserRole, (nb, new_name.strip()))
            elif act == delete_act:
                has_notes = bool(storage.list_notes(nb, sec))
                msg = (f"Delete section '{sec}' and all its notes?" if has_notes
                       else f"Delete section '{sec}'?")
                if QMessageBox.question(self, "Delete", msg) == QMessageBox.StandardButton.Yes:
                    storage.delete_section(nb, sec)
                    parent = item.parent()
                    if parent:
                        parent.removeChild(item)
