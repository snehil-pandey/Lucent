"""Windows Sticky Notes-style Hub / Manager Window.
Lists all active overlay instances with live status, source, and hover action controls.
"""
from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter, QPainterPath
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .icon import app_icon, draw_moon
from .titlebar import GLYPH


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

        self.btn_front = self._make_btn("👁", "Bring to Front")
        self.btn_ghost = self._make_btn(GLYPH["click_through"], "Toggle Click-Through / Ghost Mode")
        self.btn_collapse = self._make_btn(GLYPH["collapse"], "Toggle Collapse / Shade")
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
        if len(src) > 36:
            return src[:18] + "..." + src[-15:]
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
        super().leaveEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.bring_front_requested.emit(self.overlay)
            e.accept()
            return
        super().mouseDoubleClickEvent(e)


class HubWindow(QWidget):
    """Sticky Notes-style Manager Hub window listing all overlay instances."""

    spawn_requested = Signal()
    bring_front_requested = Signal(object)
    toggle_collapse_requested = Signal(object)
    toggle_click_through_requested = Signal(object)
    close_overlay_requested = Signal(object)

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setObjectName("HubWindow")
        self.setWindowTitle("Lucent Hub — All Overlays")
        self.setWindowIcon(app_icon())
        self.resize(380, 520)
        self.setMinimumSize(320, 360)

        # Style with dark translucent look matching Lucent
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
            QPushButton#NewBtn {{
                background: #3b82f6;
                color: white;
                font-weight: 600;
                font-size: 9.5pt;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton#NewBtn:hover {{
                background: #2563eb;
            }}
            QLineEdit#SearchBox {{
                background: rgba(255, 255, 255, 0.06);
                color: #f1f5f9;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 9pt;
            }}
            QLineEdit#SearchBox:focus {{
                border-color: #3b82f6;
                background: rgba(255, 255, 255, 0.10);
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        # Header bar: Logo + Title + New Button
        header = QHBoxLayout()
        header.setSpacing(10)

        lbl_logo = QLabel()
        lbl_logo.setPixmap(app_icon().pixmap(24, 24))
        header.addWidget(lbl_logo)

        lbl_header = QLabel("Lucent Overlays")
        lbl_header.setStyleSheet("font-size: 13pt; font-weight: 700; color: #f8fafc;")
        header.addWidget(lbl_header, 1)

        btn_new = QPushButton("+ New Note", self)
        btn_new.setObjectName("NewBtn")
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.clicked.connect(self.spawn_requested.emit)
        header.addWidget(btn_new)

        root.addLayout(header)

        # Search / filter box
        self.search_box = QLineEdit(self)
        self.search_box.setObjectName("SearchBox")
        self.search_box.setPlaceholderText("Filter overlays by title or URL...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self._filter_items)
        root.addWidget(self.search_box)

        # Scroll area containing cards
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
        self.lbl_status = QLabel("0 overlays open")
        self.lbl_status.setStyleSheet("color: #64748b; font-size: 8.5pt;")
        root.addWidget(self.lbl_status)

        self._item_widgets = []

    def refresh(self, windows):
        """Rebuild the cards list based on current active overlay windows."""
        # Clear existing items
        for item in self._item_widgets:
            self.cards_layout.removeWidget(item)
            item.deleteLater()
        self._item_widgets.clear()

        # Create card for each window
        for win in windows:
            card = OverlayListItem(win, self.scroll_content)
            card.bring_front_requested.connect(self.bring_front_requested.emit)
            card.toggle_collapse_requested.connect(self.toggle_collapse_requested.emit)
            card.toggle_click_through_requested.connect(self.toggle_click_through_requested.emit)
            card.open_settings_requested.connect(self._open_overlay_settings)
            card.close_requested.connect(self.close_overlay_requested.emit)
            # Insert before the stretch
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
            self._item_widgets.append(card)

        count = len(windows)
        self.lbl_status.setText(f"{count} {'overlay' if count == 1 else 'overlays'} open")
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
