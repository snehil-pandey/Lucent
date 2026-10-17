"""System-wide Ctrl+Alt+M on Linux/X11 (Windows uses RegisterHotKey in overlay.py).

Needs the optional `pynput` package and a real X11 session. Wayland deliberately
forbids global key listening, so there you bind a desktop shortcut to
`lucent --toggle-click-through` instead (see ipc.py).
"""
import os

from PySide6.QtCore import QObject, Signal


class GlobalHotkey(QObject):
    triggered = Signal()

    def __init__(self, combo: str = "<ctrl>+<alt>+m", parent=None):
        super().__init__(parent)
        self._combo = combo
        self._listener = None
        self.available = False

    def start(self) -> bool:
        if self._listener is not None:
            return True
        if os.environ.get("XDG_SESSION_TYPE", "").lower() != "x11":
            return False
        try:
            from pynput import keyboard
            self._listener = keyboard.GlobalHotKeys({self._combo: self.triggered.emit})
            self._listener.daemon = True
            self._listener.start()
        except Exception:
            self._listener = None
            return False
        self.available = True
        return True

    def stop(self) -> None:
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
            self.available = False
