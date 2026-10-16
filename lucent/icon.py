"""The Lucent icons: crescent moon, geometric symbols, and custom icon rendering.
Corners and styling reflect the abstract, smooth-yet-crisp Lucent aesthetic.
"""
import os
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QIcon, QLinearGradient, QPainter,
                           QPainterPath, QPixmap, QRadialGradient)

_R_OUTER = 0.34
_R_INNER = 0.30
_OFFSET = QPointF(0.15, -0.085)
_icon = None

ICON_PRESETS = ["moon", "star", "diamond", "hexagon", "sun", "note", "pin"]


def crescent_path(progress: float = 1.0) -> QPainterPath:
    """progress 0 = thin ring, 1 = full crescent (inner circle slides away)."""
    outer = QPainterPath()
    outer.addEllipse(QPointF(0.5, 0.5), _R_OUTER, _R_OUTER)
    inner = QPainterPath()
    centre = QPointF(0.5 + _OFFSET.x() * progress, 0.5 + _OFFSET.y() * progress)
    inner.addEllipse(centre, _R_INNER, _R_INNER)
    return outer.subtracted(inner)


def draw_moon(p: QPainter, rect: QRectF, progress=1.0, glow=0.0, opacity=1.0, rotation=0.0):
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.setOpacity(p.opacity() * opacity)
    p.translate(rect.center())
    p.rotate(rotation)
    p.scale(rect.width(), rect.height())
    p.translate(-0.5, -0.5)
    p.setPen(Qt.NoPen)
    if glow > 0:
        g = QRadialGradient(QPointF(0.5, 0.5), 0.7)
        g.setColorAt(0.0, QColor(90, 150, 255, int(120 * glow)))
        g.setColorAt(0.55, QColor(60, 110, 255, int(45 * glow)))
        g.setColorAt(1.0, QColor(60, 110, 255, 0))
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(0.5, 0.5), 0.7, 0.7)
    grad = QLinearGradient(0.25, 0.2, 0.75, 0.8)
    grad.setColorAt(0.0, QColor("#c4e3ff"))
    grad.setColorAt(1.0, QColor("#2f63ff"))
    p.setBrush(QBrush(grad))
    p.drawPath(crescent_path(progress))
    p.restore()


def draw_shape_icon(p: QPainter, rect: QRectF, shape: str = "moon", glow=0.0, opacity=1.0):
    """Draws one of the abstract Lucent geometric shapes with gradient coloring."""
    if shape == "moon":
        draw_moon(p, rect, glow=glow, opacity=opacity)
        return

    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.setOpacity(p.opacity() * opacity)
    p.translate(rect.center())
    p.scale(rect.width(), rect.height())
    p.translate(-0.5, -0.5)
    p.setPen(Qt.NoPen)

    grad = QLinearGradient(0.2, 0.2, 0.8, 0.8)
    grad.setColorAt(0.0, QColor("#c4e3ff"))
    grad.setColorAt(1.0, QColor("#2f63ff"))
    p.setBrush(QBrush(grad))

    path = QPainterPath()
    if shape == "star":
        # 4-pointed subtle star
        path.moveTo(0.5, 0.15)
        path.quadTo(0.5, 0.5, 0.85, 0.5)
        path.quadTo(0.5, 0.5, 0.5, 0.85)
        path.quadTo(0.5, 0.5, 0.15, 0.5)
        path.quadTo(0.5, 0.5, 0.5, 0.15)
    elif shape == "diamond":
        path.moveTo(0.5, 0.15)
        path.lineTo(0.85, 0.5)
        path.lineTo(0.5, 0.85)
        path.lineTo(0.15, 0.5)
        path.closeSubpath()
    elif shape == "hexagon":
        path.moveTo(0.5, 0.15)
        path.lineTo(0.82, 0.32)
        path.lineTo(0.82, 0.68)
        path.lineTo(0.5, 0.85)
        path.lineTo(0.18, 0.68)
        path.lineTo(0.18, 0.32)
        path.closeSubpath()
    elif shape == "sun":
        path.addEllipse(QPointF(0.5, 0.5), 0.22, 0.22)
        for i in range(8):
            angle = i * 45
            p.save()
            p.translate(0.5, 0.5)
            p.rotate(angle)
            p.setPen(QColor("#c4e3ff"))
            p.drawLine(0, 28, 0, 36)
            p.restore()
    elif shape == "note":
        # Abstract sticky note shape
        path.addRoundedRect(0.2, 0.2, 0.6, 0.6, 0.08, 0.08)
    elif shape == "pin":
        path.addEllipse(QPointF(0.5, 0.35), 0.18, 0.18)
        path.moveTo(0.42, 0.45)
        path.lineTo(0.5, 0.82)
        path.lineTo(0.58, 0.45)
    else:
        draw_moon(p, rect, glow=glow, opacity=opacity)
        p.restore()
        return

    p.drawPath(path)
    p.restore()


def render_overlay_pixmap(size: int, icon_name: str = "moon", icon_file: str = None) -> QPixmap:
    """Renders a pixmap of the specified size for an overlay window or titlebar."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)

    if icon_file and os.path.isfile(icon_file):
        custom = QPixmap(icon_file)
        if not custom.isNull():
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            p.drawPixmap(0, 0, size, size, custom)
            p.end()
            return pm

    p = QPainter(pm)
    pad = -size * 0.15
    draw_shape_icon(p, QRectF(pad, pad, size * 1.3, size * 1.3), shape=icon_name)
    p.end()
    return pm


def app_icon() -> QIcon:
    global _icon
    if _icon is None:
        _icon = QIcon()
        for size in (16, 20, 24, 32, 48, 64, 128, 256):
            pm = render_overlay_pixmap(size, "moon")
            _icon.addPixmap(pm)
    return _icon
