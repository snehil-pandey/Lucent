"""Lucent Custom Installer.
Allows the user to:
1. Select custom Installation directory (defaults to %LOCALAPPDATA%\\Programs\\Lucent).
2. Configure custom Cache directory (defaults to %LOCALAPPDATA%\\cache).
3. Add Lucent to system/user PATH so 'lucent ...' works anywhere in command-line.
4. Register Windows Explorer Right-Click Context Menu ("Open with Lucent") for supported files:
   - Images (.png, .jpg, .jpeg, .gif, .bmp, .webp, .svg, .ico, .tiff)
   - PDFs (.pdf)
   - Documents / Code (.txt, .md, .json, .log, .csv, .py, .js, .html, .htm)
5. Create Desktop and Start Menu shortcuts.
"""
import os
import shutil
import sys
import winreg
import zipfile
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
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


def add_to_user_path(directory: str) -> bool:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_READ | winreg.KEY_WRITE)
        try:
            curr_path, _ = winreg.QueryValueEx(key, "Path")
        except FileNotFoundError:
            curr_path = ""

        paths = [p for p in curr_path.split(";") if p]
        norm_dir = os.path.normpath(directory)
        if not any(os.path.normpath(p) == norm_dir for p in paths):
            paths.append(norm_dir)
            new_path = ";".join(paths)
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)

        winreg.CloseKey(key)

        # Broadcast environment change
        import ctypes
        from ctypes import wintypes
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
        print(f"Error adding to PATH: {e}")
        return False


def register_context_menus(exe_path: str) -> None:
    """Register 'Open with Lucent' context menu in Windows Explorer for supported formats."""
    try:
        # Register in HKCU\Software\Classes
        classes_root = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes", 0, winreg.KEY_READ | winreg.KEY_WRITE)

        # 1. Register for individual file extensions
        for ext in SUPPORTED_EXTS:
            try:
                ext_key = winreg.CreateKey(classes_root, ext)
                shell_key = winreg.CreateKey(ext_key, r"shell\OpenWithLucent")
                winreg.SetValue(shell_key, "", winreg.REG_SZ, "Open with Lucent")
                winreg.SetValueEx(shell_key, "Icon", 0, winreg.REG_SZ, f'"{exe_path}"')

                cmd_key = winreg.CreateKey(shell_key, "command")
                winreg.SetValue(cmd_key, "", winreg.REG_SZ, f'"{exe_path}" "%1"')
                winreg.CloseKey(cmd_key)
                winreg.CloseKey(shell_key)
                winreg.CloseKey(ext_key)
            except Exception:
                pass

        # 2. Register for generic '*' (all files context menu)
        try:
            star_key = winreg.CreateKey(classes_root, r"*\shell\OpenWithLucent")
            winreg.SetValue(star_key, "", winreg.REG_SZ, "Open with Lucent Overlay")
            winreg.SetValueEx(star_key, "Icon", 0, winreg.REG_SZ, f'"{exe_path}"')
            cmd_key = winreg.CreateKey(star_key, "command")
            winreg.SetValue(cmd_key, "", winreg.REG_SZ, f'"{exe_path}" "%1"')
            winreg.CloseKey(cmd_key)
            winreg.CloseKey(star_key)
        except Exception:
            pass

        winreg.CloseKey(classes_root)
    except Exception as e:
        print(f"Error registering context menus: {e}")


def create_shortcuts(exe_path: str, install_dir: str) -> None:
    """Create Desktop and Start Menu shortcuts."""
    try:
        import win32com.client
    except ImportError:
        # Fallback using PowerShell script
        import subprocess
        desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        start_menu = os.path.join(os.environ["APPDATA"], r"Microsoft\Windows\Start Menu\Programs")

        ico_path = os.path.join(install_dir, "app_icon.ico")
        ps_script = f"""
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut('{os.path.join(desktop, "Lucent.lnk")}')
        $Shortcut.TargetPath = '{exe_path}'
        $Shortcut.WorkingDirectory = '{install_dir}'
        if (Test-Path '{ico_path}') {{ $Shortcut.IconLocation = '{ico_path}' }}
        $Shortcut.Save()

        $ShortcutSM = $WshShell.CreateShortcut('{os.path.join(start_menu, "Lucent.lnk")}')
        $ShortcutSM.TargetPath = '{exe_path}'
        $ShortcutSM.WorkingDirectory = '{install_dir}'
        if (Test-Path '{ico_path}') {{ $ShortcutSM.IconLocation = '{ico_path}' }}
        $ShortcutSM.Save()
        """
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True)


