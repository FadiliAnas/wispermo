#!/usr/bin/env bash
# Register the WISPERMO AppImage as a normal desktop app, so it shows up in the
# GNOME/KDE app grid and launches on click (GNOME does NOT run AppImages from a
# file-manager double-click by default — this is the supported way).
#
# Usage:  ./packaging/install-desktop.sh [/path/to/wispermo-x86_64.AppImage]
# No sudo needed — installs into ~/.local.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
APP="${1:-$ROOT/wispermo-x86_64.AppImage}"
APP="$(readlink -f "$APP")"

[ -f "$APP" ] || { echo "AppImage not found: $APP (build it with packaging/build-appimage.sh)"; exit 1; }
chmod +x "$APP"

ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
APP_DIR="$HOME/.local/share/applications"
mkdir -p "$ICON_DIR" "$APP_DIR"
cp "$HERE/wispermo.png" "$ICON_DIR/wispermo.png"

cat > "$APP_DIR/wispermo.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=WISPERMO
GenericName=Voice Dictation
Comment=Local, offline push-to-talk dictation
Exec=$APP
Icon=wispermo
Terminal=false
Categories=Utility;
Keywords=dictation;speech;voice;transcribe;whisper;
StartupNotify=false
EOF
chmod +x "$APP_DIR/wispermo.desktop"

update-desktop-database "$APP_DIR" 2>/dev/null || true
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo "Installed. Search for 'WISPERMO' in your Activities / app grid."
echo "  AppImage:  $APP"
echo "  Launcher:  $APP_DIR/wispermo.desktop"
