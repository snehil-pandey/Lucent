# Lucent

**Lucent** is a transparent, always-on-top overlay viewer for Windows and Linux built with Python and PySide6 (Qt). It allows you to display PDFs, images, web pages, and text documents in customizable floating windows that can even be hidden from screenshots and screen recordings.

---

## ✨ Features

- **Multi-Format Support**:
  - **PDFs**: Full PDF rendering and viewing.
  - **Images**: PNG, JPG/JPEG, GIF, BMP, WebP, SVG, ICO, TIFF.
  - **Video & Audio**: MP4, WebM, MKV, AVI, MOV, WMV, MP3, WAV, OGG, FLAC via hardware-accelerated QtMultimedia.
  - **Web & URLs**: Full Chromium browser via QtWebEngine with local persistent cookies, permissions handling, and smart popup confirmation prompt (open in current overlay or spawn a new overlay window).
  - **Text / Code**: Plain text, Markdown (`.md`), JSON, logs (`.log`), CSV.
- **Translucent & Always-on-Top**:
  - Adjustable opacity (with smooth slider and keyboard shortcuts).
  - Configurable hue and custom accent styling.
  - Toggle always-on-top mode per overlay window.
- **◐ Invert / Dark Mode Filter (`Ctrl + I`)**:
  - Instantly toggles high-contrast inverted dark mode for documents, PDFs, and code files with washed-out text on transparent backgrounds.
- **👻 Click-Through Mode (Ghost Mode)**:
  - Toggle with **`Ctrl + Alt + M`** (system-wide global shortcut), **`Ctrl + M`** (when focused), or the ghost button on the titlebar.
  - Allows clicks to pass directly through to whatever window is behind Lucent (ideal for tracing, CAD, reference, and video watching).
  - **Easy Return**: Even when clicks pass completely through, you can toggle it back anytime via:
    1. **`Ctrl + Alt + M`** anywhere in Windows (global hotkey registered via Win32).
    2. Clicking the **System Tray icon** in the Windows taskbar notifications area.
- **🔼 Window Collapse / Window Shading**:
  - Collapse the window into just its minimalist title bar with `Ctrl + K` or the collapse button `▲` / `▼` to quickly declutter your workspace.
- **📌 System Tray Companion**:
  - Lucent runs a resident tray icon. Click it to toggle click-through across all windows, or right-click to open recent documents, new overlays, bring all windows to front, or quit cleanly.
- **🖱️ Alt + Left-Click Drag Anywhere**:
  - Move the window effortlessly by holding `Alt` and dragging anywhere on the canvas.
- **🪟 Quick Snap Presets (`Alt + 1` - `Alt + 5`)**:
  - Instant corner and center window placement shortcuts.
- **📋 Instant Clipboard Paste (`Ctrl + V`)**:
  - Press `Ctrl + V` anywhere to directly load copied images, URLs, or file paths without having to paste into the address bar.
- **⚡ Instant Splash Dismiss**:
  - Click anywhere or tap any key during the startup animation to launch straight into your overlay immediately.
- **Privacy & Screen Capture Resistance**:
  - Windows API integration (`SetWindowDisplayAffinity`) to exclude overlay windows from screen sharing, captures, and recordings.
- **Multiple Floating Overlays**:
  - Open as many simultaneous windows as needed (`Ctrl + N`).

---

## ⌨️ Keyboard Shortcuts

Dark and light mode: `Ctrl+Shift+L` (or the sun/moon button in the Hub).

