from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QPushButton, QLabel, QListWidgetItem, QMenu, QMessageBox, QStackedWidget,
    QInputDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize

from notes_app.themes import THEMES
from notes_app.widgets import NoteListWidget, TagPill
from notes_app.dialogs import PromptDialog
from notes_app import storage
from notes_app.settings import load_settings, save_settings


_PRIORITY_COLORS_FALLBACK = {1: "#F5C518", 2: "#E87C2B", 3: "#E84040"}
_SORT_LABELS = {
    "updated_desc":  "Updated (newest first)",
    "updated_asc":   "Updated (oldest first)",
    "title_asc":     "Title A \u2192 Z",
    "title_desc":    "Title Z \u2192 A",
    "priority_desc": "Priority (highest first)",
    "created_desc":  "Created (newest first)",
}


class NoteListPanel(QWidget):
    note_selected = pyqtSignal(str, str, str)
    new_note_requested = pyqtSignal()
    delete_note_requested = pyqtSignal(str, str, str)
    pin_note_requested = pyqtSignal(str, str, str)           # (nb, section, slug)
    priority_changed = pyqtSignal(str, str, str, int)        # (nb, section, slug, priority)
    rename_note_requested = pyqtSignal(str, str, str, str)   # (nb, section, slug, new_title)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = THEMES["dark"]
        self.setMinimumWidth(220)
        self.setMaximumWidth(300)
        self._current_notebook = None

        s = load_settings()
        self._sort_order: str  = s.get("note_sort", "updated_desc")
        self._filter_pinned: bool = s.get("filter_pinned", False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._toolbar = QWidget()
        self._toolbar.setFixedHeight(48)
        tl = QHBoxLayout(self._toolbar)
        tl.setContentsMargins(12, 0, 8, 0)
        self.nb_label = QLabel("Select a notebook")
        tl.addWidget(self.nb_label)
        tl.addStretch()
        self._refresh_btn = QPushButton("\u21bb")
        self._refresh_btn.setFixedSize(28, 28)
        self._refresh_btn.setToolTip("Refresh notes (Ctrl+R)")
        self._refresh_btn.clicked.connect(self.refresh)
        tl.addWidget(self._refresh_btn)
        self._new_btn = QPushButton("\uff0b Note")
        self._new_btn.setFixedHeight(28)
        self._new_btn.setToolTip("New note (Ctrl+N)")
        self._new_btn.clicked.connect(self.new_note_requested)
        tl.addWidget(self._new_btn)
        layout.addWidget(self._toolbar)

        self._search_wrap = QWidget()
        sl = QHBoxLayout(self._search_wrap)
        sl.setContentsMargins(12, 6, 12, 6)
        from PyQt6.QtWidgets import QLineEdit
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("\U0001f50d  Search notes\u2026")
        self.search_input.textChanged.connect(self._on_search)
        sl.addWidget(self.search_input)
        layout.addWidget(self._search_wrap)

        # Sort / Filter bar
        self._sortbar = QWidget()
        self._sortbar.setFixedHeight(32)
        sbl = QHBoxLayout(self._sortbar)
        sbl.setContentsMargins(12, 0, 12, 0)
        sbl.setSpacing(6)
        self._pin_filter_btn = QPushButton("\u2605 Pinned")
        self._pin_filter_btn.setCheckable(True)
        self._pin_filter_btn.setChecked(self._filter_pinned)
        self._pin_filter_btn.setFixedHeight(22)
        self._pin_filter_btn.setToolTip("Show pinned notes only")
        self._pin_filter_btn.clicked.connect(self._on_pin_filter_toggled)
        sbl.addWidget(self._pin_filter_btn)
        self._sort_btn = QPushButton("\u21c5 Sort")
        self._sort_btn.setFixedHeight(22)
        self._sort_btn.setToolTip("Sort notes")
        self._sort_btn.clicked.connect(self._show_sort_menu)
        sbl.addWidget(self._sort_btn)
        sbl.addStretch()
        layout.addWidget(self._sortbar)

        self._sep = QFrame()
        self._sep.setFrameShape(QFrame.Shape.HLine)
        self._sep.setFixedHeight(1)
        layout.addWidget(self._sep)

        self._content_stack = QStackedWidget()

        self._empty_lbl = QLabel("No notes yet.\nClick '\uff0b Note' to create one.")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_stack.addWidget(self._empty_lbl)

        self.list_widget = NoteListWidget()
        self.list_widget.currentRowChanged.connect(self._on_select)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self._content_stack.addWidget(self.list_widget)

        layout.addWidget(self._content_stack, 1)

        self._notes = []
        self._tag_filter: str | None = None
        self._current_section: str | None = None
        self._apply_styles()

    def _apply_styles(self):
        t = self._theme
        self.setStyleSheet(f"background: {t['bg4']};")
        self._toolbar.setStyleSheet(f"background: {t['bg3']};")
        self.nb_label.setStyleSheet(
            f"color: {t['accent']}; font-weight: 600; font-size: 13px;"
        )
        _icon_btn_s = f"""
            QPushButton {{
                background: {t['border']}; color: {t['muted']};
                border: none; border-radius: 14px; font-size: 14px;
            }}
            QPushButton:hover {{ background: {t['item_sel']}; color: {t['accent']}; }}
        """
        self._refresh_btn.setStyleSheet(_icon_btn_s)
        self._new_btn.setStyleSheet(f"""
            QPushButton {{
                background: {t['accent']}; color: {t['accent_fg']};
                border-radius: 14px; font-size: 11px; font-weight: 700;
                padding: 0 10px; border: none;
            }}
            QPushButton:hover {{ background: {t['accent_hover']}; color: {t['accent_fg']}; }}
        """)
        self._search_wrap.setStyleSheet(f"background: {t['bg4']};")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: {t['item_sel']}; color: {t['search_text']};
                border: 1px solid {t['border2']}; border-radius: 6px;
                padding: 5px 10px; font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {t['accent']}; }}
            QLineEdit::placeholder {{ color: {t['placeholder']}; }}
        """)
        sort_btn_s = f"""
            QPushButton {{
                background: {t['item_sel']}; color: {t['muted']};
                border: 1px solid {t['border']}; border-radius: 10px;
                font-size: 11px; padding: 0 8px;
            }}
            QPushButton:hover {{ color: {t['accent']}; border-color: {t['accent']}; }}
            QPushButton:checked {{
                background: {t['accent']}; color: {t['accent_fg']}; border-color: {t['accent']};
            }}
        """
        self._pin_filter_btn.setStyleSheet(sort_btn_s)
        self._sort_btn.setStyleSheet(sort_btn_s)
        self._sortbar.setStyleSheet(f"background: {t['bg4']};")
        self._sep.setStyleSheet(f"background: {t['border']};")
        self._content_stack.setStyleSheet(f"background: {t['bg4']};")
        self._empty_lbl.setStyleSheet(
            f"color: {t['muted2']}; font-size: 13px;"
        )
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: {t['bg4']}; border: none; outline: none;
            }}
            QListWidget::item {{
                background: {t['bg2']}; border-radius: 8px;
                margin: 4px 8px; padding: 0;
            }}
            QListWidget::item:selected {{
                background: {t['item_sel']}; border: 1px solid {t['accent']};
            }}
            QListWidget::item:hover:!selected {{ background: {t['item_hover']}; }}
            QScrollBar:vertical {{ background: {t['bg4']}; width: 4px; }}
            QScrollBar::handle:vertical {{ background: {t['border']}; border-radius: 2px; }}
        """)

    def apply_theme(self, t: dict):
        self._theme = t
        self._apply_styles()
        self.refresh()

    # ── Data loading ───────────────────────────────────────────────────────────

    def load_notes(self, notebook: str, section: str | None = None):
        self._current_notebook = notebook
        self._current_section = section
        self._tag_filter = None
        label = f"{notebook} / {section}" if section else notebook
        self.nb_label.setText(label)
        self._notes = storage.list_notes(notebook, section)
        self._render_notes(self._apply_sort_filter(self._notes))

    def filter_by_tag(self, tag: str):
        self._tag_filter = tag
        self.nb_label.setText(f"Tag: {tag}")
        self._render_notes(self._apply_sort_filter(storage.filter_by_tag(tag)))

    def filter_pinned_all(self):
        self._tag_filter = None
        self.nb_label.setText("\u2605 Pinned Notes")
        all_notes = []
        for nb in storage.list_notebooks():
            all_notes += [n for n in storage.list_notes(nb) if n.get("pinned")]
            for sec in storage.list_sections(nb):
                all_notes += [n for n in storage.list_notes(nb, sec) if n.get("pinned")]
        self._render_notes(self._apply_sort_filter(all_notes))

    def clear_tag_filter(self):
        self._tag_filter = None
        if self._current_notebook:
            label = (f"{self._current_notebook} / {self._current_section}"
                     if self._current_section else self._current_notebook)
            self.nb_label.setText(label)
            self._notes = storage.list_notes(self._current_notebook, self._current_section)
            self._render_notes(self._apply_sort_filter(self._notes))

    def refresh(self):
        if self._tag_filter:
            self._render_notes(self._apply_sort_filter(storage.filter_by_tag(self._tag_filter)))
        elif self._current_notebook:
            self._notes = storage.list_notes(self._current_notebook, self._current_section)
            self._render_notes(self._apply_sort_filter(self._notes))

    def _apply_sort_filter(self, notes: list[dict]) -> list[dict]:
        if self._filter_pinned:
            notes = [n for n in notes if n.get("pinned", False)]
        sort = self._sort_order
        key_map = {
            "updated_desc":  (lambda n: n.get("updated_at", ""),   True),
            "updated_asc":   (lambda n: n.get("updated_at", ""),   False),
            "title_asc":     (lambda n: n.get("title", "").lower(), False),
            "title_desc":    (lambda n: n.get("title", "").lower(), True),
            "priority_desc": (lambda n: n.get("priority", 0),      True),
            "created_desc":  (lambda n: n.get("created_at", ""),   True),
        }
        key_fn, reverse = key_map.get(sort, (lambda n: n.get("updated_at", ""), True))
        pinned = sorted(
            [n for n in notes if n.get("pinned", False)],
            key=lambda n: -n.get("priority", 0)
        )
        normal = sorted(
            [n for n in notes if not n.get("pinned", False)],
            key=key_fn, reverse=reverse
        )
        return pinned + normal

    def _render_notes(self, notes: list[dict]):
        self.list_widget.clear()
        if not notes:
            self._content_stack.setCurrentIndex(0)
            return
        self._content_stack.setCurrentIndex(1)
        for note in notes:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole,
                         (note["notebook"], note.get("section") or "", note["slug"]))
            item.setData(Qt.ItemDataRole.UserRole + 1,
                         {"pinned": note.get("pinned", False),
                          "priority": note.get("priority", 0)})
            widget = self._make_note_card(note)
            card_h = 58
            if note.get("tags"):
                card_h += 28
            item.setSizeHint(QSize(0, card_h))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

    def _make_note_card(self, note: dict) -> QWidget:
        t = self._theme
        priority = note.get("priority", 0)
        pinned   = note.get("pinned", False)

        outer = QWidget()
        outer.setStyleSheet("background: transparent;")
        hl = QHBoxLayout(outer)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        if priority > 0:
            _pcolors = {
                1: t.get("priority_low",  _PRIORITY_COLORS_FALLBACK[1]),
                2: t.get("priority_med",  _PRIORITY_COLORS_FALLBACK[2]),
                3: t.get("priority_high", _PRIORITY_COLORS_FALLBACK[3]),
            }
            bar = QFrame()
            bar.setFixedWidth(4)
            bar.setStyleSheet(
                f"background: {_pcolors[priority]}; border-radius: 2px; margin: 4px 0;"
            )
            hl.addWidget(bar)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        vl = QVBoxLayout(content)
        vl.setContentsMargins(12, 8, 12, 8)
        vl.setSpacing(3)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(4)
        title_lbl = QLabel(note["title"])
        title_lbl.setStyleSheet(f"color: {t['text2']}; font-weight: 600; font-size: 13px;")
        title_lbl.setWordWrap(True)
        title_row.addWidget(title_lbl, 1)
        if pinned:
            pin_icon = QLabel("\U0001f4cc")
            pin_icon.setStyleSheet("font-size: 10px;")
            pin_icon.setFixedWidth(16)
            title_row.addWidget(pin_icon)
        vl.addLayout(title_row)

        if note.get("tags"):
            tag_row = QHBoxLayout()
            tag_row.setContentsMargins(0, 0, 0, 0)
            tag_row.setSpacing(4)
            visible_tags = note["tags"][:3]
            extra = len(note["tags"]) - len(visible_tags)
            for tag in visible_tags:
                pill = TagPill(tag, removable=False)
                pill.apply_theme(t)
                tag_row.addWidget(pill)
            if extra > 0:
                more_lbl = QLabel(f"+{extra}")
                more_lbl.setStyleSheet(
                    f"color: {t['muted2']}; font-size: 10px; padding: 0 2px;"
                )
                more_lbl.setToolTip(", ".join(note["tags"][3:]))
                tag_row.addWidget(more_lbl)
            tag_row.addStretch()
            vl.addLayout(tag_row)

        date_lbl = QLabel(note.get("updated_at", "")[:10])
        date_lbl.setStyleSheet(f"color: {t['muted2']}; font-size: 10px;")
        vl.addWidget(date_lbl)

        hl.addWidget(content)
        return outer

    def _on_select(self, row):
        if row >= 0:
            item = self.list_widget.item(row)
            if item:
                nb, section, slug = item.data(Qt.ItemDataRole.UserRole)
                self.note_selected.emit(nb, section, slug)

    def _on_search(self, query: str):
        if not query.strip():
            if self._current_notebook:
                self._render_notes(self._apply_sort_filter(self._notes))
            return
        self._render_notes(self._apply_sort_filter(
            storage.search_notes(query, self._current_notebook)
        ))

    def _on_pin_filter_toggled(self):
        self._filter_pinned = self._pin_filter_btn.isChecked()
        s = load_settings()
        s["filter_pinned"] = self._filter_pinned
        save_settings(s)
        self.refresh()

    def _show_sort_menu(self):
        t = self._theme
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{ background: {t['bg3']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 4px; }}
            QMenu::item {{ padding: 6px 16px 6px 12px; border-radius: 5px; color: {t['text']}; margin: 1px 0; }}
            QMenu::item:selected {{ background: {t['item_sel']}; color: {t['text']}; }}
            QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 8px; }}
        """)
        acts = {}
        for key, label in _SORT_LABELS.items():
            a = menu.addAction(("\u2713 " if key == self._sort_order else "   ") + label)
            acts[a] = key
        chosen = menu.exec(self._sort_btn.mapToGlobal(self._sort_btn.rect().bottomLeft()))
        if chosen in acts:
            self._sort_order = acts[chosen]
            s = load_settings()
            s["note_sort"] = self._sort_order
            save_settings(s)
            self.refresh()

    def _show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        nb, section, slug = item.data(Qt.ItemDataRole.UserRole)
        extra = item.data(Qt.ItemDataRole.UserRole + 1) or {}
        is_pinned  = extra.get("pinned", False)
        priority   = extra.get("priority", 0)
        t = self._theme
        menu_ss = f"""
            QMenu {{ background: {t['bg3']}; color: {t['text']}; border: 1px solid {t['border']}; border-radius: 8px; padding: 4px; }}
            QMenu::item {{ padding: 6px 16px 6px 12px; border-radius: 5px; color: {t['text']}; margin: 1px 0; }}
            QMenu::item:selected {{ background: {t['item_sel']}; color: {t['text']}; }}
            QMenu::separator {{ height: 1px; background: {t['border']}; margin: 4px 8px; }}
        """
        menu = QMenu(self)
        menu.setStyleSheet(menu_ss)
        pin_act    = menu.addAction("\U0001f4cc  Unpin" if is_pinned else "\U0001f4cc  Pin")
        rename_act = menu.addAction("\u270f\ufe0f  Rename")
        prio_menu  = menu.addMenu("  Priority")
        prio_menu.setStyleSheet(menu_ss)
        prio_acts = {}
        for lvl, lbl in [(0, "None"), (1, "Low \u25cf"), (2, "Medium \u25cf"), (3, "High \u25cf")]:
            a = prio_menu.addAction(("\u2713 " if lvl == priority else "   ") + lbl)
            prio_acts[a] = lvl
        menu.addSeparator()
        del_act = menu.addAction("\U0001f5d1  Delete Note")

        act = menu.exec(self.list_widget.mapToGlobal(pos))
        if act == pin_act:
            self.pin_note_requested.emit(nb, section, slug)
        elif act == rename_act:
            note = storage.load_note(nb, slug, section or None)
            current_title = note.get("title", "") if note else ""
            new_title, ok = PromptDialog.get_text(
                self, "Rename Note", "New title",
                icon="✏️", text=current_title, theme=self._theme,
            )
            if ok and new_title.strip() and new_title.strip() != current_title:
                self.rename_note_requested.emit(nb, section, slug, new_title.strip())
        elif act in prio_acts:
            self.priority_changed.emit(nb, section, slug, prio_acts[act])
        elif act == del_act:
            if QMessageBox.question(self, "Delete", "Delete this note?") == QMessageBox.StandardButton.Yes:
                self.delete_note_requested.emit(nb, section, slug)
