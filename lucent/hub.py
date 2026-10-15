"""Lucent Main App Window.
Lists all active overlay instances with action controls on hover,
and provides a dedicated input bar to add new overlays from a URL, local file, or clipboard.
"""
from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .icon import app_icon, draw_moon
from .titlebar import GLYPH
from .viewers import FILE_FILTER


class OverlayListItem(QFrame):
    """Card representing an active overlay instance with action controls visible on hover."""

    bring_front_requested = Signal(object)
    toggle_collapse_requested = Signal(object)
    toggle_click_through_requested = Signal(object)
    open_settings_requested = Signal(object, object)  # overlay, anchor_widget
    close_requested = Signal(object)

    def __init__(self, overlay, parent=None):
        super().__init__(parent)
        self.overlay = overlay
        self.setAttribute(Qt.WA_Hover, True)
        self.setObjectName("OverlayListItem")
        self.setFixedHeight(64)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(10)

        # Badge / Index icon
        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(36, 36)
        self._update_icon()
        lay.addWidget(self.lbl_icon)

        # Title & source text
        info_lay = QVBoxLayout()
        info_lay.setSpacing(2)
        info_lay.setContentsMargins(0, 2, 0, 2)

        self.lbl_title = QLabel(f"Overlay #{overlay.index}")
        self.lbl_title.setObjectName("ItemTitle")
        self.lbl_title.setStyleSheet("font-weight: 600; font-size: 10pt; color: #f8fafc;")

        self.lbl_sub = QLabel(self._get_subtitle())
        self.lbl_sub.setObjectName("ItemSubtitle")
        self.lbl_sub.setStyleSheet("font-size: 8.5pt; color: #94a3b8;")

        info_lay.addWidget(self.lbl_title)
        info_lay.addWidget(self.lbl_sub)
        lay.addLayout(info_lay, 1)

        # Hover action buttons
        self.actions_widget = QWidget(self)
        actions_lay = QHBoxLayout(self.actions_widget)
        actions_lay.setContentsMargins(0, 0, 0, 0)
        actions_lay.setSpacing(4)

        self.btn_front = self._make_btn("👁", "Bring Overlay to Front")
        self.btn_ghost = self._make_btn(GLYPH["click_through"], "Toggle Click-Through / Ghost Mode")
        self.btn_collapse = self._make_btn(GLYPH["collapse"], "Toggle Collapse / Expand")
        self.btn_settings = self._make_btn(GLYPH["settings"], "Overlay Settings")
        self.btn_close = self._make_btn(GLYPH["close"], "Close Overlay", is_close=True)

        self.btn_front.clicked.connect(lambda: self.bring_front_requested.emit(self.overlay))
        self.btn_ghost.clicked.connect(lambda: self.toggle_click_through_requested.emit(self.overlay))
        self.btn_collapse.clicked.connect(lambda: self.toggle_collapse_requested.emit(self.overlay))
        self.btn_settings.clicked.connect(lambda: self.open_settings_requested.emit(self.overlay, self.btn_settings))
        self.btn_close.clicked.connect(lambda: self.close_requested.emit(self.overlay))

        actions_lay.addWidget(self.btn_front)
        actions_lay.addWidget(self.btn_ghost)
        actions_lay.addWidget(self.btn_collapse)
        actions_lay.addWidget(self.btn_settings)
        actions_lay.addWidget(self.btn_close)

        lay.addWidget(self.actions_widget)

        # Actions are hidden by default, shown on hover
        self.actions_widget.setVisible(False)
        self.update_state()

    def _get_subtitle(self):
        src = getattr(self.overlay, "current_source", None)
        if not src:
            return "Empty canvas"
        if len(src) > 38:
            return src[:19] + "..." + src[-16:]
        return src

    def _make_btn(self, glyph, tip, is_close=False):
        btn = QToolButton(self)
        btn.setText(glyph)
        btn.setToolTip(tip)
        btn.setFixedSize(28, 28)
        btn.setCursor(Qt.PointingHandCursor)
        if is_close:
            btn.setObjectName("ItemBtnClose")
        else:
            btn.setObjectName("ItemBtn")
        return btn

    def _update_icon(self):
        from PySide6.QtGui import QPixmap
        pm = QPixmap(36, 36)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)

        acc = theme.accent(self.overlay.look.hue)
        bg = theme.background(self.overlay.look.hue)
        p.setBrush(bg)
        p.setPen(acc)
        p.drawRoundedRect(QRect(1, 1, 34, 34), 8, 8)

        # Draw mini moon
        draw_moon(p, QRect(5, 5, 24, 24), glow=0.1, opacity=0.9)

        # Overlay number
        p.setPen(Qt.white)
        font = QFont("Segoe UI", 7)
        font.setBold(True)
        p.setFont(font)
        p.drawText(QRect(0, 18, 36, 16), Qt.AlignCenter, f"#{self.overlay.index}")
        p.end()
        self.lbl_icon.setPixmap(pm)

    def update_state(self):
        self.lbl_title.setText(f"Overlay #{self.overlay.index}")
        self.lbl_sub.setText(self._get_subtitle())
        self._update_icon()

        # Update ghost button color
        is_ghost = getattr(self.overlay.look, "click_through", False)
        self.btn_ghost.setStyleSheet("color: #4ade80;" if is_ghost else "")

        # Update collapse button icon
        is_collapsed = getattr(self.overlay, "_collapsed", False)
        self.btn_collapse.setText(GLYPH["expand"] if is_collapsed else GLYPH["collapse"])

    def enterEvent(self, e):
        self.actions_widget.setVisible(True)
        self.setStyleSheet("""
            QFrame#OverlayListItem {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.18);
                border-radius: 8px;
            }
        """)
        if e:
            super().enterEvent(e)

    def leaveEvent(self, e):
        self.actions_widget.setVisible(False)
        self.setStyleSheet("""
            QFrame#OverlayListItem {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
        """)
        if e:
            super().leaveEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.bring_front_requested.emit(self.overlay)
            e.accept()
            return
        super().mouseDoubleClickEvent(e)


