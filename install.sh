#!/usr/bin/env bash
# WISPERMO one-line installer for Linux (any distro).
#
#   curl -fsSL https://raw.githubusercontent.com/FadiliAnas/wispermo/main/install.sh | bash
#
# Downloads the latest AppImage, adds it to your app menu, and makes it run even
# on distros without libfuse2 (e.g. Arch). No root needed for the install itself;
# the first launch walks you through the one-time typing/hotkey permission.
set -euo pipefail

REPO="FadiliAnas/wispermo"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/256x256/apps"
APP="$BIN/wispermo-x86_64.AppImage"
WRAP="$BIN/wispermo"
say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }

[ "$(uname -m)" = "x86_64" ] || { echo "WISPERMO needs a 64-bit (x86_64) Linux PC."; exit 1; }
mkdir -p "$BIN" "$APPS" "$ICONS"

say "Downloading WISPERMO (latest release)…"
curl -fL "https://github.com/$REPO/releases/latest/download/wispermo-x86_64.AppImage" -o "$APP"
chmod +x "$APP"
curl -fsSL "https://raw.githubusercontent.com/$REPO/main/packaging/wispermo.png" -o "$ICONS/wispermo.png" 2>/dev/null || true

say "Installing launcher (works even without libfuse2)"
cat > "$WRAP" <<'WRAP'
#!/bin/sh
APP="$HOME/.local/bin/wispermo-x86_64.AppImage"
# If neither FUSE2 nor fusermount3 is available, self-extract instead of mounting.
if ! ldconfig -p 2>/dev/null | grep -q 'libfuse\.so\.2' && ! command -v fusermount3 >/dev/null 2>&1; then
  export APPIMAGE_EXTRACT_AND_RUN=1
fi
exec "$APP" "$@"
WRAP
chmod +x "$WRAP"

cat > "$APPS/wispermo.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=WISPERMO
GenericName=Voice Dictation
Comment=Local, offline push-to-talk dictation
Exec=$WRAP
Icon=wispermo
Terminal=false
Categories=Utility;
Keywords=dictation;speech;voice;transcribe;
StartupNotify=false
EOF
update-desktop-database "$APPS" 2>/dev/null || true
gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

# friendly heads-up about the audio stack (needed to record)
if ! command -v ffmpeg >/dev/null && ! command -v parec >/dev/null && ! command -v pw-record >/dev/null; then
  echo "NOTE: install PipeWire (most distros have it) so WISPERMO can record audio."
fi

say "Installed."
echo
echo "  Launch 'WISPERMO' from your applications menu (or run: $WRAP)"
echo "  First launch sets up the dictation hotkey + typing permission."
echo "  Then hold your key, speak, release — your words get typed."
