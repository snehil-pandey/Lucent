import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication
from lucent.config import Look
from lucent.overlay import OverlayWindow, TitleBar


@pytest.fixture
def overlay(qtbot):
    look = Look(opacity=0.85, hue=200, on_top=True)
    window = OverlayWindow(look)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


def test_overlay_initial_state(overlay):
    assert overlay.windowTitle().startswith("Lucent")
    assert overlay.look.opacity == 0.85
    assert overlay.look.hue == 200
    assert overlay.isFullScreen() is False


def test_opacity_slider_interaction(qtbot, overlay):
    popup = overlay.popup
    slider = popup.opacity
    # Simulate slider drag to 50%
    slider.setValue(50)
    assert overlay.look.opacity == 0.50
    assert overlay.windowOpacity() == pytest.approx(0.50, abs=0.01)


def test_hue_slider_interaction(qtbot, overlay):
    popup = overlay.popup
    popup.hue.setValue(300)
    assert overlay.look.hue == 300


def test_collapse_toggle(qtbot, overlay):
    initial_height = overlay.height()
    # Click collapse button on titlebar
    qtbot.mouseClick(overlay.titlebar.btn_collapse, Qt.LeftButton)
    assert overlay._collapsed is True
    assert overlay.height() < initial_height

    # Toggle back
    qtbot.mouseClick(overlay.titlebar.btn_collapse, Qt.LeftButton)
    assert overlay._collapsed is False


def test_invert_colors_toggle(qtbot, overlay):
    assert overlay.look.invert_colors is False
    qtbot.mouseClick(overlay.titlebar.btn_invert, Qt.LeftButton)
    assert overlay.look.invert_colors is True
    qtbot.mouseClick(overlay.titlebar.btn_invert, Qt.LeftButton)
    assert overlay.look.invert_colors is False


def test_click_through_toggle(qtbot, overlay):
    assert overlay.look.click_through is False
    qtbot.mouseClick(overlay.titlebar.btn_ghost, Qt.LeftButton)
    assert overlay.look.click_through is True
    qtbot.mouseClick(overlay.titlebar.btn_ghost, Qt.LeftButton)
    assert overlay.look.click_through is False


def test_keyboard_shortcuts(qtbot, overlay):
    # Test Ctrl+I
    qtbot.keyClick(overlay, Qt.Key_I, Qt.ControlModifier)
    assert overlay.look.invert_colors is True

    # Test Ctrl+K (Collapse)
    qtbot.keyClick(overlay, Qt.Key_K, Qt.ControlModifier)
    assert overlay._collapsed is True

    # Test Alt+4 (Snap to top-right)
    qtbot.keyClick(overlay, Qt.Key_4, Qt.AltModifier)
    assert overlay.pos().x() > 100