| Shortcut | Scope | Action |
| --- | --- | --- |
| `Ctrl + Alt + M` | **Global (System-Wide)** | **Toggle Click-Through / Ghost Mode** (works even when Lucent isn't focused) |
| `Ctrl + M` | Window | Toggle Click-Through / Ghost Mode |
| `Ctrl + I` | Window | **Toggle Invert / Dark Mode Filter** (high contrast for documents) |
| `Ctrl + K` | Window | **Collapse / Expand Window** (shade to titlebar only) |
| `Alt + Drag` | Window | **Move / Reposition Window** from anywhere on the canvas |
| `Alt + 1 - 5`| Window | **Quick Snap Presets** (Corners / Center) |
| `Ctrl + V` | Window | **Paste from Clipboard** (open copied image, path, or URL) |
| `Ctrl + N` | Window / Tray | Open a new overlay window |
| `Ctrl + O` | Window | Open file dialog |
| `Ctrl + L` | Window | Focus address / URL bar |
| `Ctrl + W` | Window | Close current overlay window |
| `F11` / `Esc` | Window | Toggle fullscreen |
| `Ctrl + Up` / `Ctrl + Down` | Window | Increase / decrease opacity |
| `Ctrl + Right` / `Ctrl + Left` | Window | Adjust color hue |
| `Ctrl + 0` | Window | Fit content to window |
| `Alt + Left` / `Alt + Right` | Window | Navigate back / forward (Web / Viewer) |
| `F5` | Window | Reload content |
| `Click / Any Key` | Window | Skip startup splash screen immediately |

---

## 🚀 Getting Started

### What works where

| Feature | Windows | Linux |
| --- | --- | --- |
| PDFs, images, web pages, text, notes | yes | yes |
| Opacity, hue, invert, collapse, snap presets, Hub | yes | yes |
| Always on top | yes | yes (X11, and Wayland through XWayland) |
| Click-through (ghost mode) | yes, title bar stays clickable | yes, whole window; use the tray icon, `Ctrl+Alt+M` on X11, or `lucent --toggle-click-through` to turn it off |
| System-wide `Ctrl+Alt+M` | yes | X11 only (needs `pynput`, installed by default) |
| Hide from screenshots and screen recordings | yes | **no**. Linux has no API for it, so the option is disabled |

Linux support is new. The test suite and the installer pass on a headless system; reports from real desktops are welcome.

### Prerequisites

- Python 3.10+ (tested on Python 3.13)
- Windows 10/11, or Linux with X11 or Wayland (Wayland runs through XWayland, which is the default here)
- Windows 10 version 2004 or later for hiding overlays from screen recordings

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd Lucent
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Installing on Linux

```
git clone https://github.com/snehil-pandey/Lucent.git
cd Lucent
packaging/linux/install.sh
```

This installs for your user only (no root): the app and its own virtualenv in `~/.local/share/lucent`, a `lucent` command in `~/.local/bin`, and a menu entry. Run `packaging/linux/install.sh --uninstall` to remove it.

If Lucent does not start, Qt may be missing a system library. On Debian or Ubuntu:

```
sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libnss3
```

**Controlling a running Lucent from the terminal.** Only one Lucent runs at a time. Running `lucent` again talks to the first one:

```
lucent report.pdf              # open a file in the running instance
lucent --toggle-click-through  # ghost mode on/off
lucent --hub                   # bring up the Hub
lucent --new                   # new empty overlay
```

On Wayland a program cannot listen for global key presses, so bind `lucent --toggle-click-through` to a key in your desktop's keyboard settings. That gives you the same `Ctrl+Alt+M` behaviour as on Windows.

On GNOME the tray icon needs the AppIndicator extension. Without it, use the command above.

If you want native Wayland instead of XWayland, set `LUCENT_WAYLAND=1`. Always-on-top and window positioning will not work there.

### Running Lucent

Launch the application:
```bash
python main.py
```

You can also pass a file path or URL directly as a command-line argument:
```bash
python main.py path/to/document.pdf
python main.py https://example.com
```

---

## 📁 Project Structure

```text
Lucent/
├── lucent/
│   ├── viewers/            # Viewer implementations (PDF, Image, Text, Note, Video, Web, Empty)
│   │   ├── base.py
│   │   ├── empty.py
│   │   ├── image.py
│   │   ├── note.py
│   │   ├── pdf.py
│   │   ├── text.py
│   │   ├── video.py
│   │   └── web.py
│   ├── config.py           # Settings management, Look configuration & storage paths
│   ├── hub.py              # Central Hub window to manage and inspect overlays
│   ├── icon.py             # Custom vector moon icon painter
│   ├── manager.py          # Multi-window and overlay lifecycle manager
│   ├── overlay.py          # Main floating overlay window widget
│   ├── settings_popup.py   # Pop-up controls (opacity, hue, on-top, capture)
│   ├── sources.py          # Input parser (paths, URLs, searches)
│   ├── splash.py           # Animated glowing crescent splash screen
│   ├── theme.py            # Dynamic single-hue CSS/QSS styling engine
│   ├── titlebar.py         # Custom frameless title bar and address input
│   └── winapi.py           # Windows display affinity & taskbar integrations
├── packaging/linux/        # install.sh and the .desktop entry
├── main.py                 # Application entry point
├── requirements.txt        # Python package dependencies
├── USER_GUIDE.md           # Comprehensive user manual & operation guide
├── LIMITATIONS.md          # Technical constraints and edge cases
└── README.md               # Quick-start documentation
```

---

## 📖 In-Depth User Guide

For a complete walkthrough of all features, workflows, shortcut combinations, and storage details, see [USER_GUIDE.md](USER_GUIDE.md).

---

## 📄 License

This project is open-source. Feel free to use and adapt it to your workflow.
