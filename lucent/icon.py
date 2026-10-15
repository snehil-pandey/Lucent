"""The Lucent crescent moon, drawn in code so there are no asset files."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QIcon, QLinearGradient, QPainter,
                           QPainterPath, QPixmap, QRadialGradient)

_R_OUTER = 0.34
_R_INNER = 0.30
_OFFSET = QPointF(0.15, -0.085)
_icon = None


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


def app_icon() -> QIcon:
    global _icon
    if _icon is None:
        _icon = QIcon()
        for size in (16, 20, 24, 32, 48, 64, 128, 256):
            pm = QPixmap(size, size)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            pad = -size * 0.15
            draw_moon(p, QRectF(pad, pad, size * 1.3, size * 1.3))
            p.end()
            _icon.addPixmap(pm)
    return _icon
