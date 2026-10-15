from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import QLabel, QVBoxLayout

from ..icon import draw_moon
from .base import Viewer


class EmptyViewer(Viewer):
    """Faint hint shown when nothing is open."""

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        s = max(60.0, min(220.0, min(w, h) * 0.32))
        draw_moon(p, QRectF((w - s) / 2, h / 2 - s * 0.9, s, s), opacity=0.25)

        f = QFont("Segoe UI", 13)
        p.setFont(f)
        p.setPen(QColor(220, 232, 255, 150))
        p.drawText(QRectF(0, h / 2 + s * 0.15, w, 30), Qt.AlignCenter, "Drop a file here, or paste a link above")
        f.setPointSize(9)
        p.setFont(f)
        p.setPen(QColor(220, 232, 255, 90))
        p.drawText(QRectF(0, h / 2 + s * 0.15 + 30, w, 24), Qt.AlignCenter,
                   "PDF   ·   Images   ·   Web pages   ·   Text        Ctrl+O to browse")
        p.end()


class UnsupportedViewer(Viewer):
    def __init__(self, message: str, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        label = QLabel(message)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("color: rgba(230,238,252,170); font-size: 11pt; padding: 30px;")
        lay.addWidget(label)
