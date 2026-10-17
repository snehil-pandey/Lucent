"""Vector UI glyphs, drawn in code.

Segoe MDL2 Assets only exists on Windows. Drawing the icons ourselves means the
title bar, Hub and flyouts look identical on every OS, with nothing to bundle.
Each icon is drawn on a 24x24 grid in a single colour, so the existing "active"
and "hover" colour states keep working: call set_glyph / recolor.
"""
import math

from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (QBrush, QColor, QGuiApplication, QIcon, QPainter,
                           QPainterPath, QPen, QPixmap, QPolygonF)
from PySide6.QtWidgets import QToolButton

from . import theme

DEFAULT_SIZE = 18
NAMES = ("sun", "moon", "new", "open", "hub", "invert", "settings", "click_through", "collapse",
         "expand", "close", "edit", "delete", "play", "view")


def _pt(x, y):
    return QPointF(x, y)


def _line(p, *pts):
    p.drawPolyline(QPolygonF([_pt(x, y) for x, y in pts]))


def _poly(p, *pts):
    p.drawPolygon(QPolygonF([_pt(x, y) for x, y in pts]))


def _new(p, c):
    _line(p, (12, 5), (12, 19))
    _line(p, (5, 12), (19, 12))


def _open(p, c):
    _poly(p, (3, 6), (10, 6), (12, 8.5), (21, 8.5), (21, 19), (3, 19))


def _hub(p, c):
    for x, y in ((4, 4), (13, 4), (4, 13), (13, 13)):
        p.drawRect(QRectF(x, y, 7, 7))


def _invert(p, c):
    p.drawEllipse(_pt(12, 12), 8, 8)
    half = QPainterPath()
    half.moveTo(12, 4)
    half.arcTo(QRectF(4, 4, 16, 16), 90, 180)
    half.closeSubpath()
    p.setBrush(QBrush(c))
    p.drawPath(half)


def _settings(p, c):
    """A toothed gear: 8 trapezoid teeth around a hub with a hole."""
    pts = []
    for i in range(8):
        base = math.tau * i / 8
        for off, r in ((-0.20, 6.6), (-0.12, 9.6), (0.12, 9.6), (0.20, 6.6)):
            pts.append((12 + math.cos(base + off) * r, 12 + math.sin(base + off) * r))
    _poly(p, *pts)
    p.drawEllipse(_pt(12, 12), 2.8, 2.8)


def _ghost(p, c):
    body = QPainterPath()
    body.moveTo(5, 20)
    body.lineTo(5, 11)
    body.arcTo(QRectF(5, 4, 14, 14), 180, -180)
    body.lineTo(19, 20)
    for x, y in ((16, 17.5), (12, 20), (8, 17.5), (5, 20)):
        body.lineTo(x, y)
    body.closeSubpath()
    p.drawPath(body)
    p.setBrush(QBrush(c))
    p.setPen(Qt.NoPen)
    p.drawEllipse(_pt(9.5, 11), 1.3, 1.6)
    p.drawEllipse(_pt(14.5, 11), 1.3, 1.6)


def _sun(p, c):
    p.setBrush(QBrush(c))
    p.drawEllipse(_pt(12, 12), 3.6, 3.6)
    for i in range(8):
        a = math.tau * i / 8
        _line(p, (12 + math.cos(a) * 6.8, 12 + math.sin(a) * 6.8),
              (12 + math.cos(a) * 9.8, 12 + math.sin(a) * 9.8))


def _moon(p, c):
    path = QPainterPath()
    path.moveTo(15.5, 4.5)
    path.arcTo(QRectF(4, 4, 16, 16), 62, 236)
    path.arcTo(QRectF(8.5, 2.5, 13, 13), 252, -190)
    path.closeSubpath()
    p.drawPath(path)


def _collapse(p, c):
    _line(p, (6, 15), (12, 9), (18, 15))


def _expand(p, c):
    _line(p, (6, 9), (12, 15), (18, 9))


