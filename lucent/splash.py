"""Animated startup: a crescent slides open, glows, and the name fades in."""
import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QGuiApplication, QPainter,
                           QRadialGradient)
from PySide6.QtWidgets import QWidget

from . import winapi
from .icon import draw_moon


def _clamp(x):
    return max(0.0, min(1.0, x))


def _smooth(x):
    x = _clamp(x)
    return x * x * (3 - 2 * x)


def _ease_out(x):
    return 1 - (1 - _clamp(x)) ** 3


class Splash(QWidget):
    handoff = Signal()   # fired near the end so the first overlay can appear under the fade
    finished = Signal()
    DURATION = 2800

    def __init__(self):
        super().__init__(None, Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(460, 460)
        geo = QGuiApplication.primaryScreen().availableGeometry()
        self.move(geo.center() - self.rect().center())

        rng = random.Random(7)
        self._stars = [
            (rng.uniform(0, math.tau), math.sqrt(rng.random()), rng.uniform(0.8, 2.2), rng.random())
            for _ in range(26)
        ]
        self._t = 0.0
        self._handed = False
        self._anim = QVariantAnimation(self)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setDuration(self.DURATION)
        self._anim.valueChanged.connect(self._tick)
        self._anim.finished.connect(self._done)

    def play(self):
        self.show()
        self._anim.start()

    def mousePressEvent(self, e):
        self._anim.stop()
        self._done()

    def keyPressEvent(self, e):
        self._anim.stop()
        self._done()

    def showEvent(self, e):
        super().showEvent(e)
        winapi.set_capture_hidden(self, True)

    def _tick(self, v):
        self._t = float(v)
        if not self._handed and self._t >= 0.84:
            self._handed = True
            self.handoff.emit()
        self.update()

    def _done(self):
        if not self._handed:
            self._handed = True
            self.handoff.emit()
        self.close()
        self.finished.emit()
        self.deleteLater()

    def paintEvent(self, _):
        t = self._t
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setOpacity(1.0 - _smooth((t - 0.86) / 0.14))
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2 - 10

        intro = _smooth(t / 0.2)
        g = QRadialGradient(QPointF(cx, cy), 215)
        g.setColorAt(0.0, QColor(10, 18, 45, int(235 * intro)))
        g.setColorAt(0.75, QColor(8, 14, 36, int(210 * intro)))
        g.setColorAt(1.0, QColor(8, 14, 36, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(g))
        p.drawEllipse(QPointF(cx, cy), 215, 215)

        for ang, rad, size, ph in self._stars:
            a = _smooth((t - 0.1 - ph * 0.3) / 0.2) * (0.45 + 0.55 * abs(math.sin(t * 10 + ph * 6.28)))
            p.setBrush(QColor(200, 225, 255, int(200 * a)))
            p.drawEllipse(QPointF(cx + math.cos(ang) * rad * 185, cy + math.sin(ang) * rad * 185), size, size)

        prog = _ease_out((t - 0.08) / 0.5)
        glow = _smooth((t - 0.3) / 0.4) * (0.8 + 0.2 * math.sin(t * 14))
        size = 170
        draw_moon(p, QRectF(cx - size / 2, cy - size / 2 - 8, size, size),
                  progress=prog, glow=glow, opacity=_clamp(t / 0.18), rotation=-70 * (1 - prog))

        ta = _smooth((t - 0.5) / 0.25)
        font = QFont("Segoe UI", 26)
        font.setWeight(QFont.Weight.Light)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 9)
        p.setFont(font)
        p.setPen(QColor(220, 234, 255, int(255 * ta)))
        p.drawText(QRectF(0, cy + 88 + (1 - ta) * 12, w, 50), Qt.AlignHCenter | Qt.AlignVCenter, "Lucent")
        p.end()
