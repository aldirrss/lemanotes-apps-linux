"""
Main window - Notes-Up clone with PyQt6
Features: Notebook sidebar, note list, WYSIWYG Markdown editor,
          tags, full-text search, dark/light theme toggle,
          rich formatting toolbar, find & replace, word count
"""

import sys
import json
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QSplitter,
    QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QLabel, QFrame,
    QScrollArea, QDialog, QDialogButtonBox, QInputDialog,
    QMessageBox, QMenu, QToolBar, QStatusBar, QSizePolicy,
    QTreeWidget, QTreeWidgetItem, QFileDialog,
    QSpinBox, QComboBox, QFormLayout, QTabWidget, QHeaderView,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize, QMimeData, QUrl, QObject, pyqtSlot, QEvent
from PyQt6.QtGui import (
    QAction, QIcon, QFont, QColor, QPalette,
    QKeySequence, QDrag, QShortcut,
)

from notes_app import storage
from notes_app.settings import load_settings, save_settings


# ─── Theme Definitions ────────────────────────────────────────────────────────

THEMES = {
    "dark": {
        "bg":           "#0D1B22",
        "bg2":          "#0A1820",
        "bg3":          "#0F2028",
        "bg4":          "#0F1E28",
        "code_bg":      "#132530",
        "border":       "#1A3A4A",
        "border2":      "#2A4A5A",
        "border3":      "#132530",
        "accent":       "#7FDBCA",
        "accent_fg":    "#0D1B22",
        "accent_hover": "#A0EDE0",
        "text":         "#C8DDE8",
        "text2":        "#D8EFF5",
        "muted":        "#8EAAB8",
        "muted2":       "#4A7A8A",
        "item_sel":     "#1A3A4A",
        "item_hover":   "#224050",
        "pill_bg":      "#2A4858",
        "pill_text":    "#7FDBCA",
        "placeholder":  "#2A5A6A",
        "empty_text":   "#2A5A6A",
        "search_text":  "#ccc",
        "tag_lbl":      "#4A7A8A",
        "theme_icon":   "\u2600",
    },
    "light": {
        "bg":           "#F5F7FA",
        "bg2":          "#FFFFFF",
        "bg3":          "#E8EEF4",
        "bg4":          "#F0F4F8",
        "code_bg":      "#EEF2F8",
        "border":       "#D0DBE3",
        "border2":      "#C0CDD5",
        "border3":      "#E0E8EF",
        "accent":       "#1A7A6A",
        "accent_fg":    "#FFFFFF",
        "accent_hover": "#12604F",
        "text":         "#1A2B35",
        "text2":        "#0A1B25",
        "muted":        "#5A7A8A",
        "muted2":       "#7A9BAA",
        "item_sel":     "#D0E4EE",
        "item_hover":   "#E4EDF4",
        "pill_bg":      "#C8E6E0",
        "pill_text":    "#1A7A6A",
        "placeholder":  "#A0BAC5",
        "empty_text":   "#A0BAC5",
        "search_text":  "#1A2B35",
        "tag_lbl":      "#5A7A8A",
        "theme_icon":   "\U0001f319",
    },
    "sepia": {
        "bg":           "#F4ECD8",
        "bg2":          "#EDE3CA",
        "bg3":          "#E8DCC0",
        "bg4":          "#F0E8D0",
        "code_bg":      "#E5D9BE",
        "border":       "#C8B896",
        "border2":      "#B8A880",
        "border3":      "#D8CAA8",
        "accent":       "#7A5C3A",
        "accent_fg":    "#F4ECD8",
        "accent_hover": "#5A3C1A",
        "text":         "#3C2A1A",
        "text2":        "#2A1A0A",
        "muted":        "#8A6A4A",
        "muted2":       "#A8886A",
        "item_sel":     "#D8C8A8",
        "item_hover":   "#E8D8B8",
        "pill_bg":      "#C8A878",
        "pill_text":    "#3C2A1A",
        "placeholder":  "#A89070",
        "empty_text":   "#A89070",
        "search_text":  "#3C2A1A",
        "tag_lbl":      "#8A6A4A",
        "theme_icon":   "\u2600",
    },
}


# ─── Shortcut Registry ────────────────────────────────────────────────────────

SHORTCUTS = [
    {"key": "Ctrl+B",       "label": "Bold",              "category": "Format"},
    {"key": "Ctrl+I",       "label": "Italic",            "category": "Format"},
    {"key": "Ctrl+Shift+S", "label": "Strikethrough",     "category": "Format"},
    {"key": "Ctrl+Shift+H", "label": "Highlight",         "category": "Format"},
    {"key": "Ctrl+K",       "label": "Insert Link",       "category": "Insert"},
    {"key": "Ctrl+Shift+I", "label": "Insert Image",      "category": "Insert"},
    {"key": "Ctrl+Shift+C", "label": "Insert Code Block", "category": "Insert"},
    {"key": "Ctrl+F",       "label": "Find",              "category": "Find"},
    {"key": "Ctrl+H",       "label": "Find & Replace",    "category": "Find"},
    {"key": "Ctrl+Z",       "label": "Undo",              "category": "Edit"},
    {"key": "Ctrl+Shift+Z", "label": "Redo",              "category": "Edit"},
    {"key": "Ctrl+N",       "label": "New Note",          "category": "App"},
    {"key": "Ctrl+Shift+N", "label": "New Notebook",      "category": "App"},
    {"key": "Ctrl+E",       "label": "Export PDF",        "category": "App"},
    {"key": "Ctrl+,",       "label": "Settings",          "category": "App"},
    {"key": "Ctrl+Shift+D", "label": "Cycle Theme",       "category": "App"},
]

_MANDATORY_SHORTCUTS = {"Ctrl+,", "Ctrl+Z"}


# ─── Insert Dialogs ───────────────────────────────────────────────────────────

