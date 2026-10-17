#!/usr/bin/env bash
# Installs Lucent for the current user (no root needed):
#   ~/.local/share/lucent        app + its own Python virtualenv
#   ~/.local/bin/lucent          launcher (also: lucent --toggle-click-through)
#   ~/.local/share/applications  menu entry
# Re-run to update. Remove with: packaging/linux/install.sh --uninstall
set -euo pipefail

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
APP_DIR="$DATA/lucent"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$DATA/applications"
ICON_DIR="$DATA/icons/hicolor/256x256/apps"
SRC="$(cd "$(dirname "$0")/../.." && pwd)"

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -rf "$APP_DIR" "$BIN_DIR/lucent" "$DESKTOP_DIR/lucent.desktop" "$ICON_DIR/lucent.png"
    echo "Lucent removed. (Settings live in ~/.config/Lucent and are left alone.)"
    exit 0
fi

command -v python3 >/dev/null || { echo "python3 is required (3.10+)."; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' \
    || { echo "Python 3.10 or newer is required."; exit 1; }

echo "Installing Lucent to $APP_DIR"
mkdir -p "$APP_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
rm -rf "$APP_DIR/src"
mkdir -p "$APP_DIR/src"
cp -r "$SRC/lucent" "$SRC/main.py" "$SRC/requirements.txt" "$APP_DIR/src/"

python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/src/requirements.txt"

cat > "$BIN_DIR/lucent" <<LAUNCH
#!/usr/bin/env bash
exec "$APP_DIR/venv/bin/python" "$APP_DIR/src/main.py" "\$@"
LAUNCH
chmod +x "$BIN_DIR/lucent"

cp "$SRC/app_icon.png" "$ICON_DIR/lucent.png"
sed "s|^Exec=lucent|Exec=$BIN_DIR/lucent|" "$SRC/packaging/linux/lucent.desktop" > "$DESKTOP_DIR/lucent.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t "$DATA/icons/hicolor" 2>/dev/null || true

case ":$PATH:" in *":$BIN_DIR:"*) ;; *) echo "Note: add $BIN_DIR to your PATH to run 'lucent' from a terminal." ;; esac

echo
echo "Done. Start Lucent from your app menu, or run: lucent"
echo
echo "System libraries Qt needs (install once if Lucent doesn't start):"
echo "  Debian/Ubuntu: sudo apt install libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-keysyms1 libxcb-shape0 libnss3"
echo "  Fedora:        sudo dnf install xcb-util-cursor xcb-util-wm xcb-util-keysyms libxkbcommon-x11 nss"
echo "  Arch:          sudo pacman -S xcb-util-cursor xcb-util-wm xcb-util-keysyms libxkbcommon-x11 nss"
