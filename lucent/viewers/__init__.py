"""Viewer registry. The first viewer whose accepts() returns True wins."""
from .base import Viewer
from .empty import EmptyViewer, UnsupportedViewer
from .image import ImageViewer
from .note import CodeEditor, NoteViewer
from .pdf import PdfViewer
from .text import TextViewer
from .web import WebViewer

VIEWERS = [PdfViewer, ImageViewer, WebViewer, TextViewer]

FILE_FILTER = (
    "Supported files (*.pdf *.png *.jpg *.jpeg *.gif *.bmp *.webp *.svg *.ico *.tif *.tiff "
    "*.html *.htm *.txt *.md *.json *.log *.csv);;All files (*)"
)


def create_viewer(source: str) -> Viewer:
    for cls in VIEWERS:
        if cls.accepts(source):
            viewer = cls()
            viewer.load(source)
            return viewer
    raise ValueError("Lucent can't preview this yet. Try a PDF, an image, a web link or a text file.")


__all__ = ["Viewer", "EmptyViewer", "UnsupportedViewer", "NoteViewer", "CodeEditor", "create_viewer", "FILE_FILTER"]

