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


if HAVE_WEB:
    class LucentWebPage(QWebEnginePage):
        """Custom QWebEnginePage that keeps navigations in the same overlay and auto-approves permissions."""

        def __init__(self, profile=None, parent=None):
            if profile:
                super().__init__(profile, parent)
            else:
                super().__init__(parent)
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
            # Target="_blank" / window.open: force open in the same window
            url = request.requestedUrl()
            if url.isValid() and not url.isEmpty():
                self.setUrl(url)

        def createWindow(self, win_type: QWebEnginePage.WebWindowType) -> QWebEnginePage:
            # Force opening popups and new tabs directly in the same Lucent overlay viewer
            return self


class WebViewer(Viewer):
    _shared_profile = None
    title_changed = Signal(str)
    source_changed = Signal(str)

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
