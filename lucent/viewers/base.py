from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget


class Viewer(QWidget):
    """Contract every content viewer follows. Add a new file type by subclassing
    this, implementing accepts()/load(), and registering it in viewers/__init__.py."""

    title_changed = Signal(str)
    source_changed = Signal(str)   # what the address bar should show

    @classmethod
    def accepts(cls, source: str) -> bool:
        return False

    def load(self, source: str) -> None:
        raise NotImplementedError

    def apply_theme(self, hue: int) -> None:
        pass

    def go_back(self) -> None:
        pass

    def go_forward(self) -> None:
        pass

    def reload(self) -> None:
        pass

    def fit(self) -> None:
        pass
