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

    address_submitted = Signal(str)
    new_overlay = Signal()
    open_file = Signal()
    settings_clicked = Signal(object)   # the button, so the popup can anchor to it
    click_through_toggled = Signal()
    collapse_toggled = Signal()
    invert_toggled = Signal()
    hub_clicked = Signal()
    fullscreen_toggled = Signal()
    minimize_clicked = Signal()
    maximize_toggled = Signal()
    close_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedHeight(self.HEIGHT)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 0, 0, 0)
        lay.setSpacing(4)

        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(20, 20))
        title = QLabel("Lucent")
        title.setObjectName("title")
        self.address = QLineEdit()
        self.address.setPlaceholderText("Paste a link, path, or press Ctrl+V to paste clipboard")
        self.address.setClearButtonEnabled(True)
        self.address.returnPressed.connect(lambda: self.address_submitted.emit(self.address.text()))

        self.btn_new = _button(GLYPH["new"], "New overlay  (Ctrl+N)", "tool")
        self.btn_open = _button(GLYPH["open"], "Open file…  (Ctrl+O)", "tool")
        self.btn_hub = _button(GLYPH["hub"], "All Overlays Hub / Sticky Notes List (Ctrl+H)", "tool")
        self.btn_invert = _button(GLYPH["invert"], "Invert / Dark mode (Ctrl+I)", "tool")
        self.btn_ghost = _button(GLYPH["click_through"], "Click-through / Ghost mode (Ctrl+M)", "tool")
        self.btn_collapse = _button(GLYPH["collapse"], "Collapse / Shade window (Ctrl+K)", "tool")
        self.btn_settings = _button(GLYPH["settings"], "Opacity, hue & options", "tool")
        self.btn_full = _button(GLYPH["full"], "Full screen  (F11)", "tool")
        self.btn_min = _button(GLYPH["min"], "Minimize", "cap", (46, self.HEIGHT))
        self.btn_max = _button(GLYPH["max"], "Maximize", "cap", (46, self.HEIGHT))
        self.btn_close = _button(GLYPH["close"], "Close", "close", (46, self.HEIGHT))

        self.btn_new.clicked.connect(self.new_overlay)
        self.btn_open.clicked.connect(self.open_file)
        self.btn_hub.clicked.connect(self.hub_clicked)
        self.btn_invert.clicked.connect(self.invert_toggled)
        self.btn_ghost.clicked.connect(self.click_through_toggled)
        self.btn_collapse.clicked.connect(self.collapse_toggled)
        self.btn_settings.clicked.connect(lambda: self.settings_clicked.emit(self.btn_settings))
        self.btn_full.clicked.connect(self.fullscreen_toggled)
        self.btn_min.clicked.connect(self.minimize_clicked)
        self.btn_max.clicked.connect(self.maximize_toggled)
        self.btn_close.clicked.connect(self.close_clicked)

        lay.addWidget(logo)
        lay.addWidget(title)
        lay.addSpacing(8)
        lay.addWidget(self.address, 1)
        for b in (self.btn_new, self.btn_open, self.btn_hub, self.btn_invert, self.btn_ghost, self.btn_collapse, self.btn_settings, self.btn_full):
            lay.addWidget(b)
        lay.addSpacing(6)
        for b in (self.btn_min, self.btn_max, self.btn_close):
            lay.addWidget(b)

    # public API ---------------------------------------------------------
    def set_address(self, text: str):
        if not self.address.hasFocus():
            self.address.setText(text)
            self.address.setCursorPosition(0)

    def focus_address(self):
        self.address.setFocus()
        self.address.selectAll()

    def set_state(self, maximized: bool, fullscreen: bool):
        self.btn_max.setText(GLYPH["restore"] if maximized else GLYPH["max"])
        self.btn_full.setText(GLYPH["full_exit"] if fullscreen else GLYPH["full"])

    def set_collapsed(self, collapsed: bool):
        self.btn_collapse.setText(GLYPH["expand"] if collapsed else GLYPH["collapse"])
        self.btn_collapse.setToolTip("Expand window (Ctrl+K)" if collapsed else "Collapse window (Ctrl+K)")

    def set_click_through(self, active: bool):
        self.btn_ghost.setStyleSheet("color: #4ade80;" if active else "")
        self.btn_ghost.setToolTip("Click-through active (Ctrl+M to unlock)" if active else "Click-through / Ghost mode (Ctrl+M)")

    def set_inverted(self, inverted: bool):
        self.btn_invert.setStyleSheet("color: #38bdf8;" if inverted else "")
        self.btn_invert.setToolTip("Inverted / Dark Mode active (Ctrl+I)" if inverted else "Invert / Dark mode (Ctrl+I)")

    def apply_theme(self, hue: int):
        acc = theme.accent(hue).name()
        self.setStyleSheet(f"""
            TitleBar {{ background: {theme.chrome(hue).name()}; }}
            QLabel#title {{ color: {theme.TEXT}; font: 600 9.5pt "Segoe UI"; }}
            QLineEdit {{ background: rgba(255,255,255,0.08); color: {theme.TEXT};
                border: 1px solid rgba(255,255,255,0.10); border-radius: 4px;
                padding: 4px 8px; selection-background-color: {acc}; }}
            QLineEdit:focus {{ border: 1px solid {acc}; background: rgba(255,255,255,0.12); }}
            QToolButton {{ background: transparent; border: none; color: {theme.TEXT};
                font-family: "Segoe MDL2 Assets"; font-size: 10pt; }}
            QToolButton:hover {{ background: rgba(255,255,255,0.12); }}
            QToolButton:pressed {{ background: rgba(255,255,255,0.20); }}
            QToolButton#close:hover {{ background: #e81123; color: white; }}
        """)

    # window dragging ----------------------------------------------------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.window().windowHandle():
            self.window().windowHandle().startSystemMove()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.maximize_toggled.emit()
