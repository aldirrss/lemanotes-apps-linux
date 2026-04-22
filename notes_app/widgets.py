from PyQt6.QtWidgets import (
    QLabel, QPushButton, QWidget, QHBoxLayout, QVBoxLayout,
    QFrame, QListWidget, QListWidgetItem, QScrollArea,
    QTreeWidget, QTreeWidgetItem, QLineEdit, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QEvent
from PyQt6.QtGui import QColor, QDrag

from notes_app.themes import THEMES


_NOTE_MIME = "application/x-lemanotes-note"


# ─── Tag Pill ─────────────────────────────────────────────────────────────────

class TagPill(QLabel):
    removed = pyqtSignal(str)

    def __init__(self, tag: str, removable=True, parent=None):
        super().__init__(parent)
        self.tag = tag
        self.removable = removable
        text = f"  {tag}  \u00d7" if removable else f"  {tag}  "
        self.setText(text)
        self.setFixedHeight(22)
        self.setCursor(Qt.CursorShape.PointingHandCursor if removable else Qt.CursorShape.ArrowCursor)
        self._apply_colors("#2A4858", "#7FDBCA")

    def _apply_colors(self, bg: str, fg: str):
        self.setStyleSheet(f"""
            QLabel {{
                background: {bg};
                color: {fg};
                border-radius: 11px;
                padding: 0 4px;
                font-size: 11px;
            }}
        """)

    def apply_theme(self, t: dict):
        self._apply_colors(t["pill_bg"], t["pill_text"])

    def mousePressEvent(self, e):
        if self.removable:
            self.removed.emit(self.tag)


# ─── Tag Picker Popup ─────────────────────────────────────────────────────────

class TagPickerPopup(QFrame):
    tag_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setFixedWidth(240)
        self._theme = THEMES["dark"]
        self._suggestions: list[str] = []
        self._current_tags: list[str] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search or create tag\u2026")
        self._search.setFixedHeight(28)
        self._search.textChanged.connect(self._refresh)
        self._search.installEventFilter(self)
        layout.addWidget(self._search)

        self._list = QListWidget()
        self._list.setMaximumHeight(180)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

        self._apply_styles()

    def _apply_styles(self):
        t = self._theme
        self.setStyleSheet(f"""
            QFrame {{
                background: {t['bg2']};
                border: 1px solid {t['border']};
                border-radius: 6px;
            }}
        """)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {t['bg']}; color: {t['text']};
                border: 1px solid {t['border']}; border-radius: 4px;
                padding: 4px 8px; font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {t['accent']}; }}
        """)
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: {t['bg2']}; border: none; font-size: 12px;
                outline: none;
            }}
            QListWidget::item {{
                color: {t['text']}; padding: 5px 8px; border-radius: 3px;
            }}
            QListWidget::item:hover {{ background: {t['item_hover']}; }}
            QListWidget::item:selected {{
                background: {t['item_sel']}; color: {t['accent']};
            }}
        """)

    def apply_theme(self, t: dict):
        self._theme = t
        self._apply_styles()

    def show_at(self, pos, suggestions: list[str], current_tags: list[str]):
        self._suggestions = suggestions
        self._current_tags = current_tags
        self._search.clear()
        self._refresh("")
        self.adjustSize()
        x, y = pos.x(), pos.y()
        screen = QApplication.primaryScreen().availableGeometry()
        if x + self.width() > screen.right():
            x = screen.right() - self.width()
        if y + self.height() > screen.bottom():
            y = pos.y() - self.height()
        self.move(x, y)
        self.show()
        self._search.setFocus()

    def _refresh(self, query: str):
        self._list.clear()
        available = [t for t in self._suggestions if t not in self._current_tags]
        q = query.strip().lower()
        filtered = [t for t in available if q in t.lower()] if q else available
        for tag in filtered:
            self._list.addItem(tag)
        if q and q not in [t.lower() for t in filtered]:
            item = QListWidgetItem(f'+ Create "{query.strip()}"')
            item.setData(Qt.ItemDataRole.UserRole, "__create__")
            item.setForeground(QColor(self._theme["accent"]))
            self._list.addItem(item)
        if self._list.count():
            self._list.setCurrentRow(0)

    def _on_item_clicked(self, item: QListWidgetItem):
        self._emit_tag(item)

    def _accept_first(self):
        item = self._list.currentItem()
        if item:
            self._emit_tag(item)
        elif self._search.text().strip():
            tag = self._search.text().strip().lower()
            if tag:
                self.tag_selected.emit(tag)
                self.hide()

    def _emit_tag(self, item: QListWidgetItem):
        if item.data(Qt.ItemDataRole.UserRole) == "__create__":
            tag = self._search.text().strip().lower()
        else:
            tag = item.text().lower()
        if tag:
            self.tag_selected.emit(tag)
        self.hide()

    def eventFilter(self, obj, event):
        if obj is self._search and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.hide()
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._accept_first()
                return True
            if key == Qt.Key.Key_Down:
                row = self._list.currentRow()
                if row < self._list.count() - 1:
                    self._list.setCurrentRow(row + 1)
                return True
            if key == Qt.Key.Key_Up:
                row = self._list.currentRow()
                if row > 0:
                    self._list.setCurrentRow(row - 1)
                return True
        return super().eventFilter(obj, event)


