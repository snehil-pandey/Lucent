# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.9.0] - 2026-10-17

### Added
- **Hardware-Accelerated Video & Audio Viewer**: Added native media playback support for `.mp4`, `.webm`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.m4v`, `.mp3`, `.wav`, `.ogg`, `.flac`, and `.m4a` with themed play/pause, seek slider, timestamp, mute, volume controls, and auto-looping.
- **Interactive Browser Popup Confirmation**: In the WebViewer, web links with `target="_blank"` or JavaScript `window.open` trigger an interactive Lucent-themed modal dialog prompting the user whether to open the page in the current overlay, spawn a new overlay window, or block/cancel.
- **Enhanced Web Compatibility**: Full browser engine capabilities configured including persistent local cookies/storage in `web_profile`, clipboard access, and auto-handled security origins.
- **Automated Build & Release Pipeline (`tools/build_release.py`)**: End-to-end version bumper, automated test runner, PyInstaller compilation, portable zip packager, installer builder, and release publisher.
- **Global CLI Version Flag**: Added `--version` / `-v` command-line option displaying the current version dynamically (`v0.9.0`).
- Light mode. The whole UI (Hub, overlays, title bar, flyouts, notes, PDF backdrop) switches between dark and light. Toggle it with the sun/moon button in the Hub, `Ctrl+Shift+L`, or the tray menu. The choice is remembered.
- `tools/make_demo.py`: renders a captioned demo video from the real widgets (no screen recorder needed). Run `python tools/make_demo.py demo.mp4`.
- Hub shows a short hint when there are no overlays yet.
- Linux support with the same UI as Windows.
- `packaging/linux/install.sh`: per-user install with its own virtualenv, a `lucent` command and a menu entry. `--uninstall` removes it.
- Single running instance. `lucent <file>` opens in the running app, and `lucent --toggle-click-through`, `--hub` and `--new` control it. This is how to get a global shortcut on Wayland.
- System-wide `Ctrl+Alt+M` on Linux/X11 through the optional `pynput` package.
- `lucent/glyphs.py`: title bar, Hub and flyout icons are drawn in code instead of using the Windows-only Segoe MDL2 font.
- Cross-platform font stack (`theme.FONT_UI`, `theme.ui_font`, `theme.mono_font`).
- On Wayland, Lucent now starts through XWayland so always-on-top and window positioning work. Set `LUCENT_WAYLAND=1` to opt out.
- `CHANGELOG.md`.

### Changed
- The Hub's "+ Add" button is a solid accent fill with white text instead of a bright neon fill.
- New gear icon (toothed) so it no longer looks like the sun icon. The empty-overlay hint now says "press Ctrl+V to paste a link".
- `theme.dark_palette` is now `theme.app_palette` (the old name still works). Colours that used a fixed white overlay now come from `theme.fg(alpha)` so they follow the mode.
- Click-through can now be turned on from the settings popup on Linux. Only the screen-recording option stays Windows-only.
- The `lucent` command prints a hint if click-through is turned on and the desktop has no tray icon or global shortcut to turn it off.
- `installer.py` now exits with a pointer to the Linux installer when run outside Windows.

### Fixed
- The Hub card list drew the operating system's window colour (dark grey on Windows dark mode, white on a light Linux theme). It is now transparent, and the app sets one explicit dark palette so unstyled widgets look the same everywhere.
- `tests/test_hub_and_hover.py::test_selective_hover_click_through_tracker` is skipped outside Windows, where the hover tracker does not exist.
