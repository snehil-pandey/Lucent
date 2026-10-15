"""Lucent: a transparent, always-on-top viewer for PDFs, images and links."""
import sys

from PySide6.QtCore import QCoreApplication, Qt

# Must be set before the QApplication exists (needed by QtWebEngine).
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

from PySide6.QtWidgets import QApplication  # noqa: E402

from lucent import winapi  # noqa: E402
from lucent.config import APP_ID, APP_NAME  # noqa: E402
from lucent.icon import app_icon  # noqa: E402
from lucent.manager import Manager  # noqa: E402


def main() -> int:
    winapi.set_app_id(APP_ID)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setWindowIcon(app_icon())

    manager = Manager(sys.argv[1:])
    manager.start()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
