import pytest
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication

from lucent import winapi
from lucent.config import Look
from lucent.overlay import OverlayWindow
from lucent.hub import HubWindow, OverlayListItem
from lucent.manager import Manager


def test_hub_window_instantiation_and_cards(qtbot):
    from lucent.config import save_overlay_registry
    save_overlay_registry([])

    mgr = Manager([])
    w1 = mgr.spawn(None)
    w2 = mgr.spawn(None)

    hub = HubWindow(mgr)
    qtbot.addWidget(hub)
    hub.refresh(mgr._windows)
    hub.show()

    assert len(hub._item_widgets) == 2
    item1 = hub._item_widgets[0]
    assert "Overlay" in item1.lbl_title.text()
    assert item1.lbl_tag.text() == "ACTIVE"
    item2 = hub._item_widgets[1]
    assert "Overlay" in item2.lbl_title.text()
    assert item2.lbl_tag.text() == "ACTIVE"

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
    hub.search_box.setText(item1.lbl_title.text())
    assert item1.isVisible()
    assert not item2.isVisible()

    w1.close()
    w2.close()
    hub.close()


@pytest.mark.skipif(not winapi.WIN, reason="hover tracker toggles WS_EX_TRANSPARENT (Windows only)")
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


def test_overlay_geometry_persistence_after_close(qtbot):
    from lucent.config import save_overlay_registry, load_overlay_registry
    save_overlay_registry([])

    mgr = Manager([])
    hub = HubWindow(mgr)
    qtbot.addWidget(hub)
    mgr._hub = hub
    hub.spawn_requested.connect(lambda src, look, oid, name, geom=None: mgr.spawn(src, look=look, overlay_id=oid, name=name, geometry=geom))

    # Spawn overlay and resize / move it
    win = mgr.spawn(None, overlay_id="custom_test_overlay_1", name="Custom Note")
    qtbot.addWidget(win)
    win.setGeometry(150, 180, 520, 410)
    win.persist_state()

    # Verify saved geometry in registry
    records = load_overlay_registry()
    rec = next(r for r in records if r["id"] == "custom_test_overlay_1")
    assert rec["geometry"] == [150, 180, 520, 410]

    # Close overlay
    win.close()

    # Re-open / restore overlay via hub
    hub.refresh(mgr._windows)
    inactive_items = [it for it in hub._item_widgets if it.record and it.record.get("id") == "custom_test_overlay_1"]
    assert len(inactive_items) == 1

    hub._restore_inactive_overlay(inactive_items[0].record)
    assert len(mgr._windows) == 1
    restored = mgr._windows[0]

    # Wait for intro animation slide to complete to target end pos
    if restored._intro:
        qtbot.wait(200)

    assert restored.overlay_id == "custom_test_overlay_1"
    assert restored.geometry().x() == 150
    assert restored.geometry().y() == 180
    assert restored.geometry().width() == 520
    assert restored.geometry().height() == 410

    restored.close()
    hub.close()
