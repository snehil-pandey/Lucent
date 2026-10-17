"""Lucent: a transparent, always-on-top viewer for PDFs, images and links."""
import sys

from PySide6.QtCore import QCoreApplication, Qt

from lucent import winapi as _winapi

# Linux: pick the XWayland backend on Wayland so overlays can stay on top. Must run
# before QApplication is created.
_winapi.platform_setup()

# Must be set before the QApplication exists (needed by QtWebEngine & high-framerate rendering).
QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
QCoreApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

from PySide6.QtWidgets import QApplication  # noqa: E402

from lucent import winapi  # noqa: E402
from lucent.config import APP_ID, APP_NAME, APP_VERSION  # noqa: E402
from lucent.icon import app_icon  # noqa: E402
from lucent.manager import Manager  # noqa: E402


def main() -> int:
    if any(arg in sys.argv[1:] for arg in ("--version", "-v")):
        print(f"{APP_NAME} v{APP_VERSION}")
        return 0

    winapi.set_app_id(APP_ID)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    from lucent import theme
    from lucent.config import load_mode
    theme.set_mode(load_mode())
    app.setPalette(theme.app_palette())
    app.setWindowIcon(app_icon())
    winapi.post_app_setup(app)

    args = sys.argv[1:]
    skip_splash = ("--quick" in args) or ("--no-splash" in args)
    clean_args = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--quick", "--no-splash", "--no-ipc"):
            i += 1
            continue
        if a == "--set-cache" and i + 1 < len(args):
            from lucent.config import set_cache_location
            set_cache_location(args[i + 1])
            i += 2
            continue
        clean_args.append(a)
        i += 1

    # Talk to an already-running Lucent instead of starting a second one.
    from lucent import ipc
    commands = [a for a in clean_args if a in ("--toggle-click-through", "--hub", "--new")]
    sources = [a for a in clean_args if a not in commands]
    clean_args = sources
    if "--no-ipc" not in args:
        lines = [c[2:] for c in commands] + [f"open {s}" for s in sources]
        if lines and ipc.send(lines):
            return 0
        if not lines and ipc.send(["hub"]):
            return 0
        if "--toggle-click-through" in commands:
            print("Lucent isn't running, so there's nothing to toggle.", file=sys.stderr)
            return 1

    manager = Manager(clean_args)
    if "--no-ipc" not in args:
        server = ipc.Server(manager)
        server.command.connect(manager.handle_command)
    if skip_splash:
        manager._launch()
    else:
        manager.start()
    try:
        return app.exec()
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