class HubWindow(QWidget):
    """Main App Window: Lists all active overlays, with a focused input box to create new overlays."""

    spawn_requested = Signal(object)  # source url/path or None
    bring_front_requested = Signal(object)
    toggle_collapse_requested = Signal(object)
    toggle_click_through_requested = Signal(object)
    close_overlay_requested = Signal(object)

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setObjectName("HubWindow")
        self.setWindowTitle("Lucent — Overlays")
        self.setWindowIcon(app_icon())
        self.resize(420, 560)
        self.setMinimumSize(360, 400)

        # Style with clean dark look matching Lucent theme
        self.setStyleSheet(f"""
            QWidget#HubWindow {{
                background: #11141a;
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
                padding: 7px 14px;
            }}
            QPushButton#ActionBtn:hover {{
                background: #2563eb;
            }}
            QToolButton#FileBtn {{
                background: rgba(255, 255, 255, 0.08);
                color: #f1f5f9;
                font-size: 10pt;
                border: 1px solid rgba(255, 255, 255, 0.14);
                border-radius: 6px;
                padding: 6px 10px;
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
                background: rgba(255, 255, 255, 0.12);
            }}
            QLineEdit#SearchBox {{
                background: rgba(255, 255, 255, 0.05);
                color: #e2e8f0;
                border: 1px solid rgba(255, 255, 255, 0.10);
                border-radius: 6px;
                padding: 5px 10px;
                font-size: 8.5pt;
            }}
            QLineEdit#SearchBox:focus {{
                border: 1px solid #3b82f6;
                background: rgba(255, 255, 255, 0.08);
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Header bar: Logo + App Title
        header = QHBoxLayout()
        header.setSpacing(10)

        lbl_logo = QLabel()
        lbl_logo.setPixmap(app_icon().pixmap(24, 24))
        header.addWidget(lbl_logo)

        lbl_header = QLabel("Lucent Overlays")
        lbl_header.setStyleSheet("font-size: 13pt; font-weight: 700; color: #f8fafc;")
        header.addWidget(lbl_header, 1)

        root.addLayout(header)

        # Main Input Box Area: Focused text box for URL / path / clipboard + File picker button + Add button
        input_container = QFrame(self)
        input_container.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 8px;
                padding: 8px;
            }
        """)
        input_box_lay = QVBoxLayout(input_container)
        input_box_lay.setContentsMargins(4, 4, 4, 4)
        input_box_lay.setSpacing(8)

        lbl_input_prompt = QLabel("Add New Overlay:")
        lbl_input_prompt.setStyleSheet("font-weight: 600; font-size: 9pt; color: #94a3b8;")
        input_box_lay.addWidget(lbl_input_prompt)

        row_lay = QHBoxLayout()
        row_lay.setSpacing(6)

        self.input_box = QLineEdit(input_container)
        self.input_box.setObjectName("UrlInputBox")
        self.input_box.setPlaceholderText("Paste URL, local path, or press Enter for empty overlay")
        self.input_box.setClearButtonEnabled(True)
        self.input_box.returnPressed.connect(self._on_add_submitted)
        row_lay.addWidget(self.input_box, 1)

        btn_browse = QToolButton(input_container)
        btn_browse.setObjectName("FileBtn")
        btn_browse.setText("📁 Browse")
        btn_browse.setToolTip("Browse local file (PDF, Image, Markdown, Text)")
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

        # Filter / Search bar for active overlays
        self.search_box = QLineEdit(self)
        self.search_box.setObjectName("SearchBox")
        self.search_box.setPlaceholderText("Filter active overlays...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self._filter_items)
        root.addWidget(self.search_box)

        # Scroll area containing active overlay cards
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
        self.lbl_status = QLabel("0 overlays active")
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
        self.spawn_requested.emit(source)

    def _on_browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select file to overlay", "", FILE_FILTER)
        if path:
            self.spawn_requested.emit(path)

    def refresh(self, windows):
        """Rebuild the cards list based on current active overlay windows."""
        for item in self._item_widgets:
            self.cards_layout.removeWidget(item)
            item.deleteLater()
        self._item_widgets.clear()

        for win in windows:
            card = OverlayListItem(win, self.scroll_content)
            card.bring_front_requested.connect(self.bring_front_requested.emit)
            card.toggle_collapse_requested.connect(self.toggle_collapse_requested.emit)
            card.toggle_click_through_requested.connect(self.toggle_click_through_requested.emit)
            card.open_settings_requested.connect(self._open_overlay_settings)
            card.close_requested.connect(self.close_overlay_requested.emit)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
            self._item_widgets.append(card)

        count = len(windows)
        self.lbl_status.setText(f"{count} {'overlay' if count == 1 else 'overlays'} active")
        self._filter_items(self.search_box.text())

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
            item.setVisible(q in title or q in sub)
