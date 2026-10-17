"""Video and media viewer for Lucent supporting MP4, WebM, MKV, AVI, MOV, and MP3/WAV."""
import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from .. import theme
from .base import Viewer

try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    from PySide6.QtMultimediaWidgets import QVideoWidget
    HAVE_MEDIA = True
except ImportError:  # pragma: no cover
    HAVE_MEDIA = False

VIDEO_EXTS = {
    ".mp4", ".m4v", ".webm", ".mkv", ".avi", ".mov", ".wmv", ".flv",
    ".ts", ".ogv", ".3gp", ".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"
}


class VideoViewer(Viewer):
    """Clean transparent video & media player with playback controls and auto-hiding bar."""

    @classmethod
    def accepts(cls, source: str) -> bool:
        if not HAVE_MEDIA:
            return False
        if not source or not isinstance(source, str):
            return False
        _, ext = os.path.splitext(source.lower())
        return ext in VIDEO_EXTS or (os.path.isfile(source) and ext in VIDEO_EXTS)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source = ""
        self._duration = 0
        self._is_slider_down = False
        self._hue = 215

        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)

        self.video_widget = QVideoWidget(self)
        self.player.setVideoOutput(self.video_widget)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        root_lay = QVBoxLayout(self)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        root_lay.addWidget(self.video_widget, 1)

        # Bottom media control bar
        self.controls = QWidget(self)
        self.controls.setObjectName("MediaControls")
        c_lay = QHBoxLayout(self.controls)
        c_lay.setContentsMargins(12, 6, 12, 6)
        c_lay.setSpacing(8)

        self.btn_play = QPushButton(self.controls)
        self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.btn_play.setFixedSize(30, 26)
        self.btn_play.setCursor(Qt.PointingHandCursor)

        self.lbl_time = QLabel("00:00 / 00:00", self.controls)
        self.lbl_time.setObjectName("MediaTime")

        self.slider = QSlider(Qt.Horizontal, self.controls)
        self.slider.setRange(0, 0)
        self.slider.setCursor(Qt.PointingHandCursor)

        # Volume button / mute toggle
        self.btn_mute = QPushButton(self.controls)
        self.btn_mute.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))
        self.btn_mute.setFixedSize(30, 26)
        self.btn_mute.setCursor(Qt.PointingHandCursor)

        self.vol_slider = QSlider(Qt.Horizontal, self.controls)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(70)
        self.audio.setVolume(0.8)

        c_lay.addWidget(self.btn_play)
        c_lay.addWidget(self.lbl_time)
        c_lay.addWidget(self.slider, 1)
        c_lay.addWidget(self.btn_mute)
        c_lay.addWidget(self.vol_slider)

        root_lay.addWidget(self.controls)
        self.apply_theme(self._hue)

    def _connect_signals(self):
        self.btn_play.clicked.connect(self._toggle_playback)
        self.btn_mute.clicked.connect(self._toggle_mute)
        self.slider.sliderPressed.connect(self._on_slider_pressed)
        self.slider.sliderMoved.connect(self._on_slider_moved)
        self.slider.sliderReleased.connect(self._on_slider_released)
        self.vol_slider.valueChanged.connect(self._on_volume_changed)

        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)

    def _format_time(self, ms: int) -> str:
        s = max(0, ms // 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _toggle_mute(self):
        muted = not self.audio.isMuted()
        self.audio.setMuted(muted)
        icon = QStyle.SP_MediaVolumeMuted if muted else QStyle.SP_MediaVolume
        self.btn_mute.setIcon(self.style().standardIcon(icon))

    def _on_volume_changed(self, val: int):
        self.audio.setVolume(val / 100.0)
        if self.audio.isMuted() and val > 0:
            self.audio.setMuted(False)
            self.btn_mute.setIcon(self.style().standardIcon(QStyle.SP_MediaVolume))

    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlayingState:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.btn_play.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def _on_position_changed(self, pos: int):
        if not self._is_slider_down:
            self.slider.setValue(pos)
        cur = self._format_time(pos)
        dur = self._format_time(self._duration)
        self.lbl_time.setText(f"{cur} / {dur}")

    def _on_duration_changed(self, dur: int):
        self._duration = dur
        self.slider.setRange(0, dur)
        cur = self._format_time(self.player.position())
        tot = self._format_time(dur)
        self.lbl_time.setText(f"{cur} / {tot}")

    def _on_slider_pressed(self):
        self._is_slider_down = True

    def _on_slider_moved(self, pos: int):
        cur = self._format_time(pos)
        dur = self._format_time(self._duration)
        self.lbl_time.setText(f"{cur} / {dur}")

    def _on_slider_released(self):
        self._is_slider_down = False
        self.player.setPosition(self.slider.value())

    def load(self, source: str) -> None:
        self._source = source
        url = QUrl.fromLocalFile(source) if os.path.isfile(source) else QUrl(source)
        self.player.setSource(url)
        self.player.play()
        base_name = os.path.basename(source) if os.path.isfile(source) else str(source)
        self.title_changed.emit(base_name)
        self.source_changed.emit(source)

    def apply_theme(self, hue: int) -> None:
        self._hue = hue
        acc = theme.accent(hue).name()
        bg = theme.background(hue)
        bg.setAlpha(235)
        bg_col = bg.name(QColor.NameFormat.HexArgb)
        fg_col = theme.TEXT
        self.controls.setStyleSheet(f"""
            QWidget#MediaControls {{
                background-color: {bg_col};
                border-top: 1px solid {theme.fg(0.12)};
            }}
            QLabel#MediaTime {{
                color: {theme.TEXT_MUTED};
                font-family: {theme.FONT_UI};
                font-size: 8.5pt;
            }}
            QPushButton {{
                background: {theme.fg(0.08)};
                border: 1px solid {theme.fg(0.15)};
                border-radius: 4px;
                color: {fg_col};
            }}
            QPushButton:hover {{
                background: {theme.fg(0.18)};
                border-color: {acc};
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: {theme.fg(0.15)};
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {acc};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {acc};
                width: 12px;
                margin-top: -4px;
                margin-bottom: -4px;
                border-radius: 6px;
            }}
        """)

    def reload(self) -> None:
        if self._source:
            self.load(self._source)

    def go_back(self) -> None:
        # Seek back 5 seconds
        self.player.setPosition(max(0, self.player.position() - 5000))

    def go_forward(self) -> None:
        # Seek forward 5 seconds
        self.player.setPosition(min(self._duration, self.player.position() + 5000))
