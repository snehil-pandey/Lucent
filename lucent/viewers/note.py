"""Interactive Note & Code Editor for Sticky Notes and Scratchpads.
Features line numbers, syntax highlighting for code/markdown, tab indent support,
auto-indent, and persistent editing.
"""
from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QPainter,
                           QSyntaxHighlighter, QTextCharFormat, QTextCursor)
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPlainTextEdit, QTextEdit, QVBoxLayout, QWidget

from .. import theme
from .base import Viewer


class SimpleCodeHighlighter(QSyntaxHighlighter):
    """Clean, high-performance syntax highlighter for code, markdown, and notes."""

    def __init__(self, parent, hue=215):
        super().__init__(parent)
        self._hue = hue
        self._init_formats()

    def _init_formats(self):
        acc = theme.accent(self._hue)

        # Keyword format (blue/accent tint)
        self.fmt_keyword = QTextCharFormat()
        self.fmt_keyword.setForeground(acc)
        self.fmt_keyword.setFontWeight(QFont.Bold)

        # String format (soft green/cyan)
        self.fmt_string = QTextCharFormat()
        self.fmt_string.setForeground(QColor("#7ee787"))

        # Comment / Heading format (muted text or italic)
        self.fmt_comment = QTextCharFormat()
        self.fmt_comment.setForeground(QColor(160, 180, 210, 160))
        self.fmt_comment.setFontItalic(True)

        # Number / Constant format (amber/orange)
        self.fmt_number = QTextCharFormat()
        self.fmt_number.setForeground(QColor("#ffa657"))

        self.keywords = {
            "def", "class", "import", "from", "return", "if", "else", "elif",
            "while", "for", "in", "try", "except", "finally", "with", "as",
            "const", "let", "var", "function", "async", "await", "public",
            "private", "static", "void", "int", "string", "bool", "true", "false",
            "null", "None", "True", "False"
        }

    def set_hue(self, hue):
        self._hue = hue
        self._init_formats()
        self.rehighlight()

    def highlightBlock(self, text: str):
        # Comments or markdown headings
        stripped = text.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            self.setFormat(0, len(text), self.fmt_comment)
            return

        # Simple fast word tokenizer
        import re
        words = re.finditer(r"\b\w+\b", text)
        for m in words:
            word = m.group(0)
            if word in self.keywords:
                self.setFormat(m.start(), len(word), self.fmt_keyword)
            elif word.isdigit():
                self.setFormat(m.start(), len(word), self.fmt_number)

        # Double and single quoted strings
        strings = re.finditer(r"(\"[^\"]*\"|'[^']*')", text)
        for m in strings:
            self.setFormat(m.start(), m.end() - m.start(), self.fmt_string)


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self._hue = 215

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.setFrameShape(QFrame.NoFrame)
        self.setFont(theme.mono_font(10))
        self.setTabStopDistance(QFontMetrics(self.font()).horizontalAdvance(" ") * 4)

    def line_number_area_width(self):
        digits = 1
        m = max(1, self.blockCount())
        while m >= 10:
            m //= 10
            digits += 1
        space = 14 + self.fontMetrics().horizontalAdvance("9") * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def highlight_current_line(self):
        # Subtle cursor line highlight
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(theme.TEXT)
            line_color.setAlpha(14)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextCharFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        # Subtle tinted gutter backdrop
        painter.fillRect(event.rect(), QColor(0, 0, 0, 50))

        # Calculate exact negative (inverted) color of the active theme background
        bg = theme.background(self._hue)
        inv_r = 255 - bg.red()
        inv_g = 255 - bg.green()
        inv_b = 255 - bg.blue()
        line_num_color = QColor(inv_r, inv_g, inv_b, 225)

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        painter.setPen(line_num_color)
        painter.setFont(self.font())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(
                    0, int(top), self.line_number_area.width() - 6,
                    self.fontMetrics().height(), Qt.AlignRight, number
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1


class NoteViewer(Viewer):
    """Full-featured interactive Sticky Note and Code Editor Viewer."""

    text_modified = Signal(str)

    def __init__(self, initial_text: str = "", parent=None):
        super().__init__(parent)
        self._hue = 215

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.editor = CodeEditor(self)
        self.highlighter = SimpleCodeHighlighter(self.editor.document(), hue=self._hue)
        self.editor.setPlaceholderText("Type your note or code snippet here… (Markdown, Python, JS, Plain Text)")

        if initial_text:
            self.editor.setPlainText(initial_text)

        self.editor.textChanged.connect(self._on_text_changed)
        lay.addWidget(self.editor)

    def _on_text_changed(self):
        text = self.editor.toPlainText()
        self.text_modified.emit(text)

    def apply_theme(self, hue: int):
        self._hue = hue
        self.editor._hue = hue
        acc = theme.accent(hue).name()
        self.highlighter.set_hue(hue)
        self.editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                color: {theme.TEXT};
                selection-background-color: {acc};
                padding: 4px;
            }}
            {theme.scrollbar_stylesheet(hue)}
        """)
        self.editor.highlight_current_line()
        self.editor.line_number_area.update()

    def set_text(self, text: str):
        self.editor.setPlainText(text)

    def text(self) -> str:
        return self.editor.toPlainText()

    def load(self, source: str):
        pass
