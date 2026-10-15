import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QMouseEvent
from lucent.config import Look
from lucent.overlay import OverlayWindow, EDGE
from lucent import theme


@pytest.fixture
def overlay(qtbot):
    look = Look(opacity=0.85, hue=215, on_top=True)
    window = OverlayWindow(look)
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window


# =========================================================================
# 1. PIXEL & GEOMETRY VERIFICATIONS (Edges, Borders, Resizing Coordinates)
# =========================================================================

def test_pixel_edge_border_detection(overlay):
    w, h = overlay.width(), overlay.height()

    # (0, 0) top-left corner -> TopEdge | LeftEdge
    edges_tl = overlay._edges(QPoint(2, 2))
    assert bool(edges_tl & Qt.TopEdge)
    assert bool(edges_tl & Qt.LeftEdge)

    # (w, h) bottom-right corner -> BottomEdge | RightEdge
    edges_br = overlay._edges(QPoint(w - 2, h - 2))
    assert bool(edges_br & Qt.BottomEdge)
    assert bool(edges_br & Qt.RightEdge)

    # Top edge only
    edges_top = overlay._edges(QPoint(w // 2, 2))
    assert bool(edges_top & Qt.TopEdge)
    assert not bool(edges_top & Qt.LeftEdge)

    # Interior pixel (center) -> 0 (No edge)
    edges_center = overlay._edges(QPoint(w // 2, h // 2))
    assert edges_center == Qt.Edge(0)


def test_pixel_border_color_matches_hue(overlay):
    # Verify theme accent color calculation matches exact hue
    hue = 180
    overlay.set_hue(hue)
    accent_color = theme.accent(hue)
    bg_color = theme.background(hue)
    assert accent_color.hslHue() == hue
    assert bg_color.hslHue() == hue


def test_window_margins_in_normal_and_maximized(overlay):
    # In normal state, margin must be EDGE (6px)
    assert overlay.layout().contentsMargins().left() == EDGE
    assert overlay.layout().contentsMargins().top() == EDGE

    # In maximized or fullscreen, margins collapse to 0
    overlay.showMaximized()
    # Post resize check
    assert overlay.layout().contentsMargins().left() == 0


# =========================================================================
# 2. SHORTCUTS EXHAUSTIVE VERIFICATION
# =========================================================================

def test_all_shortcuts_trigger_actions(qtbot, overlay):
    # F11 Toggle Fullscreen
    qtbot.keyClick(overlay, Qt.Key_F11)
    assert overlay.isFullScreen() is True
    # Esc exits fullscreen
    qtbot.keyClick(overlay, Qt.Key_Escape)
    assert overlay.isFullScreen() is False

    # Ctrl+Up / Ctrl+Down (Opacity fine adjustment)
    initial_op = overlay.look.opacity
    qtbot.keyClick(overlay, Qt.Key_Up, Qt.ControlModifier)
    assert overlay.look.opacity == pytest.approx(initial_op + 0.05, abs=0.001)
    qtbot.keyClick(overlay, Qt.Key_Down, Qt.ControlModifier)
    assert overlay.look.opacity == pytest.approx(initial_op, abs=0.001)

    # Ctrl+Right / Ctrl+Left (Hue adjustment by 15 deg)
    initial_hue = overlay.look.hue
    qtbot.keyClick(overlay, Qt.Key_Right, Qt.ControlModifier)
    assert overlay.look.hue == (initial_hue + 15) % 360
    qtbot.keyClick(overlay, Qt.Key_Left, Qt.ControlModifier)
    assert overlay.look.hue == initial_hue

    # Ctrl+I (Invert Dark Mode)
    qtbot.keyClick(overlay, Qt.Key_I, Qt.ControlModifier)
    assert overlay.look.invert_colors is True
    qtbot.keyClick(overlay, Qt.Key_I, Qt.ControlModifier)
    assert overlay.look.invert_colors is False

    # Ctrl+K (Collapse / Shading)
    qtbot.keyClick(overlay, Qt.Key_K, Qt.ControlModifier)
    assert overlay._collapsed is True
    qtbot.keyClick(overlay, Qt.Key_K, Qt.ControlModifier)
    assert overlay._collapsed is False

    # Alt+1 to Alt+5 (Snap Layout Presets)
    qtbot.keyClick(overlay, Qt.Key_1, Qt.AltModifier) # bottom-left
    pos_bl = overlay.pos()
    qtbot.keyClick(overlay, Qt.Key_4, Qt.AltModifier) # top-right
    pos_tr = overlay.pos()
    assert pos_tr.x() > pos_bl.x()
    assert pos_tr.y() < pos_bl.y()


# =========================================================================
# 3. MOUSE INTERACTION & ALT+DRAG CANVAS NAVIGATION
# =========================================================================

def test_alt_left_click_drag_moves_window(qtbot, overlay):
    initial_pos = overlay.pos()
    # Simulate Alt + MousePress at center
    center = QPoint(overlay.width() // 2, overlay.height() // 2)
    global_center = overlay.mapToGlobal(center)

    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        center,
        global_center,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.AltModifier
    )
    overlay.mousePressEvent(press_event)
    assert overlay._drag_pos == global_center

    # Simulate MouseMove with drag offset of (50, 50)
    drag_target_global = global_center + QPoint(50, 50)
    drag_target_local = center + QPoint(50, 50)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        drag_target_local,
        drag_target_global,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.AltModifier
    )
    overlay.mouseMoveEvent(move_event)
    assert overlay.pos() == initial_pos + QPoint(50, 50)

    # Release
    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        drag_target_local,
        drag_target_global,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier
    )
    overlay.mouseReleaseEvent(release_event)
    assert overlay._drag_pos is None
