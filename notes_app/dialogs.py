from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QDialogButtonBox, QLineEdit, QSpinBox, QComboBox,
    QPushButton, QLabel, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QHeaderView, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QByteArray, QSize
from PyQt6.QtGui import QColor, QPixmap, QIcon

from notes_app.themes import THEMES
from notes_app.shortcuts import SHORTCUTS, _MANDATORY_SHORTCUTS

_GITHUB_SVG = b"""<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
<path fill="white" d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387
.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416
-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729
1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997
.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931
0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176
0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0 1 12 5.803c1.02.005
2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653
.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807
5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694
.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z"/>
</svg>"""

_GOOGLE_SVG = b"""<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
<path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92
c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
<path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77
c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84
C3.99 20.53 7.7 23 12 23z"/>
<path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43
.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z"/>
<path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15
C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84
c.87-2.6 3.3-4.53 6.16-4.53z"/>
</svg>"""


def _svg_icon(svg_bytes: bytes, size: int = 18) -> QIcon:
    pm = QPixmap()
    pm.loadFromData(QByteArray(svg_bytes), "SVG")
    return QIcon(pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation))


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


# ─── Supabase Setup Dialog ─────────────────────────────────────────────────────

class SyncSetupDialog(QDialog):
    def __init__(self, parent=None, t=None):
        super().__init__(parent)
        t = t or THEMES["dark"]
        self.setWindowTitle("Setup Supabase")
        self.setModal(True)
        self.setFixedSize(460, 200)
        self.setStyleSheet(_dialog_style(t))

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 16, 20, 16)

        info = QLabel(
            "Get your URL and Anon Key from\n"
            "Supabase Dashboard → Project Settings → API"
        )
        info.setStyleSheet(f"color: {t['muted']}; font-size: 11px;")
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(8)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://xxxx.supabase.co")
        form.addRow("Project URL:", self.url_input)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("eyJhbGciOiJIUzI1NiIs...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Anon Key:", self.key_input)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self._save_btn = btns.button(QDialogButtonBox.StandardButton.Save)
        self._save_btn.setText("Save & Connect")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.url_input.textChanged.connect(self._check_ready)
        self.key_input.textChanged.connect(self._check_ready)
        self._check_ready()

    def _check_ready(self):
        ok = bool(self.url_input.text().strip() and self.key_input.text().strip())
        self._save_btn.setEnabled(ok)

    def values(self) -> tuple[str, str]:
        return self.url_input.text().strip(), self.key_input.text().strip()


# ─── Login Dialog ──────────────────────────────────────────────────────────────

class LoginDialog(QDialog):
    oauth_requested = pyqtSignal(str)  # provider name

    def __init__(self, parent=None, t=None):
        super().__init__(parent)
        t = t or THEMES["dark"]
        self._t = t
        self.setWindowTitle("Login — LemaNotes Sync")
        self.setModal(True)
        self.setFixedSize(380, 320)
        self.setStyleSheet(_dialog_style(t))

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(24, 20, 24, 16)

        title = QLabel("☁  Sync Across Devices")
        title.setStyleSheet(f"color: {t['accent']}; font-weight: 700; font-size: 14px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("you@example.com")
        form.addRow("Email:", self.email_input)

        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Password")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Password:", self.pass_input)

        layout.addLayout(form)

        self._err_lbl = QLabel("")
        self._err_lbl.setStyleSheet(f"color: #e84040; font-size: 11px;")
        self._err_lbl.setWordWrap(True)
        self._err_lbl.hide()
        layout.addWidget(self._err_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._login_btn = QPushButton("Login")
        self._login_btn.setEnabled(False)
        self._login_btn.clicked.connect(self.accept)
        self._register_btn = QPushButton("Register")
        self._register_btn.setEnabled(False)
        self._register_btn.setProperty("secondary", True)
        self._register_btn.clicked.connect(lambda: self.done(2))
        btn_row.addWidget(self._login_btn)
        btn_row.addWidget(self._register_btn)
        layout.addLayout(btn_row)

        sep_lbl = QLabel("── or continue with ──")
        sep_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sep_lbl.setStyleSheet(f"color: {t['muted2']}; font-size: 10px;")
        layout.addWidget(sep_lbl)

        oauth_row = QHBoxLayout()
        oauth_row.setSpacing(8)
        gh_btn = QPushButton("  GitHub")
        gh_btn.setIcon(_svg_icon(_GITHUB_SVG, 18))
        gh_btn.setIconSize(QSize(18, 18))
        gh_btn.clicked.connect(lambda: self._on_oauth("github"))
        gh_btn.setStyleSheet(
            "QPushButton { background: #24292f; color: #ffffff; border: none;"
            " border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { background: #3a3f46; }"
        )
        gg_btn = QPushButton("  Google")
        gg_btn.setIcon(_svg_icon(_GOOGLE_SVG, 18))
        gg_btn.setIconSize(QSize(18, 18))
        gg_btn.clicked.connect(lambda: self._on_oauth("google"))
        gg_btn.setStyleSheet(
            "QPushButton { background: #ffffff; color: #3c4043; border: 1px solid #dadce0;"
            " border-radius: 6px; padding: 6px 14px; font-size: 12px; font-weight: 600; }"
            "QPushButton:hover { background: #f8f9fa; border-color: #c0c0c0; }"
        )
        oauth_row.addWidget(gh_btn)
        oauth_row.addWidget(gg_btn)
        layout.addLayout(oauth_row)

        setup_btn = QPushButton("⚙  Configure Supabase URL & Key")
        setup_btn.setStyleSheet(
            f"QPushButton {{ background: transparent; color: {t['muted']}; "
            f"border: none; font-size: 10px; padding: 0; }}"
            f"QPushButton:hover {{ color: {t['accent']}; }}"
        )
        setup_btn.clicked.connect(lambda: self.done(3))
        layout.addWidget(setup_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.email_input.textChanged.connect(self._check_ready)
        self.pass_input.textChanged.connect(self._check_ready)
        self.pass_input.returnPressed.connect(self._login_btn.click)

        self._login_btn.setStyleSheet(self._btn_style(t, primary=True))
        self._register_btn.setStyleSheet(self._btn_style(t, primary=False))

    def _btn_style(self, t: dict, primary: bool) -> str:
        bg = t["accent"] if primary else t["item_sel"]
        fg = t["accent_fg"] if primary else t["text"]
        hover = t["accent_hover"] if primary else t["border2"]
        return (f"QPushButton {{ background: {bg}; color: {fg}; border: 1px solid {t['border']}; "
                f"border-radius: 4px; padding: 5px 14px; font-size: 12px; }}"
                f"QPushButton:hover {{ background: {hover}; }}"
                f"QPushButton:disabled {{ color: {t['muted2']}; }}")

    def _check_ready(self):
        ok = bool(self.email_input.text().strip() and self.pass_input.text())
        self._login_btn.setEnabled(ok)
        self._register_btn.setEnabled(ok)

    def _on_oauth(self, provider: str):
        self.oauth_requested.emit(provider)
        self.done(4)  # distinct code — not Accepted(1), Register(2), or Setup(3)

    def show_error(self, msg: str):
        self._err_lbl.setText(msg)
        self._err_lbl.show()

    def values(self) -> tuple[str, str]:
        return self.email_input.text().strip(), self.pass_input.text()