def _dialog_style(t: dict) -> str:
    return f"""
        QDialog   {{ background: {t['bg3']}; color: {t['text']}; }}
        QLabel    {{ color: {t['muted']}; }}
        QLineEdit, QSpinBox, QComboBox {{
            background: {t['bg']}; color: {t['text']};
            border: 1px solid {t['border']}; border-radius: 4px;
            padding: 4px 8px;
        }}
        QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
            border-color: {t['accent']};
        }}
        QPushButton {{
            background: {t['item_sel']}; color: {t['accent']};
            border: 1px solid {t['border']}; border-radius: 4px;
            padding: 4px 14px;
        }}
        QPushButton:hover {{ background: {t['accent']}; color: {t['accent_fg']}; }}
        QPushButton:disabled {{ color: {t['muted2']}; }}
        QComboBox::drop-down {{ border: none; }}
        QComboBox QAbstractItemView {{
            background: {t['bg3']}; color: {t['text']};
            selection-background-color: {t['item_sel']};
        }}
    """


class InsertLinkDialog(QDialog):
    def __init__(self, parent=None, t=None):
        super().__init__(parent)
        t = t or THEMES["dark"]
        self.setWindowTitle("Insert Link")
        self.setModal(True)
        self.setFixedSize(420, 140)
        self.setStyleSheet(_dialog_style(t))

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://…")
        form.addRow("URL:", self.url_input)

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Link text (optional)")
        form.addRow("Text:", self.text_input)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok = btns.button(QDialogButtonBox.StandardButton.Ok)
        self._ok.setEnabled(False)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.url_input.textChanged.connect(
            lambda s: self._ok.setEnabled(bool(s.strip()))
        )

    def values(self):
        url = self.url_input.text().strip()
        text = self.text_input.text().strip() or url
        return url, text


class InsertTableDialog(QDialog):
    def __init__(self, parent=None, t=None):
        super().__init__(parent)
        t = t or THEMES["dark"]
        self.setWindowTitle("Insert Table")
        self.setModal(True)
        self.setFixedSize(300, 130)
        self.setStyleSheet(_dialog_style(t))

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setSpacing(8)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 30)
        self.rows_spin.setValue(3)
        form.addRow("Rows:", self.rows_spin)

        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 10)
        self.cols_spin.setValue(3)
        form.addRow("Columns:", self.cols_spin)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def values(self):
        return self.rows_spin.value(), self.cols_spin.value()


class InsertCodeBlockDialog(QDialog):
    _LANGS = [
        "", "python", "javascript", "typescript", "bash", "sh",
        "rust", "go", "java", "c", "cpp", "css", "html",
        "sql", "json", "yaml", "toml", "markdown",
    ]

    def __init__(self, parent=None, t=None):
        super().__init__(parent)
        t = t or THEMES["dark"]
        self.setWindowTitle("Insert Code Block")
        self.setModal(True)
        self.setFixedSize(300, 110)
        self.setStyleSheet(_dialog_style(t))

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        form = QFormLayout()
        form.setSpacing(8)

        self.lang_combo = QComboBox()
        self.lang_combo.addItem("(none)", "")
        for lang in self._LANGS[1:]:
            self.lang_combo.addItem(lang, lang)
        form.addRow("Language:", self.lang_combo)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def language(self) -> str:
        return self.lang_combo.currentData() or ""


