# Lucent: Comprehensive User & Operational Guide

**Lucent** is a sleek, transparent, always-on-top multi-format overlay companion for Windows, developed using Python and PySide6 (Qt).

---

## Table of Contents
1. [Overview & Core Architecture](#1-overview--core-architecture)
2. [Interface Anatomy](#2-interface-anatomy)
   - [The Lucent Hub Dashboard](#the-lucent-hub-dashboard)
   - [The Overlay Window & Hover Title Bar](#the-overlay-window--hover-title-bar)
   - [Settings Flyout & Global Presets](#settings-flyout--global-presets)
   - [System Tray Companion](#system-tray-companion)
3. [Supported File Formats & Viewers](#3-supported-file-formats--viewers)
4. [Master Shortcut & Gesture Matrix](#4-master-shortcut--gesture-matrix)
5. [In-Depth Feature Walkthroughs](#5-in-depth-feature-walkthroughs)
   - [Click-Through (Ghost Mode)](#click-through-ghost-mode)
   - [Contrast Inversion Filter](#contrast-inversion-filter)
   - [Faceted Theme & Color Derivation](#faceted-theme--color-derivation)
   - [Screen Capture & Recording Protection](#screen-capture--recording-protection)
   - [Window Snapping & Shading](#window-snapping--shading)
   - [Sticky Notes Mode](#sticky-notes-mode)
6. [Storage, Cache & Registry Locations](#6-storage-cache--registry-locations)
7. [Known Limitations & Troubleshooting](#7-known-limitations--troubleshooting)
8. [CLI Arguments & Development Tips](#8-cli-arguments--development-tips)

---

## 1. Overview & Core Architecture

Lucent is organized into two primary windows:
* **The Hub (`HubWindow`)**: A central management panel listing all active and previously saved overlays, offering search, inline renaming, restoration, and deletion.
* **The Overlays (`OverlayWindow`)**: Floating, frameless, translucent viewports that hover above your desktop and apps.

### Core Philosophy
- **Unified Single-Hue Palette**: Every background, panel, card, input, and border dynamically calculates its color from a single hue value ($0^\circ - 359^\circ$) via `theme.py`.
- **Faceted Geometry**: Angular chamfered edges with zero rounded radii across all windows and controls.
- **Hover Non-Disruptive Title Bar**: The titlebar only fades in when your cursor approaches the top edge (or while typing in the address bar). It floats over the viewport without displacing your content.

---

## 2. Interface Anatomy

### The Lucent Hub Dashboard
Open anytime using **`Ctrl + H`** or via the system tray.
* **Header Bar**:
  * Frameless title bar with app icon, minimize (`_`), and close (`✕`).
  * **Settings Gear (``)**: Opens the parent settings flyout to configure default hue, opacity, and window policies for future overlays.
* **Creation Bar**:
  * **Input Bar**: Type or paste any local file path or web URL, then press `Enter` or click **`+ Add Overlay`**.
  * **`Sticky Note` Button**: Spawns an empty translucent Sticky Note overlay immediately.
  * **File Picker**: Click the folder icon on the input bar to browse files visually.
* **Filter / Search Bar**: Live search filter across overlay titles and file paths.
* **Card List**:
  * **Active Overlays** (Tagged with accent color): Displays size, coordinates, and 3 quick actions:
    1. **`View` (`👁`)**: Brings the window to the front and focuses it.
    2. **`Rename` (`✎`)**: Prompts for a new custom display title.
    3. **`Close` (`✕`)**: Closes the window and saves its geometry to the inactive list.
  * **Inactive / Saved Overlays** (Tagged with subtle neutral):
    1. **`Open` (`▶`)**: Spawns the overlay back at its saved screen coordinates.
    2. **`Rename` (`✎`)**: Changes saved title.
    3. **`Delete` (`✕`)**: Permanently removes the overlay record from registry.
* **Footer**:
  * Overlay tally (`X Active • Y Saved`).
  * Clickable **`Cache: Local`** indicator (copies cache path to clipboard on click).

---

### The Overlay Window & Hover Title Bar
* **Frameless Canvas**: Renders your document, image, or web page with adjustable transparency.
* **Downward Gradient Hover Titlebar**:
  * **History**: `` Back, `` Forward, `` Reload.
  * **Address Bar (`Ctrl + L`)**: Displays current file/link; accepts pasted links or typed search queries.
  * **`◐` Invert**: Inverts content colors for high-contrast reading.
  * **`👻` Ghost**: Toggles mouse click-through mode.
  * **`▲` / `▼` Shading**: Collapses the overlay to just its minimalist title bar.
  * **`` Settings**: Adjusts individual window opacity, hue, on-top status, and capture protection.
  * **Window Buttons**: Minimize (`_`) and Close (`✕`).

---

### Settings Flyout & Global Presets
Accessible from either the Hub header or any Overlay's title bar:
- **Opacity Slider**: Smoothly adjust transparency from 10% to 100%.
- **Hue Slider**: Pick any accent hue on the 360° spectrum.
- **Always on Top Checkbox**: Pin window above standard desktop windows.
- **Click-Through Checkbox**: Enable or disable mouse transparency.
- **Hide from Screen Capture Checkbox**: Guard overlay from OBS, Discord, Teams, or Snipping Tool.
- **Cache Row**: Displays the exact local cache directory with one-click copying.

---

### System Tray Companion
Located in the Windows notification area:
- **Single-Click**: Toggles Ghost (click-through) mode across all active overlays.
- **Right-Click Menu**:
  - `All Overlays Hub (Ctrl+H)`: Restores and brings the Hub to focus.
  - `Toggle Click-Through (Ctrl+Alt+M)`: Master toggle for click-through.
  - `New Overlay (Ctrl+N)`: Creates a fresh overlay.
  - `Open Recent`: Submenu listing recently opened files and web pages.
  - `Bring All to Front`: Restores and raises every open overlay.
  - `Quit Lucent`: Cleanly saves session geometries and exits.

---

## 3. Supported File Formats & Viewers

| Viewer | Formats / Schemes | Key Features & Controls |
| :--- | :--- | :--- |
| **PDF Viewer** | `.pdf` | Multi-page rendering; `Ctrl + Wheel` zooming; `PageUp` / `PageDown` or `Up` / `Down` page navigation. |
| **Image Viewer** | `.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`, `.svg`, `.ico`, `.tiff` | Middle-click canvas panning; `Ctrl + Wheel` zoom; `R` / `Shift + R` 90° clockwise/counter-clockwise rotation. |
| **Text Viewer** | `.txt`, `.md`, `.json`, `.log`, `.csv`, `.py`, `.js`, etc. | Monospaced syntax display; scrollable; dark/light inversion mode support. |
| **Sticky Note** | Built-in editor | Translucent note editor; real-time line numbers rendered in the exact negative contrast of the background (`255 - R, 255 - G, 255 - B`). |
| **Web Viewer** | `http://`, `https://` | Full Chromium engine (QtWebEngine) with persistent profile cookies and cache in `~/.lucent_web_profile`. |
| **Empty Canvas** | Initial drop zone | Clean drop zone: *"Drop a file here, or press Ctrl+V to paste a link"*. |

---

## 4. Master Shortcut & Gesture Matrix

### Window & Navigation Shortcuts
| Shortcut | Context | Action |
| :--- | :--- | :--- |
| **`Ctrl + Alt + M`** | **Global (System-Wide)** | **Toggle Click-Through (Ghost Mode)** even when Lucent is unfocused |
| **`Ctrl + M`** | Overlay Window | Toggle Click-Through (Ghost Mode) |
| **`Ctrl + I`** | Overlay Window | Toggle Invert / High-Contrast Dark Mode Filter |
| **`Ctrl + K`** | Overlay Window | Collapse / Expand window (Window Shading) |
| **`Ctrl + H`** | Overlay Window | Show / Focus the Lucent Hub |
| **`Ctrl + N`** | Overlay / Tray | Spawn a new overlay window |
| **`Ctrl + O`** | Overlay Window | Open file browser dialog |
| **`Ctrl + L`** | Overlay Window | Focus title bar address / source bar |
| **`Ctrl + V`** | Overlay Window | Instant paste copied image, path, or URL |
| **`Ctrl + W`** | Overlay Window | Close current overlay window |
| **`F11` / `Esc`** | Overlay Window | Toggle Fullscreen / Exit Fullscreen |
| **`Ctrl + 0`** | Overlay Window | Fit content to window |
| **`F5`** | Overlay Window | Reload current document or webpage |
| **`Alt + Left` / `Right`** | Overlay Window | Navigate history back / forward |
| **`Ctrl + Up` / `Down`** | Overlay Window | Increase / Decrease opacity by 5% |
| **`Ctrl + Right` / `Left`**| Overlay Window | Shift color hue by +15° / -15° |

### Quick Snap Layout Presets
| Shortcut | Target Screen Anchor |
| :--- | :--- |
| **`Alt + 1`** | Snap to **Bottom-Left** corner |
| **`Alt + 2`** | Snap to **Bottom-Right** corner |
| **`Alt + 3`** | Snap to **Top-Left** corner |
| **`Alt + 4`** | Snap to **Top-Right** corner |
| **`Alt + 5`** | Snap to **Center** of screen |

### Mouse Canvas Gestures
- **`Alt + Left-Click Drag`**: Click and drag anywhere on the canvas to move the window.
- **`Middle-Click Drag`**: Pan large images in the Image Viewer.
- **`Ctrl + Mouse Wheel`**: Zoom in and out across PDFs and images.
- **Startup Click / Keypress**: Instantly dismisses the startup glowing splash screen.

---

## 5. In-Depth Feature Walkthroughs

### Click-Through (Ghost Mode)
Ghost Mode allows you to trace reference images, read docs while typing into an IDE behind the overlay, or watch videos without obstructing underlying apps:
1. Turn Ghost Mode on with `Ctrl + M` or the `👻` button on the titlebar.
2. The overlay becomes invisible to mouse interactions (`WS_EX_TRANSPARENT`).
3. To regain control, press the **global shortcut `Ctrl + Alt + M`** anywhere in Windows or left-click the **System Tray icon**.

### Contrast Inversion Filter (`Ctrl + I`)
When working over dark IDEs, light PDF backgrounds or white document pages can cause intense glare. Pressing `Ctrl + I` applies an inversion filter, flipping white backgrounds to deep dark tones and text to high-contrast legible foreground colors.

### Faceted Theme & Color Derivation
Every visual component in Lucent adheres to an angular, chamfered design language with zero rounded corners:
- `theme.background(hue)`: Window fill.
- `theme.surface_0`, `theme.surface_1`, `theme.surface_2`: Layered dark backgrounds for inputs and cards.
- `theme.accent(hue)`: 1px borders, focus outlines, and active tags.
- `theme.accent_fill(hue)`: Solid button fill color for primary actions.

### Screen Capture & Recording Protection
Using the Windows User32 `SetWindowDisplayAffinity` API, Lucent can exclude overlay windows from screen shares (Discord, Teams, Zoom, OBS) and screenshot tools (Snipping Tool). Check **Hide from Screen Capture** in the Settings flyout (``) to enable protection.

---

## 6. Storage, Cache & Registry Locations

| Data Type | Windows Location | Purpose |
| :--- | :--- | :--- |
| **Configuration & Registry** | `\HKEY_CURRENT_USER\Software\Lucent\Lucent` | Window geometry, saved overlays, master look settings, recent documents. |
| **Browser Web Engine Profile** | `%USERPROFILE%\.lucent_web_profile` | WebViewer session cookies, site storage, and cache. |
| **Local App Cache** | `%LOCALAPPDATA%\cache` | Cached assets and rendered document components. |

*Tip: You can copy the exact cache path at any time by clicking `Cache: Local` in the Hub footer.*

---

## 7. Known Limitations & Troubleshooting

*(Derived from `LIMITATIONS.md`)*

1. **Elevated (Administrator) Windows**:
   - In Windows, UIPI (User Interface Privilege Isolation) prevents standard user processes from receiving hotkeys or placing transparent overlays over elevated apps (e.g., Task Manager or an admin command prompt).
   - **Workaround**: If you need overlays to stay on top of an admin window, launch Lucent as Administrator.
2. **Screen Capture Affinity on Non-Windows**:
   - `WDA_EXCLUDEFROMCAPTURE` is a Windows 10/11 feature. On other operating systems, this option is disabled gracefully.
3. **DRM Video Playback**:
   - The embedded QtWebEngine browser does not ship with proprietary DRM components (Widevine). Commercial streaming platforms requiring DRM (e.g. Netflix, Spotify) will not play inside the overlay.
4. **Mixed Multi-Monitor DPI Scaling**:
   - Snapping across displays with divergent scaling (e.g., 100% and 175%) calculates based on the primary monitor's geometry. Dragging across displays is fully supported by Windows.

---

## 8. CLI Arguments & Development Tips

### Launch Options
```powershell
# Launch default Hub
python main.py

# Launch directly with a specific file or URL
python main.py "C:\path\to\document.pdf"
python main.py "https://docs.python.org"

# Skip the startup splash animation
python main.py --quick
python main.py --no-splash
```

### Running the Test Suite
The project includes a 23-test unit and blackbox GUI verification suite:
```powershell
.\.venv\Scripts\pytest -v tests/
```