def _close(p, c):
    _line(p, (6, 6), (18, 18))
    _line(p, (18, 6), (6, 18))


def _edit(p, c):
    _poly(p, (5, 19), (6, 14), (15, 5), (19, 9), (10, 18))
    _line(p, (13, 7), (17, 11))


def _delete(p, c):
    _line(p, (4.5, 7), (19.5, 7))
    _line(p, (9, 7), (9, 4.5), (15, 4.5), (15, 7))
    _poly(p, (6.5, 7), (7.8, 20), (16.2, 20), (17.5, 7))
    _line(p, (10.5, 10.5), (10.8, 16.5))
    _line(p, (13.5, 10.5), (13.2, 16.5))


def _play(p, c):
    p.setBrush(QBrush(c))
    _poly(p, (8, 5), (19, 12), (8, 19))


def _view(p, c):
    eye = QPainterPath()
    eye.moveTo(2.5, 12)
    eye.quadTo(12, 3, 21.5, 12)
    eye.quadTo(12, 21, 2.5, 12)
    p.drawPath(eye)
    p.setBrush(QBrush(c))
    p.drawEllipse(_pt(12, 12), 2.8, 2.8)


_DRAW = {
    "sun": _sun, "moon": _moon,
    "new": _new, "open": _open, "hub": _hub, "invert": _invert, "settings": _settings,
    "click_through": _ghost, "collapse": _collapse, "expand": _expand, "close": _close,
    "edit": _edit, "delete": _delete, "play": _play, "view": _view,
}


def render(name: str, color: str = None, size: int = DEFAULT_SIZE) -> QPixmap:
    screen = QGuiApplication.primaryScreen()
    dpr = max(1.0, math.ceil(screen.devicePixelRatio())) if screen else 1.0
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.setDevicePixelRatio(dpr)
    pm.fill(Qt.transparent)
    col = QColor(color or theme.TEXT)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(size / 24.0, size / 24.0)
    p.setPen(QPen(col, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    _DRAW[name](p, col)
    p.end()
    return pm


class _HoverSwap(QObject):
    """Swaps the button icon on hover so glyphs can turn e.g. red on a close button."""

    def __init__(self, btn):
        super().__init__(btn)
        self.btn = btn
        self.normal = QIcon()
        self.hover = QIcon()
        btn.installEventFilter(self)

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Enter:
            self.btn.setIcon(self.hover)
        elif ev.type() in (QEvent.Leave, QEvent.Hide):
            self.btn.setIcon(self.normal)
        return False


def set_glyph(btn, name: str, color: str = None, hover: str = None, size: int = DEFAULT_SIZE):
    """Put glyph `name` on a QToolButton.

    color=None means "the current text colour", which follows dark/light mode.
    `hover` is the colour while the mouse is over it.
    """
    swap = getattr(btn, "_glyph_swap", None)
    if swap is None:
        swap = btn._glyph_swap = _HoverSwap(btn)
    btn._glyph_name, btn._glyph_color = name, color
    btn._glyph_hover, btn._glyph_size = hover, size
    swap.normal = QIcon(render(name, color, size))
    swap.hover = QIcon(render(name, hover or color, size))
    btn.setText("")
    btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
    btn.setIconSize(QSize(size, size))
    btn.setIcon(swap.normal)


def recolor(btn, color: str = None, hover: str = None):
    """Change a glyph's colour, e.g. to show a toggled-on state. None = text colour."""
    set_glyph(btn, btn._glyph_name, color, hover or getattr(btn, "_glyph_hover", None),
              getattr(btn, "_glyph_size", DEFAULT_SIZE))


def refresh(root):
    """Re-render every glyph under `root`, e.g. after switching dark/light."""
    for btn in root.findChildren(QToolButton):
        if hasattr(btn, "_glyph_name"):
            set_glyph(btn, btn._glyph_name, btn._glyph_color, btn._glyph_hover, btn._glyph_size)
