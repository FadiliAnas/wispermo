#!/usr/bin/env bash
# Build WISPERMO.app + a drag-to-install WISPERMO.dmg on macOS (Apple Silicon).
#
# Run this ON your Mac (mini M4):
#     cd wispermo
#     ./packaging/build-macos.sh
#
# It installs what it needs, bundles the speech model (offline), and produces
# WISPERMO.dmg — open it and drag WISPERMO into Applications, like Chrome.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
VENV="$ROOT/.venv-macos"
say() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }

[ "$(uname)" = "Darwin" ] || { echo "This script must run on macOS."; exit 1; }

# Must be run from inside the WISPERMO project (it needs the source + spec).
if [ ! -f "$ROOT/requirements-macos.txt" ] || [ ! -d "$ROOT/wispermo" ]; then
  echo "ERROR: run this from inside the WISPERMO project folder."
  echo "You appear to have copied only the script. Copy the WHOLE project"
  echo "folder to the Mac, then:  cd wispermo && ./packaging/build-macos.sh"
  exit 1
fi

# 1. Homebrew + Python -------------------------------------------------------
if ! command -v brew >/dev/null 2>&1; then
  say "Installing Homebrew (needs your password once)…"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$([ -x /opt/homebrew/bin/brew ] && /opt/homebrew/bin/brew shellenv)"
fi
command -v python3 >/dev/null 2>&1 || brew install python
command -v create-dmg >/dev/null 2>&1 || brew install create-dmg || true

# 2. venv + deps -------------------------------------------------------------
say "Creating virtualenv + installing dependencies"
python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install -q --upgrade pip
pip install -q -r "$ROOT/requirements-macos.txt" pyinstaller

# 3. bundle the speech model (offline) --------------------------------------
say "Fetching the speech model once (so it's bundled, no download for users)"
python - <<'PY'
from faster_whisper import WhisperModel
WhisperModel("base")   # downloads to the HF cache
print("model ready")
PY
SNAP=$(ls -d "$HOME/.cache/huggingface/hub/models--Systran--faster-whisper-base/snapshots/"*/ 2>/dev/null | head -1)
rm -rf "$HERE/macos-model/base"; mkdir -p "$HERE/macos-model/base"
[ -n "$SNAP" ] && cp -RL "$SNAP". "$HERE/macos-model/base/" && say "model bundled"

# 4. app icon (.icns from the PNG) ------------------------------------------
say "Generating app icon"
ICONSET="$HERE/wispermo.iconset"; rm -rf "$ICONSET"; mkdir -p "$ICONSET"
for s in 16 32 64 128 256 512; do
  sips -z $s $s "$HERE/wispermo.png" --out "$ICONSET/icon_${s}x${s}.png" >/dev/null
  d=$((s*2)); sips -z $d $d "$HERE/wispermo.png" --out "$ICONSET/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$HERE/wispermo.icns"

# 5. build the .app ----------------------------------------------------------
say "Building WISPERMO.app (PyInstaller)"
rm -rf "$HERE/build" "$HERE/dist"
pyinstaller --noconfirm --distpath "$HERE/dist" --workpath "$HERE/build" \
    "$HERE/wispermo-macos.spec"
APP="$HERE/dist/WISPERMO.app"
[ -d "$APP" ] || { echo "Build failed: no .app produced"; exit 1; }

# ad-hoc sign so Gatekeeper lets it run locally (not notarized)
codesign --force --deep --sign - "$APP" 2>/dev/null || true

# 6. drag-to-install .dmg ----------------------------------------------------
say "Creating WISPERMO.dmg (drag into Applications)"
OUT="$ROOT/WISPERMO.dmg"; rm -f "$OUT"
if command -v create-dmg >/dev/null 2>&1; then
  create-dmg --volname "WISPERMO" --app-drop-link 480 200 \
    --icon "WISPERMO.app" 160 200 --window-size 640 360 \
    "$OUT" "$APP" || { say "create-dmg fell back to plain dmg"; }
fi
if [ ! -f "$OUT" ]; then
  STAGE="$HERE/dmg"; rm -rf "$STAGE"; mkdir -p "$STAGE"
  cp -R "$APP" "$STAGE/"; ln -s /Applications "$STAGE/Applications"
  hdiutil create -volname "WISPERMO" -srcfolder "$STAGE" -ov -format UDZO "$OUT"
fi

say "Done -> $OUT"
echo
echo "Open WISPERMO.dmg, drag WISPERMO into Applications, then launch it."
echo "On first use, grant: Microphone, Accessibility, and Input Monitoring"
echo "in System Settings ▸ Privacy & Security (macOS will prompt you)."
