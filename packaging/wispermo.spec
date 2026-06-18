# PyInstaller spec for WISPERMO (onedir, bundled into an AppImage afterwards).
import os
from PyInstaller.utils.hooks import collect_all

PROJECT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas, binaries, hiddenimports = [], [], []
for pkg in ("faster_whisper", "ctranslate2", "av", "tokenizers",
            "onnxruntime", "huggingface_hub"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# ship the project's setup data (uinput udev rule) for the onboarding wizard
datas += [(os.path.join(PROJECT, "setup", "60-wispermo-uinput.rules"), "setup")]

a = Analysis(
    [os.path.join(SPECPATH, "entry.py")],
    pathex=[PROJECT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports + ["wispermo", "wispermo.app"],
    excludes=[
        "tkinter", "matplotlib", "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets", "PySide6.QtQuick3D", "PySide6.Qt3DCore",
        "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtMultimedia",
        "PySide6.QtPdf", "PySide6.QtPositioning", "PySide6.QtSensors",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="wispermo",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False,
    upx=False,
    name="wispermo",
)