class SettingsDialog(QDialog):
    def __init__(self, parent=None, t=None, current_theme="dark",
                 current_font_size=15, disabled_shortcuts=None):
        super().__init__(parent)
        t = t or THEMES["dark"]
        self._t = t
        self._original_theme = current_theme
        self._original_font_size = current_font_size
        self._original_disabled = list(disabled_shortcuts or [])
        self._preview_cb = None
        self._shortcuts_cb = None

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(520, 440)
        self.setMinimumSize(480, 380)
        self.setStyleSheet(_dialog_style(t))

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 12, 16, 12)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(self._tab_style())

        # ── Tab 1: Appearance ──
        ap_widget = QWidget()
        ap_layout = QVBoxLayout(ap_widget)
        ap_layout.setContentsMargins(16, 16, 16, 8)
        form = QFormLayout()
        form.setSpacing(10)

        self.theme_combo = QComboBox()
        for label, val in [("Dark", "dark"), ("Light", "light"), ("Sepia", "sepia")]:
            self.theme_combo.addItem(label, val)
        idx = self.theme_combo.findData(current_theme)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        form.addRow("Theme:", self.theme_combo)

        self.font_spin = QSpinBox()
        self.font_spin.setRange(10, 24)
        self.font_spin.setValue(current_font_size)
        self.font_spin.setSuffix(" px")
        form.addRow("Font size:", self.font_spin)

        ap_layout.addLayout(form)
        ap_layout.addStretch()
        self._tabs.addTab(ap_widget, "Appearance")

        self.theme_combo.currentIndexChanged.connect(self._on_preview)
        self.font_spin.valueChanged.connect(self._on_preview)

        # ── Tab 2: Shortcuts ──
        sc_widget = QWidget()
        sc_layout = QVBoxLayout(sc_widget)
        sc_layout.setContentsMargins(8, 8, 8, 4)

        self._sc_tree = QTreeWidget()
        self._sc_tree.setColumnCount(3)
        self._sc_tree.setHeaderLabels(["Action", "Shortcut", "Enabled"])
        self._sc_tree.setRootIsDecorated(True)
        self._sc_tree.setAnimated(True)
        self._sc_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._sc_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._sc_tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self._sc_tree.header().resizeSection(2, 64)
        self._sc_tree.setStyleSheet(self._tree_style())

        disabled_set = set(disabled_shortcuts or [])
        categories: dict[str, QTreeWidgetItem] = {}
        for sc in SHORTCUTS:
            cat = sc["category"]
            if cat not in categories:
                cat_item = QTreeWidgetItem(self._sc_tree, [cat, "", ""])
                cat_item.setExpanded(True)
                f = cat_item.font(0)
                f.setBold(True)
                cat_item.setFont(0, f)
                cat_item.setForeground(0, QColor(t["accent"]))
                categories[cat] = cat_item

            row = QTreeWidgetItem(categories[cat])
            row.setText(0, sc["label"])
            row.setText(1, sc["key"])
            row.setData(0, Qt.ItemDataRole.UserRole, sc["key"])
            is_mandatory = sc["key"] in _MANDATORY_SHORTCUTS
            is_enabled = sc["key"] not in disabled_set or is_mandatory
            row.setCheckState(2, Qt.CheckState.Checked if is_enabled else Qt.CheckState.Unchecked)
            if is_mandatory:
                row.setFlags(row.flags() & ~Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                row.setToolTip(2, "This shortcut cannot be disabled")

        sc_layout.addWidget(self._sc_tree)

        hint = QLabel("Uncheck to disable a shortcut. Greyed-out shortcuts are always active.")
        hint.setStyleSheet(f"color: {t['muted2']}; font-size: 10px; padding: 2px 4px;")
        sc_layout.addWidget(hint)
        self._tabs.addTab(sc_widget, "Shortcuts")

        self._sc_tree.itemChanged.connect(self._on_shortcut_changed)

        layout.addWidget(self._tabs)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self._on_cancel)
        layout.addWidget(btns)

    def _tab_style(self) -> str:
        t = self._t
        return f"""
            QTabWidget::pane {{
                border: 1px solid {t['border']}; background: {t['bg3']};
                border-radius: 0 4px 4px 4px;
            }}
            QTabBar::tab {{
                background: {t['bg']}; color: {t['muted']};
                padding: 6px 18px; border: 1px solid {t['border']};
                border-bottom: none; border-radius: 4px 4px 0 0; margin-right: 2px;
            }}
            QTabBar::tab:selected {{ background: {t['bg3']}; color: {t['accent']}; font-weight: 600; }}
            QTabBar::tab:hover:!selected {{ color: {t['text']}; }}
        """

    def _tree_style(self) -> str:
        t = self._t
        return f"""
            QTreeWidget {{
                background: {t['bg']}; color: {t['text']};
                border: 1px solid {t['border']}; border-radius: 4px; outline: none;
            }}
            QTreeWidget::item {{ padding: 3px 4px; }}
            QTreeWidget::item:selected {{ background: {t['item_sel']}; color: {t['accent']}; }}
            QTreeWidget::item:hover:!selected {{ background: {t['item_hover']}; }}
            QHeaderView::section {{
                background: {t['bg2']}; color: {t['muted']};
                border: none; border-bottom: 1px solid {t['border']};
                padding: 4px 8px; font-size: 11px;
            }}
            QScrollBar:vertical {{ background: {t['bg']}; width: 4px; }}
            QScrollBar::handle:vertical {{ background: {t['border']}; border-radius: 2px; }}
        """

    def set_preview_callback(self, cb):
        self._preview_cb = cb

    def set_shortcuts_callback(self, cb):
        self._shortcuts_cb = cb

    def _on_preview(self):
        if self._preview_cb:
            self._preview_cb(self.theme_combo.currentData(), self.font_spin.value())

    def _on_shortcut_changed(self, item: QTreeWidgetItem, column: int):
        if column != 2 or not item.data(0, Qt.ItemDataRole.UserRole):
            return
        if self._shortcuts_cb:
            self._shortcuts_cb(self._get_disabled())

    def _get_disabled(self) -> list[str]:
        disabled = []
        root = self._sc_tree.invisibleRootItem()
        for i in range(root.childCount()):
            cat_item = root.child(i)
            for j in range(cat_item.childCount()):
                row = cat_item.child(j)
                key = row.data(0, Qt.ItemDataRole.UserRole)
                if key and row.checkState(2) == Qt.CheckState.Unchecked:
                    disabled.append(key)
        return disabled

    def _on_cancel(self):
        if self._preview_cb:
            self._preview_cb(self._original_theme, self._original_font_size)
        if self._shortcuts_cb:
            self._shortcuts_cb(self._original_disabled)
        self.reject()

    def values(self):
        return self.theme_combo.currentData(), self.font_spin.value(), self._get_disabled()


# ─── Tag Pill Widget ──────────────────────────────────────────────────────────

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

_NOTE_MIME = "application/x-notesup-note"


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
    # (src_nb, src_sec, slug, dst_nb, dst_sec)
    note_dropped = pyqtSignal(str, str, str, str, str)

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


# ─── Notebook Sidebar ─────────────────────────────────────────────────────────

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
        self.setMinimumWidth(180)
        self.setMaximumWidth(250)

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
                border: none;
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

        # ★ Pinned Notes special filter
        pin_btn = QPushButton("  \u2605 Pinned Notes")
        pin_btn.setCheckable(True)
        pin_btn.setChecked(self._active_pinned_filter)
        pin_btn.setStyleSheet(self._tag_btn_style(t, special=True))
        pin_btn.clicked.connect(self._on_pinned_filter_clicked)
        self._tags_layout.addWidget(pin_btn)
        self._pin_filter_btn_ref = pin_btn

        for tag in storage.get_all_tags():
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
            QMenu {{ background: {t['bg3']}; color: {t['text']}; border: 1px solid {t['border']}; }}
            QMenu::item:selected {{ background: {t['item_sel']}; }}
        """)
        a_z = menu.addAction("Sort A \u2192 Z")
        z_a = menu.addAction("Sort Z \u2192 A")
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
            QMenu {{ background: {t['bg3']}; color: {t['text']}; border: 1px solid {t['border']}; }}
            QMenu::item:selected {{ background: {t['item_sel']}; }}
        """)

        if not sec:
            # Notebook item
            add_sec_act = menu.addAction("\U0001f4c4  Add Section")
            menu.addSeparator()
            rename_act = menu.addAction("Rename Notebook")
            delete_act = menu.addAction("Delete Notebook")
            act = menu.exec(e.globalPos())
            if act == add_sec_act:
                name, ok = QInputDialog.getText(self, "New Section", "Section name:")
                if ok and name.strip() and not name.strip().startswith("."):
                    if storage.create_section(nb, name.strip()):
                        sec_item = QTreeWidgetItem(item, [f"  \U0001f4c4  {name.strip()}"])
                        sec_item.setData(0, Qt.ItemDataRole.UserRole, (nb, name.strip()))
                        item.setExpanded(True)
            elif act == rename_act:
                new_name, ok = QInputDialog.getText(self, "Rename Notebook", "New name:", text=nb)
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
            # Section item
            rename_act = menu.addAction("Rename Section")
            delete_act = menu.addAction("Delete Section")
            act = menu.exec(e.globalPos())
            if act == rename_act:
                new_name, ok = QInputDialog.getText(self, "Rename Section", "New name:", text=sec)
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


# ─── Note List Panel ──────────────────────────────────────────────────────────

