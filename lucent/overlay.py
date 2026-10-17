"""One Lucent overlay window. Open as many as you like; each has its own look.
The overlay viewport does not resize or shift when hovering; the title bar is an
overlay positioned directly on top of the content viewport.
Taskbar icon is hidden (Qt.SubWindow / Qt.Tool) so overlays do not clutter the taskbar.
"""
from PySide6.QtCore import (QEasingCurve, QEvent, QParallelAnimationGroup,
                            QPoint, QPropertyAnimation, QRect, QRectF, Qt, QTimer, Signal)
from PySide6.QtGui import (QColor, QCursor, QFont, QGuiApplication, QKeySequence,
                           QPainter, QShortcut)
from PySide6.QtWidgets import QFileDialog, QVBoxLayout, QWidget

from . import theme, winapi
from .config import Look, add_recent_source, save_look, upsert_overlay_record
from .icon import app_icon, draw_shape_icon, render_overlay_pixmap
from .settings_popup import SettingsPopup
from .sources import normalize_source
from .titlebar import TitleBar
from .viewers import FILE_FILTER, EmptyViewer, NoteViewer, UnsupportedViewer, create_viewer

EDGE = 6          # resize border, in px
MIN_OPACITY = 0.25
HOTKEY_ID_BASE = 9000
VK_M = 0x4D


