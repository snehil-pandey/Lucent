import os

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QPlainTextEdit, QVBoxLayout

from .. import theme
from .base import Viewer

TEXT_EXTS = {".txt", ".md", ".log", ".json", ".csv", ".ini", ".cfg", ".yaml", ".yml",
             ".xml", ".py", ".js", ".ts", ".c", ".cpp", ".h", ".java", ".rs", ".go",
             ".css", ".toml", ".sh", ".bat", ".rst"}
MAX_BYTES = 2 * 1024 * 1024


class TextViewer(Viewer):
    @classmethod
    def accepts(cls, source):
        if not os.path.isfile(source):
            return False
        if os.path.splitext(source)[1].lower() in TEXT_EXTS:
            return True
        try:
            with open(source, "rb") as f:
                return b"\x00" not in f.read(4096)
        except OSError:
            return False

    def __init__(self, parent=None):
        super().__init__(parent)
        self._edit = QPlainTextEdit(self)
        self._edit.setReadOnly(True)
        self._edit.setFrameShape(QFrame.NoFrame)
        self._edit.setFont(theme.mono_font(10))
        self._edit.setStyleSheet(f"QPlainTextEdit {{ background: transparent; color: {theme.TEXT}; padding: 8px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._edit)

    def apply_theme(self, hue):
        from .. import theme
        acc = theme.accent(hue).name()
        self._edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                color: {theme.TEXT};
                padding: 10px;
                selection-background-color: {acc};
            }}
            {theme.scrollbar_stylesheet(hue)}
        """)

    def load(self, source):
        with open(source, "rb") as f:
            data = f.read(MAX_BYTES)
        self._edit.setPlainText(data.decode("utf-8", errors="replace"))
        self.title_changed.emit(os.path.basename(source))
        self.source_changed.emit(source)
