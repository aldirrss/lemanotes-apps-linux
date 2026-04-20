import json
import shutil
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QFrame,
    QFileDialog, QDialog,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl, QObject, pyqtSlot
from PyQt6.QtGui import QKeySequence, QShortcut

from notes_app.themes import THEMES
from notes_app.shortcuts import _MANDATORY_SHORTCUTS
from notes_app.dialogs import InsertLinkDialog, InsertTableDialog, InsertCodeBlockDialog
from notes_app.widgets import TagBar
from notes_app import storage


_EDITOR_HTML = str(Path(__file__).parent.parent / "assets" / "editor.html")


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
