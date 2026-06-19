#!/usr/bin/env bash
# Build a self-contained WISPERMO AppImage.
#
#   1. PyInstaller bundles the app + Python + PySide6 + faster-whisper (onedir)
#   2. We assemble an AppDir around it (AppRun, .desktop, icon)
#   3. appimagetool packs it into wispermo-x86_64.AppImage
#
# The speech model (~150 MB) is NOT bundled; it downloads to ~/.cache on first
# use, keeping the AppImage smaller and letting users pick a model.
#
# Requirements: the project's .venv with deps installed. appimagetool is
# downloaded automatically if missing.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
PY="$ROOT/.venv/bin/python"
DIST="$HERE/dist"
BUILD="$HERE/build"
APPDIR="$HERE/WISPERMO.AppDir"
ARCH="${ARCH:-x86_64}"

say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }

# Bootstrap a virtualenv with deps if one isn't present (CI / fresh machine).
if [ ! -x "$PY" ]; then
  say "Creating virtualenv + installing dependencies"
  python3 -m venv "$ROOT/.venv"
  "$PY" -m pip install -q --upgrade pip
  "$PY" -m pip install -q -r "$ROOT/requirements.txt"
fi
say "Ensuring PyInstaller is installed"
"$PY" -m pip install -q --upgrade pyinstaller

if [ "${BUNDLE_MODEL:-1}" = "1" ]; then
  say "Pre-downloading the speech model (so it can be bundled)"
  "$PY" - <<'PY' || true
from faster_whisper import WhisperModel
WhisperModel("base")
PY
fi

say "Running PyInstaller (this takes a few minutes)…"
rm -rf "$DIST" "$BUILD"
"$PY" -m PyInstaller --noconfirm \
    --distpath "$DIST" --workpath "$BUILD" \
    "$HERE/wispermo.spec"

say "Assembling AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp -r "$DIST/wispermo/." "$APPDIR/usr/bin/"
cp "$HERE/wispermo.png" "$APPDIR/wispermo.png"
cp "$HERE/wispermo.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/wispermo.png"
cp "$HERE/wispermo.desktop" "$APPDIR/wispermo.desktop"
cp "$HERE/wispermo.desktop" "$APPDIR/usr/share/applications/wispermo.desktop"

cat > "$APPDIR/AppRun" <<'APPRUN'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
export APPDIR="${APPDIR:-$HERE}"
exec "$HERE/usr/bin/wispermo" "$@"
APPRUN
chmod +x "$APPDIR/AppRun"

# Audio capture uses PipeWire/Pulse tools (parec / pw-record) or system ffmpeg,
# which ship with the desktop audio stack — no ffmpeg bundling needed (and the
# static ffmpeg build lacks PulseAudio support anyway).

if [ "${BUNDLE_MODEL:-1}" = "1" ]; then
  say "Bundling speech model — works fully offline, no download"
  SNAP=$(ls -d "$HOME/.cache/huggingface/hub/models--Systran--faster-whisper-base/snapshots/"*/ 2>/dev/null | head -1)
  if [ -n "$SNAP" ]; then
    mkdir -p "$APPDIR/usr/share/wispermo/models/base"
    cp -rL "$SNAP". "$APPDIR/usr/share/wispermo/models/base/"
  else
    say "  (model not in cache; it will download on first run instead)"
  fi
fi

say "Fetching appimagetool if needed"
TOOL="$HERE/appimagetool-${ARCH}.AppImage"
if [ ! -x "$TOOL" ]; then
  curl -fL -o "$TOOL" \
    "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
  chmod +x "$TOOL"
fi

say "Packing AppImage"
OUT="$ROOT/wispermo-${ARCH}.AppImage"
# --appimage-extract-and-run avoids needing FUSE on the build machine
ARCH="$ARCH" "$TOOL" --appimage-extract-and-run "$APPDIR" "$OUT"

say "Done -> $OUT"
ls -lh "$OUT"
