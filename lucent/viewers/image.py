import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QImageReader, QPainter, QPixmap
from PySide6.QtWidgets import (QFrame, QGraphicsScene, QGraphicsView,
                               QVBoxLayout)

from .base import Viewer

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".jfif", ".gif", ".bmp", ".webp",
              ".svg", ".ico", ".tif", ".tiff"}


class _ZoomView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.item = None
        self.auto_fit = True
        self.setFrameShape(QFrame.NoFrame)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHints(QPainter.SmoothPixmapTransform | QPainter.Antialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("background: transparent;")
        self.viewport().setAutoFillBackground(False)

    def fit(self):
        if not self.item:
            return
        self.resetTransform()
        self.fitInView(self.item, Qt.KeepAspectRatio)
        if self.transform().m11() > 1:      # never blow small images up past 100%
            self.resetTransform()
            self.centerOn(self.item)
        self.auto_fit = True

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.scale(f, f)
        self.auto_fit = False

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_R:
            self.rotate(90 if not (e.modifiers() & Qt.ShiftModifier) else -90)
            self.auto_fit = False
            return
        super().keyPressEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MiddleButton:
            self._pan_start = e.pos()
            self.setCursor(Qt.ClosedHandCursor)
            e.accept()
            return
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if hasattr(self, "_pan_start") and self._pan_start is not None:
            delta = e.pos() - self._pan_start
            self._pan_start = e.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            e.accept()
            return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MiddleButton and hasattr(self, "_pan_start"):
            self._pan_start = None
            self.unsetCursor()
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.auto_fit:
            self.fit()

    def mouseDoubleClickEvent(self, e):
        self.fit()


class ImageViewer(Viewer):
    @classmethod
    def accepts(cls, source):
        return os.path.isfile(source) and os.path.splitext(source)[1].lower() in IMAGE_EXTS

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._view = _ZoomView(self._scene, self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._view)

    def load(self, source):
        reader = QImageReader(source)
        reader.setAutoTransform(True)
        img = reader.read()
        if img.isNull():
            raise ValueError(f"Couldn't read this image: {reader.errorString()}")
        self._scene.clear()
        self._view.item = self._scene.addPixmap(QPixmap.fromImage(img))
        self._view.item.setTransformationMode(Qt.SmoothTransformation)
        self._scene.setSceneRect(self._view.item.boundingRect())
        self._view.fit()
        self.title_changed.emit(os.path.basename(source))
        self.source_changed.emit(source)

    def fit(self):
        self._view.fit()
