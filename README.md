# WISPERMO

**Local, offline push-to-talk dictation for Linux** — a free, private alternative
to Wispr Flow. Press a hotkey, speak, press again, and your words are typed into
whatever app you're using. No cloud, no account, no subscription. Your voice
never leaves your machine.

![mic](packaging/wispermo.png)

- **Engine:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
  (OpenAI Whisper via CTranslate2) — runs fully on CPU.
- **UI:** PySide6 — system-tray icon (where supported), a floating "listening"
  overlay, a control window, settings, onboarding and history.
- **Platform:** Fedora / GNOME on Wayland with PipeWire (adaptable to other
  distros & X11).

## Features

- 🎤 **One-key dictation** — global hotkey to start/stop, text typed at your cursor
- 🟣 **Floating mic button** — always-on-top, draggable, click to dictate
- 🌊 **Live waveform overlay** — a pill that animates to your real voice level
- 🔒 **100% offline** — no network, no telemetry
- ⚡ **Instant** — the model stays warm in RAM; short clips transcribe in <1 s on CPU
- 🌍 **Multilingual** — 90+ languages, auto-detected or pinned
- 📖 **Custom dictionary** — auto-replace spoken phrases (names, jargon, emails)
- ✨ **Smart formatting** — capitalisation/spacing tidy-up + optional trailing space
- 📋 **Smart output** — types via `ydotool`, or pastes, or copies to clipboard
- 🧰 **Guided setup** — first-run wizard handles the one-time system permission
- 🕘 **History & stats** — searchable history, words dictated, time saved
- 🎛️ **Polished UI** — sidebar app (Home · History · Dictionary · Settings · About)
  with a dark design system and animated controls

> ### A note on the model
> This started from a request to use [microsoft/VibeVoice](https://github.com/microsoft/VibeVoice).
> VibeVoice **does** include a speech-to-text model (VibeVoice-ASR), but it's a
> 7–9B-parameter, GPU-oriented model built for hour-long recordings — minutes per
> clip on a CPU laptop. For *instant* dictation, faster-whisper is the right
> engine. The transcription backend is isolated in
> [`wispermo/transcriber.py`](wispermo/transcriber.py), so a VibeVoice/GPU backend
> can be dropped in later by setting `device=cuda` or swapping that one class.

---

## Run from source (development)

```bash
cd ~/Work/WISPERMO
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
./bin/wispermo            # launches the app; first run opens the setup wizard
```

The setup wizard will:
1. **Grant typing permission** — installs a udev rule (via `pkexec`) so `ydotool`
   can type into other apps without root, and starts the `ydotoold` service.
   *(One logout/login is needed the first time for the `input` group to apply.)*
2. **Register your hotkey** as a GNOME custom shortcut (default **Ctrl+Alt+D**).

Then press the hotkey, speak, press again — done.

## Build a shippable AppImage

```bash
./packaging/build-appimage.sh
#   -> wispermo-x86_64.AppImage   (single file you can distribute/sell)
```

This bundles Python, PySide6 and faster-whisper with PyInstaller, then packs an
AppImage. The speech model is downloaded on first use (so the file stays smaller
and users can choose model size). To distribute:

```bash
chmod +x wispermo-x86_64.AppImage
./wispermo-x86_64.AppImage          # runs anywhere; first launch runs onboarding
```

The AppImage is a single executable; the GNOME hotkey is registered to call it as
`/path/to/wispermo-x86_64.AppImage toggle`.

### Make it appear in the app grid (recommended)

GNOME does **not** launch an AppImage from a Files double-click (a GNOME security
default). Register a desktop entry so WISPERMO shows up in Activities / your app
grid and launches on click — no sudo:

```bash
./packaging/install-desktop.sh            # uses ./wispermo-x86_64.AppImage
#   ./packaging/install-desktop.sh /path/to/wispermo-x86_64.AppImage
```

For end users you'd ship the AppImage plus this one command (or bundle it into
your installer). Then "WISPERMO" is searchable and clickable like any app.

---

## Architecture

```
  GNOME hotkey ─► `wispermo toggle` ─(unix socket)─► running app
                                                         │
  app (GUI thread)                                       │
   ├─ system tray (if available) / control window        │
   ├─ floating overlay (listening / transcribing)        │
   └─ engine worker (own thread):                         ▼
        record mic (ffmpeg+PipeWire) → faster-whisper → type into focused window
```

| Module | Role |
|---|---|
| [`app.py`](wispermo/app.py) | controller: tray, overlay, worker thread, socket, single-instance |
| [`transcriber.py`](wispermo/transcriber.py) | faster-whisper wrapper (swap here for GPU/VibeVoice) |
| [`recorder.py`](wispermo/recorder.py) | ffmpeg/PipeWire mic capture |
| [`typist.py`](wispermo/typist.py) | deliver text (ydotool type / paste / clipboard) |
| [`overlay.py`](wispermo/overlay.py) | floating state pill |
| [`main_window.py`](wispermo/main_window.py) | control panel + history |
| [`settings_window.py`](wispermo/settings_window.py) | settings dialog |
| [`onboarding.py`](wispermo/onboarding.py) | first-run wizard |
| [`sysintegration.py`](wispermo/sysintegration.py) | GNOME hotkey, uinput setup, autostart |
| [`history.py`](wispermo/history.py) | transcription history & stats |
| [`config.py`](wispermo/config.py) | JSON settings at `~/.config/wispermo/` |

## Settings

Edit in the app (Settings window) or directly in `~/.config/wispermo/config.json`.
Any value can also be overridden with an env var, e.g. `WISPERMO_MODEL=small`.

| Setting | Default | Notes |
|---|---|---|
| Model | `base` | `tiny`/`base`/`small`/`medium`/`large-v3` |
| Language | auto | pin to a language for speed/reliability |
| Output | `paste` | `paste` (Ctrl+V) · `type` · `clipboard` |
| Microphone | default | pick a PipeWire/Pulse source |
| Hotkey | `Ctrl+Alt+D` | GNOME custom shortcut |
| Autostart | on | launch on login |

## Troubleshooting

- **No tray icon on GNOME** — expected. GNOME hides legacy tray icons; WISPERMO
  runs in the background and shows the overlay while you speak. Re-launch it any
  time to open the control window. For a real tray icon, install the GNOME
  extension *AppIndicator and KStatusNotifierItem Support* and log out/in.
- **Text isn't typed** (but a notification shows the transcription) — `ydotool`
  can't reach `/dev/uinput`. Re-run the setup wizard, then log out/in once and
  `systemctl --user restart ydotoold`. Or set Output → *Clipboard* and paste.
- **Wrong language detected** on short clips — pin the language in Settings.
- **Wrong mic** — choose the right source in Settings (or `pactl list short sources`).

## License & selling

The app code is yours to license as you wish. Dependencies: PySide6 is **LGPL**
(fine for commercial/closed-source distribution as long as the Qt libraries
remain replaceable, which the AppImage layout preserves); faster-whisper is MIT,
CTranslate2 is MIT, Whisper models are MIT. Keep the third-party license notices.
