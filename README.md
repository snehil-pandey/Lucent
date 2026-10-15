# Lucent

**Lucent** is a sleek, transparent, always-on-top overlay viewer for Windows built with Python and PySide6 (Qt). It allows you to display PDFs, images, web pages, and text documents in customizable floating windows that can even be hidden from screenshots and screen recordings.

---

## ✨ Features

- **Multi-Format Support**:
  - **PDFs**: Full PDF rendering and viewing.
  - **Images**: PNG, JPG/JPEG, GIF, BMP, WebP, SVG, ICO, TIFF.
  - **Web & URLs**: Embedded browser view via QtWebEngine.
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

### Prerequisites

- Python 3.10+ (tested on Python 3.13)
- Windows 10/11 (for Windows-specific display affinity features)

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
│   ├── viewers/            # Viewer implementations (PDF, Image, Text, Web, Empty)
│   │   ├── base.py
│   │   ├── empty.py
│   │   ├── image.py
│   │   ├── pdf.py
│   │   ├── text.py
│   │   └── web.py
│   ├── config.py           # Settings management & Look configuration
│   ├── icon.py             # Custom vector moon icon painter
│   ├── manager.py          # Multi-window and overlay lifecycle manager
│   ├── overlay.py          # Main floating overlay window widget
│   ├── settings_popup.py   # Pop-up controls (opacity, hue, on-top, capture)
│   ├── sources.py          # Input parser (paths, URLs, searches)
│   ├── splash.py           # Animated glowing crescent splash screen
│   ├── theme.py            # Dynamic CSS/QSS styling engine
│   ├── titlebar.py         # Custom frameless title bar and address input
│   └── winapi.py           # Windows display affinity & taskbar integrations
├── main.py                 # Application entry point
├── requirements.txt        # Python package dependencies
└── README.md               # Documentation
```

---

## 📄 License

This project is open-source. Feel free to use and adapt it to your workflow.
