"""Turn whatever the user typed, pasted or dropped into a path or URL."""
import os
import re
from urllib.parse import quote_plus

from PySide6.QtCore import QUrl

_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
_DOMAIN = re.compile(r"^[\w-]+(\.[\w-]+)+(:\d+)?([/?#].*)?$")


def is_url(source: str) -> bool:
    return bool(re.match(r"^https?://", source, re.I))


def normalize_source(text: str):
    t = (text or "").strip().strip("\"'")
    if not t:
        return None
    if t.lower().startswith("file:"):
        t = QUrl(t).toLocalFile() or t
    path = os.path.expanduser(os.path.expandvars(t))
    if os.path.exists(path):
        return os.path.abspath(path)
    if _SCHEME.match(t):
        return t
    if " " not in t and (_DOMAIN.match(t) or t.startswith("localhost")):
        return "https://" + t
    return "https://duckduckgo.com/?q=" + quote_plus(t)
