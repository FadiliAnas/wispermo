# PyInstaller spec for WISPERMO on macOS (Apple Silicon / arm64).
# Produces dist/WISPERMO.app — build-macos.sh wraps it into a drag-to-install .dmg.
import os
from PyInstaller.utils.hooks import collect_all

PROJECT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas, binaries, hiddenimports = [], [], []
for pkg in ("faster_whisper", "ctranslate2", "av", "tokenizers", "onnxruntime",
            "huggingface_hub", "sounddevice", "pynput"):
    try:
        d, b, h = collect_all(pkg)
        datas += d; binaries += b; hiddenimports += h
    except Exception:
        pass

# bundled speech model (populated by build-macos.sh -> offline, no download)
MODEL = os.path.join(SPECPATH, "macos-model", "base")
if os.path.exists(os.path.join(MODEL, "model.bin")):
    datas += [(MODEL, "models/base")]

ICON = os.path.join(SPECPATH, "wispermo.icns")
icon = ICON if os.path.exists(ICON) else None

a = Analysis(
    [os.path.join(SPECPATH, "entry.py")],
    pathex=[PROJECT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + [
        "wispermo", "wispermo.app", "sounddevice",
        "pynput", "pynput.keyboard", "pynput.mouse",
    ],
    excludes=[
        "tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
        "PySide6.QtQuick3D", "PySide6.Qt3DCore", "PySide6.QtCharts",
        "PySide6.QtDataVisualization", "PySide6.QtMultimedia", "PySide6.QtPdf",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="WISPERMO",
          console=False, target_arch="arm64", icon=icon)
coll = COLLECT(exe, a.binaries, a.datas, name="WISPERMO")
app = BUNDLE(
    coll,
    name="WISPERMO.app",
    icon=icon,
    bundle_identifier="com.wispermo.app",
    info_plist={
        "CFBundleName": "WISPERMO",
        "CFBundleDisplayName": "WISPERMO",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        # permission prompts shown to the user on first use
        "NSMicrophoneUsageDescription":
            "WISPERMO transcribes your speech on-device.",
        "NSAppleEventsUsageDescription":
            "WISPERMO types your transcribed text into the focused app.",
        "NSInputMonitoringUsageDescription":
            "WISPERMO listens for your dictation hotkey.",
    },
)