class InstallWorker(QThread):
    progress = Signal(int, str)
    finished_signal = Signal(bool, str)

    def __init__(self, src_bundle_dir: str, install_dir: str, cache_dir: str, add_path: bool, add_context: bool, add_shortcuts: bool):
        super().__init__()
        self.src_bundle_dir = src_bundle_dir
        self.install_dir = install_dir
        self.cache_dir = cache_dir
        self.add_path = add_path
        self.add_context = add_context
        self.add_shortcuts = add_shortcuts

    def run(self):
        try:
            self.progress.emit(10, "Preparing directories...")
            os.makedirs(self.install_dir, exist_ok=True)
            if self.cache_dir:
                os.makedirs(self.cache_dir, exist_ok=True)

            self.progress.emit(25, "Locating application package...")
            zip_to_extract = None
            if self.src_bundle_dir and os.path.isdir(self.src_bundle_dir):
                for item in os.listdir(self.src_bundle_dir):
                    s = os.path.join(self.src_bundle_dir, item)
                    d = os.path.join(self.install_dir, item)
                    if os.path.isdir(s):
                        if os.path.exists(d):
                            shutil.rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
            elif self.src_bundle_dir and os.path.isfile(self.src_bundle_dir) and zipfile.is_zipfile(self.src_bundle_dir):
                zip_to_extract = self.src_bundle_dir
            else:
                # Check adjacent to installer exe
                exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                local_candidates = [
                    os.path.join(exe_dir, "Lucent-Portable.zip"),
                    os.path.join(exe_dir, "dist", "Lucent-Portable.zip"),
                    os.path.join(os.getcwd(), "Lucent-Portable.zip"),
                    os.path.join(os.getcwd(), "dist", "Lucent-Portable.zip")
                ]
                for cand in local_candidates:
                    if os.path.isfile(cand) and zipfile.is_zipfile(cand):
                        zip_to_extract = cand
                        break

                if not zip_to_extract:
                    # Download release package
                    self.progress.emit(30, "Fetching package from repository release...")
                    import urllib.request
                    download_url = "https://github.com/snehil-pandey/Lucent/releases/latest/download/Lucent-Portable.zip"
                    temp_zip = os.path.join(self.install_dir, "temp_download.zip")
                    try:
                        urllib.request.urlretrieve(download_url, temp_zip)
                        zip_to_extract = temp_zip
                    except Exception as err:
                        raise RuntimeError(f"Could not find local Lucent-Portable.zip and download failed: {err}")

            if zip_to_extract:
                self.progress.emit(45, "Extracting binaries and Qt runtime...")
                with zipfile.ZipFile(zip_to_extract, 'r') as zip_ref:
                    zip_ref.extractall(self.install_dir)
                if zip_to_extract.endswith("temp_download.zip") and os.path.exists(zip_to_extract):
                    os.remove(zip_to_extract)

            target_exe = os.path.join(self.install_dir, "Lucent.exe")
            cmd_wrapper = os.path.join(self.install_dir, "lucent.cmd")
            with open(cmd_wrapper, "w") as f:
                f.write(f'@echo off\nstart "" "{target_exe}" %*\n')

            # Install uninstaller helper script and cmd shortcut
            uninstall_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uninstall.py")
            uninstall_dst = os.path.join(self.install_dir, "uninstall.py")
            if os.path.isfile(uninstall_src):
                shutil.copy2(uninstall_src, uninstall_dst)
            uninst_cmd = os.path.join(self.install_dir, "uninstall.cmd")
            with open(uninst_cmd, "w") as f:
                f.write(f'@echo off\npython "{uninstall_dst}" %*\n')

            self.progress.emit(60, "Configuring custom cache directory in settings...")
            if self.cache_dir:
                # Save cache location to registry
                try:
                    s_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\Lucent\Lucent")
                    winreg.SetValueEx(s_key, "cache_location", 0, winreg.REG_SZ, self.cache_dir)
                    winreg.CloseKey(s_key)
                except Exception as e:
                    print(f"Registry cache set error: {e}")

            # Register in Windows Add/Remove Programs
            try:
                from lucent.config import APP_VERSION
                uninst_reg = winreg.CreateKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Lucent"
                )
                winreg.SetValueEx(uninst_reg, "DisplayName", 0, winreg.REG_SZ, "Lucent Overlay Viewer")
                winreg.SetValueEx(uninst_reg, "DisplayVersion", 0, winreg.REG_SZ, APP_VERSION)
                winreg.SetValueEx(uninst_reg, "DisplayIcon", 0, winreg.REG_SZ, target_exe)
                winreg.SetValueEx(uninst_reg, "InstallLocation", 0, winreg.REG_SZ, self.install_dir)
                winreg.SetValueEx(uninst_reg, "Publisher", 0, winreg.REG_SZ, "Lucent")
                uninst_string = f'"{uninst_cmd}"'
                winreg.SetValueEx(uninst_reg, "UninstallString", 0, winreg.REG_SZ, uninst_string)
                winreg.CloseKey(uninst_reg)
            except Exception as e:
                print(f"Error registering uninstaller: {e}")

            if self.add_path:
                self.progress.emit(75, "Adding Lucent to PATH...")
                add_to_user_path(self.install_dir)

            if self.add_context:
                self.progress.emit(85, "Registering Windows Explorer Right-Click menus...")
                register_context_menus(target_exe)

            if self.add_shortcuts:
                self.progress.emit(95, "Creating Desktop and Start Menu shortcuts...")
                create_shortcuts(target_exe, self.install_dir)

            self.progress.emit(100, "Installation Complete!")
            self.finished_signal.emit(True, "Lucent has been successfully installed!")
        except Exception as e:
            self.finished_signal.emit(False, str(e))


