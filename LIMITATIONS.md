# Known Limitations & Technical Constraints

This document outlines the current technical limitations, edge cases, and design constraints in **Lucent**, along with potential workarounds and roadmap considerations.

---

## 1. Operating System & Platform Dependencies

- **Screen Capture Exclusion (`WDA_EXCLUDEFROMCAPTURE`)**:
  - Relies on Windows User32 `SetWindowDisplayAffinity`. It does not hide a window from a phone camera or a hardware capture card.
  - *Linux*: not possible. X11 and Wayland compositors offer no way to exclude one window from capture, so the option is disabled with a tooltip. Anything recording the screen will see the overlay.
- **Click-Through Mode (`WS_EX_TRANSPARENT` & `WS_EX_LAYERED`)**:
  - On Windows, uses native `WS_EX_TRANSPARENT` so clicks pass straight to underlying applications.
  - *Linux*: uses Qt's `Qt.WindowTransparentForInput` flag. The whole window ignores the mouse, including the title bar, so unlocking has to come from the tray icon, `Ctrl+Alt+M` (X11), or `lucent --toggle-click-through`. If none of those is available, Lucent prints a reminder when you turn click-through on.
- **Global & Local Hotkeys**:
  - On Windows, uses system-wide `RegisterHotKey` (`Ctrl+Alt+M`) so click-through can be unlocked even when the window is unfocused.
  - *Linux/X11*: a global `Ctrl+Alt+M` through `pynput`. *Wayland*: not possible by design. Bind `lucent --toggle-click-through` to a key instead.
  - `Ctrl+Alt+M` and `Ctrl+M` are also local shortcuts, and the tray icon toggles click-through everywhere a tray exists (GNOME needs the AppIndicator extension).
- **Wayland**: Lucent switches to XWayland automatically because native Wayland ignores always-on-top and window positions. Set `LUCENT_WAYLAND=1` to opt out.
- **Compositing**: transparency on Linux needs a compositing window manager. Without one, windows draw opaque.

---

## 2. Window Management & UX Constraints
*(Status: Addressed & Improved)*

- **Session Persistence**:
  - Automatically saves all open windows, coordinates, sizes, and currently opened documents/links upon app quit, and restores them seamlessly upon restart.
- **Alt + Left-Click Drag Anywhere**:
  - Users can hold `Alt` and drag from anywhere on the canvas to move the overlay window, removing the strict need to hunt for the top titlebar.
- **Quick Snap Presets**:
  - Hotkeys `Alt + 1` (bottom-left), `Alt + 2` (bottom-right), `Alt + 3` (top-left), `Alt + 4` (top-right), and `Alt + 5` (center) allow instant corner and center window placement.
- **Recent Files Menu**:
  - Accessible directly through the System Tray companion submenu ("Open Recent") for instant re-opening of past documents and URLs.
- **Window Snapping**:
  - Basic snap presets now resolve positioning without fighting frameless Qt window margins.

---

## 3. Visual & Transparency Challenges
*(Status: Addressed & Improved)*

- **Contrast & Legibility on Variable Backgrounds**:
  - Implemented **Invert / Dark Mode Filter** (`Ctrl + I` or Titlebar `◐` button). When reading white PDFs, light text files, or transparent documentation, toggling invert flips background and text color roles into a high-contrast dark theme so text remains crystal clear against busy desktop backgrounds.
- **Dynamic Accent Tinting**:
  - Titlebar, borders, address bar highlights, and viewer frames dynamically synchronize with hue selection.

---

## 4. Content Viewer Limitations
*(Status: Addressed & Improved)*

### 📄 PDF Viewer (`PdfViewer`)
- Multi-page viewing with smooth `Ctrl + Wheel` zooming.
- Added direct keyboard page navigation: `PageDown` / `Down` to jump forward, `PageUp` / `Up` to jump backward across pages.

### 🌐 Embedded Web Viewer (`WebViewer` / QtWebEngine)
- **Persistent Profile & Cookies**: WebViewer now utilizes a shared, persistent `QWebEngineProfile` stored in `~/.lucent_web_profile`. Login sessions, cookies, and cache now survive application restarts.

### 🖼️ Image Viewer (`ImageViewer`)
- **Interactive Manipulation**: Added middle-click drag canvas panning and `R` / `Shift + R` 90° image rotation alongside pinch/wheel zoom and auto-fit.

---

## 5. Security & Permission Considerations

- **High-Integrity / Elevated Windows**:
  - In Windows, UIPI (User Interface Privilege Isolation) restricts lower-privilege applications from interacting with or receiving input over elevated (Run as Administrator) windows. If another application runs as Admin, global hotkeys or focus ordering may exhibit priority conflicts unless Lucent is run with matching privileges.
