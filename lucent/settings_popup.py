"""Flyout with the opacity / hue sliders, window options, and icon customizer."""
import sys

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFrame,
                               QHBoxLayout, QLabel, QPushButton, QSlider,
                               QToolButton, QVBoxLayout)

from . import theme, winapi
from .icon import ICON_PRESETS, render_overlay_pixmap

_HUE_GRADIENT = ", ".join(
    f"stop:{i / 6:.3f} hsv({min(i * 60, 359)},170,235)" for i in range(7)
)


class SettingsPopup(QFrame):
    opacity_changed = Signal(float)
    hue_changed = Signal(int)
    on_top_changed = Signal(bool)
    capture_changed = Signal(bool)
    click_through_changed = Signal(bool)
    icon_changed = Signal(str, object)  # icon_name, icon_file
    new_overlay = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("SettingsPopup")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(290)
        self._hide_capture = True
        self._current_icon_name = "moon"
        self._current_icon_file = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        head = QLabel("Overlay Settings")
        head.setObjectName("head")
        lay.addWidget(head)

        self._op_val = QLabel()
        self.opacity = QSlider(Qt.Horizontal)
        self.opacity.setRange(25, 100)
        lay.addLayout(self._row("Transparency", self._op_val))
        lay.addWidget(self.opacity)

        self._hue_val = QLabel()
        self.hue = QSlider(Qt.Horizontal)
        self.hue.setObjectName("hue")
        self.hue.setRange(0, 359)
        lay.addLayout(self._row("Hue", self._hue_val))
        lay.addWidget(self.hue)

        # Icon customizer row
        icon_row = QHBoxLayout()
        icon_row.addWidget(QLabel("Icon"))
        icon_row.addStretch(1)

        self.cmb_icon = QComboBox(self)
        self.cmb_icon.setObjectName("IconSelect")
        for preset in ICON_PRESETS:
            self.cmb_icon.addItem(preset.capitalize(), preset)
        self.cmb_icon.currentIndexChanged.connect(self._on_preset_selected)
        icon_row.addWidget(self.cmb_icon)

        self.btn_custom_icon = QToolButton(self)
        self.btn_custom_icon.setText("Custom…")
        self.btn_custom_icon.setToolTip("Pick a custom PNG/ICO file for this overlay")
        self.btn_custom_icon.clicked.connect(self._pick_custom_icon_file)
        icon_row.addWidget(self.btn_custom_icon)

        lay.addLayout(icon_row)

        self.chk_top = QCheckBox("Always on top")
        self.chk_click = QCheckBox("Click-through (Ghost mode)  [Ctrl+M]")
        self.chk_capture = QCheckBox("Hide from screen recording")
        if not winapi.WIN:
            self.chk_capture.setEnabled(False)
            self.chk_capture.setToolTip("Only available on Windows")
            self.chk_click.setEnabled(False)
            self.chk_click.setToolTip("Only available on Windows")
        lay.addSpacing(4)
        lay.addWidget(self.chk_top)
        lay.addWidget(self.chk_click)
        lay.addWidget(self.chk_capture)

        # Cache & Storage Location section
        from .config import get_storage_locations
        locs = get_storage_locations()
        cache_path = locs.get("cache", "")

        self.lbl_cache = QLabel(f"Cache: {cache_path}")
        self.lbl_cache.setObjectName("CacheLabel")
        self.lbl_cache.setToolTip(f"App Cache Location:\n{cache_path}\n(Click to copy path)")
        self.lbl_cache.setCursor(Qt.PointingHandCursor)
        self.lbl_cache.mousePressEvent = lambda e: QGuiApplication.clipboard().setText(cache_path)
        lay.addSpacing(2)
        lay.addWidget(self.lbl_cache)

        btn = QPushButton("New overlay")
        btn.clicked.connect(self.new_overlay)
        btn.clicked.connect(self.close)
        lay.addSpacing(4)
        lay.addWidget(btn)

        self.opacity.valueChanged.connect(self._on_opacity)
        self.hue.valueChanged.connect(self._on_hue)
        self.chk_top.toggled.connect(self.on_top_changed)
        self.chk_click.toggled.connect(self.click_through_changed)
        self.chk_capture.toggled.connect(self.capture_changed)

    def _on_preset_selected(self, index):
        name = self.cmb_icon.currentData()
        self._current_icon_name = name
        self._current_icon_file = None
        self.icon_changed.emit(name, None)

    def _pick_custom_icon_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Icon File", "", "Images (*.png *.ico *.svg *.jpg *.bmp);;All files (*)"
        )
        if path:
            self._current_icon_file = path
            self.icon_changed.emit(self._current_icon_name, path)

    @staticmethod
    def _row(name, value_label):
        row = QHBoxLayout()
        row.addWidget(QLabel(name))
        row.addStretch(1)
        value_label.setObjectName("value")
        row.addWidget(value_label)
        return row

    def _on_opacity(self, v):
        self._op_val.setText(f"{100 - v}%")   # shown as how see-through it is
        self.opacity_changed.emit(v / 100.0)

    def _on_hue(self, v):
        self._hue_val.setText(f"{v}°")
        self.hue_changed.emit(v)

    def sync(self, look):
        for w in (self.opacity, self.hue, self.chk_top, self.chk_click, self.chk_capture, self.cmb_icon):
            w.blockSignals(True)
        self.opacity.setValue(round(look.opacity * 100))
        self.hue.setValue(look.hue)
        self.chk_top.setChecked(look.on_top)
        self.chk_click.setChecked(look.click_through)
        self.chk_capture.setChecked(look.hide_from_capture)

        idx = self.cmb_icon.findData(look.icon_name)
        if idx >= 0:
            self.cmb_icon.setCurrentIndex(idx)
        self._current_icon_name = look.icon_name
        self._current_icon_file = look.icon_file

        for w in (self.opacity, self.hue, self.chk_top, self.chk_click, self.chk_capture, self.cmb_icon):
            w.blockSignals(False)
        self._op_val.setText(f"{100 - self.opacity.value()}%")
        self._hue_val.setText(f"{self.hue.value()}°")

    def set_capture_hidden(self, hidden: bool):
        self._hide_capture = hidden

    def apply_theme(self, hue: int):
        acc = theme.accent(hue).name()
        bg = theme.background(hue).lighter(115).name()
        self.setStyleSheet(f"""
            QFrame#SettingsPopup, SettingsPopup {{
                background: {bg};
                border: 1px solid {acc};
                border-radius: 4px;
            }}
            QLabel {{ color: {theme.TEXT}; font: 9.5pt "Segoe UI"; }}
            QLabel#head {{ font: 600 11pt "Segoe UI"; }}
            QLabel#value {{ color: rgba(230,238,252,150); }}
            QLabel#CacheLabel {{
                color: rgba(230,238,252,140);
                font-size: 7.5pt;
                padding: 4px 6px;
                background: rgba(255,255,255,0.05);
                border-radius: 4px;
            }}
            QLabel#CacheLabel:hover {{
                color: {theme.TEXT};
                background: rgba(255,255,255,0.10);
            }}
            QCheckBox {{ color: {theme.TEXT}; font: 9.5pt "Segoe UI"; spacing: 8px; }}
            QSlider::groove:horizontal {{ height: 6px; border-radius: 3px; background: rgba(255,255,255,0.18); }}
            QSlider::sub-page:horizontal {{ background: {acc}; border-radius: 3px; }}
            QSlider#hue::groove:horizontal {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, {_HUE_GRADIENT}); }}
            QSlider#hue::sub-page:horizontal {{ background: transparent; }}
            QSlider::handle:horizontal {{ background: white; width: 14px; height: 14px;
                margin: -5px 0; border-radius: 7px; }}
            QComboBox#IconSelect {{
                background: rgba(255,255,255,0.10);
                color: {theme.TEXT};
                border: 1px solid rgba(255,255,255,0.18);
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 9pt;
            }}
            QComboBox#IconSelect QAbstractItemView {{
                background: {bg};
                color: {theme.TEXT};
                selection-background-color: {acc};
                border: 1px solid {acc};
            }}
            QToolButton {{
                background: rgba(255,255,255,0.10);
                color: {theme.TEXT};
                border: 1px solid rgba(255,255,255,0.15);
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 8.5pt;
            }}
            QToolButton:hover {{
                background: rgba(255,255,255,0.18);
            }}
            QPushButton {{ background: rgba(255,255,255,0.10); color: {theme.TEXT};
                border: 1px solid rgba(255,255,255,0.15); border-radius: 4px; padding: 6px; }}
            QPushButton:hover {{ background: rgba(255,255,255,0.18); }}
        """)

    def show_below(self, button):
        self.adjustSize()
        pos = button.mapToGlobal(QPoint(button.width() - self.width(), button.height() + 4))
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        pos.setX(max(geo.left(), min(pos.x(), geo.right() - self.width())))
        pos.setY(max(geo.top(), min(pos.y(), geo.bottom() - self.height())))
        self.move(pos)
        self.show()

    def showEvent(self, e):
        super().showEvent(e)
        winapi.set_capture_hidden(self, self._hide_capture)
