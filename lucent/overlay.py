"""One Lucent overlay window. Open as many as you like; each has its own look."""
from PySide6.QtCore import (QEasingCurve, QEvent, QParallelAnimationGroup,
                            QPoint, QPropertyAnimation, Qt, QTimer, Signal)
from PySide6.QtGui import QColor, QGuiApplication, QKeySequence, QPainter, QShortcut
from PySide6.QtWidgets import QFileDialog, QVBoxLayout, QWidget

from . import theme, winapi
from .config import Look, add_recent_source, save_look
from .icon import app_icon
from .settings_popup import SettingsPopup
from .sources import normalize_source
from .titlebar import TitleBar
from .viewers import FILE_FILTER, EmptyViewer, UnsupportedViewer, create_viewer

EDGE = 6          # resize border, in px
MIN_OPACITY = 0.25
HOTKEY_ID_BASE = 9000
VK_M = 0x4D


class OverlayWindow(QWidget):
    closed = Signal(object)
    new_overlay_requested = Signal(object)   # a source to open, or None for an empty one

    def __init__(self, look: Look, source=None):
        super().__init__()
        self.look = look
        self.current_source = None
        self._viewer = None
        self._intro = None
        self._was_maximized = False
        self._drag_pos = None

        self.setWindowTitle("Lucent")
        self.setWindowIcon(app_icon())
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setMinimumSize(380, 260)
        self.resize(940, 640)
        self.setWindowFlags(self._flags())

        root = QVBoxLayout(self)
        root.setContentsMargins(EDGE, EDGE, EDGE, EDGE)
        root.setSpacing(0)
        self.titlebar = TitleBar(self)
        self.body = QWidget(self)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.titlebar)
        root.addWidget(self.body, 1)

        self._collapsed = False
        self._pre_collapse_height = 640

        self.popup = SettingsPopup(self)
        self._wire()
        self._shortcuts()
        self.popup.sync(self.look)
        self._show_viewer(EmptyViewer())
        self._retheme()
        if source:
            self.open_source(source)

    # setup --------------------------------------------------------------
    def _flags(self):
        f = Qt.Window | Qt.FramelessWindowHint
        if self.look.on_top:
            f |= Qt.WindowStaysOnTopHint
        if not winapi.WIN and self.look.click_through:
            f |= Qt.WindowTransparentForInput
        return f

    def _wire(self):
        t = self.titlebar
        t.address_submitted.connect(self.open_source)
        t.new_overlay.connect(lambda: self.new_overlay_requested.emit(None))
        t.open_file.connect(self.open_dialog)
        t.settings_clicked.connect(self.popup.show_below)
        t.invert_toggled.connect(self.toggle_invert_colors)
        t.click_through_toggled.connect(self.toggle_click_through)
        t.collapse_toggled.connect(self.toggle_collapse)
        t.fullscreen_toggled.connect(self.toggle_fullscreen)
        t.minimize_clicked.connect(self.showMinimized)
        t.maximize_toggled.connect(self.toggle_maximize)
        t.close_clicked.connect(self.close)
        p = self.popup
        p.opacity_changed.connect(self.set_opacity)
        p.hue_changed.connect(self.set_hue)
        p.on_top_changed.connect(self.set_on_top)
        p.click_through_changed.connect(self.set_click_through)
        p.capture_changed.connect(self.set_hide_from_capture)
        p.new_overlay.connect(lambda: self.new_overlay_requested.emit(None))

    def _shortcuts(self):
        def sc(seq, fn):
            QShortcut(QKeySequence(seq), self, activated=fn)

        sc("F11", self.toggle_fullscreen)
        sc("Esc", lambda: self.isFullScreen() and self.toggle_fullscreen())
        sc("Ctrl+N", lambda: self.new_overlay_requested.emit(None))
        sc("Ctrl+O", self.open_dialog)
        sc("Ctrl+L", self.titlebar.focus_address)
        sc("Ctrl+W", self.close)
        sc("Ctrl+I", self.toggle_invert_colors)
        sc("Ctrl+M", self.toggle_click_through)
        sc("Ctrl+Alt+M", self.toggle_click_through)
        sc("Ctrl+K", self.toggle_collapse)
        sc("Ctrl+V", self.paste_from_clipboard)
        sc("Ctrl+Up", lambda: self.set_opacity(self.look.opacity + 0.05))
        sc("Ctrl+Down", lambda: self.set_opacity(self.look.opacity - 0.05))
        sc("Ctrl+Right", lambda: self.set_hue(self.look.hue + 15))
        sc("Ctrl+Left", lambda: self.set_hue(self.look.hue - 15))
        sc("Ctrl+0", lambda: self._viewer and self._viewer.fit())
        sc("Alt+Left", lambda: self._viewer and self._viewer.go_back())
        sc("Alt+Right", lambda: self._viewer and self._viewer.go_forward())
        sc("F5", lambda: self._viewer and self._viewer.reload())
        # Quick Snap Layout Presets
        sc("Alt+1", lambda: self.snap_to("bottom-left"))
        sc("Alt+2", lambda: self.snap_to("bottom-right"))
        sc("Alt+3", lambda: self.snap_to("top-left"))
        sc("Alt+4", lambda: self.snap_to("top-right"))
        sc("Alt+5", lambda: self.snap_to("center"))

    def snap_to(self, position: str):
        geo = QGuiApplication.primaryScreen().availableGeometry()
        w, h = self.width(), self.height()
        margin = 20
        if position == "top-left":
            self.move(geo.left() + margin, geo.top() + margin)
        elif position == "top-right":
            self.move(geo.right() - w - margin, geo.top() + margin)
        elif position == "bottom-left":
            self.move(geo.left() + margin, geo.bottom() - h - margin)
        elif position == "bottom-right":
            self.move(geo.right() - w - margin, geo.bottom() - h - margin)
        elif position == "center":
            self.move(geo.center() - QPoint(w // 2, h // 2))

    def paste_from_clipboard(self):
        clipboard = QGuiApplication.clipboard()
        md = clipboard.mimeData()
        if not md:
            return
        if md.hasImage():
            img = clipboard.image()
            if not img.isNull():
                import tempfile
                tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                tmp.close()
                img.save(tmp.name, "PNG")
                self.open_source(tmp.name)
                return
        if md.hasUrls():
            urls = md.urls()
            if urls:
                src = urls[0].toLocalFile() if urls[0].isLocalFile() else urls[0].toString()
                self.open_source(src)
                return
        text = clipboard.text().strip()
        if text:
            self.open_source(text)

    def toggle_collapse(self):
        self._collapsed = not self._collapsed
        if self._collapsed:
            self._pre_collapse_height = max(self.height(), 260)
            self.body.hide()
            self.setMinimumHeight(TitleBar.HEIGHT + 2 * EDGE)
            self.resize(self.width(), TitleBar.HEIGHT + 2 * EDGE)
        else:
            self.body.show()
            self.setMinimumHeight(260)
            self.resize(self.width(), self._pre_collapse_height)
        self.titlebar.set_collapsed(self._collapsed)

    def toggle_click_through(self):
        self.set_click_through(not self.look.click_through)

    def set_click_through(self, enabled: bool):
        self.look.click_through = enabled
        if winapi.WIN:
            winapi.set_click_through(self, enabled)
        else:
            # Cross-platform Qt fallback for Linux/macOS
            was_visible = self.isVisible()
            self.setWindowFlag(Qt.WindowTransparentForInput, enabled)
            if was_visible:
                self.show()
        self.titlebar.set_click_through(enabled)
        self.popup.sync(self.look)
        save_look(self.look)

    # content ------------------------------------------------------------
    def open_source(self, text):
        source = normalize_source(text)
        if source is None:
            return
        self.current_source = source
        add_recent_source(source)
        try:
            viewer = create_viewer(source)
        except Exception as exc:
            viewer = UnsupportedViewer(str(exc))
        self._show_viewer(viewer)

    def open_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open in Lucent", "", FILE_FILTER)
        if path:
            self.open_source(path)

    def _show_viewer(self, viewer):
        old = self._viewer
        if old is not None:
            self.body_layout.removeWidget(old)
            old.hide()
            old.deleteLater()
        self._viewer = viewer
        self.body_layout.addWidget(viewer)
        viewer.apply_theme(self.look.hue)
        viewer.title_changed.connect(self._on_title)
        viewer.source_changed.connect(self.titlebar.set_address)

    def _on_title(self, title):
        self.setWindowTitle(f"{title} — Lucent" if title else "Lucent")

    # look ---------------------------------------------------------------
    def set_opacity(self, value: float):
        self.look.opacity = max(MIN_OPACITY, min(1.0, value))
        if self._intro:
            self._intro.stop()
            self._intro = None
        self.setWindowOpacity(self.look.opacity)
        self.popup.sync(self.look)
        save_look(self.look)

    def set_hue(self, hue: int):
        self.look.hue = hue % 360
        self._retheme()
        self.popup.sync(self.look)
        save_look(self.look)

    def set_on_top(self, on: bool):
        self.look.on_top = on
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        if visible:
            self.show()
        save_look(self.look)

    def set_hide_from_capture(self, hidden: bool):
        self.look.hide_from_capture = hidden
        self._apply_capture()
        save_look(self.look)

    def _apply_capture(self):
        winapi.set_capture_hidden(self, self.look.hide_from_capture)
        self.popup.set_capture_hidden(self.look.hide_from_capture)

    def toggle_invert_colors(self):
        self.set_invert_colors(not self.look.invert_colors)

    def set_invert_colors(self, inverted: bool):
        self.look.invert_colors = inverted
        self.titlebar.set_inverted(inverted)
        self._apply_inversion()
        save_look(self.look)

    def _apply_inversion(self):
        if not self._viewer:
            return
        if self.look.invert_colors:
            # Apply high contrast invert filter to content viewer
            # For Web/HTML and Text viewers, CSS filters or background adjustments make reading transparent docs effortless
            self.body.setStyleSheet("QWidget#body { background: transparent; }")
            # For WebEngine or generic widgets, we can apply an invert stylesheet filter or theme update
            if hasattr(self._viewer, "_edit"):
                self._viewer._edit.setStyleSheet("QPlainTextEdit { background: rgba(10, 10, 15, 0.90); color: #f8fafc; padding: 8px; }")
            elif hasattr(self._viewer, "_view") and hasattr(self._viewer._view, "setPalette"):
                pal = self._viewer._view.palette()
                pal.setColor(pal.ColorRole.Base, QColor(20, 20, 25))
                pal.setColor(pal.ColorRole.WindowText, QColor(240, 240, 245))
                self._viewer._view.setPalette(pal)
        else:
            if hasattr(self._viewer, "_edit"):
                self._viewer._edit.setStyleSheet("QPlainTextEdit { background: transparent; color: #e6eefc; padding: 8px; }")
            elif hasattr(self._viewer, "_view") and hasattr(self._viewer._view, "setPalette"):
                self._viewer.apply_theme(self.look.hue)

    def _retheme(self):
        h = self.look.hue
        self.titlebar.apply_theme(h)
        self.titlebar.set_inverted(self.look.invert_colors)
        self.popup.apply_theme(h)
        if self._viewer:
            self._viewer.apply_theme(h)
            self._apply_inversion()
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), theme.background(self.look.hue))
        border = theme.accent(self.look.hue)
        border.setAlpha(110)
        p.setPen(border)
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        p.end()

    # showing, fullscreen, maximize --------------------------------------
    def show_animated(self):
        end = self.pos()
        self.setWindowOpacity(0.0)
        self.move(end + QPoint(0, 10))
        self.show()
        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setStartValue(0.0)
        fade.setEndValue(self.look.opacity)
        fade.setDuration(260)
        fade.setEasingCurve(QEasingCurve.OutQuad)

        slide = QPropertyAnimation(self, b"pos")
        slide.setStartValue(end + QPoint(0, 10))
        slide.setEndValue(end)
        slide.setDuration(260)
        slide.setEasingCurve(QEasingCurve.OutQuad)

        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(slide)
        group.finished.connect(lambda: self.setWindowOpacity(self.look.opacity))
        self._intro = group
        group.start()

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self._apply_capture)
        if self.look.click_through:
            QTimer.singleShot(0, lambda: winapi.set_click_through(self, True))
        self._register_hotkey()

    def _register_hotkey(self):
        if winapi.WIN and self.winId():
            # Register Ctrl+Alt+M globally so click-through can ALWAYS be toggled back
            winapi.register_global_hotkey(int(self.winId()), HOTKEY_ID_BASE, winapi.MOD_CONTROL | winapi.MOD_ALT, VK_M)

    def _unregister_hotkey(self):
        if winapi.WIN and self.winId():
            winapi.unregister_global_hotkey(int(self.winId()), HOTKEY_ID_BASE)

    def nativeEvent(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            import ctypes
            from ctypes import wintypes
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == winapi.WM_HOTKEY:
                if msg.wParam == HOTKEY_ID_BASE:
                    self.toggle_click_through()
                    return True, 0
        return super().nativeEvent(event_type, message)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized() if self._was_maximized else self.showNormal()
        else:
            self._was_maximized = self.isMaximized()
            self.showFullScreen()

    def toggle_maximize(self):
        if self.isFullScreen():
            self.showNormal()
        elif self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def changeEvent(self, e):
        if e.type() == QEvent.WindowStateChange:
            fs, mx = self.isFullScreen(), self.isMaximized()
            m = 0 if (fs or mx) else EDGE
            self.layout().setContentsMargins(m, m, m, m)
            self.titlebar.setVisible(not fs)
            self.titlebar.set_state(mx, fs)
        super().changeEvent(e)

    def closeEvent(self, e):
        self._unregister_hotkey()
        save_look(self.look)
        self.closed.emit(self)
        super().closeEvent(e)

    # edge resizing (frameless window) -----------------------------------
    def _edges(self, pos):
        e = Qt.Edge(0)
        if self.isFullScreen() or self.isMaximized():
            return e
        if pos.x() <= EDGE:
            e |= Qt.LeftEdge
        if pos.x() >= self.width() - EDGE:
            e |= Qt.RightEdge
        if pos.y() <= EDGE:
            e |= Qt.TopEdge
        if pos.y() >= self.height() - EDGE:
            e |= Qt.BottomEdge
        return e

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and (e.buttons() & Qt.LeftButton):
            diff = e.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + diff)
            self._drag_pos = e.globalPosition().toPoint()
            e.accept()
            return

        edges = self._edges(e.position().toPoint())
        horiz = bool(edges & (Qt.LeftEdge | Qt.RightEdge))
        vert = bool(edges & (Qt.TopEdge | Qt.BottomEdge))
        if horiz and vert:
            diag = (bool(edges & Qt.LeftEdge) == bool(edges & Qt.TopEdge))
            self.setCursor(Qt.SizeFDiagCursor if diag else Qt.SizeBDiagCursor)
        elif horiz:
            self.setCursor(Qt.SizeHorCursor)
        elif vert:
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.unsetCursor()

    def mousePressEvent(self, e):
        # Alt + Left Click anywhere on the overlay window lets you drag and move it!
        if e.button() == Qt.LeftButton and (e.modifiers() & Qt.AltModifier):
            self._drag_pos = e.globalPosition().toPoint()
            e.accept()
            return

        if e.button() == Qt.LeftButton and self.windowHandle():
            edges = self._edges(e.position().toPoint())
            if edges:
                self.windowHandle().startSystemResize(edges)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self._drag_pos is not None:
            self._drag_pos = None
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def leaveEvent(self, e):
        self.unsetCursor()
        super().leaveEvent(e)

    # drag & drop --------------------------------------------------------
    def dragEnterEvent(self, e):
        md = e.mimeData()
        if md.hasUrls() or md.hasText():
            e.acceptProposedAction()

    def dropEvent(self, e):
        md = e.mimeData()
        sources = [u.toLocalFile() if u.isLocalFile() else u.toString() for u in md.urls()]
        if not sources and md.hasText():
            sources = [md.text()]
        if not sources:
            return
        self.open_source(sources[0])
        for extra in sources[1:]:
            self.new_overlay_requested.emit(extra)
        e.acceptProposedAction()
