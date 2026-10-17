"""Lucent Main App Window.
Lists all overlays created (both currently Active and Inactive/Saved in past),
displays status tags, supports inline renaming, deletion, opening/spawning,
and includes an input bar aligned to create overlays from a URL, local file, or clipboard.
All styles strictly follow the theme hue system with frameless title bar.
Includes default settings corner, icon customization, and sticky notes creation.
"""
import os
from PySide6.QtCore import QPoint, QRect, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QKeySequence, QPainter, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import glyphs, theme, winapi
from .config import (
    Look,
    delete_overlay_record,
    load_look,
    load_overlay_registry,
    save_look,
    upsert_overlay_record,
)
from .icon import app_icon, draw_shape_icon, render_overlay_pixmap
from .settings_popup import SettingsPopup
from .viewers import FILE_FILTER


class OverlayListItem(QFrame):
    """Card representing an overlay in the registry with status tag, rename, delete, and open controls."""

    open_requested = Signal(dict)
    bring_front_requested = Signal(object)
    toggle_collapse_requested = Signal(object)
    toggle_click_through_requested = Signal(object)
    open_settings_requested = Signal(object, object)  # overlay, anchor_widget
    close_requested = Signal(object)
    rename_requested = Signal(str, str)  # overlay_id, new_name
    delete_requested = Signal(str)  # overlay_id

    def __init__(self, record: dict, live_overlay=None, parent=None, hue: int = 215):
        super().__init__(parent)
        self.record = record
        self.overlay = live_overlay  # OverlayWindow instance if currently open, else None
        self._hue = hue
        self.setAttribute(Qt.WA_Hover, True)
        self.setObjectName("OverlayListItem")
        self.setFixedHeight(68)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(12)

        # Icon with badge
        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(36, 36)
        self._update_icon()
        lay.addWidget(self.lbl_icon)

        # Title, Source, and Status Tag
        info_lay = QVBoxLayout()
        info_lay.setSpacing(3)
        info_lay.setContentsMargins(0, 2, 0, 2)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        name = self.record.get("name") or "Unnamed Overlay"
        self.lbl_title = QLabel(name)
        self.lbl_title.setObjectName("ItemTitle")
        title_row.addWidget(self.lbl_title)

        # Status Tag: Active (accent) vs Saved (neutral low-alpha white)
        self.lbl_tag = QLabel()
        self._update_tag()
        title_row.addWidget(self.lbl_tag)
        title_row.addStretch(1)

        info_lay.addLayout(title_row)

        src = self.record.get("source", "")
        if not src:
            src_display = "Empty Canvas / Sticky Note"
        elif len(src) > 40:
            src_display = src[:20] + "..." + src[-17:]
        else:
            src_display = src

        self.lbl_sub = QLabel(src_display)
        self.lbl_sub.setObjectName("ItemSubtitle")
        info_lay.addWidget(self.lbl_sub)

        lay.addLayout(info_lay, 1)

        # Hover action buttons
        self.actions_widget = QWidget(self)
        actions_lay = QHBoxLayout(self.actions_widget)
        actions_lay.setContentsMargins(0, 0, 0, 0)
        actions_lay.setSpacing(4)

        if self.overlay is not None:
            # Controls for Active Overlays (3 buttons matching inactive card layout)
            self.btn_front = self._make_btn("view", "Bring Overlay to Front")
            self.btn_rename = self._make_btn("edit", "Rename Overlay")
            self.btn_close = self._make_btn("close", "Close Window", is_close=True)

            self.btn_front.clicked.connect(lambda: self.bring_front_requested.emit(self.overlay))
            self.btn_rename.clicked.connect(self._prompt_rename)
            self.btn_close.clicked.connect(lambda: self.close_requested.emit(self.overlay))

            actions_lay.addWidget(self.btn_front)
            actions_lay.addWidget(self.btn_rename)
            actions_lay.addWidget(self.btn_close)
        else:
            # Controls for Inactive / Saved Overlays
            self.btn_open = self._make_btn("play", "Open / Restore Overlay")
            self.btn_rename = self._make_btn("edit", "Rename Overlay")
            self.btn_delete = self._make_btn("delete", "Delete Overlay Record", is_close=True)

            self.btn_open.clicked.connect(lambda: self.open_requested.emit(self.record))
            self.btn_rename.clicked.connect(self._prompt_rename)
            self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.record.get("id")))

            actions_lay.addWidget(self.btn_open)
            actions_lay.addWidget(self.btn_rename)
            actions_lay.addWidget(self.btn_delete)

        lay.addWidget(self.actions_widget)
        self.actions_widget.setVisible(False)
        self.apply_theme(self._hue)

    def apply_theme(self, hue: int):
        self._hue = hue
        self._update_icon()
        self._update_tag()
        self._apply_idle_style()

    def _update_tag(self):
        acc = theme.accent(self._hue).name()
        if self.overlay is not None:
            self.lbl_tag.setText("ACTIVE")
            self.lbl_tag.setStyleSheet(f"""
                QLabel {{
                    background: {theme.fg(0.08)};
                    color: {acc};
                    border: 1px solid {acc};
                    border-radius: 4px;
                    padding: 1px 6px;
                    font-size: 7.5pt;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                }}
            """)
        else:
            self.lbl_tag.setText("SAVED")
            self.lbl_tag.setStyleSheet(f"""
                QLabel {{
                    background: {theme.fg(0.04)};
                    color: {theme.TEXT_MUTED};
                    border: 1px solid {theme.fg(0.12)};
                    border-radius: 4px;
                    padding: 1px 6px;
                    font-size: 7.5pt;
                    font-weight: 600;
                    letter-spacing: 0.5px;
                }}
            """)

    def _prompt_rename(self):
        current = self.lbl_title.text()
        text, ok = QInputDialog.getText(self, "Rename Overlay", "Enter a custom name for this overlay:", text=current)
        if ok and text.strip():
            new_name = text.strip()
            self.lbl_title.setText(new_name)
            self.record["name"] = new_name
            overlay_id = self.record.get("id")
            if self.overlay:
                self.overlay.custom_name = new_name
                self.overlay.setWindowTitle(f"{new_name} — Lucent")
                self.overlay.titlebar.set_title(new_name)
                self.overlay.persist_state()
            else:
                upsert_overlay_record(
                    overlay_id,
                    new_name,
                    self.record.get("source", ""),
                    self.record.get("look", {}),
                    self.record.get("geometry", [100, 100, 940, 640]),
                )
            self.rename_requested.emit(overlay_id, new_name)

    def _make_btn(self, glyph, tip, is_close=False):
        btn = QToolButton(self)
        glyphs.set_glyph(btn, glyph, hover="#e81123" if is_close else None, size=16)
        btn.setToolTip(tip)
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("ItemBtnClose" if is_close else "ItemBtn")
        return btn

    def _update_icon(self):
        pm = QPixmap(36, 36)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)

        hue = self._hue
        icon_name = "moon"
        icon_file = None
        if self.overlay:
            hue = self.overlay.look.hue
            icon_name = self.overlay.look.icon_name
            icon_file = self.overlay.look.icon_file
        elif "look" in self.record and isinstance(self.record["look"], dict):
            hue = self.record["look"].get("hue", self._hue)
            icon_name = self.record["look"].get("icon_name", "moon")
            icon_file = self.record["look"].get("icon_file", None)

        acc = theme.accent(hue)
        bg = theme.background(hue)
        p.setBrush(bg)
        p.setPen(acc)
        p.drawRoundedRect(QRect(1, 1, 34, 34), 4, 4)

        if icon_file and os.path.isfile(icon_file):
            custom_pm = render_overlay_pixmap(24, icon_name, icon_file)
            p.drawPixmap(6, 6, custom_pm)
        else:
            draw_shape_icon(p, QRectF(6, 6, 24, 24), shape=icon_name, glow=0.1, opacity=0.9)
        p.end()
        self.lbl_icon.setPixmap(pm)

    def _apply_idle_style(self):
        self.setStyleSheet(f"""
            QFrame#OverlayListItem {{
                background: {theme.fg(0.04)};
                border: 1px solid {theme.fg(0.10)};
                border-radius: 4px;
            }}
            QLabel#ItemTitle {{
                color: {theme.TEXT};
                font-family: {theme.FONT_UI}; font-size: 9.5pt; font-weight: 600;
            }}
            QLabel#ItemSubtitle {{
                color: {theme.TEXT_MUTED};
                font-family: {theme.FONT_UI}; font-size: 8.5pt;
            }}
            {theme.toolbutton_stylesheet()}
        """)

    def enterEvent(self, e):
        self.actions_widget.setVisible(True)
        acc = theme.accent(self._hue).name()
        self.setStyleSheet(f"""
            QFrame#OverlayListItem {{
                background: {theme.fg(0.08)};
                border: 1px solid {acc};
                border-radius: 4px;
            }}
            QLabel#ItemTitle {{
                color: {theme.TEXT};
                font-family: {theme.FONT_UI}; font-size: 9.5pt; font-weight: 600;
            }}
            QLabel#ItemSubtitle {{
                color: {theme.TEXT_MUTED};
                font-family: {theme.FONT_UI}; font-size: 8.5pt;
            }}
            {theme.toolbutton_stylesheet()}
        """)
        if e:
            super().enterEvent(e)

    def leaveEvent(self, e):
        self.actions_widget.setVisible(False)
        self._apply_idle_style()
        if e:
            super().leaveEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            if self.overlay:
                self.bring_front_requested.emit(self.overlay)
            else:
                self.open_requested.emit(self.record)
            e.accept()
            return
        super().mouseDoubleClickEvent(e)


