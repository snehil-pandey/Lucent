"""Windows-style custom title bar: icon, title, address box, tools, min/max/close."""
import sys

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QToolButton, QWidget

from . import theme
from .icon import app_icon

WIN = sys.platform == "win32"
GLYPH = {
    "new": "\uE710" if WIN else "+",
    "open": "\uE8E5" if WIN else "▤",
    "hub": "\uE8C0" if WIN else "🗈",
    "invert": "\uE793" if WIN else "◐",
    "settings": "\uE713" if WIN else "⚙",
    "click_through": "\uE790" if WIN else "👻",
    "collapse": "\uE70E" if WIN else "▲",
    "expand": "\uE70D" if WIN else "▼",
    "full": "\uE740" if WIN else "⛶",
    "full_exit": "\uE73F" if WIN else "⛶",
    "min": "\uE921" if WIN else "–",
    "max": "\uE922" if WIN else "□",
    "restore": "\uE923" if WIN else "❐",
    "close": "\uE8BB" if WIN else "✕",
    "edit": "\uE70F" if WIN else "✎",
    "delete": "\uE74D" if WIN else "✕",
    "play": "\uE768" if WIN else "▶",
    "view": "\uE7B3" if WIN else "👁",
}


def _button(glyph, tip, name="", size=(36, 32)):
    b = QToolButton()
    b.setText(glyph)
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

        self.btn_new = _button(GLYPH["new"], "Add new overlay  (Ctrl+N)", "tool")
        self.btn_collapse = _button(GLYPH["collapse"], "Collapse to icon  (Ctrl+K)", "tool")
        self.btn_invert = _button(GLYPH["invert"], "Enhanced Readability / High-Contrast Mode  (Ctrl+I)", "tool")
        self.btn_ghost = _button(GLYPH["click_through"], "Click-through / Ghost mode  (Ctrl+M)", "tool")
        self.btn_settings = _button(GLYPH["settings"], "Overlay opacity, hue & options", "tool")
        self.btn_close = _button(GLYPH["close"], "Close overlay", "close", (44, self.HEIGHT))

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
        self.btn_ghost.setStyleSheet("color: #4ade80;" if active else "")
        self.btn_ghost.setToolTip("Click-through active (Ctrl+M to unlock)" if active else "Click-through / Ghost mode  (Ctrl+M)")

    def set_inverted(self, inverted: bool):
        self._inverted = inverted
        self.btn_invert.setStyleSheet("color: #38bdf8; font-weight: bold;" if inverted else "")
        self.btn_invert.setToolTip("Enhanced Readability active (Ctrl+I)" if inverted else "Enhanced Readability / High-Contrast Mode  (Ctrl+I)")

    def apply_theme(self, hue: int):
        acc = theme.accent(hue).name()
        self.setStyleSheet(f"""
            TitleBar {{ background: {theme.chrome(hue).name()}; }}
            QLabel#title {{ color: {theme.TEXT}; font: 600 9.5pt "Segoe UI"; }}
            QToolButton {{ background: transparent; border: none; color: {theme.TEXT};
                font-family: "Segoe MDL2 Assets"; font-size: 10pt; }}
            QToolButton:hover {{ background: rgba(255,255,255,0.12); }}
            QToolButton:pressed {{ background: rgba(255,255,255,0.20); }}
            QToolButton#close:hover {{ background: rgba(255,255,255,0.12); color: #e81123; }}
            QToolButton#close:pressed {{ background: rgba(255,255,255,0.20); color: #e81123; }}
        """)

    # window dragging ----------------------------------------------------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()
