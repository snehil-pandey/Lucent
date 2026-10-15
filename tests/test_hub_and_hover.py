import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication

from lucent.config import Look
from lucent.overlay import OverlayWindow
from lucent.hub import HubWindow, OverlayListItem
from lucent.manager import Manager


def test_hub_window_instantiation_and_cards(qtbot):
    mgr = Manager([])
    w1 = mgr.spawn(None)
    w2 = mgr.spawn(None)

    hub = HubWindow(mgr)
    qtbot.addWidget(hub)
    hub.refresh(mgr._windows)
    hub.show()

    assert len(hub._item_widgets) == 2
    item1 = hub._item_widgets[0]
    assert "Overlay #1" in item1.lbl_title.text()
    item2 = hub._item_widgets[1]
    assert "Overlay #2" in item2.lbl_title.text()

    # Test actions widget hidden initially, shown on enterEvent
    assert not item1.actions_widget.isVisible()
    item1.enterEvent(None)
    assert item1.actions_widget.isVisible()
    item1.leaveEvent(None)
    assert not item1.actions_widget.isVisible()

    # Test filter search
    hub.search_box.setText("NonExistentXYZ")
    assert not item1.isVisible()
    assert not item2.isVisible()
    hub.search_box.setText("Overlay #1")
    assert item1.isVisible()
    assert not item2.isVisible()

    w1.close()
    w2.close()
    hub.close()


def test_selective_hover_click_through_tracker(qtbot):
    look = Look()
    win = OverlayWindow(look, None, index=1)
    qtbot.addWidget(win)
    win.show()

    # Enable click-through
    win.set_click_through(True)
    assert win.look.click_through is True
    assert hasattr(win, "_ghost_timer")
    assert win._ghost_timer.isActive()

    # Disable click-through
    win.set_click_through(False)
    assert not win._ghost_timer.isActive()

    win.close()
