"""Cross-platform behaviour: vector glyphs, Wayland handling, IPC, hotkey fallback."""
import pytest
from PySide6.QtWidgets import QToolButton

from lucent import glyphs, hotkeys, ipc, winapi


@pytest.mark.parametrize("name", glyphs.NAMES)
def test_every_glyph_draws_something(qtbot, name):
    img = glyphs.render(name, "#ffffff", 24).toImage()
    opaque = sum(1 for x in range(img.width()) for y in range(img.height())
                 if img.pixelColor(x, y).alpha() > 0)
    assert opaque > 20, f"{name} rendered (almost) nothing"


def _ink(icon):
    """Colour of the most opaque pixel in the icon."""
    img = icon.pixmap(18, 18).toImage()
    best = max(((img.pixelColor(x, y).alpha(), x, y) for x in range(img.width()) for y in range(img.height())))
    return img.pixelColor(best[1], best[2]).name()


def test_glyph_recolor_changes_pixels(qtbot):
    btn = QToolButton()
    qtbot.addWidget(btn)
    glyphs.set_glyph(btn, "click_through")
    before = _ink(btn.icon())
    glyphs.recolor(btn, "#4ade80")
    after = _ink(btn.icon())
    assert before == "#e6eefc" and after == "#4ade80"
    assert btn.text() == ""


def test_hover_swaps_icon(qtbot):
    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication
    btn = QToolButton()
    qtbot.addWidget(btn)
    glyphs.set_glyph(btn, "close", hover="#e81123")
    normal = btn.icon().cacheKey()
    QApplication.sendEvent(btn, QEvent(QEvent.Enter))
    assert btn.icon().cacheKey() != normal
    QApplication.sendEvent(btn, QEvent(QEvent.Leave))
    assert btn.icon().cacheKey() == normal


def test_wayland_session_switches_to_xwayland(monkeypatch):
    monkeypatch.setattr(winapi, "LINUX", True)
    for k in ("QT_QPA_PLATFORM", "LUCENT_WAYLAND"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("DISPLAY", ":0")
    winapi.platform_setup()
    import os
    assert os.environ["QT_QPA_PLATFORM"] == "xcb"


def test_wayland_opt_out_and_explicit_platform_respected(monkeypatch):
    import os
    monkeypatch.setattr(winapi, "LINUX", True)
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.setenv("LUCENT_WAYLAND", "1")
    winapi.platform_setup()
    assert "QT_QPA_PLATFORM" not in os.environ
    monkeypatch.delenv("LUCENT_WAYLAND")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    winapi.platform_setup()
    assert os.environ["QT_QPA_PLATFORM"] == "offscreen"


def test_global_hotkey_declines_on_wayland(monkeypatch):
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    hk = hotkeys.GlobalHotkey()
    assert hk.start() is False and hk.available is False


def test_ipc_roundtrip(qtbot):
    assert ipc.send(["hub"], 100) is False            # nothing running yet
    server = ipc.Server()
    assert server.ok
    got = []
    server.command.connect(got.append)
    assert ipc.send(["toggle-click-through", "open /tmp/a b.pdf"])
    qtbot.waitUntil(lambda: len(got) == 2, timeout=3000)
    assert got == ["toggle-click-through", "open /tmp/a b.pdf"]


def test_manager_handles_commands_and_queues_during_splash(qtbot):
    from lucent.manager import Manager
    m = Manager([])
    m.handle_command("hub")                 # arrives before launch -> queued
    assert m._pending == ["hub"] and m._hub is None
    m._launch()
    assert m._pending == [] and m._hub is not None
    m.handle_command("new")
    assert len(m._windows) == 1
    m.handle_command("open /tmp")           # a folder: opens an overlay with an error viewer
    assert len(m._windows) == 2
    for w in list(m._windows):
        w.close()


def test_light_mode_flips_every_token(qtbot):
    from lucent import theme
    from lucent.hub import HubWindow
    from lucent.manager import Manager
    m = Manager([])
    try:
        theme.set_mode("dark")
        dark = (theme.TEXT, theme.fg(0.1), theme.background(215).lightness())
        hub = HubWindow(m)
        qtbot.addWidget(hub)
        m._hub = hub                      # as show_hub() would register it
        m.set_mode("light")
        light = (theme.TEXT, theme.fg(0.1), theme.background(215).lightness())
        assert all(a != b for a, b in zip(dark, light))
        assert theme.is_light() and "#14202b" in hub.styleSheet()   # hub re-themed itself
        btn_ink = hub.btn_mode.icon().pixmap(16, 16).toImage()
        assert btn_ink.width() > 0
    finally:
        m.set_mode("dark")
