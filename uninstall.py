"""Lucent Uninstaller.
Performs clean removal of:
1. Windows Explorer Right-Click Context Menus ("Open with Lucent").
2. User Environment PATH entries.
3. Windows Desktop and Start Menu shortcuts.
4. Windows Add/Remove Programs uninstall registry entries.
5. Application files and directories.
"""
import argparse
import ctypes
from ctypes import wintypes
import os
import shutil
import subprocess
import sys
import winreg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

SUPPORTED_EXTS = [
    ".pdf",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico", ".tiff",
    ".mp4", ".m4v", ".webm", ".mkv", ".avi", ".mov", ".wmv", ".mp3", ".wav",
    ".txt", ".md", ".json", ".log", ".csv", ".py", ".js", ".html", ".htm"
]


def remove_from_user_path(directory: str) -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE)
        try:
            curr_path, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            curr_path = ""

        norm_target = os.path.normpath(directory).lower()
        paths = [p for p in curr_path.split(";") if p and os.path.normpath(p).lower() != norm_target]
        new_path = ";".join(paths)
        winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
        winreg.CloseKey(key)

        # Broadcast environment change
        HWND_BROADCAST = 0xFFFF
        WM_SETTINGCHANGE = 0x001A
        SMTO_ABORTIFHUNG = 0x0002
        res = wintypes.DWORD()
        ctypes.windll.user32.SendMessageTimeoutW(
            HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment",
            SMTO_ABORTIFHUNG, 5000, ctypes.byref(res)
        )
        return True
    except Exception as e:
        print(f"Error removing from PATH: {e}")
        return False


def _delete_reg_tree(root, subkey: str) -> None:
    try:
        hkey = winreg.OpenKey(root, subkey, 0, winreg.KEY_ALL_ACCESS)
    except FileNotFoundError:
        return
    except Exception:
        return

    while True:
        try:
            child = winreg.EnumKey(hkey, 0)
            _delete_reg_tree(hkey, child)
        except OSError:
            break
    winreg.CloseKey(hkey)
    try:
        winreg.DeleteKey(root, subkey)
    except Exception:
        pass


def unregister_context_menus() -> None:
    try:
        classes_root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes", 0, winreg.KEY_READ | winreg.KEY_WRITE)
        for ext in SUPPORTED_EXTS:
            _delete_reg_tree(classes_root, rf"{ext}\shell\OpenWithLucent")
        _delete_reg_tree(classes_root, r"*\shell\OpenWithLucent")
        winreg.CloseKey(classes_root)
    except Exception as e:
        print(f"Error unregistering context menus: {e}")


def remove_shortcuts() -> None:
    desktop = os.path.join(os.environ.get("USERPROFILE", ""), "Desktop", "Lucent.lnk")
    if os.path.isfile(desktop):
        try:
            os.remove(desktop)
        except Exception:
            pass

    start_menu = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs",
        "Lucent.lnk"
    )
    if os.path.isfile(start_menu):
        try:
            os.remove(start_menu)
        except Exception:
            pass


def remove_uninstall_registration() -> None:
    _delete_reg_tree(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Lucent"
    )


def remove_app_settings() -> None:
    _delete_reg_tree(winreg.HKEY_CURRENT_USER, r"Software\Lucent")


def perform_uninstall(install_dir: str, remove_settings: bool = False) -> None:
    # 1. Unregister integration points
    unregister_context_menus()
    remove_from_user_path(install_dir)
    remove_shortcuts()
    remove_uninstall_registration()

    if remove_settings:
        remove_app_settings()

    # 2. Self-delete schedule for installed directory if running inside it
    norm_install = os.path.normpath(install_dir)
    if os.path.isdir(norm_install):
        ps_cmd = (
            f"Start-Sleep -Seconds 1; "
            f"Remove-Item -Recurse -Force -LiteralPath '{norm_install}' -ErrorAction SilentlyContinue"
        )
        subprocess.Popen(
            ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            close_fds=True
        )


class UninstallerWindow(QWidget):
    def __init__(self, install_dir: str):
        super().__init__()
        self.install_dir = install_dir
        from lucent.config import APP_VERSION
        from lucent.icon import app_icon
        self.setWindowTitle(f"Uninstall Lucent v{APP_VERSION}")
        self.setFixedSize(480, 260)
        self.setWindowIcon(app_icon())
        self.setStyleSheet("""
            QWidget {
                background: #0f141c;
                color: #e6eefc;
                font-family: 'Segoe UI', sans-serif;
            }
            QLabel {
                font-size: 13px;
            }
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #e6eefc;
                border: 1px solid rgba(255, 255, 255, 0.16);
                border-radius: 5px;
                padding: 7px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
                border-color: #3b82f6;
            }
            QPushButton#danger {
                background: #dc2626;
                color: #ffffff;
                border: none;
                font-weight: 600;
            }
            QPushButton#danger:hover {
                background: #b91c1c;
            }
            QCheckBox {
                color: #94a3b8;
                font-size: 12px;
            }
        """)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(24, 20, 24, 20)
        vbox.setSpacing(14)

        title = QLabel("<b style='font-size: 16px;'>Uninstall Lucent</b>")
        vbox.addWidget(title)

        desc = QLabel(
            f"Are you sure you want to completely remove Lucent and all its system integrations from:\n"
            f"<b>{self.install_dir}</b>?"
        )
        desc.setWordWrap(True)
        vbox.addWidget(desc)

        self.chk_settings = QCheckBox("Also remove user settings, layout history and cache")
        vbox.addWidget(self.chk_settings)

        vbox.addStretch(1)

        btn_box = QHBoxLayout()
        btn_box.addStretch(1)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.close)

        btn_uninstall = QPushButton("Uninstall")
        btn_uninstall.setObjectName("danger")
        btn_uninstall.clicked.connect(self._do_uninstall)

        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_uninstall)
        vbox.addLayout(btn_box)

    def _do_uninstall(self):
        try:
            perform_uninstall(self.install_dir, remove_settings=self.chk_settings.isChecked())
            QMessageBox.information(
                self,
                "Lucent Uninstalled",
                "Lucent has been successfully removed from your system."
            )
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Uninstall Error", f"An error occurred during uninstallation:\n{e}")


def main():
    parser = argparse.ArgumentParser(description="Lucent Uninstaller")
    parser.add_argument("--silent", action="store_true", help="Silent uninstall without UI")
    parser.add_argument("--dir", default="", help="Target installation directory to remove")
    parser.add_argument("--purge-settings", action="store_true", help="Remove user settings and cache")
    args = parser.parse_args()

    # Determine default install dir
    install_dir = args.dir
    if not install_dir:
        # Check current executable location or default location
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        if os.path.isfile(os.path.join(exe_dir, "Lucent.exe")):
            install_dir = exe_dir
        else:
            install_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Lucent")

    if args.silent:
        perform_uninstall(install_dir, remove_settings=args.purge_settings)
        sys.exit(0)

    app = QApplication(sys.argv)
    win = UninstallerWindow(install_dir)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    if sys.platform != "win32":
        print("This uninstaller is for Windows. On Linux run: packaging/linux/install.sh --uninstall")
        sys.exit(1)
    main()
