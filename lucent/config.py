import json
from dataclasses import asdict, dataclass
from typing import List, Optional

from PySide6.QtCore import QSettings

APP_NAME = "Lucent"
APP_ID = "Lucent.Overlay"


@dataclass
class Look:
    opacity: float = 0.88
    hue: int = 215
    on_top: bool = True
    hide_from_capture: bool = True
    click_through: bool = False
    invert_colors: bool = False


def _settings() -> QSettings:
    return QSettings("Lucent", "Lucent")


def _flag(value) -> bool:
    return str(value).lower() == "true"


def load_look() -> Look:
    s = _settings()
    return Look(
        opacity=float(s.value("opacity", 0.88)),
        hue=int(s.value("hue", 215)),
        on_top=_flag(s.value("on_top", "true")),
        hide_from_capture=_flag(s.value("hide_from_capture", "true")),
        click_through=_flag(s.value("click_through", "false")),
        invert_colors=_flag(s.value("invert_colors", "false")),
    )


def save_look(look: Look) -> None:
    s = _settings()
    s.setValue("opacity", look.opacity)
    s.setValue("hue", look.hue)
    s.setValue("on_top", look.on_top)
    s.setValue("hide_from_capture", look.hide_from_capture)
    s.setValue("click_through", look.click_through)
    s.setValue("invert_colors", look.invert_colors)


# Session & Recent Files Persistence ---------------------------------
MAX_RECENT = 10


def get_recent_sources() -> List[str]:
    s = _settings()
    raw = s.value("recent_sources", "[]")
    try:
        return json.loads(raw)
    except Exception:
        return []


def add_recent_source(source: str) -> None:
    if not source:
        return
    sources = get_recent_sources()
    if source in sources:
        sources.remove(source)
    sources.insert(0, source)
    sources = sources[:MAX_RECENT]
    s = _settings()
    s.setValue("recent_sources", json.dumps(sources))


def save_session(windows_data: list) -> None:
    s = _settings()
    s.setValue("saved_session", json.dumps(windows_data))


def load_session() -> list:
    s = _settings()
    raw = s.value("saved_session", "[]")
    try:
        return json.loads(raw)
    except Exception:
        return []
