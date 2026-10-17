"""Colours, fonts and the dark/light switch.

Every colour in the app comes from here. Functions take the overlay's hue;
colours that depend on the mode read the module state at call time, so
set_mode() followed by a re-theme is all it takes to flip the whole UI.
"""
from PySide6.QtGui import QColor, QFont, QPalette

# --- mode state (updated by set_mode) --------------------------------------
_MODE = "dark"
TEXT = "#e6eefc"
TEXT_MUTED = "rgba(230, 238, 252, 150)"
_INK = "255, 255, 255"      # colour of hover/border overlays: white on dark, navy on light

# Segoe UI on Windows; sensible equivalents elsewhere so the UI looks the same.
FONT_FAMILIES = ["Segoe UI", "Inter", "Cantarell", "Noto Sans", "Ubuntu", "DejaVu Sans", "sans-serif"]
FONT_UI = ", ".join(f'"{f}"' if " " in f else f for f in FONT_FAMILIES)
MONO_FAMILIES = ["Cascadia Mono", "Consolas", "JetBrains Mono", "DejaVu Sans Mono", "Monospace"]


def mode() -> str:
    return _MODE


def is_light() -> bool:
    return _MODE == "light"


def set_mode(new_mode: str) -> None:
    """'dark' or 'light'. Callers re-theme their windows afterwards."""
    global _MODE, TEXT, TEXT_MUTED, _INK
    _MODE = "light" if new_mode == "light" else "dark"
    if is_light():
        TEXT, TEXT_MUTED, _INK = "#14202b", "rgba(20, 32, 43, 150)", "12, 28, 48"
    else:
        TEXT, TEXT_MUTED, _INK = "#e6eefc", "rgba(230, 238, 252, 150)", "255, 255, 255"


def fg(alpha: float) -> str:
    """CSS colour for hover fills, borders and dividers (white on dark, navy on light)."""
    return f"rgba({_INK}, {alpha})"


def ui_font(pt: float, weight=None) -> QFont:
    f = QFont()
    f.setFamilies([n for n in FONT_FAMILIES if n != "sans-serif"])
    f.setStyleHint(QFont.SansSerif)
    f.setPointSizeF(pt)
    if weight is not None:
        f.setWeight(weight)
    return f


def mono_font(pt: float) -> QFont:
    f = QFont()
    f.setFamilies(MONO_FAMILIES)
    f.setStyleHint(QFont.Monospace)
    f.setPointSizeF(pt)
    return f


def _c(hue: int, s: float, l: float) -> QColor:
    return QColor.fromHslF((hue % 360) / 360.0, s, l)


def background(hue: int) -> QColor:
    return _c(hue, 0.45, 0.93) if is_light() else _c(hue, 0.55, 0.10)


def chrome(hue: int) -> QColor:
    return _c(hue, 0.40, 0.88) if is_light() else _c(hue, 0.55, 0.065)


def accent(hue: int) -> QColor:
    """Borders, focus rings and active states."""
    return _c(hue, 0.80, 0.38) if is_light() else _c(hue, 0.85, 0.62)


def accent_fill(hue: int) -> QColor:
    """Solid fill for primary buttons (white text sits on top)."""
    return _c(hue, 0.75, 0.42) if is_light() else _c(hue, 0.70, 0.38)


def page_backdrop(hue: int) -> QColor:
    """Colour behind PDF pages and other documents."""
    return background(hue).darker(108) if is_light() else background(hue).lighter(130)


def toolbutton_stylesheet() -> str:
    return f"""
        QToolButton {{
            background: transparent;
            border: none;
            border-radius: 4px;
            color: {TEXT};
        }}
        QToolButton:hover {{
            background: {fg(0.12)};
        }}
        QToolButton:pressed {{
            background: {fg(0.20)};
        }}
        QToolButton#close:hover, QToolButton#ItemBtnClose:hover {{
            background: {fg(0.12)};
            color: #e81123;
        }}
        QToolButton#close:pressed, QToolButton#ItemBtnClose:pressed {{
            background: {fg(0.20)};
            color: #e81123;
        }}
    """


def scrollbar_stylesheet(hue: int) -> str:
    acc = accent(hue).name()
    return f"""
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {fg(0.22)};
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover, QScrollBar::handle:vertical:pressed {{
            background: {acc};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
            background: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
            margin: 0px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: {fg(0.22)};
            min-width: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover, QScrollBar::handle:horizontal:pressed {{
            background: {acc};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
            background: none;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
    """


def app_palette(hue: int = 215) -> QPalette:
    """One explicit palette for the whole app.

    Without it, any widget we don't style by hand falls back to the OS palette:
    dark grey on Windows dark mode, white on a light Linux theme.
    """
    pal = QPalette()
    text = QColor(TEXT)
    muted = QColor(text)
    muted.setAlpha(150)
    if is_light():
        base, alt, window, button = _c(hue, 0.30, 0.98), _c(hue, 0.30, 0.95), _c(hue, 0.35, 0.94), _c(hue, 0.30, 0.90)
    else:
        base, alt, window, button = _c(hue, 0.30, 0.08), _c(hue, 0.30, 0.12), _c(hue, 0.30, 0.11), _c(hue, 0.30, 0.15)
    roles = {
        QPalette.Window: window, QPalette.WindowText: text, QPalette.Base: base,
        QPalette.AlternateBase: alt, QPalette.Text: text, QPalette.Button: button,
        QPalette.ButtonText: text, QPalette.ToolTipBase: button, QPalette.ToolTipText: text,
        QPalette.PlaceholderText: muted, QPalette.Highlight: accent_fill(hue),
        QPalette.HighlightedText: QColor("#ffffff"), QPalette.Link: accent(hue),
    }
    for role, color in roles.items():
        pal.setColor(role, color)
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, muted)
    return pal


dark_palette = app_palette   # old name, kept so nothing breaks
