import os

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QVBoxLayout

from ..sources import is_url
from .base import Viewer

try:
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAVE_WEB = True
except ImportError:  # pragma: no cover
    HAVE_WEB = False


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
            # Persistent profile in user AppData / home directory so logins & cookies persist
            profile_dir = os.path.join(os.path.expanduser("~"), ".lucent_web_profile")
            os.makedirs(profile_dir, exist_ok=True)
            cls._shared_profile = QWebEngineProfile("LucentProfile", None)
            cls._shared_profile.setPersistentStoragePath(profile_dir)
            cls._shared_profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        return cls._shared_profile

    def __init__(self, parent=None):
        super().__init__(parent)
        profile = self.get_shared_profile()
        page = QWebEnginePage(profile, self) if profile else QWebEnginePage(self)
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
