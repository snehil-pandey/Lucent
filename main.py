"""Lucent: a transparent, always-on-top viewer for PDFs, images and links."""
import sys

from PySide6.QtCore import QCoreApplication, Qt

# Must be set before the QApplication exists (needed by QtWebEngine & high-framerate rendering).
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
QCoreApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

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

    args = sys.argv[1:]
    skip_splash = ("--quick" in args) or ("--no-splash" in args)
    clean_args = [a for a in args if a not in ("--quick", "--no-splash")]

    manager = Manager(clean_args)
    if skip_splash:
        manager._launch()
    else:
        manager.start()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
