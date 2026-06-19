#!/usr/bin/env bash
# Build Wispermo.app (native Swift) and sign it with the stable self-signed
# identity so macOS permissions persist across rebuilds.
#
# The project lives on the iCloud Desktop, which re-stamps com.apple.FinderInfo
# onto the bundle and breaks codesign — so we assemble + sign the .app in a temp
# dir (non-iCloud) and ditto the signed bundle back (ditto preserves signatures).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

APPNAME="Wispermo"
BUNDLE_ID="com.wispermo.mac"
LOCAL_KC="$HOME/Library/Keychains/wispermo-signing.keychain-db"
LOCAL_ID="WISPERMO Self-Signed"
CONFIG="${1:-release}"

echo "==> swift build -c $CONFIG"
swift build -c "$CONFIG"
BIN=".build/$CONFIG/$APPNAME"
[ -f "$BIN" ] || { echo "build failed: no binary"; exit 1; }

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/wmmac.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
APP="$STAGE/$APPNAME.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$BIN" "$APP/Contents/MacOS/$APPNAME"
[ -f "$HERE/AppIcon.icns" ] && cp "$HERE/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Wispermo</string>
  <key>CFBundleDisplayName</key><string>Wispermo</string>
  <key>CFBundleIdentifier</key><string>$BUNDLE_ID</string>
  <key>CFBundleExecutable</key><string>$APPNAME</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>${WISPERMO_BUILD:-1}</string>
  <key>CFBundleShortVersionString</key><string>0.1.0</string>
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSMicrophoneUsageDescription</key><string>Wispermo transcribes your speech on-device.</string>
</dict></plist>
PLIST

# Bundle the Whisper model + tokenizer so the app is plug-and-play (NO first-run
# download). Cached in .model-cache so rebuilds don't re-fetch.
MODEL_VARIANT="${WISPERMO_MODEL:-base}"
MODEL_CACHE="$HERE/.model-cache/$MODEL_VARIANT"
if [ ! -d "$MODEL_CACHE/models/argmaxinc/whisperkit-coreml/openai_whisper-$MODEL_VARIANT" ]; then
  echo "==> fetching Whisper '$MODEL_VARIANT' model to bundle (one-time, ~150MB)…"
  rm -rf "$MODEL_CACHE"; mkdir -p "$MODEL_CACHE"
  swift run FetchModel "$MODEL_VARIANT" "$MODEL_CACHE"
fi
mkdir -p "$APP/Contents/Resources/WhisperKitAssets"
ditto "$MODEL_CACHE/models" "$APP/Contents/Resources/WhisperKitAssets/models"
echo "==> bundled Whisper '$MODEL_VARIANT' model ($(du -sh "$MODEL_CACHE" | cut -f1))"

xattr -cr "$APP" 2>/dev/null || true

if security find-identity -p codesigning "$LOCAL_KC" 2>/dev/null | grep -q "$LOCAL_ID"; then
  security unlock-keychain -p wispermo "$LOCAL_KC"
  if ! security list-keychains -d user | tr -d '"' | grep -qF "$LOCAL_KC"; then
    security list-keychains -d user -s "$LOCAL_KC" \
      $(security list-keychains -d user | tr -d '"')
  fi
  echo "==> signing with $LOCAL_ID"
  codesign --force --sign "$LOCAL_ID" --keychain "$LOCAL_KC" "$APP"
else
  echo "==> self-signed identity not found — ad-hoc signing"
  codesign --force --sign - "$APP"
fi
codesign --verify --verbose=2 "$APP" 2>&1 | tail -1
codesign -dvv "$APP" 2>&1 | grep -iE "Authority=|adhoc" | head -2

# ditto the signed bundle back into the project (preserves the signature)
rm -rf "$HERE/$APPNAME.app"
ditto "$APP" "$HERE/$APPNAME.app"
echo "==> built $HERE/$APPNAME.app"

# drag-to-install .dmg (assembled in temp via ditto so the signature survives)
DMGROOT="$STAGE/dmgroot"; mkdir -p "$DMGROOT"
ditto "$APP" "$DMGROOT/$APPNAME.app"
ln -s /Applications "$DMGROOT/Applications"
hdiutil detach "/Volumes/$APPNAME" >/dev/null 2>&1 || true
hdiutil create -volname "$APPNAME" -srcfolder "$DMGROOT" -ov -format UDZO \
  "$STAGE/$APPNAME.dmg" >/dev/null
rm -f "$HERE/$APPNAME.dmg"
cp "$STAGE/$APPNAME.dmg" "$HERE/$APPNAME.dmg"
echo "==> built $HERE/$APPNAME.dmg"
