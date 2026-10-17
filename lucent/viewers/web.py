import os

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QVBoxLayout

from ..sources import is_url
from .base import Viewer

try:
    from PySide6.QtWebEngineCore import (
        QWebEngineCertificateError,
        QWebEnginePage,
        QWebEngineProfile,
        QWebEngineSettings,
    )
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAVE_WEB = True
except ImportError:  # pragma: no cover
    HAVE_WEB = False

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from .. import theme


if HAVE_WEB:
    class PopupConfirmDialog(QDialog):
        """Clean modal dialog asking user how to handle a new window / popup request."""

        def __init__(self, url_str: str, parent=None, hue: float = 0.58):
            super().__init__(parent)
            self.setWindowTitle("Open Link Confirmation")
            self.setMinimumWidth(380)
            self.choice = "cancel"

            # Style with Lucent theme
            acc = theme.accent(hue).name()
            bg = theme.background(hue).name()
            self.setStyleSheet(f"""
                QDialog {{
                    background: {bg};
                    color: {theme.TEXT};
                    border: 1px solid {acc};
                    border-radius: 8px;
                }}
                QLabel {{
                    color: {theme.TEXT};
                    font-family: {theme.FONT_UI};
                }}
                QPushButton {{
                    background: rgba(255, 255, 255, 0.08);
                    color: {theme.TEXT};
                    border: 1px solid rgba(255, 255, 255, 0.16);
                    border-radius: 5px;
                    padding: 6px 14px;
                    font-family: {theme.FONT_UI};
                    font-size: 11px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 0.16);
                    border-color: {acc};
                }}
                QPushButton#primary {{
                    background: {acc};
                    color: #ffffff;
                    border: none;
                    font-weight: 600;
                }}
                QPushButton#primary:hover {{
                    background: {acc};
                    opacity: 0.9;
                }}
            """)

            vbox = QVBoxLayout(self)
            vbox.setContentsMargins(18, 16, 18, 16)
            vbox.setSpacing(12)

            title_lbl = QLabel("<b>A web page requested to open a new window:</b>")
            title_lbl.setWordWrap(True)
            vbox.addWidget(title_lbl)

            url_lbl = QLabel(url_str)
            url_lbl.setWordWrap(True)
            url_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px; padding: 4px; background: rgba(0,0,0,0.25); border-radius: 4px;")
            vbox.addWidget(url_lbl)

            prompt_lbl = QLabel("Where would you like to open this link?")
            vbox.addWidget(prompt_lbl)

            btn_box = QHBoxLayout()
            btn_box.setSpacing(8)

            btn_same = QPushButton("Current Overlay")
            btn_same.clicked.connect(self._choose_same)

            btn_new = QPushButton("New Overlay")
            btn_new.setObjectName("primary")
            btn_new.clicked.connect(self._choose_new)

            btn_cancel = QPushButton("Block / Cancel")
            btn_cancel.clicked.connect(self._choose_cancel)

            btn_box.addWidget(btn_same)
            btn_box.addWidget(btn_new)
            btn_box.addWidget(btn_cancel)
            vbox.addLayout(btn_box)

        def _choose_same(self):
            self.choice = "same"
            self.accept()

        def _choose_new(self):
            self.choice = "new"
            self.accept()

        def _choose_cancel(self):
            self.choice = "cancel"
            self.reject()


    class LucentWebPage(QWebEnginePage):
        """Custom QWebEnginePage that handles popup confirmations and auto-approves permissions."""

        def __init__(self, profile=None, parent=None):
            if profile:
                super().__init__(profile, parent)
            else:
                super().__init__(parent)
            self._viewer = parent
            self.certificateError.connect(self._on_certificate_error)
            self.featurePermissionRequested.connect(self._on_feature_permission_requested)
            self.newWindowRequested.connect(self._on_new_window_requested)

        def _on_certificate_error(self, error: QWebEngineCertificateError):
            # Allow navigation past self-signed or local certificates
            error.acceptCertificate()

        def _on_feature_permission_requested(self, security_origin, feature):
            # Auto-grant clipboard, media, notifications, and other requested web capabilities
            self.setFeaturePermission(
                security_origin,
                feature,
                QWebEnginePage.PermissionPolicy.PermissionGrantedByUser,
            )

        def _on_new_window_requested(self, request):
            url = request.requestedUrl()
            if not url.isValid() or url.isEmpty():
                return

            url_str = url.toString()
            parent_widget = self._viewer if isinstance(self._viewer, WebViewer) else None
            hue = parent_widget._hue if parent_widget and hasattr(parent_widget, "_hue") else 0.58

            dlg = PopupConfirmDialog(url_str, parent=parent_widget, hue=hue)
            dlg.exec()

            if dlg.choice == "same":
                self.setUrl(url)
            elif dlg.choice == "new":
                if parent_widget and hasattr(parent_widget, "new_window_requested"):
                    parent_widget.new_window_requested.emit(url_str)
            # choice == "cancel" blocks opening

        def createWindow(self, win_type: QWebEnginePage.WebWindowType) -> QWebEnginePage:
            # Route window creation back to current page; newWindowRequested handler manages action
            return self


