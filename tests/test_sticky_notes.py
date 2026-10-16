import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

from lucent.config import Look
from lucent.overlay import OverlayWindow
from lucent.viewers.note import CodeEditor, LineNumberArea, NoteViewer, SimpleCodeHighlighter


def test_note_viewer_typing_and_highlighter(qtbot):
    viewer = NoteViewer(initial_text="def hello_world():\n    return 42\n")
    qtbot.addWidget(viewer)
    viewer.apply_theme(210)

    assert viewer.text().startswith("def hello_world():")
    editor = viewer.editor
    assert isinstance(editor, CodeEditor)
    assert editor.line_number_area_width() > 0

    # Type additional text
    editor.setFocus()
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    editor.insertPlainText("# A quick comment\n")

    assert "# A quick comment" in viewer.text()


def test_overlay_sticky_note_mode(qtbot):
    look = Look()
    # Spawning an overlay as a Sticky Note
    overlay = OverlayWindow(look, source=None, name="Sticky Note #1")
    qtbot.addWidget(overlay)

    assert isinstance(overlay._viewer, NoteViewer)
    overlay._viewer.set_text("print('Lucent Sticky Note')")
    assert "print('Lucent Sticky Note')" in overlay.current_source

    # Spawning an overlay with note: prefix
    overlay2 = OverlayWindow(look, source="note:Existing persisted note content")
    qtbot.addWidget(overlay2)
    assert isinstance(overlay2._viewer, NoteViewer)
    assert overlay2._viewer.text() == "Existing persisted note content"
