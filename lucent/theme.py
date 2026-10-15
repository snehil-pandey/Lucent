from PySide6.QtGui import QColor

TEXT = "#e6eefc"


def _c(hue: int, s: float, l: float) -> QColor:
    return QColor.fromHslF((hue % 360) / 360.0, s, l)


def background(hue: int) -> QColor:
    return _c(hue, 0.55, 0.10)


def chrome(hue: int) -> QColor:
    return _c(hue, 0.55, 0.065)


def accent(hue: int) -> QColor:
    return _c(hue, 0.85, 0.62)
