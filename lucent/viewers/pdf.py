import os

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QFrame, QVBoxLayout

from .. import theme
from .base import Viewer

try:
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView
    HAVE_PDF = True
except ImportError:  # pragma: no cover
    HAVE_PDF = False


class PdfViewer(Viewer):
    @classmethod
    def accepts(cls, source):
        return HAVE_PDF and os.path.isfile(source) and source.lower().endswith(".pdf")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = QPdfDocument(self)
        self._view = QPdfView(self)
        self._view.setDocument(self._doc)
        self._view.setPageMode(QPdfView.PageMode.MultiPage)
        self._view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self._view.setFrameShape(QFrame.NoFrame)
        self._view.viewport().installEventFilter(self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._view)

    def load(self, source):
        err = self._doc.load(source)
        if err != QPdfDocument.Error.None_:
            raise ValueError(f"Couldn't open this PDF ({err.name}).")
        self.title_changed.emit(os.path.basename(source))
        self.source_changed.emit(source)

    def apply_theme(self, hue):
        pal = self._view.palette()
        pal.setColor(QPalette.Dark, theme.background(hue).lighter(130))
        self._view.setPalette(pal)

    def fit(self):
        self._view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

    def _current_zoom(self) -> float:
        """Estimate what fit-to-width currently is so Ctrl+wheel doesn't jump."""
        try:
            m = self._view.documentMargins()
            avail = self._view.viewport().width() - m.left() - m.right()
            page_w = self._doc.pagePointSize(0).width() * self.logicalDpiX() / 72.0
            return max(0.1, avail / page_w)
        except Exception:
            return 1.0

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Wheel and ev.modifiers() & Qt.ControlModifier:
            zoom = (self._view.zoomFactor()
                    if self._view.zoomMode() == QPdfView.ZoomMode.Custom
                    else self._current_zoom())
            zoom *= 1.12 if ev.angleDelta().y() > 0 else 1 / 1.12
            self._view.setZoomMode(QPdfView.ZoomMode.Custom)
            self._view.setZoomFactor(max(0.1, min(6.0, zoom)))
            return True
        if ev.type() == QEvent.KeyPress:
            if ev.key() == Qt.Key_PageDown or ev.key() == Qt.Key_Down:
                nav = self._view.pageNavigator()
                if nav and nav.currentPage() < self._doc.pageCount() - 1:
                    nav.jump(nav.currentPage() + 1, nav.currentLocation(), nav.currentZoom())
                    return True
            elif ev.key() == Qt.Key_PageUp or ev.key() == Qt.Key_Up:
                nav = self._view.pageNavigator()
                if nav and nav.currentPage() > 0:
                    nav.jump(nav.currentPage() - 1, nav.currentLocation(), nav.currentZoom())
                    return True
        return super().eventFilter(obj, ev)
