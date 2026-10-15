"""Lucent Main App Window.
Lists all overlays created (both currently Active and Inactive/Saved in past),
displays status tags, supports inline renaming, deletion, opening/spawning,
and includes an input bar aligned to create overlays from a URL, local file, or clipboard.
"""
from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter
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

from . import theme
from .config import (
    Look,
    delete_overlay_record,
    load_overlay_registry,
    upsert_overlay_record,
)
from .icon import app_icon, draw_moon
from .titlebar import GLYPH
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

    def __init__(self, record: dict, live_overlay=None, parent=None):
        super().__init__(parent)
        self.record = record
        self.overlay = live_overlay  # OverlayWindow instance if currently open, else None
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
        self.lbl_title.setStyleSheet("font-weight: 600; font-size: 10pt; color: #f8fafc;")
        title_row.addWidget(self.lbl_title)

        # Status Tag: Active (green) vs Saved (slate)
        self.lbl_tag = QLabel()
        self._update_tag()
        title_row.addWidget(self.lbl_tag)
        title_row.addStretch(1)

        info_lay.addLayout(title_row)

        src = self.record.get("source", "")
        if not src:
            src_display = "Empty Canvas"
        elif len(src) > 40:
            src_display = src[:20] + "..." + src[-17:]
        else:
            src_display = src

        self.lbl_sub = QLabel(src_display)
        self.lbl_sub.setObjectName("ItemSubtitle")
        self.lbl_sub.setStyleSheet("font-size: 8.5pt; color: #94a3b8;")
        info_lay.addWidget(self.lbl_sub)

        lay.addLayout(info_lay, 1)

        # Hover action buttons
        self.actions_widget = QWidget(self)
        actions_lay = QHBoxLayout(self.actions_widget)
        actions_lay.setContentsMargins(0, 0, 0, 0)
        actions_lay.setSpacing(4)

        if self.overlay is not None:
            # Controls for Active Overlays
            self.btn_front = self._make_btn("👁", "Bring Overlay to Front")
            self.btn_ghost = self._make_btn(GLYPH["click_through"], "Toggle Click-Through / Ghost Mode")
            self.btn_collapse = self._make_btn(GLYPH["collapse"], "Toggle Collapse / Expand")
            self.btn_settings = self._make_btn(GLYPH["settings"], "Overlay Settings")
            self.btn_rename = self._make_btn("✎", "Rename Overlay")
            self.btn_close = self._make_btn(GLYPH["close"], "Close Window", is_close=True)

            self.btn_front.clicked.connect(lambda: self.bring_front_requested.emit(self.overlay))
            self.btn_ghost.clicked.connect(lambda: self.toggle_click_through_requested.emit(self.overlay))
            self.btn_collapse.clicked.connect(lambda: self.toggle_collapse_requested.emit(self.overlay))
            self.btn_settings.clicked.connect(lambda: self.open_settings_requested.emit(self.overlay, self.btn_settings))
            self.btn_rename.clicked.connect(self._prompt_rename)
            self.btn_close.clicked.connect(lambda: self.close_requested.emit(self.overlay))

            actions_lay.addWidget(self.btn_front)
            actions_lay.addWidget(self.btn_ghost)
            actions_lay.addWidget(self.btn_collapse)
            actions_lay.addWidget(self.btn_settings)
            actions_lay.addWidget(self.btn_rename)
            actions_lay.addWidget(self.btn_close)
        else:
            # Controls for Inactive / Saved Overlays
            self.btn_open = self._make_btn("▶", "Open / Restore Overlay")
            self.btn_rename = self._make_btn("✎", "Rename Overlay")
            self.btn_delete = self._make_btn("🗑", "Delete Overlay Record", is_close=True)

            self.btn_open.clicked.connect(lambda: self.open_requested.emit(self.record))
            self.btn_rename.clicked.connect(self._prompt_rename)
            self.btn_delete.clicked.connect(lambda: self.delete_requested.emit(self.record.get("id")))

            actions_lay.addWidget(self.btn_open)
            actions_lay.addWidget(self.btn_rename)
            actions_lay.addWidget(self.btn_delete)

        lay.addWidget(self.actions_widget)
        self.actions_widget.setVisible(False)
        self._apply_idle_style()

    def _update_tag(self):
        if self.overlay is not None:
            self.lbl_tag.setText("ACTIVE")
            self.lbl_tag.setStyleSheet("""
                QLabel {
                    background: rgba(34, 197, 94, 0.18);
                    color: #4ade80;
                    border: 1px solid rgba(74, 222, 128, 0.35);
                    border-radius: 4px;
                    padding: 1px 6px;
                    font-size: 7.5pt;
                    font-weight: 700;
                    letter-spacing: 0.5px;
                }
            """)
        else:
            self.lbl_tag.setText("SAVED")
            self.lbl_tag.setStyleSheet("""
                QLabel {
                    background: rgba(148, 163, 184, 0.12);
                    color: #94a3b8;
                    border: 1px solid rgba(148, 163, 184, 0.25);
                    border-radius: 4px;
                    padding: 1px 6px;
                    font-size: 7.5pt;
                    font-weight: 600;
                    letter-spacing: 0.5px;
                }
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
        btn.setText(glyph)
        btn.setToolTip(tip)
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("ItemBtnClose" if is_close else "ItemBtn")
        return btn

    def _update_icon(self):
        from PySide6.QtGui import QPixmap
        pm = QPixmap(36, 36)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)

        hue = 215
        if self.overlay:
            hue = self.overlay.look.hue
        elif "look" in self.record and isinstance(self.record["look"], dict):
            hue = self.record["look"].get("hue", 215)

        acc = theme.accent(hue)
        bg = theme.background(hue)
        p.setBrush(bg)
        p.setPen(acc)
        p.drawRoundedRect(QRect(1, 1, 34, 34), 8, 8)

        draw_moon(p, QRect(5, 5, 24, 24), glow=0.1, opacity=0.9)
        p.end()
        self.lbl_icon.setPixmap(pm)

    def _apply_idle_style(self):
        self.setStyleSheet("""
            QFrame#OverlayListItem {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.07);
                border-radius: 8px;
            }
        """)

    def enterEvent(self, e):
        self.actions_widget.setVisible(True)
        self.setStyleSheet("""
            QFrame#OverlayListItem {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.20);
                border-radius: 8px;
            }
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

    spawn_requested = Signal(object, object, str, str)  # source, look, overlay_id, name
    bring_front_requested = Signal(object)
    toggle_collapse_requested = Signal(object)
    toggle_click_through_requested = Signal(object)
    close_overlay_requested = Signal(object)

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setObjectName("HubWindow")
        self.setWindowTitle("Lucent — All Overlays")
        self.setWindowIcon(app_icon())
        self.resize(440, 600)
        self.setMinimumSize(380, 440)

        # Sleek dark theme matching Lucent aesthetic
        self.setStyleSheet(f"""
            QWidget#HubWindow {{
                background: #0f1218;
                color: #e2e8f0;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 0.20);
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255, 255, 255, 0.40);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QToolButton#ItemBtn, QToolButton#ItemBtnClose {{
                background: transparent;
                border: none;
                border-radius: 4px;
                color: #cbd5e1;
                font-family: "Segoe MDL2 Assets";
                font-size: 10pt;
            }}
            QToolButton#ItemBtn:hover {{
                background: rgba(255, 255, 255, 0.15);
                color: white;
            }}
            QToolButton#ItemBtnClose:hover {{
                background: #e81123;
                color: white;
            }}
            QPushButton#ActionBtn {{
                background: #3b82f6;
                color: white;
                font-weight: 600;
                font-size: 9.5pt;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton#ActionBtn:hover {{
                background: #2563eb;
            }}
            QToolButton#FileBtn {{
                background: rgba(255, 255, 255, 0.08);
                color: #f1f5f9;
                font-size: 9.5pt;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                padding: 7px 12px;
            }}
            QToolButton#FileBtn:hover {{
                background: rgba(255, 255, 255, 0.16);
            }}
            QLineEdit#UrlInputBox {{
                background: rgba(255, 255, 255, 0.07);
                color: #f8fafc;
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 9.5pt;
            }}
            QLineEdit#UrlInputBox:focus {{
                border: 1.5px solid #3b82f6;
                background: rgba(255, 255, 255, 0.11);
            }}
            QLineEdit#SearchBox {{
                background: rgba(255, 255, 255, 0.05);
                color: #e2e8f0;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 8.5pt;
            }}
            QLineEdit#SearchBox:focus {{
                border: 1px solid #3b82f6;
                background: rgba(255, 255, 255, 0.08);
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        # Header bar: Logo + App Title
        header = QHBoxLayout()
        header.setSpacing(10)

        lbl_logo = QLabel()
        lbl_logo.setPixmap(app_icon().pixmap(24, 24))
        header.addWidget(lbl_logo)

        lbl_header = QLabel("Lucent Overlays")
        lbl_header.setStyleSheet("font-size: 13.5pt; font-weight: 700; color: #f8fafc;")
        header.addWidget(lbl_header, 1)

        root.addLayout(header)

        # Input Card Container
        input_container = QFrame(self)
        input_container.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 10px;
            }
        """)
        input_box_lay = QVBoxLayout(input_container)
        input_box_lay.setContentsMargins(6, 6, 6, 6)
        input_box_lay.setSpacing(10)

        lbl_input_prompt = QLabel("Create New Overlay")
        lbl_input_prompt.setStyleSheet("font-weight: 600; font-size: 9pt; color: #94a3b8;")
        input_box_lay.addWidget(lbl_input_prompt)

        row_lay = QHBoxLayout()
        row_lay.setSpacing(8)

        self.input_box = QLineEdit(input_container)
        self.input_box.setObjectName("UrlInputBox")
        self.input_box.setPlaceholderText("Enter URL, file path, or leave blank...")
        self.input_box.setClearButtonEnabled(True)
        self.input_box.returnPressed.connect(self._on_add_submitted)
        row_lay.addWidget(self.input_box, 1)

        btn_browse = QToolButton(input_container)
        btn_browse.setObjectName("FileBtn")
        btn_browse.setText("Browse…")
        btn_browse.setToolTip("Browse local file (PDF, Image, Markdown, Code)")
        btn_browse.setCursor(Qt.PointingHandCursor)
        btn_browse.clicked.connect(self._on_browse_file)
        row_lay.addWidget(btn_browse)

        btn_add = QPushButton("+ Add", input_container)
        btn_add.setObjectName("ActionBtn")
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.clicked.connect(self._on_add_submitted)
        row_lay.addWidget(btn_add)

        input_box_lay.addLayout(row_lay)
        root.addWidget(input_container)

        # Search / filter box
        self.search_box = QLineEdit(self)
        self.search_box.setObjectName("SearchBox")
        self.search_box.setPlaceholderText("Filter overlays by name, URL or status...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self._filter_items)
        root.addWidget(self.search_box)

        # Scroll area containing overlay cards
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setContentsMargins(0, 4, 4, 4)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch(1)
        self.scroll.setWidget(self.scroll_content)

        root.addWidget(self.scroll, 1)

        # Footer with status
        self.lbl_status = QLabel("0 overlays recorded")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 8.5pt;")
        root.addWidget(self.lbl_status)

        self._item_widgets = []

    def focus_input(self):
        """Focus the input text box and select all for rapid new overlay creation."""
        self.input_box.setFocus()
        self.input_box.selectAll()

    def _on_add_submitted(self):
        text = self.input_box.text().strip()
        source = text if text else None
        self.input_box.clear()
        self.spawn_requested.emit(source, None, None, None)

    def _on_browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select file to overlay", "", FILE_FILTER)
        if path:
            self.spawn_requested.emit(path, None, None, None)

    def refresh(self, active_windows):
        """Rebuild list showing ALL overlays (active + inactive/saved in past)."""
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
            card = OverlayListItem(rec, live_overlay=live_win, parent=self.scroll_content)
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
            )
        oid = record.get("id")
        name = record.get("name")
        self.spawn_requested.emit(src, look, oid, name)

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