# ─── Tag Bar ──────────────────────────────────────────────────────────────────

class TagBar(QWidget):
    tags_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tags: list[str] = []
        self._suggestions: list[str] = []
        self._theme = THEMES["dark"]

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self._add_btn = QPushButton("+ tag")
        self._add_btn.setFixedHeight(22)
        self._add_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._show_popup)
        self._layout.addWidget(self._add_btn)

        self._popup = TagPickerPopup()
        self._popup.tag_selected.connect(self._add_tag)

        self._update_btn_style()

    def _update_btn_style(self):
        t = self._theme
        self._add_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px dashed {t['border2']};
                color: {t['muted']};
                border-radius: 11px;
                font-size: 11px;
                padding: 0 8px;
            }}
            QPushButton:hover {{
                border-color: {t['accent']};
                color: {t['accent']};
                border-style: solid;
            }}
        """)

    def apply_theme(self, t: dict):
        self._theme = t
        self._update_btn_style()
        self._popup.apply_theme(t)
        for i in range(self._layout.count() - 1):
            w = self._layout.itemAt(i).widget()
            if isinstance(w, TagPill):
                w.apply_theme(t)

    def set_suggestions(self, tags: list[str]):
        self._suggestions = list(tags)

    def set_tags(self, tags: list[str]):
        self._tags = list(tags)
        self._rebuild()

    def get_tags(self) -> list[str]:
        return list(self._tags)

    def _rebuild(self):
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for tag in self._tags:
            pill = TagPill(tag, removable=True)
            pill.apply_theme(self._theme)
            pill.removed.connect(self._remove_tag)
            self._layout.insertWidget(self._layout.count() - 1, pill)

    def _show_popup(self):
        pos = self._add_btn.mapToGlobal(self._add_btn.rect().bottomLeft())
        self._popup.show_at(pos, self._suggestions, self._tags)

    def _add_tag(self, tag: str):
        tag = tag.strip().lower()
        if tag and tag not in self._tags:
            self._tags.append(tag)
            if tag not in self._suggestions:
                self._suggestions.append(tag)
                self._suggestions.sort()
            self._rebuild()
            self.tags_changed.emit(self._tags)

    def _remove_tag(self, tag: str):
        if tag in self._tags:
            self._tags.remove(tag)
            self._rebuild()
            self.tags_changed.emit(self._tags)


# ─── Drag & Drop Widgets ──────────────────────────────────────────────────────

class NoteListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)

    def startDrag(self, supported_actions):
        item = self.currentItem()
        if not item:
            return
        nb, section, slug = item.data(Qt.ItemDataRole.UserRole)
        mime = QMimeData()
        mime.setData(_NOTE_MIME, f"{nb}\x00{section}\x00{slug}".encode())
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)


class NotebookTreeWidget(QTreeWidget):
    note_dropped = pyqtSignal(str, str, str, str, str)  # (src_nb, src_sec, slug, dst_nb, dst_sec)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setIndentation(14)
        self.setAnimated(True)
        self.setExpandsOnDoubleClick(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(_NOTE_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(_NOTE_MIME):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        if not e.mimeData().hasFormat(_NOTE_MIME):
            e.ignore()
            return
        raw = e.mimeData().data(_NOTE_MIME).data().decode()
        parts = raw.split("\x00", 2)
        src_nb  = parts[0]
        src_sec = parts[1] if len(parts) > 1 else ""
        slug    = parts[2] if len(parts) > 2 else ""
        target_item = self.itemAt(e.position().toPoint())
        if not target_item:
            e.ignore()
            return
        dst_nb, dst_sec = target_item.data(0, Qt.ItemDataRole.UserRole)
        if dst_nb == src_nb and (dst_sec or "") == (src_sec or ""):
            e.ignore()
            return
        e.acceptProposedAction()
        self.note_dropped.emit(src_nb, src_sec, slug, dst_nb, dst_sec or "")
