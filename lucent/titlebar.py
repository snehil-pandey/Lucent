"""Windows-style custom title bar: icon, title, address box, tools, min/max/close."""
import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QToolButton, QWidget

from . import glyphs, theme
from .icon import app_icon



def _button(glyph, tip, name="", size=(36, 32)):
    b = QToolButton()
    glyphs.set_glyph(b, glyph, hover="#e81123" if name == "close" else None)
    b.setToolTip(tip)
    b.setObjectName(name)
    b.setFixedSize(*size)
    b.setFocusPolicy(Qt.NoFocus)
    b.setCursor(Qt.ArrowCursor)
    return b


class TitleBar(QWidget):
    HEIGHT = 36

    new_overlay = Signal()
    collapse_clicked = Signal()
    settings_clicked = Signal(object)   # the button, so the popup can anchor to it
    click_through_toggled = Signal()
    invert_toggled = Signal()
    close_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(self.HEIGHT)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 0, 0)
        lay.setSpacing(6)

        self.logo = QLabel()
        self.logo.setPixmap(app_icon().pixmap(18, 18))
        self.title_label = QLabel("Lucent Overlay")
        self.title_label.setObjectName("title")

        self.btn_new = _button("new", "Add new overlay  (Ctrl+N)", "tool")
        self.btn_collapse = _button("collapse", "Collapse to icon  (Ctrl+K)", "tool")
        self.btn_invert = _button("invert", "Enhanced Readability / High-Contrast Mode  (Ctrl+I)", "tool")
        self.btn_ghost = _button("click_through", "Click-through / Ghost mode  (Ctrl+M)", "tool")
        self.btn_settings = _button("settings", "Overlay opacity, hue & options", "tool")
        self.btn_close = _button("close", "Close overlay", "close", (44, self.HEIGHT))

        self.btn_new.clicked.connect(self.new_overlay)
        self.btn_collapse.clicked.connect(self.collapse_clicked)
        self.btn_invert.clicked.connect(self.invert_toggled)
        self.btn_ghost.clicked.connect(self.click_through_toggled)
        self.btn_settings.clicked.connect(lambda: self.settings_clicked.emit(self.btn_settings))
        self.btn_close.clicked.connect(self.close_clicked)

        lay.addWidget(self.logo)
        lay.addWidget(self.title_label)
        lay.addStretch(1)
        for b in (self.btn_new, self.btn_collapse, self.btn_invert, self.btn_ghost, self.btn_settings, self.btn_close):
            lay.addWidget(b)

    # public API ---------------------------------------------------------
    def set_title(self, text: str):
        self.title_label.setText(text if text else "Lucent Overlay")

    def set_icon_pixmap(self, pm):
        self.logo.setPixmap(pm)

    def set_click_through(self, active: bool):
        glyphs.recolor(self.btn_ghost, "#4ade80" if active else None)
        self.btn_ghost.setToolTip("Click-through active (Ctrl+M to unlock)" if active else "Click-through / Ghost mode  (Ctrl+M)")

    def set_inverted(self, inverted: bool):
        self._inverted = inverted
        glyphs.recolor(self.btn_invert, "#38bdf8" if inverted else None)
        self.btn_invert.setToolTip("Enhanced Readability active (Ctrl+I)" if inverted else "Enhanced Readability / High-Contrast Mode  (Ctrl+I)")

    def apply_theme(self, hue: int):
        acc = theme.accent(hue).name()
        ch = theme.chrome(hue)
        ch_top = f"rgba({ch.red()}, {ch.green()}, {ch.blue()}, 0.94)"
        ch_mid = f"rgba({ch.red()}, {ch.green()}, {ch.blue()}, 0.72)"
        ch_bottom = f"rgba({ch.red()}, {ch.green()}, {ch.blue()}, 0.05)"
        self.setStyleSheet(f"""
            TitleBar {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0.0 {ch_top},
                    stop:0.75 {ch_mid},
                    stop:1.0 {ch_bottom});
                border-bottom: 1px solid {theme.fg(0.04)};
            }}
            QLabel#title {{ color: {theme.TEXT}; font-family: {theme.FONT_UI}; font-size: 9.5pt; font-weight: 600; }}
            QToolButton {{ background: transparent; border: none; color: {theme.TEXT}; }}
            QToolButton:hover {{ background: {theme.fg(0.12)}; }}
            QToolButton:pressed {{ background: {theme.fg(0.20)}; }}
            QToolButton#close:hover {{ background: {theme.fg(0.12)}; color: #e81123; }}
            QToolButton#close:pressed {{ background: {theme.fg(0.20)}; color: #e81123; }}
        """)
        glyphs.refresh(self)

    # window dragging ----------------------------------------------------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()
