from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDialogButtonBox, QLineEdit, QSpinBox, QComboBox,
    QPushButton, QLabel, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QHeaderView,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from notes_app.themes import THEMES
from notes_app.shortcuts import SHORTCUTS, _MANDATORY_SHORTCUTS


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
        self.url_input.setPlaceholderText("https://\u2026")
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
        for label, val in [
            ("─── Dark ───", None),
            ("Dark",         "dark"),
            ("Deep Sea",     "deep_sea"),
            ("Midnight",     "midnight"),
            ("Night Forest", "night_forest"),
            ("─── Light ───", None),
            ("Classic",      "classic"),
            ("Ocean",        "ocean"),
            ("Forest",       "forest"),
            ("Rose",         "rose"),
        ]:
            if val is None:
                self.theme_combo.addItem(label)
                self.theme_combo.model().item(
                    self.theme_combo.count() - 1
                ).setEnabled(False)
            else:
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