_PRIORITY_COLORS = {1: "#F5C518", 2: "#E87C2B", 3: "#E84040"}
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
        self._new_btn = QPushButton("\uff0b Note")
        self._new_btn.setFixedHeight(28)
        self._new_btn.clicked.connect(self.new_note_requested)
        tl.addWidget(self._new_btn)
        layout.addWidget(self._toolbar)

        self._search_wrap = QWidget()
        sl = QHBoxLayout(self._search_wrap)
        sl.setContentsMargins(12, 6, 12, 6)
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
        self._pin_filter_btn.clicked.connect(self._on_pin_filter_toggled)
        sbl.addWidget(self._pin_filter_btn)
        self._sort_btn = QPushButton("\u21c5 Sort")
        self._sort_btn.setFixedHeight(22)
        self._sort_btn.clicked.connect(self._show_sort_menu)
        sbl.addWidget(self._sort_btn)
        sbl.addStretch()
        layout.addWidget(self._sortbar)

        self._sep = QFrame()
        self._sep.setFrameShape(QFrame.Shape.HLine)
        self._sep.setFixedHeight(1)
        layout.addWidget(self._sep)

        self.list_widget = NoteListWidget()
        self.list_widget.currentRowChanged.connect(self._on_select)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.list_widget)

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
        """)
        self._sortbar.setStyleSheet(f"background: {t['bg4']};")
        _sb_btn = f"""
            QPushButton {{
                background: {t['item_sel']}; color: {t['muted']};
                border: 1px solid {t['border']}; border-radius: 10px;
                font-size: 10px; padding: 0 8px;
            }}
            QPushButton:hover {{ color: {t['accent']}; border-color: {t['accent']}; }}
            QPushButton:checked {{
                background: {t['accent']}; color: {t['accent_fg']};
                border-color: {t['accent']};
            }}
        """
        self._pin_filter_btn.setStyleSheet(_sb_btn)
        self._sort_btn.setStyleSheet(_sb_btn)
        self._sep.setStyleSheet(f"background: {t['border']};")
        self.list_widget.setStyleSheet(f"""
            QListWidget {{ background: {t['bg4']}; border: none; }}
            QListWidget::item {{ border-bottom: 1px solid {t['border3']}; padding: 0; }}
            QListWidget::item:selected {{ background: {t['item_sel']}; }}
            QListWidget::item:hover:!selected {{ background: {t['item_hover']}; }}
        """)

    def apply_theme(self, t: dict):
        self._theme = t
        self._apply_styles()
        if self._tag_filter:
            self._render_notes(storage.filter_by_tag(self._tag_filter))
        elif self._current_notebook:
            self._render_notes(self._notes)

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
        from notes_app import storage as _s
        all_notes = []
        for nb in _s.list_notebooks():
            all_notes += [n for n in _s.list_notes(nb) if n.get("pinned")]
            for sec in _s.list_sections(nb):
                all_notes += [n for n in _s.list_notes(nb, sec) if n.get("pinned")]
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
            "updated_desc":  (lambda n: n.get("updated_at", ""),  True),
            "updated_asc":   (lambda n: n.get("updated_at", ""),  False),
            "title_asc":     (lambda n: n.get("title", "").lower(), False),
            "title_desc":    (lambda n: n.get("title", "").lower(), True),
            "priority_desc": (lambda n: n.get("priority", 0),     True),
            "created_desc":  (lambda n: n.get("created_at", ""),  True),
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
        for note in notes:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole,
                         (note["notebook"], note.get("section") or "", note["slug"]))
            item.setData(Qt.ItemDataRole.UserRole + 1,
                         {"pinned": note.get("pinned", False),
                          "priority": note.get("priority", 0)})
            widget = self._make_note_card(note)
            item.setSizeHint(widget.sizeHint())
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

        # Priority color bar
        if priority > 0:
            bar = QFrame()
            bar.setFixedWidth(4)
            bar.setStyleSheet(
                f"background: {_PRIORITY_COLORS[priority]}; border-radius: 2px; margin: 4px 0;"
            )
            hl.addWidget(bar)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        vl = QVBoxLayout(content)
        vl.setContentsMargins(12, 8, 12, 8)
        vl.setSpacing(3)

        # Title row with optional pin icon
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
            for tag in note["tags"][:3]:
                pill = TagPill(tag, removable=False)
                pill.apply_theme(t)
                tag_row.addWidget(pill)
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
            QMenu {{ background: {t['bg3']}; color: {t['text']}; border: 1px solid {t['border']}; }}
            QMenu::item:selected {{ background: {t['item_sel']}; }}
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
            QMenu {{ background: {t['bg3']}; color: {t['text']}; border: 1px solid {t['border']}; }}
            QMenu::item:selected {{ background: {t['item_sel']}; }}
        """
        menu = QMenu(self)
        menu.setStyleSheet(menu_ss)
        pin_act  = menu.addAction("\U0001f4cc  Unpin" if is_pinned else "\U0001f4cc  Pin")
        prio_menu = menu.addMenu("  Priority")
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
        elif act in prio_acts:
            self.priority_changed.emit(nb, section, slug, prio_acts[act])
        elif act == del_act:
            if QMessageBox.question(self, "Delete", "Delete this note?") == QMessageBox.StandardButton.Yes:
                self.delete_note_requested.emit(nb, section, slug)


# ─── Editor Bridge ────────────────────────────────────────────────────────────

class EditorBridge(QObject):
    content_changed = pyqtSignal(str)
    editor_ready = pyqtSignal()
    format_changed = pyqtSignal(str)

    @pyqtSlot(str)
    def on_content_change(self, markdown: str):
        self.content_changed.emit(markdown)

    @pyqtSlot()
    def on_editor_ready(self):
        self.editor_ready.emit()

    @pyqtSlot(str)
    def on_format_change(self, json_str: str):
        self.format_changed.emit(json_str)


# ─── Editor Panel ─────────────────────────────────────────────────────────────

_EDITOR_HTML = str(Path(__file__).parent.parent / "assets" / "editor.html")