class OverlayWindow(QWidget):
    closed = Signal(object)
    new_overlay_requested = Signal(object)   # a source to open, or None for an empty one
    hub_requested = Signal()
    mode_toggle_requested = Signal()

    def __init__(self, look: Look, source=None, index: int = 1, overlay_id: str = None, name: str = None, geometry=None):
        super().__init__()
        self.look = look
        self.index = index
        self.overlay_id = overlay_id or f"overlay_{index}_{id(self)}"
        self.custom_name = name or f"Overlay #{self.index}"
        self.current_source = None
        self._viewer = None
        self._intro = None
        self._was_maximized = False
        self._drag_pos = None

        self.setWindowTitle(f"Lucent — {self.custom_name}")
        self.setWindowIcon(app_icon())
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setAttribute(Qt.WA_Hover, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setMinimumSize(380, 260)
        if geometry and len(geometry) == 4:
            self.setGeometry(QRect(int(geometry[0]), int(geometry[1]), int(geometry[2]), int(geometry[3])))
        else:
            self.resize(940, 640)
        self.setWindowFlags(self._flags())

        root = QVBoxLayout(self)
        root.setContentsMargins(EDGE, EDGE, EDGE, EDGE)
        root.setSpacing(0)

        # Body fills the entire window client area
        self.body = QWidget(self)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self.body, 1)

        # Floating Hover TitleBar overlaid on top of content so viewport NEVER shifts
        self.titlebar = TitleBar(self)
        self.titlebar.set_title(self.custom_name)
        self.titlebar.setVisible(False)  # Hidden by default; appears seamlessly on hover
        self.titlebar.raise_()

        # Title bar auto-hide timer: visible for 4.5s on hover, then auto-hides until hovered again
        self._titlebar_timer = QTimer(self)
        self._titlebar_timer.setSingleShot(True)
        self._titlebar_timer.setInterval(4500)
        self._titlebar_timer.timeout.connect(self._on_titlebar_timeout)

        self._collapsed = False
        self._pre_collapse_geom = None

        self.popup = SettingsPopup(self)
        self._wire()
        self._shortcuts()
        self.popup.sync(self.look)

        if source and str(source).startswith("note:"):
            # Sticky note with text
            initial_text = str(source)[5:]
            self.open_note(initial_text)
        elif name and "Sticky Note" in name and not source:
            # New Sticky Note requested
            self.open_note("")
        else:
            self._show_viewer(EmptyViewer())
            if source:
                self.open_source(source)
        self._retheme()


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
        t.new_overlay.connect(lambda: self.new_overlay_requested.emit(None))
        t.collapse_clicked.connect(self.toggle_collapse)
        t.settings_clicked.connect(self.popup.show_below)
        t.invert_toggled.connect(self.toggle_invert_colors)
        t.click_through_toggled.connect(self.toggle_click_through)
        t.close_clicked.connect(self.close)

        p = self.popup
        p.opacity_changed.connect(self.set_opacity)
        p.hue_changed.connect(self.set_hue)
        p.on_top_changed.connect(self.set_on_top)
        p.click_through_changed.connect(self.set_click_through)
        p.capture_changed.connect(self.set_hide_from_capture)
        p.icon_changed.connect(self.set_icon)
        p.new_overlay.connect(lambda: self.new_overlay_requested.emit(None))

    def _shortcuts(self):
        def sc(seq, fn):
            QShortcut(QKeySequence(seq), self, activated=fn)

        sc("F11", self.toggle_fullscreen)
        sc("Esc", lambda: self.isFullScreen() and self.toggle_fullscreen())
        sc("Ctrl+N", lambda: self.new_overlay_requested.emit(None))
        sc("Ctrl+H", self.hub_requested.emit)
        sc("Ctrl+Shift+L", self.mode_toggle_requested.emit)
        sc("Ctrl+O", self.open_dialog)
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
        # Stop any existing collapse animation
        if hasattr(self, "_collapse_anim") and self._collapse_anim and self._collapse_anim.state() == QPropertyAnimation.Running:
            self._collapse_anim.stop()

        self._collapsed = not self._collapsed
        cur_geom = self.geometry()

        if self._collapsed:
            self._pre_collapse_geom = cur_geom
            target_geom = QRect(cur_geom.x(), cur_geom.y(), 50, 50)
            self.titlebar.hide()
            self.body.hide()
            self.layout().setContentsMargins(0, 0, 0, 0)
            self.setMinimumSize(0, 0)
            self.setMaximumSize(16777215, 16777215)
            self.setFixedSize(50, 50)
            self.setToolTip(f"Lucent #{self.index} (Double-click or press Ctrl+K to expand)")

            # Animate geometry shrink smoothly & swiftly
            anim = QPropertyAnimation(self, b"geometry")
            anim.setDuration(120)
            anim.setStartValue(cur_geom)
            anim.setEndValue(target_geom)
            anim.setEasingCurve(QEasingCurve.OutQuad)
            anim.finished.connect(lambda: (self.setFixedSize(50, 50), self.update()))
            self._collapse_anim = anim
            anim.start()
        else:
            self.setMinimumSize(380, 260)
            self.setMaximumSize(16777215, 16777215)
            self.layout().setContentsMargins(EDGE, EDGE, EDGE, EDGE)
            self.body.show()
            self._position_floating_titlebar()
            self.setToolTip("")

            target_geom = self._pre_collapse_geom if self._pre_collapse_geom else QRect(cur_geom.x(), cur_geom.y(), 940, 640)

            anim = QPropertyAnimation(self, b"geometry")
            anim.setDuration(140)
            anim.setStartValue(cur_geom)
            anim.setEndValue(target_geom)
            anim.setEasingCurve(QEasingCurve.OutQuad)
            anim.finished.connect(lambda: (self._position_floating_titlebar(), self.update()))
            self._collapse_anim = anim
            anim.start()

    def toggle_click_through(self):
        self.set_click_through(not self.look.click_through)

    def set_click_through(self, enabled: bool):
        self.look.click_through = enabled
        if winapi.WIN:
            winapi.set_click_through(self, enabled)
            if enabled:
                self._start_ghost_hover_tracker()
            else:
                self._stop_ghost_hover_tracker()
        else:
            # Cross-platform Qt fallback for Linux/macOS
            was_visible = self.isVisible()
            self.setWindowFlag(Qt.WindowTransparentForInput, enabled)
            if was_visible:
                self.show()
            if enabled and not winapi.can_unlock_click_through():
                # No tray and no global hotkey here, so say how to get the mouse back.
                print("Lucent: click-through is on. Run `lucent --toggle-click-through` "
                      "(bind it to a shortcut) to turn it off.")
        self.titlebar.set_click_through(enabled)
        self.popup.sync(self.look)
        save_look(self.look)

    def _start_ghost_hover_tracker(self):
        if not hasattr(self, "_ghost_timer"):
            self._ghost_timer = QTimer(self)
            self._ghost_timer.setInterval(40)  # fast, responsive 25fps poll
            self._ghost_timer.timeout.connect(self._check_ghost_hover)
        self._ghost_btn_active = False
        self._ghost_timer.start()

    def _stop_ghost_hover_tracker(self):
        if hasattr(self, "_ghost_timer") and self._ghost_timer.isActive():
            self._ghost_timer.stop()
        self._ghost_btn_active = False

    def _check_ghost_hover(self):
        if not self.look.click_through or not self.isVisible() or self._collapsed:
            return
        btn = self.titlebar.btn_ghost
        cursor_pos = QCursor.pos()

        # Check if cursor is over overlay window
        win_rect = self.geometry()
        is_over_win = win_rect.contains(cursor_pos)
        if is_over_win and not self.titlebar.isVisible():
            self.titlebar.setVisible(True)
            self.titlebar.raise_()
        elif not is_over_win and self.titlebar.isVisible() and not self.popup.isVisible():
            self.titlebar.setVisible(False)

        # Convert button global rect to check if cursor is strictly over the ghost button
        btn_top_left = btn.mapToGlobal(QPoint(0, 0))
        btn_rect = QRect(btn_top_left, btn.size())

        is_over_btn = btn_rect.contains(cursor_pos)
        if is_over_btn != self._ghost_btn_active:
            self._ghost_btn_active = is_over_btn
            if is_over_btn:
                # Cursor is hovering over ONLY the click-through button:
                # Temporarily remove WS_EX_TRANSPARENT so the button can receive click
                winapi.set_click_through(self, False)
            else:
                # Outside the button: restore click-through pass-through immediately
                winapi.set_click_through(self, True)

    # content ------------------------------------------------------------
    def open_source(self, text):
        source = normalize_source(text)
        if source is None:
            return
        self.current_source = source
        add_recent_source(source)
        self.persist_state()
        try:
            viewer = create_viewer(source)
        except Exception as exc:
            viewer = UnsupportedViewer(str(exc))
        self._show_viewer(viewer)

    def open_note(self, initial_text: str = ""):
        self.current_source = f"note:{initial_text}"
        viewer = NoteViewer(initial_text=initial_text)
        viewer.text_modified.connect(self._on_note_text_modified)
        self._show_viewer(viewer)
        self.persist_state()

    def _on_note_text_modified(self, text: str):
        self.current_source = f"note:{text}"
        self.persist_state()

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
        if hasattr(viewer, "source_changed"):
            viewer.source_changed.connect(self._on_source_changed)

    def _on_source_changed(self, new_source: str):
        if new_source and new_source != self.current_source:
            self.current_source = new_source
            add_recent_source(new_source)
            self.persist_state()

    def _on_title(self, title):
        display_title = title if title else f"Overlay #{self.index}"
        self.setWindowTitle(f"Lucent — {display_title}")
        self.titlebar.set_title(display_title)

    # look ---------------------------------------------------------------
    def set_opacity(self, value: float):
        self.look.opacity = max(MIN_OPACITY, min(1.0, value))
        if self._intro:
            self._intro.stop()
            self._intro = None
        self.setWindowOpacity(self.look.opacity)
        self.popup.sync(self.look)
        save_look(self.look)
        self.persist_state()

    def set_icon(self, icon_name: str, icon_file: str = None):
        self.look.icon_name = icon_name
        self.look.icon_file = icon_file
        pm = render_overlay_pixmap(18, icon_name, icon_file)
        self.titlebar.set_icon_pixmap(pm)
        save_look(self.look)
        self.persist_state()
        self.update()

    def persist_state(self):
        if self._collapsed and self._pre_collapse_geom:
            g = self._pre_collapse_geom
        else:
            g = self.normalGeometry() if (self.isMaximized() or self.isFullScreen()) else self.geometry()
        look_dict = {
            "opacity": self.look.opacity,
            "hue": self.look.hue,
            "on_top": self.look.on_top,
            "hide_from_capture": self.look.hide_from_capture,
            "click_through": self.look.click_through,
            "invert_colors": self.look.invert_colors,
            "icon_name": self.look.icon_name,
            "icon_file": self.look.icon_file,
        }
        upsert_overlay_record(
            overlay_id=self.overlay_id,
            name=self.custom_name,
            source=self.current_source or "",
            look=look_dict,
            geometry=[g.x(), g.y(), g.width(), g.height()],
        )

    def set_hue(self, hue: int):
        self.look.hue = hue % 360
        self._retheme()
        self.popup.sync(self.look)
        save_look(self.look)
        self.persist_state()

    def set_on_top(self, on: bool):
        self.look.on_top = on
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        if visible:
            self.show()
        save_look(self.look)
        self.persist_state()

    def set_hide_from_capture(self, hidden: bool):
        self.look.hide_from_capture = hidden
        self._apply_capture()
        save_look(self.look)
        self.persist_state()

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
        self.persist_state()

    def _apply_inversion(self):
        if not self._viewer:
            self.update()
            return
        if self.look.invert_colors:
            # Enhanced readability high-contrast mode:
            # Sets a deep obsidian background for crisp legibility and inverts/high-contrasts documents
            self.body.setStyleSheet("QWidget#body { background: transparent; }")
            if hasattr(self._viewer, "editor") and hasattr(self._viewer.editor, "setStyleSheet"):
                # NoteViewer / CodeEditor
                self._viewer.editor.setStyleSheet(f"""
                    QPlainTextEdit {{
                        background: rgba(8, 10, 15, 0.95);
                        color: #ffffff;
                        selection-background-color: {theme.accent(self.look.hue).name()};
                        padding: 6px;
                    }}
                    {theme.scrollbar_stylesheet(self.look.hue)}
                """)
            elif hasattr(self._viewer, "_edit"):
                # TextViewer
                self._viewer._edit.setStyleSheet(f"""
                    QPlainTextEdit {{
                        background: rgba(8, 10, 15, 0.95);
                        color: #ffffff;
                        padding: 10px;
                        selection-background-color: {theme.accent(self.look.hue).name()};
                    }}
                    {theme.scrollbar_stylesheet(self.look.hue)}
                """)
            elif hasattr(self._viewer, "_view") and hasattr(self._viewer._view, "setPalette"):
                # PdfViewer
                pal = self._viewer._view.palette()
                pal.setColor(pal.ColorRole.Base, QColor(12, 14, 20))
                pal.setColor(pal.ColorRole.WindowText, QColor(255, 255, 255))
                self._viewer._view.setPalette(pal)
            elif hasattr(self._viewer, "_web"):
                # WebViewer: run dark mode / inverted CSS injection for instant high-contrast readability
                js = """
                (function() {
                    let el = document.getElementById('lucent-readability-style');
                    if (!el) {
                        el = document.createElement('style');
                        el.id = 'lucent-readability-style';
                        el.innerHTML = 'html { filter: invert(90%) hue-rotate(180deg) contrast(110%) !important; background: #111 !important; }';
                        document.head.appendChild(el);
                    }
                })();
                """
                self._viewer._web.page().runJavaScript(js)
        else:
            if hasattr(self._viewer, "editor"):
                self._viewer.apply_theme(self.look.hue)
            elif hasattr(self._viewer, "_edit"):
                self._viewer.apply_theme(self.look.hue)
            elif hasattr(self._viewer, "_view") and hasattr(self._viewer._view, "setPalette"):
                self._viewer.apply_theme(self.look.hue)
            elif hasattr(self._viewer, "_web"):
                js = """
                (function() {
                    let el = document.getElementById('lucent-readability-style');
                    if (el) el.remove();
                })();
                """
                self._viewer._web.page().runJavaScript(js)
        self.update()

    def _retheme(self):
        h = self.look.hue
        self.setStyleSheet(theme.scrollbar_stylesheet(h))
        self.titlebar.apply_theme(h)
        self.titlebar.set_inverted(self.look.invert_colors)
        pm = render_overlay_pixmap(18, self.look.icon_name, self.look.icon_file)
        self.titlebar.set_icon_pixmap(pm)
        self.popup.apply_theme(h)
        if self._viewer:
            self._viewer.apply_theme(h)
            self._apply_inversion()
        self.update()

    def _position_floating_titlebar(self):
        if self.isFullScreen() or self.isMaximized():
            self.titlebar.setGeometry(0, 0, self.width(), self.titlebar.HEIGHT)
        else:
            self.titlebar.setGeometry(EDGE, EDGE, max(10, self.width() - 2 * EDGE), self.titlebar.HEIGHT)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._position_floating_titlebar()
        if not self._collapsed:
            self.persist_state()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self._collapsed:
            # Draw abstract, crisp rounded icon badge with custom icon and overlay number
            rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
            p.setBrush(theme.background(self.look.hue))
            acc = theme.accent(self.look.hue)
            p.setPen(acc)
            p.drawRoundedRect(rect, 4, 4)

            # Draw icon shape in center
            icon_rect = QRectF(8, 8, 34, 34)
            if self.look.icon_file and os.path.isfile(self.look.icon_file):
                pm = render_overlay_pixmap(34, self.look.icon_name, self.look.icon_file)
                p.drawPixmap(8, 8, pm)
            else:
                draw_shape_icon(p, icon_rect, shape=self.look.icon_name, glow=0.3, opacity=0.95)

            # Draw overlay index badge in bottom-right corner
            badge_bg = acc
            badge_bg.setAlpha(220)
            p.setBrush(badge_bg)
            p.setPen(Qt.NoPen)
            badge_rect = QRectF(28, 28, 18, 18)
            p.drawRoundedRect(badge_rect, 4, 4)

            p.setPen(Qt.white)
            font = theme.ui_font(8)
            font.setBold(True)
            p.setFont(font)
            p.drawText(badge_rect, Qt.AlignCenter, str(self.index))
        else:
            if self.look.invert_colors:
                # High-contrast enhanced readability backdrop
                p.fillRect(self.rect(), QColor(10, 12, 18, 245))
                border = theme.accent(self.look.hue)
                border.setAlpha(200)
                p.setPen(border)
                p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 4, 4)
            else:
                p.fillRect(self.rect(), theme.background(self.look.hue))
                border = theme.accent(self.look.hue)
                border.setAlpha(110)
                p.setPen(border)
                p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 4, 4)
        p.end()

    def mouseDoubleClickEvent(self, e):
        if self._collapsed:
            self.toggle_collapse()
            e.accept()
            return
        super().mouseDoubleClickEvent(e)

    # showing, fullscreen, maximize --------------------------------------
    def minimize_animated(self):
        cur_pos = self.pos()
        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setStartValue(self.windowOpacity())
        fade.setEndValue(0.0)
        fade.setDuration(110)
        fade.setEasingCurve(QEasingCurve.InQuad)

        slide = QPropertyAnimation(self, b"pos")
        slide.setStartValue(cur_pos)
        slide.setEndValue(cur_pos + QPoint(0, 10))
        slide.setDuration(110)
        slide.setEasingCurve(QEasingCurve.InQuad)

        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(slide)

        def on_min_done():
            self.showMinimized()
            self.setWindowOpacity(self.look.opacity)
            self.move(cur_pos)

        group.finished.connect(on_min_done)
        self._min_anim = group
        group.start()

    def show_animated(self):
        end = self.pos()
        self.setWindowOpacity(0.0)
        self.move(end + QPoint(0, 6))
        self.show()
        fade = QPropertyAnimation(self, b"windowOpacity")
        fade.setStartValue(0.0)
        fade.setEndValue(self.look.opacity)
        fade.setDuration(140)
        fade.setEasingCurve(QEasingCurve.OutQuad)

        slide = QPropertyAnimation(self, b"pos")
        slide.setStartValue(end + QPoint(0, 6))
        slide.setEndValue(end)
        slide.setDuration(140)
        slide.setEasingCurve(QEasingCurve.OutQuad)

        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(slide)
        group.finished.connect(lambda: self.setWindowOpacity(self.look.opacity))
        self._intro = group
        group.start()

    def showEvent(self, e):
        super().showEvent(e)
        self._position_floating_titlebar()
        QTimer.singleShot(0, self._apply_capture)
        QTimer.singleShot(0, lambda: winapi.set_taskbar_hidden(self, True))
        QTimer.singleShot(0, lambda: winapi.set_window_rounded_corners(self, small=True))
        if self.look.click_through:
            QTimer.singleShot(0, lambda: self.set_click_through(True))
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
            self._position_floating_titlebar()
            self.titlebar.setVisible(not fs)
        super().changeEvent(e)

    def closeEvent(self, e):
        self._titlebar_timer.stop()
        self._stop_ghost_hover_tracker()
        self._unregister_hotkey()
        self.persist_state()
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
        # In collapsed icon mode, let user directly drag the icon without needing Alt
        if self._collapsed and e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint()
            e.accept()
            return

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
            self.persist_state()
            e.accept()
            return
        super().mouseReleaseEvent(e)

    def _on_titlebar_timeout(self):
        if not self._collapsed and not self.popup.isVisible():
            self.titlebar.setVisible(False)

    def enterEvent(self, e):
        if not self._collapsed:
            self._position_floating_titlebar()
            self.titlebar.setVisible(True)
            self.titlebar.raise_()
            self._titlebar_timer.start(4500)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.unsetCursor()
        self._titlebar_timer.stop()
        # Keep titlebar visible if settings popup or child widget has focus/active
        if not self._collapsed and not self.popup.isVisible():
            self.titlebar.setVisible(False)
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
