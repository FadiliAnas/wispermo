"""Locate resources bundled inside the AppImage (ffmpeg, speech model).

The AppImage runtime sets $APPDIR to the mount root. When present we prefer the
bundled copies so the app needs no system packages and no model download —
truly click-to-run. Falls back to system tools / online download otherwise.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _appdir() -> Path | None:
    d = os.environ.get("APPDIR")
    return Path(d) if d else None


def _meipass() -> Path | None:
    """PyInstaller bundle root (set in frozen builds, incl. the macOS .app)."""
    p = getattr(sys, "_MEIPASS", None)
    return Path(p) if p else None


def ffmpeg() -> str:
    """Path to a usable ffmpeg — bundled build if present, else PATH."""
    for base, rel in ((_appdir(), "usr/bin"), (_meipass(), "")):
        if base:
            for name in ("ffmpeg", "ffmpeg-static"):
                p = base / rel / name if rel else base / name
                if p.exists():
                    return str(p)
    return "ffmpeg"


def model_path(name: str) -> str:
    """Local bundled model dir for `name` if present, else the name itself
    (which faster-whisper will download on first use)."""
    candidates = []
    d = _appdir()
    if d:
        candidates.append(d / "usr" / "share" / "wispermo" / "models" / name)
    m = _meipass()
    if m:
        candidates.append(m / "models" / name)        # macOS .app / frozen
    for c in candidates:
        if (c / "model.bin").exists():
            return str(c)
    return name