class EditorPanel(QWidget):
    note_saved = pyqtSignal()
    note_loaded = pyqtSignal(bool)
    pdf_export_done = pyqtSignal(str, bool)
    word_count_updated = pyqtSignal(str)
    pin_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = THEMES["dark"]
        self._theme_name = "dark"
        self._font_size = 15
        self._notebook = None
        self._section: str | None = None
        self._slug = None
        self._editor_ready = False
        self._pending_content: str | None = None

        self._pinned = False

        self._auto_save_timer = QTimer()
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.timeout.connect(self._auto_save)

        self._word_count_timer = QTimer()
        self._word_count_timer.setInterval(2000)
        self._word_count_timer.timeout.connect(self._poll_word_count)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Top bar (title) ──
        self._topbar = QWidget()
        self._topbar.setFixedHeight(52)
        tl = QHBoxLayout(self._topbar)
        tl.setContentsMargins(20, 0, 16, 0)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Note title\u2026")
        self.title_input.textChanged.connect(self._schedule_save)
        tl.addWidget(self.title_input)
        self._pin_btn = QPushButton("\u2606")
        self._pin_btn.setFixedSize(28, 28)
        self._pin_btn.setToolTip("Pin note")
        self._pin_btn.clicked.connect(self._toggle_pin)
        tl.addWidget(self._pin_btn)
        layout.addWidget(self._topbar)

        # ── Tag bar ──
        self._tag_wrap = QWidget()
        self._tag_wrap.setFixedHeight(36)
        tagl = QHBoxLayout(self._tag_wrap)
        tagl.setContentsMargins(20, 0, 16, 0)
        self._tag_icon = QLabel("\U0001f3f7")
        tagl.addWidget(self._tag_icon)
        self.tag_bar = TagBar()
        self.tag_bar.tags_changed.connect(self._schedule_save)
        tagl.addWidget(self.tag_bar)
        layout.addWidget(self._tag_wrap)

        # ── Formatting toolbar ──
        self._fmt_toolbar = QWidget()
        self._fmt_toolbar.setFixedHeight(36)
        fmtl = QHBoxLayout(self._fmt_toolbar)
        fmtl.setContentsMargins(10, 4, 10, 4)
        fmtl.setSpacing(3)

        self._fmt_buttons: list[QPushButton] = []
        self._fmt_dividers: list[QFrame] = []
        self._fmt_btn_map: dict[str, QPushButton] = {}

        def _btn(label: str, slot, tip: str = "",
                 name: str = "", checkable: bool = False) -> QPushButton:
            b = QPushButton(label)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            if tip:
                b.setToolTip(tip)
            if checkable:
                b.setCheckable(True)
            b.clicked.connect(slot)
            fmtl.addWidget(b)
            self._fmt_buttons.append(b)
            if name:
                self._fmt_btn_map[name] = b
            return b

        def _div():
            d = QFrame()
            d.setFrameShape(QFrame.Shape.VLine)
            d.setFixedWidth(1)
            fmtl.addWidget(d)
            self._fmt_dividers.append(d)

        # Undo / Redo
        _btn("\u21a9", lambda: self._js_cmd("undo"), "Undo (Ctrl+Z)")
        _btn("\u21aa", lambda: self._js_cmd("redo"), "Redo (Ctrl+Shift+Z)")
        _div()
        # Group 1: inline text
        _btn("B",   lambda: self._js_cmd("bold"),    "Bold (Ctrl+B)",
             name="bold",   checkable=True)
        _btn("I",   lambda: self._js_cmd("italic"),  "Italic (Ctrl+I)",
             name="italic", checkable=True)
        _btn("S\u0336", lambda: self._js_cmd("strike"), "Strikethrough (Ctrl+Shift+S)",
             name="strike", checkable=True)
        _btn("H\u0336", lambda: self._js_highlight(), "Highlight (Ctrl+Shift+H)")
        _btn("T\u0078\u0332",
             lambda: self._wysiwyg.page().runJavaScript("clearFormat()"),
             "Clear formatting")
        _div()
        # Group 2: headings
        _btn("H1", lambda: self._wysiwyg.page().runJavaScript("toggleHeading(1)"),
             "Heading 1", name="h1", checkable=True)
        _btn("H2", lambda: self._wysiwyg.page().runJavaScript("toggleHeading(2)"),
             "Heading 2", name="h2", checkable=True)
        _btn("H3", lambda: self._wysiwyg.page().runJavaScript("toggleHeading(3)"),
             "Heading 3", name="h3", checkable=True)
        _btn("\xb6",
             lambda: self._wysiwyg.page().runJavaScript("setParagraph()"),
             "Body text (normal paragraph)")
        _div()
        # Group 3: lists & blocks
        _btn("\u2022",  lambda: self._js_cmd("bulletList"),  "Bullet list",
             name="bulletList",  checkable=True)
        _btn("1.",      lambda: self._js_cmd("orderedList"), "Ordered list",
             name="orderedList", checkable=True)
        _btn("\u2611",  lambda: self._js_cmd("taskList"),    "Task list",
             name="taskList",    checkable=True)
        _btn("\u201c",  lambda: self._js_cmd("blockQuote"),  "Blockquote",
             name="blockquote",  checkable=True)
        _btn("\u2014",  lambda: self._js_cmd("hr"),          "Horizontal rule")
        _div()
        # Group 4: insert
        _btn("\U0001f517", self._insert_link,       "Insert link (Ctrl+K)")
        _btn("\U0001f5bc",  self._insert_image,      "Insert image (Ctrl+Shift+I)")
        _btn("\U0001f4cb", self._insert_table,      "Insert table")
        _btn("</>",        self._insert_code_block, "Insert code block (Ctrl+Shift+C)")

        fmtl.addStretch()
        self._fmt_toolbar.setEnabled(False)
        layout.addWidget(self._fmt_toolbar)

        # ── Find / Replace bar (hidden by default) ──
        self._find_bar = QWidget()
        fb_layout = QVBoxLayout(self._find_bar)
        fb_layout.setContentsMargins(10, 4, 10, 4)
        fb_layout.setSpacing(4)

        find_row = QHBoxLayout()
        find_row.setSpacing(4)
        self._find_lbl = QLabel("Find:")
        self._find_lbl.setFixedWidth(52)
        self._find_input = QLineEdit()
        self._find_input.setPlaceholderText("Search in note\u2026")
        self._find_input.textChanged.connect(self._on_find_changed)
        self._find_input.returnPressed.connect(self._find_next)
        self._find_prev_btn = QPushButton("\u25b2")
        self._find_prev_btn.setFixedSize(26, 26)
        self._find_prev_btn.setToolTip("Previous (Shift+F3)")
        self._find_prev_btn.clicked.connect(self._find_prev)
        self._find_next_btn = QPushButton("\u25bc")
        self._find_next_btn.setFixedSize(26, 26)
        self._find_next_btn.setToolTip("Next (F3)")
        self._find_next_btn.clicked.connect(self._find_next)
        self._find_close_btn = QPushButton("\u00d7")
        self._find_close_btn.setFixedSize(26, 26)
        self._find_close_btn.setToolTip("Close (Escape)")
        self._find_close_btn.clicked.connect(self.hide_find_bar)
        find_row.addWidget(self._find_lbl)
        find_row.addWidget(self._find_input)
        find_row.addWidget(self._find_prev_btn)
        find_row.addWidget(self._find_next_btn)
        find_row.addWidget(self._find_close_btn)
        fb_layout.addLayout(find_row)

        self._replace_row = QWidget()
        repl_row = QHBoxLayout(self._replace_row)
        repl_row.setContentsMargins(0, 0, 0, 0)
        repl_row.setSpacing(4)
        self._replace_lbl = QLabel("Replace:")
        self._replace_lbl.setFixedWidth(52)
        self._replace_input = QLineEdit()
        self._replace_input.setPlaceholderText("Replace with\u2026")
        self._replace_btn = QPushButton("Replace")
        self._replace_btn.setFixedHeight(26)
        self._replace_btn.clicked.connect(self._do_replace)
        self._replace_all_btn = QPushButton("All")
        self._replace_all_btn.setFixedHeight(26)
        self._replace_all_btn.clicked.connect(self._do_replace_all)
        repl_row.addWidget(self._replace_lbl)
        repl_row.addWidget(self._replace_input)
        repl_row.addWidget(self._replace_btn)
        repl_row.addWidget(self._replace_all_btn)
        fb_layout.addWidget(self._replace_row)
        self._replace_row.hide()

        self._find_bar.hide()
        layout.addWidget(self._find_bar)

        # ── WYSIWYG view ──
        self._wysiwyg = QWebEngineView()
        self._bridge = EditorBridge()
        self._bridge.content_changed.connect(self._schedule_save)
        self._bridge.editor_ready.connect(self._on_editor_ready)
        self._channel = QWebChannel()
        self._channel.registerObject("bridge", self._bridge)
        self._wysiwyg.page().setWebChannel(self._channel)
        self._wysiwyg.page().pdfPrintingFinished.connect(
            lambda path, ok: self.pdf_export_done.emit(path, ok)
        )
        self._wysiwyg.load(QUrl.fromLocalFile(_EDITOR_HTML))
        self._wysiwyg.hide()
        layout.addWidget(self._wysiwyg)

        # ── Empty state ──
        self.empty_label = QLabel("Select a note or create a new one")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)

        # ── Keyboard shortcuts ──
        self._sc_objects: list[QShortcut] = []
        self._register_shortcuts([])

        self._apply_styles()

    # ── Shortcuts ──────────────────────────────────────────────────────────────

    def _build_shortcut_map(self) -> dict:
        return {
            "Ctrl+Z":       (lambda: self._js_cmd("undo"),      self),
            "Ctrl+Shift+Z": (lambda: self._js_cmd("redo"),      self),
            "Ctrl+B":       (lambda: self._js_cmd("bold"),      self),
            "Ctrl+I":       (lambda: self._js_cmd("italic"),    self),
            "Ctrl+Shift+S": (lambda: self._js_cmd("strike"),    self),
            "Ctrl+Shift+H": (self._js_highlight,                self),
            "Ctrl+K":       (self._insert_link,                 self),
            "Ctrl+Shift+I": (self._insert_image,                self),
            "Ctrl+Shift+C": (self._insert_code_block,           self),
            "Ctrl+F":       (lambda: self.show_find_bar(False), self),
            "Ctrl+H":       (lambda: self.show_find_bar(True),  self),
        }

    def _register_shortcuts(self, disabled: list[str]):
        disabled_set = set(disabled)
        for key, (slot, parent) in self._build_shortcut_map().items():
            if key in disabled_set:
                continue
            sc = QShortcut(QKeySequence(key), parent)
            sc.activated.connect(slot)
            self._sc_objects.append(sc)
        for key, slot in [("F3", self._find_next), ("Shift+F3", self._find_prev)]:
            sc = QShortcut(QKeySequence(key), self)
            sc.activated.connect(slot)
            self._sc_objects.append(sc)
        sc = QShortcut(QKeySequence("Escape"), self._find_bar)
        sc.activated.connect(self.hide_find_bar)
        self._sc_objects.append(sc)

    def apply_shortcuts(self, disabled: list[str]):
        for sc in self._sc_objects:
            sc.setEnabled(False)
            sc.deleteLater()
        self._sc_objects = []
        self._register_shortcuts(disabled)

    # ── Theme ──────────────────────────────────────────────────────────────────

    def _apply_styles(self):
        t = self._theme
        self.setStyleSheet(f"background: {t['bg']};")
        self._topbar.setStyleSheet(
            f"background: {t['bg2']}; border-bottom: 1px solid {t['border']};"
        )
        self.title_input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent; border: none;
                color: {t['text2']}; font-size: 17px; font-weight: 700;
            }}
        """)
        self._pin_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: none;
                color: {t['muted2']}; font-size: 16px;
            }}
            QPushButton:hover {{ color: {t['accent']}; }}
        """)
        self._tag_wrap.setStyleSheet(
            f"background: {t['bg2']}; border-bottom: 1px solid {t['border3']};"
        )
        self._tag_icon.setStyleSheet(f"color: {t['tag_lbl']}; font-size: 12px;")
        self._fmt_toolbar.setStyleSheet(
            f"background: {t['bg2']}; border-bottom: 1px solid {t['border3']};"
        )
        btn_s = f"""
            QPushButton {{
                background: {t['item_sel']}; color: {t['accent']};
                border: 1px solid {t['border2']}; border-radius: 4px;
                font-size: 11px; font-weight: 700;
                padding: 0 6px; min-width: 24px; height: 22px;
            }}
            QPushButton:hover {{ background: {t['item_hover']}; }}
            QPushButton:pressed {{ background: {t['accent']}; color: {t['accent_fg']}; }}
            QPushButton:checked {{
                background: {t['accent']}; color: {t['accent_fg']};
                border-color: {t['accent']};
            }}
        """
        for btn in self._fmt_buttons:
            btn.setStyleSheet(btn_s)
        for div in self._fmt_dividers:
            div.setStyleSheet(f"background: {t['border']}; margin: 2px 2px;")

        # Find bar
        self._find_bar.setStyleSheet(
            f"background: {t['bg2']}; border-bottom: 1px solid {t['border3']};"
        )
        find_lbl_s = f"color: {t['muted']}; font-size: 11px;"
        self._find_lbl.setStyleSheet(find_lbl_s)
        self._replace_lbl.setStyleSheet(find_lbl_s)
        find_input_s = f"""
            QLineEdit {{
                background: {t['bg']}; color: {t['text']};
                border: 1px solid {t['border']}; border-radius: 4px;
                padding: 3px 8px; font-size: 12px;
            }}
            QLineEdit:focus {{ border-color: {t['accent']}; }}
        """
        self._find_input.setStyleSheet(find_input_s)
        self._replace_input.setStyleSheet(find_input_s)
        fb_btn_s = f"""
            QPushButton {{
                background: {t['item_sel']}; color: {t['accent']};
                border: 1px solid {t['border']}; border-radius: 4px;
                font-size: 11px; padding: 0 6px;
            }}
            QPushButton:hover {{ background: {t['accent']}; color: {t['accent_fg']}; }}
        """
        for b in (self._find_prev_btn, self._find_next_btn, self._find_close_btn,
                  self._replace_btn, self._replace_all_btn):
            b.setStyleSheet(fb_btn_s)

        self._wysiwyg.setStyleSheet(f"background: {t['bg']};")
        self.empty_label.setStyleSheet(f"color: {t['empty_text']}; font-size: 16px;")
        self.tag_bar.apply_theme(t)

    def apply_theme(self, t: dict, name: str):
        self._theme = t
        self._theme_name = name
        self._apply_styles()
        if self._editor_ready:
            self.set_theme(name)

    def set_theme(self, name: str):
        self._wysiwyg.page().runJavaScript(f"setTheme('{name}')")

    def set_font_size(self, size: int):
        self._font_size = size
        if self._editor_ready:
            self._wysiwyg.page().runJavaScript(f"setFontSize({size})")

    # ── Public API ─────────────────────────────────────────────────────────────

    def load_note(self, notebook: str, slug: str,
                  section: str | None = None):
        note = storage.load_note(notebook, slug, section)
        if not note:
            return
        self._notebook = notebook
        self._section = section
        self._slug = slug
        self._pinned = note.get("pinned", False)
        self._pin_btn.setText("\u2605" if self._pinned else "\u2606")
        self._pin_btn.setToolTip("Unpin note" if self._pinned else "Pin note")
        self.title_input.blockSignals(True)
        self.title_input.setText(note.get("title", ""))
        self.title_input.blockSignals(False)
        self.tag_bar.set_suggestions(storage.get_all_tags())
        self.tag_bar.set_tags(note.get("tags", []))
        md = note.get("content", "")
        if self._editor_ready:
            self._inject_content(md)
        else:
            self._pending_content = md
        self.empty_label.hide()
        self._wysiwyg.show()
        self._fmt_toolbar.setEnabled(True)
        self._word_count_timer.start()
        self.note_loaded.emit(True)

    def clear(self):
        self._notebook = None
        self._section = None
        self._slug = None
        self._pinned = False
        self._pin_btn.setText("\u2606")
        self._pin_btn.setToolTip("Pin note")
        self._pending_content = None
        if self._editor_ready:
            self._inject_content("")
        self._wysiwyg.hide()
        self.empty_label.show()
        self._fmt_toolbar.setEnabled(False)
        self.hide_find_bar()
        self._word_count_timer.stop()
        self.word_count_updated.emit("")
        self.note_loaded.emit(False)

    def export_pdf(self, output_path: str):
        self._wysiwyg.page().printToPdf(output_path)

    def _toggle_pin(self):
        if not self._notebook or not self._slug:
            return
        new_pinned = storage.toggle_pin(self._notebook, self._slug, self._section)
        self._pinned = new_pinned
        self._pin_btn.setText("\u2605" if new_pinned else "\u2606")
        self._pin_btn.setToolTip("Unpin note" if new_pinned else "Pin note")
        self.pin_toggled.emit(new_pinned)

    # ── Find & Replace ─────────────────────────────────────────────────────────

    def show_find_bar(self, replace_mode: bool = False):
        self._find_bar.show()
        self._replace_row.setVisible(replace_mode)
        self._find_input.setFocus()
        self._find_input.selectAll()

    def hide_find_bar(self):
        self._find_bar.hide()
        self._wysiwyg.page().findText("")
        self._wysiwyg.setFocus()

    def _on_find_changed(self, text: str):
        if text:
            self._wysiwyg.page().findText(text)
        else:
            self._wysiwyg.page().findText("")

    def _find_next(self):
        q = self._find_input.text()
        if q:
            self._wysiwyg.page().findText(q)

    def _find_prev(self):
        q = self._find_input.text()
        if q:
            self._wysiwyg.page().findText(q, QWebEnginePage.FindFlag.FindBackward)

    def _do_replace(self):
        find = self._find_input.text()
        if find:
            self._wysiwyg.page().runJavaScript(
                f"replaceInEditor({json.dumps(find)}, {json.dumps(self._replace_input.text())}, false)"
            )

    def _do_replace_all(self):
        find = self._find_input.text()
        if find:
            self._wysiwyg.page().runJavaScript(
                f"replaceInEditor({json.dumps(find)}, {json.dumps(self._replace_input.text())}, true)"
            )

    # ── Insert helpers ─────────────────────────────────────────────────────────

    def _insert_link(self):
        dlg = InsertLinkDialog(self, self._theme)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            url, text = dlg.values()
            self._wysiwyg.page().runJavaScript(
                f"insertLink({json.dumps(url)}, {json.dumps(text)})"
            )

    def _insert_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Insert Image", str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.gif *.webp *.svg)"
        )
        if not path:
            return
        use_path = path
        if self._notebook and self._slug:
            try:
                if self._section:
                    att_dir = storage.NOTES_ROOT / self._notebook / self._section / ".attachments" / self._slug
                else:
                    att_dir = storage.NOTES_ROOT / self._notebook / ".attachments" / self._slug
                att_dir.mkdir(parents=True, exist_ok=True)
                dest = att_dir / Path(path).name
                shutil.copy2(path, dest)
                use_path = str(dest)
            except Exception:
                pass
        alt = Path(path).stem
        self._wysiwyg.page().runJavaScript(
            f"insertImage({json.dumps('file://' + use_path)}, {json.dumps(alt)})"
        )

    def _insert_table(self):
        dlg = InsertTableDialog(self, self._theme)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            rows, cols = dlg.values()
            self._wysiwyg.page().runJavaScript(f"insertTable({rows}, {cols})")

    def _insert_code_block(self):
        dlg = InsertCodeBlockDialog(self, self._theme)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._wysiwyg.page().runJavaScript(
                f"insertCodeBlock({json.dumps(dlg.language())})"
            )

    def _js_highlight(self):
        self._wysiwyg.page().runJavaScript("highlightSelection()")

    def _on_format_changed(self, json_str: str):
        try:
            active = json.loads(json_str)
        except Exception:
            return
        for key in ("bold", "italic", "strike", "bulletList",
                    "orderedList", "taskList", "blockquote"):
            btn = self._fmt_btn_map.get(key)
            if btn:
                btn.blockSignals(True)
                btn.setChecked(bool(active.get(key, False)))
                btn.blockSignals(False)
        heading = active.get("heading", 0)
        for lvl in (1, 2, 3):
            btn = self._fmt_btn_map.get(f"h{lvl}")
            if btn:
                btn.blockSignals(True)
                btn.setChecked(heading == lvl)
                btn.blockSignals(False)

    # ── Word count ─────────────────────────────────────────────────────────────

    def _poll_word_count(self):
        if self._editor_ready:
            self._wysiwyg.page().runJavaScript(
                "getStats()",
                lambda s: self._emit_word_count(s)
            )

    def _emit_word_count(self, stats):
        if stats and isinstance(stats, dict):
            w = stats.get("words", 0)
            c = stats.get("chars", 0)
            self.word_count_updated.emit(f"{w:,} words \u00b7 {c:,} chars")

    # ── Internal ───────────────────────────────────────────────────────────────

    def _on_editor_ready(self):
        self._editor_ready = True
        self._bridge.format_changed.connect(self._on_format_changed)
        self.set_theme(self._theme_name)
        self.set_font_size(self._font_size)
        if self._pending_content is not None:
            self._inject_content(self._pending_content)
            self._pending_content = None

    def _inject_content(self, md: str):
        self._wysiwyg.page().runJavaScript(f"setContent({json.dumps(md)})")

    def _js_cmd(self, cmd: str, payload: str = "undefined"):
        self._wysiwyg.page().runJavaScript(f"execCmd('{cmd}', {payload})")

    def _schedule_save(self):
        self._auto_save_timer.start(800)

    def _auto_save(self):
        if not self._notebook or not self._slug:
            return
        nb, sec, slug = self._notebook, self._section, self._slug
        title = self.title_input.text()
        tags = self.tag_bar.get_tags()
        self._wysiwyg.page().runJavaScript(
            "getContent()",
            lambda md: self._do_save(nb, sec, slug, md, title, tags)
        )

    def _do_save(self, notebook: str, section: str | None, slug: str,
                 content: str, title: str, tags: list):
        if not content and not title:
            return
        storage.save_note(notebook, slug, content=content, title=title,
                          tags=tags, section=section)
        self.note_saved.emit()