class InstallerWindow(QWidget):
    def __init__(self, bundle_source: str):
        super().__init__()
        self.bundle_source = bundle_source
        from lucent.config import APP_VERSION
        self.setWindowTitle(f"Lucent Setup & Custom Installer v{APP_VERSION}")
        self.setFixedSize(560, 490)
        from lucent.icon import app_icon, render_overlay_pixmap
        self.setWindowIcon(app_icon())
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #121820;
                color: #e6eefc;
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
            }
            QLabel {
                background-color: transparent;
                background: transparent;
            }
            QFrame#HeaderCard {
                background-color: #161f2c;
                border: 1px solid #2563eb;
                padding: 14px;
            }
            QLabel#Title {
                font-size: 18px;
                font-weight: bold;
                color: #60a5fa;
                background: transparent;
            }
            QLineEdit {
                background-color: #0b1118;
                border: 1px solid #1e293b;
                padding: 6px 10px;
                color: #e6eefc;
            }
            QLineEdit:focus {
                border: 1px solid #38bdf8;
            }
            QPushButton {
                background-color: #1d4ed8;
                border: 1px solid #3b82f6;
                color: #ffffff;
                font-weight: bold;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton#BrowseBtn {
                background-color: #1e293b;
                border: 1px solid #334155;
            }
            QPushButton#BrowseBtn:hover {
                background-color: #334155;
            }
            QCheckBox {
                spacing: 8px;
                background-color: transparent;
                background: transparent;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QProgressBar {
                background-color: #0b1118;
                border: 1px solid #1e293b;
                text-align: center;
                height: 18px;
            }
            QProgressBar::chunk {
                background-color: #2563eb;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header with Moon Icon from icon.py
        header = QFrame()
        header.setObjectName("HeaderCard")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(10, 10, 10, 10)
        h_lay.setSpacing(14)

        from lucent.icon import render_overlay_pixmap
        lbl_icon = QLabel()
        lbl_icon.setPixmap(render_overlay_pixmap(44, "moon"))
        h_lay.addWidget(lbl_icon)

        text_vlay = QVBoxLayout()
        text_vlay.setSpacing(4)
        from lucent.config import APP_VERSION
        lbl_title = QLabel(f"Lucent Setup v{APP_VERSION}")
        lbl_title.setObjectName("Title")
        lbl_desc = QLabel("Install Lucent transparent overlay viewer with custom directories and integrations.")
        lbl_desc.setStyleSheet("color: #94a3b8; font-size: 12px; background: transparent;")
        text_vlay.addWidget(lbl_title)
        text_vlay.addWidget(lbl_desc)
        h_lay.addLayout(text_vlay, 1)

        layout.addWidget(header)

        # 1. Install Location
        lbl_inst = QLabel("Installation Directory:")
        layout.addWidget(lbl_inst)
        inst_row = QHBoxLayout()
        default_inst = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\"), "Programs", "Lucent")
        self.edit_inst = QLineEdit(default_inst)
        btn_inst_browse = QPushButton("Browse...")
        btn_inst_browse.setObjectName("BrowseBtn")
        btn_inst_browse.clicked.connect(self._browse_install)
        inst_row.addWidget(self.edit_inst, 1)
        inst_row.addWidget(btn_inst_browse)
        layout.addLayout(inst_row)

        # 2. Cache Location
        lbl_cache = QLabel("Cache Location:")
        layout.addWidget(lbl_cache)
        cache_row = QHBoxLayout()
        default_cache = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\"), "cache", "Lucent")
        self.edit_cache = QLineEdit(default_cache)
        btn_cache_browse = QPushButton("Browse...")
        btn_cache_browse.setObjectName("BrowseBtn")
        btn_cache_browse.clicked.connect(self._browse_cache)
        cache_row.addWidget(self.edit_cache, 1)
        cache_row.addWidget(btn_cache_browse)
        layout.addLayout(cache_row)

        # Options Checkboxes
        self.chk_path = QCheckBox("Add Lucent to user PATH (so 'lucent ...' works anywhere in command line)")
        self.chk_path.setChecked(True)
        layout.addWidget(self.chk_path)

        self.chk_context = QCheckBox("Add 'Open with Lucent' right-click menu for supported images, PDFs & code")
        self.chk_context.setChecked(True)
        layout.addWidget(self.chk_context)

        self.chk_shortcuts = QCheckBox("Create Desktop & Start Menu shortcuts")
        self.chk_shortcuts.setChecked(True)
        layout.addWidget(self.chk_shortcuts)

        # Progress
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #38bdf8; font-size: 12px; background: transparent;")
        layout.addWidget(self.status_lbl)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Action Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setObjectName("BrowseBtn")
        self.btn_cancel.clicked.connect(self.close)
        self.btn_install = QPushButton("Install Now")
        self.btn_install.clicked.connect(self._start_install)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_install)
        layout.addLayout(btn_row)

    def _browse_install(self):
        d = QFileDialog.getExistingDirectory(self, "Select Installation Directory", self.edit_inst.text())
        if d:
            self.edit_inst.setText(os.path.normpath(d))

    def _browse_cache(self):
        d = QFileDialog.getExistingDirectory(self, "Select Cache Directory", self.edit_cache.text())
        if d:
            self.edit_cache.setText(os.path.normpath(d))

    def _start_install(self):
        install_dir = self.edit_inst.text().strip()
        cache_dir = self.edit_cache.text().strip()
        if not install_dir:
            QMessageBox.warning(self, "Invalid Directory", "Please specify a valid installation directory.")
            return

        self.btn_install.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(True)

        self.worker = InstallWorker(
            src_bundle_dir=self.bundle_source,
            install_dir=install_dir,
            cache_dir=cache_dir,
            add_path=self.chk_path.isChecked(),
            add_context=self.chk_context.isChecked(),
            add_shortcuts=self.chk_shortcuts.isChecked(),
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _on_progress(self, val: int, msg: str):
        self.progress.setValue(val)
        self.status_lbl.setText(msg)

    def _on_finished(self, success: bool, msg: str):
        if success:
            QMessageBox.information(self, "Success", msg)
            self.close()
        else:
            QMessageBox.critical(self, "Error", f"Installation failed:\n{msg}")
            self.btn_install.setEnabled(True)
            self.btn_cancel.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    # Check if bundled source exists
    dist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "Lucent")
    zip_pkg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "Lucent-Portable.zip")

    source = dist_dir if os.path.isdir(dist_dir) else zip_pkg
    window = InstallerWindow(source)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    if sys.platform != "win32":
        print("This installer is for Windows. On Linux run: packaging/linux/install.sh")
        sys.exit(1)
    main()
