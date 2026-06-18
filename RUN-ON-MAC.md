# Running WISPERMO on your Mac (mini M4) — full step-by-step

This guide takes you from zero to a working **WISPERMO.app** installed in
Applications, the Chrome-style way (build a `.dmg`, drag into Applications).

> A macOS app must be built **on a Mac** — it can't be made on Linux. So you
> run one build command on the Mac; it handles everything (installs tools,
> bundles the speech model, makes the `.dmg`).

---

## A. Get the project onto the Mac

Pick **one** of these.

### Option 1 — from GitHub (once it's pushed)
```bash
cd ~/Downloads
git clone https://github.com/FadiliAnas/wispermo.git
cd wispermo
```

### Option 2 — from a zip (no GitHub needed)
On the **Linux** machine, make a clean zip:
```bash
cd ~/Work/WISPERMO
zip -r ~/wispermo-src.zip . \
  -x '.venv/*' '.venv-macos/*' '*.AppImage' \
     'packaging/build/*' 'packaging/dist/*' 'packaging/ffmpeg-static/*' '.git/*'
```
AirDrop / USB `wispermo-src.zip` to the Mac, then on the **Mac**:
```bash
cd ~/Downloads
unzip wispermo-src.zip -d wispermo
cd wispermo
```

> ✅ Check you're in the right place: `ls packaging/build-macos.sh` should list the file.

---

## B. Build the app (one command)

```bash
./packaging/build-macos.sh
```

What it does automatically (no setup needed beforehand):
1. installs **Homebrew** + **Python** if missing (asks your password once),
2. creates a virtualenv and installs dependencies,
3. downloads the speech model **once** and **bundles it** (so the app is offline),
4. generates the app icon,
5. builds **WISPERMO.app** (Apple Silicon / arm64),
6. produces **`WISPERMO.dmg`** in the project folder.

First build takes a while (downloads ~a few hundred MB of Python packages). Later
builds are fast.

> **If it errors:** copy the last ~20 lines of output and send them to me — Mac
> packaging (PyInstaller + pynput/pyobjc) sometimes needs a small fix. This is
> expected on the first try.

---

## C. Install it

1. Double-click **`WISPERMO.dmg`**.
2. In the window that opens, **drag the WISPERMO icon onto the Applications folder.**
3. Eject the disk image. WISPERMO is now in **Applications / Launchpad**.

---

## D. First launch + permissions (important)

Because the app isn't notarized by Apple yet, the **first** launch needs:

1. In **Applications**, **right-click WISPERMO → Open** → click **Open** in the
   dialog. (Only needed once. After that, double-click normally.)

Then grant these when macOS prompts (or in **System Settings ▸ Privacy & Security**):

| Permission | What it's for |
|---|---|
| **Microphone** | record your voice |
| **Accessibility** | type / paste text into other apps |
| **Input Monitoring** | detect your dictation hotkey |

After enabling **Accessibility** and **Input Monitoring**, **quit WISPERMO and
reopen it** so they take effect.

---

## E. Use it

- **Push-to-talk:** hold your hotkey, speak, release → the text is typed where
  your cursor is.
- Change the hotkey, switch to toggle mode, pick the writing-effect output, etc.
  in **WISPERMO ▸ Settings ▸ General / Output**.
- On macOS the default Super/Command-based combos work well; pick whatever's free.

---

## F. Quick alternative — run from source (no .app, for testing)

If you just want to try it fast without building the `.dmg`:
```bash
cd wispermo
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-macos.txt
python -m wispermo.app
```
Grant the same 3 permissions to **Terminal** (or your Python) when prompted.

---

## G. Troubleshooting

- **"requirements-macos.txt not found"** → you're not inside the project folder.
  `cd` into the folder that contains `packaging/` and re-run.
- **"command not found: python3"** → re-run the build script; it installs Python
  via Homebrew. Or `brew install python`.
- **App opens but no text appears** → grant **Accessibility**, then quit/reopen.
- **Hotkey does nothing** → grant **Input Monitoring**, then quit/reopen.
- **No audio / empty transcripts** → grant **Microphone**.
- **"WISPERMO is damaged/can't be opened"** → Gatekeeper. Run once:
  `xattr -dr com.apple.quarantine /Applications/WISPERMO.app` then open it.

---

## H. Make it open with zero warnings for anyone (optional)

That requires signing + notarizing with a paid **Apple Developer account ($99/yr)**.
Once you have it, tell me and I'll wire notarization into the build so the `.dmg`
opens cleanly on any Mac with no right-click step.