# ─── Main Window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LemaNotes")
        self.resize(1200, 780)
        self.setMinimumSize(800, 500)
        self._current_notebook = None
        self._current_section: str | None = None

        settings = load_settings()
        self._theme_name = settings.get("theme", "dark")
        self._font_size = settings.get("font_size", 15)
        self._disabled_shortcuts: list[str] = settings.get("disabled_shortcuts", [])
        self._notebook_sort: str = settings.get("notebook_sort", "name_asc")

        self._build_ui()
        self._build_menu()
        self.editor_panel.note_loaded.connect(self._export_pdf_act.setEnabled)
        self.editor_panel.pdf_export_done.connect(self._on_pdf_exported)
        self.editor_panel.word_count_updated.connect(self._word_count_lbl.setText)
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
        cycle = {"dark": "light", "light": "sepia", "sepia": "dark"}
        self._apply_theme(cycle.get(self._theme_name, "dark"))

    def _register_menu_shortcuts(self, disabled: list[str]):
        disabled_set = set(disabled)
        menu_map = {
            "Ctrl+N":       self._new_note_act,
            "Ctrl+Shift+N": self._new_nb_act,
            "Ctrl+E":       self._export_pdf_act,
            "Ctrl+Shift+D": self._toggle_theme_act,
            "Ctrl+,":       self._settings_act,
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
        sort = self._notebook_sort
        if sort == "name_desc":
            nbs = sorted(nbs, reverse=True)
        elif sort == "manual":
            s = load_settings()
            order = s.get("notebook_order", [])
            ordered = [nb for nb in order if nb in nbs]
            remaining = [nb for nb in nbs if nb not in order]
            nbs = ordered + remaining
        self.sidebar.load_notebooks(nbs)
        self.sidebar.select_first()

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

    def _export_pdf(self):
        if not self.editor_panel._slug:
            return
        title = self.editor_panel.title_input.text().strip() or "note"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export as PDF", str(Path.home() / f"{title}.pdf"), "PDF Files (*.pdf)"
        )
        if path:
            self.editor_panel.export_pdf(path)

    def _on_pin_requested(self, notebook: str, section: str, slug: str):
        storage.toggle_pin(notebook, slug, section or None)
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
        self.note_list.refresh()

    def _on_note_pin_toggled(self, pinned: bool):
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