class WebViewer(Viewer):
    _shared_profile = None
    title_changed = Signal(str)
    source_changed = Signal(str)
    new_window_requested = Signal(str)

    @classmethod
    def accepts(cls, source):
        if not HAVE_WEB:
            return False
        if is_url(source):
            return True
        return os.path.isfile(source) and source.lower().endswith((".html", ".htm", ".xhtml"))

    @classmethod
    def get_shared_profile(cls):
        if cls._shared_profile is None and HAVE_WEB:
            # Persistent profile in user cache / AppData directory so logins & cookies persist
            from ..config import get_cache_location
            cache_base = get_cache_location()
            profile_dir = os.path.join(cache_base, "web_profile")
            os.makedirs(profile_dir, exist_ok=True)
            cls._shared_profile = QWebEngineProfile("LucentProfile", None)
            cls._shared_profile.setPersistentStoragePath(profile_dir)
            cls._shared_profile.setCachePath(profile_dir)
            cls._shared_profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)

            # Standardize user agent (remove QtWebEngine token that triggers unsupported browser blocks)
            default_ua = cls._shared_profile.httpUserAgent()
            cleaned_ua = " ".join(part for part in default_ua.split() if not part.startswith("QtWebEngine/"))
            cls._shared_profile.setHttpUserAgent(cleaned_ua)

            # Configure full functional web capabilities and compatibility settings
            s = cls._shared_profile.settings()
            attrs = [
                QWebEngineSettings.WebAttribute.JavascriptEnabled,
                QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
                QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard,
                QWebEngineSettings.WebAttribute.JavascriptCanPaste,
                QWebEngineSettings.WebAttribute.LocalStorageEnabled,
                QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
                QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
                QWebEngineSettings.WebAttribute.AllowRunningInsecureContent,
                QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,
                QWebEngineSettings.WebAttribute.WebGLEnabled,
                QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled,
                QWebEngineSettings.WebAttribute.AutoLoadImages,
                QWebEngineSettings.WebAttribute.AutoLoadIconsForPage,
                QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled,
                QWebEngineSettings.WebAttribute.ErrorPageEnabled,
                QWebEngineSettings.WebAttribute.PluginsEnabled,
                QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript,
            ]
            for attr in attrs:
                s.setAttribute(attr, True)

        return cls._shared_profile

    def __init__(self, parent=None):
        super().__init__(parent)
        profile = self.get_shared_profile()
        page = LucentWebPage(profile, self) if profile else LucentWebPage(None, self)
        self._web = QWebEngineView(self)
        self._web.setPage(page)
        self._web.page().setBackgroundColor(QColor(0, 0, 0, 0))
        self._web.titleChanged.connect(self.title_changed)
        self._web.urlChanged.connect(self._on_url_changed)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self._web)

    def _on_url_changed(self, url):
        u_str = url.toString() if hasattr(url, "toString") else str(url)
        self.source_changed.emit(u_str)

    def load(self, source):
        url = QUrl.fromLocalFile(source) if os.path.isfile(source) else QUrl(source)
        self._web.load(url)
        self.source_changed.emit(url.toString())

    def go_back(self):
        self._web.back()

    def go_forward(self):
        self._web.forward()

    def reload(self):
        self._web.reload()

    def apply_theme(self, hue: float):
        self._hue = hue