class HubWindow(QWidget):
    """Main App Window: Complete Overlay Manager listing all past & present overlays,
    with an aligned input bar to create new overlays and full per-overlay customization."""

    spawn_requested = Signal(object, object, str, str, object)  # source, look, overlay_id, name, geometry
    bring_front_requested = Signal(object)
    toggle_collapse_requested = Signal(object)
    toggle_click_through_requested = Signal(object)
    close_overlay_requested = Signal(object)

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.default_look = load_look()
        self._hue = self.default_look.hue
        self.setObjectName("HubWindow")
        self.setWindowTitle("Lucent — Overlays")
        self.setWindowIcon(app_icon())
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.resize(440, 600)
        self.setMinimumSize(380, 440)

        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)

        # Custom Frameless Titlebar
        self.titlebar = QWidget(self)
        self.titlebar.setObjectName("HubTitleBar")
        self.titlebar.setFixedHeight(36)
        title_lay = QHBoxLayout(self.titlebar)
        title_lay.setContentsMargins(12, 0, 0, 0)
        title_lay.setSpacing(8)

        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(18, 18))
        self.lbl_title = QLabel("Lucent Overlays")
        self.lbl_title.setObjectName("title")

        # Default Settings Corner button
        self.btn_default_settings = QToolButton(self.titlebar)
        glyphs.set_glyph(self.btn_default_settings, "settings")
        self.btn_default_settings.setToolTip("App Default Settings (Theme, Transparency, Default Look)")
        self.btn_default_settings.setObjectName("settings")
        self.btn_default_settings.setFixedSize(36, 36)
        self.btn_default_settings.setFocusPolicy(Qt.NoFocus)

        self.btn_mode = QToolButton(self.titlebar)
        self.btn_mode.setObjectName("settings")
        self.btn_mode.setFixedSize(36, 36)
        self.btn_mode.setFocusPolicy(Qt.NoFocus)
        self.btn_mode.clicked.connect(lambda: self.manager.toggle_mode())
        self._update_mode_button()

        self.btn_close = QToolButton(self.titlebar)
        glyphs.set_glyph(self.btn_close, "close", hover="#e81123")
        self.btn_close.setToolTip("Close Hub")
        self.btn_close.setObjectName("close")
        self.btn_close.setFixedSize(44, 36)
        self.btn_close.setFocusPolicy(Qt.NoFocus)
        self.btn_close.clicked.connect(self.close)

        title_lay.addWidget(logo)
        title_lay.addWidget(self.lbl_title)
        title_lay.addStretch(1)
        title_lay.addWidget(self.btn_mode)
        title_lay.addWidget(self.btn_default_settings)
        title_lay.addWidget(self.btn_close)
        root.addWidget(self.titlebar)

        # Settings popup for Default Settings Corner
        QShortcut(QKeySequence("Ctrl+Shift+L"), self, activated=lambda: self.manager.toggle_mode())
        self.default_popup = SettingsPopup(self)
        self.default_popup.sync(self.default_look)
        self._wire_default_settings()

        # Main Body
        body = QWidget(self)
        body.setObjectName("HubBody")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(16, 14, 16, 14)
        body_lay.setSpacing(12)

        # Input Card Container
        self.input_container = QFrame(body)
        self.input_container.setObjectName("InputContainer")
        input_box_lay = QVBoxLayout(self.input_container)
        input_box_lay.setContentsMargins(10, 10, 10, 10)
        input_box_lay.setSpacing(8)

        lbl_row = QHBoxLayout()
        self.lbl_input_prompt = QLabel("Create New Overlay")
        self.lbl_input_prompt.setObjectName("InputPrompt")
        lbl_row.addWidget(self.lbl_input_prompt)
        lbl_row.addStretch(1)

        self.btn_sticky_note = QPushButton("Sticky Note", self.input_container)
        self.btn_sticky_note.setObjectName("StickyNoteBtn")
        self.btn_sticky_note.setToolTip("Create a blank note overlay for sticky notes / scratchpad")
        self.btn_sticky_note.setCursor(Qt.PointingHandCursor)
        self.btn_sticky_note.clicked.connect(self._create_sticky_note)
        lbl_row.addWidget(self.btn_sticky_note)

        input_box_lay.addLayout(lbl_row)

        row_lay = QHBoxLayout()
        row_lay.setSpacing(8)

        self.input_box = QLineEdit(self.input_container)
        self.input_box.setObjectName("UrlInputBox")
        self.input_box.setPlaceholderText("Enter URL, file path, or leave blank...")
        self.input_box.setClearButtonEnabled(True)
        self.input_box.returnPressed.connect(self._on_add_submitted)
        row_lay.addWidget(self.input_box, 1)

        # Browse button with icon
        self.btn_browse = QToolButton(self.input_container)
        self.btn_browse.setObjectName("FileBtn")
        glyphs.set_glyph(self.btn_browse, "open")
        self.btn_browse.setToolTip("Browse local file (PDF, Image, Markdown, Code)")
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        self.btn_browse.setFixedSize(36, 32)
        self.btn_browse.clicked.connect(self._on_browse_file)
        row_lay.addWidget(self.btn_browse)

        self.btn_add = QPushButton("+ Add", self.input_container)
        self.btn_add.setObjectName("ActionBtn")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.clicked.connect(self._on_add_submitted)
        row_lay.addWidget(self.btn_add)

        input_box_lay.addLayout(row_lay)
        body_lay.addWidget(self.input_container)

        # Search / filter box
        self.search_box = QLineEdit(body)
        self.search_box.setObjectName("SearchBox")
        self.search_box.setPlaceholderText("Filter overlays by name, URL or status...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self._filter_items)
        body_lay.addWidget(self.search_box)

        # Scroll area containing overlay cards
        self.scroll = QScrollArea(body)
        self.scroll.setObjectName("CardsScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setContentsMargins(0, 2, 2, 2)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch(1)
        self.lbl_empty = QLabel("No overlays yet.\nPaste a link or choose a file above, or start a Sticky Note.")
        self.lbl_empty.setObjectName("EmptyState")
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.lbl_empty.setWordWrap(True)
        self.cards_layout.insertWidget(0, self.lbl_empty)
        self.scroll.setWidget(self.scroll_content)
        self.scroll.viewport().setAutoFillBackground(False)
        self.scroll_content.setAutoFillBackground(False)

        body_lay.addWidget(self.scroll, 1)

        # Footer with status and cache location
        footer_row = QHBoxLayout()
        self.lbl_status = QLabel("0 overlays recorded")
        self.lbl_status.setObjectName("StatusLabel")
        footer_row.addWidget(self.lbl_status)
        footer_row.addStretch(1)

        from .config import get_storage_locations
        locs = get_storage_locations()
        cache_path = locs.get("cache", "")
        self.lbl_cache_info = QLabel("Cache: Local")
        self.lbl_cache_info.setObjectName("StatusLabel")
        self.lbl_cache_info.setToolTip(f"Lucent Cache Directory:\n{cache_path}\n(Click to copy path)")
        self.lbl_cache_info.setCursor(Qt.PointingHandCursor)
        self.lbl_cache_info.mousePressEvent = lambda e: QGuiApplication.clipboard().setText(cache_path)
        footer_row.addWidget(self.lbl_cache_info)

        body_lay.addLayout(footer_row)

        root.addWidget(body, 1)

        self._item_widgets = []
        self.apply_theme(self._hue)

    def _wire_default_settings(self):
        self.btn_default_settings.clicked.connect(lambda: self.default_popup.show_below(self.btn_default_settings))
        self.default_popup.hue_changed.connect(self._on_default_hue_changed)
        self.default_popup.opacity_changed.connect(self._on_default_opacity_changed)
        self.default_popup.on_top_changed.connect(lambda b: (setattr(self.default_look, "on_top", b), save_look(self.default_look)))
        self.default_popup.click_through_changed.connect(lambda b: (setattr(self.default_look, "click_through", b), save_look(self.default_look)))
        self.default_popup.capture_changed.connect(lambda b: (setattr(self.default_look, "hide_from_capture", b), save_look(self.default_look)))
        self.default_popup.icon_changed.connect(self._on_default_icon_changed)
        self.default_popup.new_overlay.connect(lambda: self.spawn_requested.emit(None, None, None, None, None))

    def _on_default_hue_changed(self, hue: int):
        self.default_look.hue = hue
        save_look(self.default_look)
        self.apply_theme(hue)

    def _on_default_opacity_changed(self, op: float):
        self.default_look.opacity = op
        save_look(self.default_look)

    def _on_default_icon_changed(self, name: str, file_path: str):
        self.default_look.icon_name = name
        self.default_look.icon_file = file_path
        save_look(self.default_look)

    def _create_sticky_note(self):
        note_name = f"Sticky Note #{len(self._item_widgets) + 1}"
        self.spawn_requested.emit(None, None, None, note_name, None)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and e.position().y() <= 36 and self.windowHandle():
            self.windowHandle().startSystemMove()
        super().mousePressEvent(e)

    def showEvent(self, e):
        super().showEvent(e)
        winapi.set_window_rounded_corners(self, small=False)

    def apply_theme(self, hue: int):
        self._hue = hue
        acc = theme.accent(hue).name()
        bg = theme.background(hue).name()
        ch = theme.chrome(hue).name()

        self.setStyleSheet(f"""
            QWidget#HubWindow {{
                background: {bg};
                border: 1px solid {acc};
                border-radius: 4px;
            }}
            QWidget#HubTitleBar {{
                background: {ch};
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                border-bottom: 1px solid {theme.fg(0.08)};
            }}
            QLabel#title {{
                color: {theme.TEXT};
                font-family: {theme.FONT_UI}; font-size: 9.5pt; font-weight: 600;
            }}
            QWidget#HubBody {{
                background: transparent;
            }}
            QScrollArea#CardsScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea#CardsScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QFrame#InputContainer {{
                background: {theme.fg(0.04)};
                border: 1px solid {theme.fg(0.10)};
                border-radius: 4px;
            }}
            QLabel#InputPrompt {{
                font-family: {theme.FONT_UI}; font-size: 9pt; font-weight: 600;
                color: {theme.TEXT_MUTED};
            }}
            QPushButton#StickyNoteBtn {{
                background: {theme.fg(0.08)};
                color: {theme.TEXT};
                font-family: {theme.FONT_UI}; font-size: 8.5pt;
                border: 1px solid {theme.fg(0.14)};
                border-radius: 4px;
                padding: 3px 8px;
            }}
            QPushButton#StickyNoteBtn:hover {{
                background: {theme.fg(0.16)};
            }}
            QLabel#StatusLabel {{
                color: {theme.TEXT_MUTED};
                font-family: {theme.FONT_UI}; font-size: 8.5pt;
            }}
            QLineEdit#UrlInputBox {{
                background: {theme.fg(0.06)};
                color: {theme.TEXT};
                border: 1px solid {theme.fg(0.14)};
                border-radius: 4px;
                padding: 6px 10px;
                font-family: {theme.FONT_UI}; font-size: 9.5pt;
            }}
            QLineEdit#UrlInputBox:focus {{
                border: 1px solid {acc};
                background: {theme.fg(0.10)};
            }}
            QLineEdit#SearchBox {{
                background: {theme.fg(0.04)};
                color: {theme.TEXT};
                border: 1px solid {theme.fg(0.10)};
                border-radius: 4px;
                padding: 6px 10px;
                font-family: {theme.FONT_UI}; font-size: 8.5pt;
            }}
            QLineEdit#SearchBox:focus {{
                border: 1px solid {acc};
                background: {theme.fg(0.08)};
            }}
            QToolButton#FileBtn {{
                background: {theme.fg(0.08)};
                color: {theme.TEXT};
                font-size: 10pt;
                border: 1px solid {theme.fg(0.15)};
                border-radius: 4px;
            }}
            QToolButton#FileBtn:hover {{
                background: {theme.fg(0.16)};
            }}
            QPushButton#ActionBtn {{
                background: {theme.accent_fill(hue).name()};
                color: #ffffff;
                font-family: {theme.FONT_UI}; font-size: 9.5pt; font-weight: 600;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
            }}
            QPushButton#ActionBtn:hover {{
                background: {theme.accent_fill(hue).lighter(115).name()};
            }}
            QLabel#EmptyState {{
                color: {theme.TEXT_MUTED};
                font-family: {theme.FONT_UI}; font-size: 10pt;
            }}
            {theme.toolbutton_stylesheet()}
            {theme.scrollbar_stylesheet(hue)}
        """)

        self.default_popup.apply_theme(hue)
        for item in self._item_widgets:
            item.apply_theme(hue)
        self._update_mode_button()
        glyphs.refresh(self)

    def _update_mode_button(self):
        light = theme.is_light()
        glyphs.set_glyph(self.btn_mode, "moon" if light else "sun")
        self.btn_mode.setToolTip("Switch to dark mode  (Ctrl+Shift+L)" if light
                                 else "Switch to light mode  (Ctrl+Shift+L)")

    def focus_input(self):
        """Focus the input text box and select all for rapid new overlay creation."""
        self.input_box.setFocus()
        self.input_box.selectAll()

    def _on_add_submitted(self):
        text = self.input_box.text().strip()
        source = text if text else None
        self.input_box.clear()
        self.spawn_requested.emit(source, None, None, None, None)

    def _on_browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select file to overlay", "", FILE_FILTER)
        if path:
            self.spawn_requested.emit(path, None, None, None, None)

    def refresh(self, active_windows):
        """Rebuild list showing ALL overlays (active + inactive/saved in past)."""
        # Hub's master/parent default hue
        cur_hue = load_look().hue
        if cur_hue != self._hue:
            self.apply_theme(cur_hue)

        for item in self._item_widgets:
            self.cards_layout.removeWidget(item)
            item.deleteLater()
        self._item_widgets.clear()

        # Load all past records from registry
        registry = load_overlay_registry()

        # Map active windows by overlay_id
        active_map = {w.overlay_id: w for w in active_windows}

        # Sync active windows into registry if not already present
        for w in active_windows:
            if not any(r.get("id") == w.overlay_id for r in registry):
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
                upsert_overlay_record(
                    w.overlay_id,
                    w.custom_name,
                    w.current_source or "",
                    look_dict,
                    [g.x(), g.y(), g.width(), g.height()],
                )
        registry = load_overlay_registry()

        # Separate into active first, then saved
        active_records = [r for r in registry if r.get("id") in active_map]
        inactive_records = [r for r in registry if r.get("id") not in active_map]
        all_ordered = active_records + inactive_records

        for rec in all_ordered:
            oid = rec.get("id")
            live_win = active_map.get(oid)
            card = OverlayListItem(rec, live_overlay=live_win, parent=self.scroll_content, hue=self._hue)
            card.bring_front_requested.connect(self.bring_front_requested.emit)
            card.toggle_collapse_requested.connect(self.toggle_collapse_requested.emit)
            card.toggle_click_through_requested.connect(self.toggle_click_through_requested.emit)
            card.open_settings_requested.connect(self._open_overlay_settings)
            card.close_requested.connect(self.close_overlay_requested.emit)
            card.open_requested.connect(self._restore_inactive_overlay)
            card.delete_requested.connect(self._delete_record)
            card.rename_requested.connect(lambda oid, name: self.refresh(self.manager._windows))

            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
            self._item_widgets.append(card)

        total = len(all_ordered)
        active_count = len(active_windows)
        self.lbl_status.setText(f"{active_count} active / {total} total overlays recorded")
        self._filter_items(self.search_box.text())
        self.lbl_empty.setVisible(total == 0)

    def _restore_inactive_overlay(self, record: dict):
        src = record.get("source") or None
        raw_look = record.get("look")
        look = None
        if raw_look and isinstance(raw_look, dict):
            look = Look(
                opacity=float(raw_look.get("opacity", 0.88)),
                hue=int(raw_look.get("hue", 215)),
                on_top=bool(raw_look.get("on_top", True)),
                hide_from_capture=bool(raw_look.get("hide_from_capture", True)),
                click_through=bool(raw_look.get("click_through", False)),
                invert_colors=bool(raw_look.get("invert_colors", False)),
                icon_name=str(raw_look.get("icon_name", "moon")),
                icon_file=raw_look.get("icon_file", None),
            )
        oid = record.get("id")
        name = record.get("name")
        geom = record.get("geometry")
        self.spawn_requested.emit(src, look, oid, name, geom)

    def _delete_record(self, overlay_id: str):
        delete_overlay_record(overlay_id)
        self.refresh(self.manager._windows)

    def _open_overlay_settings(self, overlay, anchor_btn):
        overlay.showNormal()
        overlay.raise_()
        overlay.activateWindow()
        overlay.popup.show_at(anchor_btn)

    def _filter_items(self, query: str):
        q = query.strip().lower()
        for item in self._item_widgets:
            if not q:
                item.setVisible(True)
                continue
            title = item.lbl_title.text().lower()
            sub = item.lbl_sub.text().lower()
            tag = item.lbl_tag.text().lower()
            item.setVisible(q in title or q in sub or q in tag)
