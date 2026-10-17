"""Platform helpers. The Win32 calls are no-ops elsewhere; Linux gets its own setup."""
import os
import sys

WIN = sys.platform == "win32"
LINUX = sys.platform.startswith("linux")
MAC = sys.platform == "darwin"

WDA_NONE = 0x00
WDA_MONITOR = 0x01             # older Windows: capture shows black instead
WDA_EXCLUDEFROMCAPTURE = 0x11  # Windows 10 2004+: window is invisible to capture

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000


def session_type() -> str:
    """'x11', 'wayland' or '' (Linux only)."""
    return os.environ.get("XDG_SESSION_TYPE", "").lower()


def platform_setup() -> None:
    """Call BEFORE QApplication exists.

    Wayland has no protocol for always-on-top, absolute window positions or
    global shortcuts, which are the whole point of an overlay. Running through
    XWayland (the xcb backend) restores all three. Set LUCENT_WAYLAND=1 to
    stay on native Wayland anyway.
    """
    if not LINUX or "QT_QPA_PLATFORM" in os.environ or os.environ.get("LUCENT_WAYLAND") == "1":
        return
    on_wayland = session_type() == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
    if on_wayland and os.environ.get("DISPLAY"):
        os.environ["QT_QPA_PLATFORM"] = "xcb"


def post_app_setup(app) -> None:
    """Call right after QApplication is created."""
    if LINUX:
        # Lets the desktop match our window to lucent.desktop (icon, taskbar grouping).
        app.setDesktopFileName("lucent")
        app.setApplicationDisplayName("Lucent")
        if app.platformName() == "wayland":
            print("Lucent: running on native Wayland - always-on-top and window "
                  "positioning are not honoured there. Unset LUCENT_WAYLAND to use XWayland.",
                  file=sys.stderr)


# Set by the Manager so a click-through window never becomes impossible to unlock.
UNLOCK_PATHS = {"tray": False, "hotkey": False}


def can_unlock_click_through() -> bool:
    return WIN or UNLOCK_PATHS["tray"] or UNLOCK_PATHS["hotkey"]


def set_app_id(app_id: str) -> None:
    """Gives the taskbar our own identity (and our icon) instead of python.exe's."""
    if not WIN:
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def set_taskbar_hidden(widget, hidden: bool = True) -> bool:
    """Prevents overlay window from being listed in the Windows taskbar."""
    if not WIN:
        return False
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        hwnd = wintypes.HWND(int(widget.winId()))
        get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
        set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
        style = get_long(hwnd, GWL_EXSTYLE)
        if hidden:
            new_style = (style & ~WS_EX_APPWINDOW) | WS_EX_TOOLWINDOW
        else:
            new_style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
        set_long(hwnd, GWL_EXSTYLE, new_style)
        return True
    except Exception:
        return False


def set_capture_hidden(widget, hidden: bool = True) -> bool:
    """Hide (or show again) a top-level window in screenshots and screen recordings."""
    if not WIN:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.SetWindowDisplayAffinity.restype = wintypes.BOOL
        hwnd = wintypes.HWND(int(widget.winId()))
        if not hidden:
            return bool(user32.SetWindowDisplayAffinity(hwnd, WDA_NONE))
        if user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE):
            return True
        return bool(user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR))
    except Exception:
        return False


def set_click_through(widget, enable: bool = True) -> bool:
    """Enable or disable mouse click-through using WS_EX_TRANSPARENT."""
    if not WIN:
        return False
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        hwnd = wintypes.HWND(int(widget.winId()))
        
        # Use GetWindowLongPtrW / SetWindowLongPtrW for 64-bit compatibility
        get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
        set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
        
        style = get_long(hwnd, GWL_EXSTYLE)
        if enable:
            new_style = style | WS_EX_TRANSPARENT | WS_EX_LAYERED
        else:
            new_style = (style & ~WS_EX_TRANSPARENT)
        
        set_long(hwnd, GWL_EXSTYLE, new_style)
        return True
    except Exception:
        return False


# Modifiers for RegisterHotKey
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312


def register_global_hotkey(hwnd_int: int, hotkey_id: int, modifiers: int, vk: int) -> bool:
    """Register a Windows global hotkey so the app can wake up even when not focused."""
    if not WIN:
        return False
    try:
        import ctypes
        return bool(ctypes.windll.user32.RegisterHotKey(
            ctypes.c_void_p(hwnd_int),
            ctypes.c_int(hotkey_id),
            ctypes.c_uint(modifiers | MOD_NOREPEAT),
            ctypes.c_uint(vk)
        ))
    except Exception:
        return False


def unregister_global_hotkey(hwnd_int: int, hotkey_id: int) -> bool:
    """Unregister a Windows global hotkey."""
    if not WIN:
        return False
    try:
        import ctypes
        return bool(ctypes.windll.user32.UnregisterHotKey(
            ctypes.c_void_p(hwnd_int),
            ctypes.c_int(hotkey_id)
        ))
    except Exception:
        return False


# DWM Window Corner Preferences (Windows 11 build 22000+)
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_DEFAULT = 0
DWMWCP_DONOTROUND = 1
DWMWCP_ROUND = 2       # standard window corner radius (~8-12px)
DWMWCP_ROUNDSMALL = 3  # small subtle corner radius (~4-6px)


def set_window_rounded_corners(widget, small: bool = True) -> bool:
    """Apply native Windows 11 rounded window corners via DwmSetWindowAttribute."""
    if not WIN:
        return False
    try:
        import ctypes
        from ctypes import wintypes
        dwmapi = ctypes.windll.dwmapi
        hwnd = wintypes.HWND(int(widget.winId()))
        pref = ctypes.c_int(DWMWCP_ROUNDSMALL if small else DWMWCP_ROUND)
        hr = dwmapi.DwmSetWindowAttribute(
            hwnd,
            ctypes.c_uint(DWMWA_WINDOW_CORNER_PREFERENCE),
            ctypes.byref(pref),
            ctypes.sizeof(pref)
        )
        return hr == 0
    except Exception:
        return False

