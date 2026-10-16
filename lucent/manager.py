"""Owns the splash and every open overlay."""
from copy import copy

from PySide6.QtCore import QObject, QPoint, QRect
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from .config import (Look, get_recent_sources, load_look, load_session,
                     save_session)
from .hub import HubWindow
from .icon import app_icon
from .overlay import OverlayWindow
from .splash import Splash


class Manager(QObject):
    def __init__(self, sources, parent=None):
        super().__init__(parent)
        self._sources = list(sources)
        self._windows = []
        self._look = load_look()
        self._splash = None
        self._launched = False
        self._tray = None
        self._menu = None
        self._hub = None
        self._init_tray()
        app = QGuiApplication.instance()
        if app:
            app.aboutToQuit.connect(self._on_app_quit)

    def _init_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        tray = QSystemTrayIcon(app_icon(), self)
        tray.setToolTip("Lucent (Global: Ctrl+Alt+M to toggle click-through)")
        self._menu = QMenu()
        self._menu.aboutToShow.connect(self._rebuild_tray_menu)
        tray.setContextMenu(self._menu)
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        self._tray = tray

    def _rebuild_tray_menu(self):
        m = self._menu
        m.clear()

        act_hub = QAction("All Overlays Hub (Ctrl+H)", m)
        act_hub.triggered.connect(self.show_hub)
        m.addAction(act_hub)

        act_toggle_ghost = QAction("Toggle Click-Through (Ctrl+Alt+M)", m)
        act_toggle_ghost.triggered.connect(self.toggle_all_click_through)
        m.addAction(act_toggle_ghost)

        act_new = QAction("New Overlay (Ctrl+N)", m)
        act_new.triggered.connect(lambda: self.spawn())
        m.addAction(act_new)

        # Recent Files / Links submenu
        recent = get_recent_sources()
        if recent:
            rec_menu = m.addMenu("Open Recent")
            for item in recent:
                display_name = item
                if len(display_name) > 45:
                    display_name = display_name[:20] + "..." + display_name[-22:]
                act = QAction(display_name, rec_menu)
                act.triggered.connect(lambda checked=False, src=item: self.spawn(src))
                rec_menu.addAction(act)

        m.addSeparator()

        act_bring_front = QAction("Bring All to Front", m)
        act_bring_front.triggered.connect(self.bring_all_to_front)
        m.addAction(act_bring_front)

        m.addSeparator()

        act_quit = QAction("Quit Lucent", m)
        act_quit.triggered.connect(QGuiApplication.instance().quit)
        m.addAction(act_quit)

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_all_click_through()

    def toggle_all_click_through(self):
        if not self._windows:
            return
        any_ghost = any(w.look.click_through for w in self._windows)
        for w in self._windows:
            w.set_click_through(not any_ghost)

    def bring_all_to_front(self):
        for w in self._windows:
            w.showNormal()
            w.raise_()
            w.activateWindow()

    def start(self):
        self._splash = Splash()
        self._splash.handoff.connect(self._launch)
        self._splash.play()

    def _launch(self):
        if self._launched:
            return
        self._launched = True

        # If user explicitly passed files or links via CLI arguments, open them
        if self._sources:
            for src in self._sources:
                self.spawn(src)

        # Always open the Main App screen on startup with focus on input box; user controls when overlays open
        self.show_hub(focus_input=True)

    def _on_app_quit(self):
        try:
            session_data = []
            for w in list(self._windows):
                g = w.geometry()
                look_dict = {
                    "opacity": w.look.opacity,
                    "hue": w.look.hue,
                    "on_top": w.look.on_top,
                    "hide_from_capture": w.look.hide_from_capture,
                    "click_through": w.look.click_through,
                    "invert_colors": w.look.invert_colors,
                    "icon_name": w.look.icon_name,
                    "icon_file": w.look.icon_file,
                }
                session_data.append({
                    "id": w.overlay_id,
                    "name": w.custom_name,
                    "source": getattr(w, "current_source", None),
                    "geometry": [g.x(), g.y(), g.width(), g.height()],
                    "look": look_dict,
                })
            save_session(session_data)
        except Exception:
            pass

    def show_hub(self, focus_input: bool = False):
        if self._hub is None:
            self._hub = HubWindow(self)
            self._hub.spawn_requested.connect(lambda src, look, oid, name, geom=None: self.spawn(src, look=look, overlay_id=oid, name=name, geometry=geom))
            self._hub.bring_front_requested.connect(self._bring_overlay_to_front)
            self._hub.toggle_collapse_requested.connect(lambda w: (w.toggle_collapse(), self._hub.refresh(self._windows)))
            self._hub.toggle_click_through_requested.connect(lambda w: (w.toggle_click_through(), self._hub.refresh(self._windows)))
            self._hub.close_overlay_requested.connect(lambda w: w.close())

        self._hub.refresh(self._windows)
        self._hub.showNormal()
        self._hub.raise_()
        self._hub.activateWindow()
        if focus_input:
            self._hub.focus_input()

    def _bring_overlay_to_front(self, win):
        if win in self._windows:
            win.showNormal()
            win.raise_()
            win.activateWindow()

    def spawn(self, source=None, origin=None, look=None, overlay_id=None, name=None, geometry=None):
        if look is None:
            look = copy(origin.look if origin else self._look)
        index = len(self._windows) + 1
        win = OverlayWindow(look, source, index=index, overlay_id=overlay_id, name=name, geometry=geometry)
        win.closed.connect(self._on_closed)
        win.new_overlay_requested.connect(lambda s: self.show_hub(focus_input=True))
        win.hub_requested.connect(self.show_hub)

        if geometry and len(geometry) == 4:
            win.setGeometry(QRect(int(geometry[0]), int(geometry[1]), int(geometry[2]), int(geometry[3])))
        elif origin:
            full = origin.isMaximized() or origin.isFullScreen()
            g = origin.normalGeometry() if full else origin.geometry()
            win.resize(g.size())
            win.move(g.topLeft() + QPoint(42, 42))
        else:
            geo = QGuiApplication.primaryScreen().availableGeometry()
            n = len(self._windows)
            c = geo.center() - QPoint(win.width() // 2, win.height() // 2)
            win.move(c + QPoint(n * 36, n * 36))

        self._windows.append(win)
        win.show_animated()
        if self._hub and self._hub.isVisible():
            self._hub.refresh(self._windows)
        return win

    def _on_closed(self, win):
        if win in self._windows:
            self._windows.remove(win)
        if self._hub and self._hub.isVisible():
            self._hub.refresh(self._windows)
