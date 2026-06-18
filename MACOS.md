# WISPERMO on macOS (Apple Silicon — Mac mini M4)

WISPERMO's UI is cross-platform; only the audio/typing/hotkey layer is
platform-specific, and macOS versions of those are included. You build the
`.app` **on the Mac** (a macOS app cannot be cross-compiled from Linux).

## Build it (one command, on the Mac)

```bash
# get the project onto the Mac (clone, AirDrop, USB, etc.), then:
cd wispermo
./packaging/build-macos.sh
```

The script will, with no prior setup:
1. install Homebrew + Python if missing,
2. create a virtualenv and install dependencies,
3. download the speech model **once** and bundle it (so the app is offline),
4. generate the app icon,
5. build **WISPERMO.app** with PyInstaller (arm64),
6. produce **`WISPERMO.dmg`**.

## Install it (the Chrome-style way)

Double-click **`WISPERMO.dmg`** → a window opens → **drag `WISPERMO` onto the
Applications folder**. Done. Launch it from Launchpad/Applications.

Everything (Python, Qt, the model) is inside the `.app` — nothing else to install.

## First launch — grant 3 permissions

macOS will prompt the first time; or set them in **System Settings ▸ Privacy &
Security**:

| Permission | Why | Where |
|---|---|---|
| **Microphone** | record your voice | Privacy & Security ▸ Microphone |
| **Accessibility** | type / paste into other apps | Privacy & Security ▸ Accessibility |
| **Input Monitoring** | detect your dictation hotkey | Privacy & Security ▸ Input Monitoring |

After granting Accessibility/Input Monitoring, **quit and reopen** WISPERMO so
they take effect.

> **Gatekeeper note:** the build is *ad-hoc signed*, not notarized by Apple. The
> first launch may need **right-click ▸ Open** (or *Open Anyway* in Privacy &
> Security). For a download you hand to friends without that step, the app must
> be signed with an Apple Developer ID and notarized — see below.

## Differences from the Linux version (automatic)

- **Audio:** CoreAudio via `sounddevice` (no ffmpeg/PipeWire needed).
- **Hotkey:** in-app global listener via `pynput` (no GNOME shortcuts). Default
  Push-to-talk: hold the key to talk, release to stop. Change it in
  Settings ▸ General.
- **Typing:** `pbcopy` + ⌘V paste, or the character-by-character writing effect.
- **Always-on-top** mic button + overlay work natively (no XWayland needed).

## Distributing to others (optional, later)

To let someone install without the right-click-Open step, on the Mac:

```bash
# requires a paid Apple Developer account
codesign --deep --options runtime --sign "Developer ID Application: YOUR NAME (TEAMID)" dist/WISPERMO.app
xcrun notarytool submit WISPERMO.dmg --apple-id you@example.com --team-id TEAMID --password APP_SPECIFIC_PW --wait
xcrun stapler staple WISPERMO.dmg
```

Then the `.dmg` opens cleanly on any Mac.
