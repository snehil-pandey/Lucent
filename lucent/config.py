import json
from dataclasses import asdict, dataclass
from typing import List, Optional

from PySide6.QtCore import QSettings

APP_NAME = "Lucent"
APP_ID = "Lucent.Overlay"
APP_VERSION = "0.9.0"


@dataclass
class Look:
    opacity: float = 0.88
    hue: int = 215
    on_top: bool = True
    hide_from_capture: bool = True
    click_through: bool = False
    invert_colors: bool = False
    icon_name: str = "moon"
    icon_file: Optional[str] = None


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
        icon_name=str(s.value("icon_name", "moon")),
        icon_file=s.value("icon_file", None),
    )


def save_look(look: Look) -> None:
    s = _settings()
    s.setValue("opacity", look.opacity)
    s.setValue("hue", look.hue)
    s.setValue("on_top", look.on_top)
    s.setValue("hide_from_capture", look.hide_from_capture)
    s.setValue("click_through", look.click_through)
    s.setValue("invert_colors", look.invert_colors)
    s.setValue("icon_name", look.icon_name)
    if look.icon_file:
        s.setValue("icon_file", look.icon_file)
    else:
        s.remove("icon_file")


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


# Complete Overlay Registry (all past & present overlays) -------------
def load_overlay_registry() -> list:
    s = _settings()
    raw = s.value("overlay_registry", "[]")
    try:
        return json.loads(raw)
    except Exception:
        return []


def save_overlay_registry(items: list) -> None:
    s = _settings()
    s.setValue("overlay_registry", json.dumps(items))


def upsert_overlay_record(overlay_id: str, name: str, source: str, look: dict, geometry: list = None) -> list:
    items = load_overlay_registry()
    found = False
    for it in items:
        if it.get("id") == overlay_id:
            it["name"] = name
            it["source"] = source
            it["look"] = look
            if geometry:
                it["geometry"] = geometry
            found = True
            break
    if not found:
        items.insert(0, {
            "id": overlay_id,
            "name": name,
            "source": source,
            "look": look,
            "geometry": geometry or [100, 100, 940, 640],
        })
    save_overlay_registry(items)
    return items


def delete_overlay_record(overlay_id: str) -> list:
    items = load_overlay_registry()
    items = [it for it in items if it.get("id") != overlay_id]
    save_overlay_registry(items)
    return items


def get_cache_location() -> str:
    s = _settings()
    custom = s.value("cache_location", None)
    if custom and isinstance(custom, str) and custom.strip():
        return custom.strip()
    from PySide6.QtCore import QStandardPaths
    return QStandardPaths.writableLocation(QStandardPaths.StandardLocation.CacheLocation)


def set_cache_location(path: Optional[str]) -> None:
    s = _settings()
    if path and path.strip():
        s.setValue("cache_location", path.strip())
    else:
        s.remove("cache_location")


def get_storage_locations() -> dict:
    from PySide6.QtCore import QStandardPaths
    cache_dir = get_cache_location()
    appdata_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    config_file = _settings().fileName()
    return {
        "cache": cache_dir,
        "appdata": appdata_dir,
        "config": config_file,
    }


# UI mode (dark / light) ----------------------------------------------
def load_mode() -> str:
    return "light" if str(_settings().value("ui_mode", "dark")).lower() == "light" else "dark"


def save_mode(mode: str) -> None:
    _settings().setValue("ui_mode", "light" if mode == "light" else "dark")
