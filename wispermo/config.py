"""Persistent configuration for WISPERMO.

Settings live in a JSON file under ~/.config/wispermo/config.json and are edited
through the Settings window. Environment variables of the form WISPERMO_<KEY>
still override the stored value (handy for testing/power users).

Defaults are tuned for a CPU-only laptop so the app works out of the box.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "WISPERMO"
APP_ID = "wispermo"


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    d = Path(base) / APP_ID
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_dir() -> Path:
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    d = Path(base) / APP_ID
    d.mkdir(parents=True, exist_ok=True)
    return d


def runtime_dir() -> str:
    return os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"


def socket_path() -> str:
    return os.path.join(runtime_dir(), "wispermo.sock")


CONFIG_FILE = config_dir() / "config.json"

# key -> (default, type, env-override-name)
DEFAULTS: dict[str, object] = {
    "model": "base",            # tiny/base/small/medium/large-v3
    "language": "",             # "" = auto-detect; else en/fr/ar/...
    "device": "cpu",            # or "cuda"
    "compute_type": "int8",     # int8 / int8_float32 / float32
    "output": "paste",          # paste / type / clipboard
    "type_delay_ms": 6,         # per-char delay for the "type" writing effect
    "audio_source": "default",  # pactl source name
    "beep": True,
    "notify": True,
    "vad": True,
    "hotkey": "<Ctrl><Alt>d",   # GNOME accelerator syntax
    "hotkey_mode": "ptt",       # ptt (hold to talk) | toggle (press on/off)
    "autostart": True,
    "onboarded": False,
    "keep_history": True,
    "max_history": 200,
    # recognition tuning
    "accuracy": "balanced",     # fast / balanced / accurate  -> beam size
    "vocabulary": "",           # names/terms to bias recognition toward
    "reduce_hallucination": True,  # suppress phantom words on silence/noise
    # text post-processing
    "formatting": True,         # tidy capitalisation/spacing
    "smart_format": True,       # voice commands, lists, bullets, email shaping
    "trailing_space": True,     # add a space after inserted text
    "remove_fillers": False,    # drop um/uh/er…
    "dictionary": {},           # {spoken phrase: written form}
    # floating mic button
    "show_mini_button": True,
    "mini_button_pos": [],      # [x, y] best-effort remembered position
    # appearance
    "appearance": "light",      # light / dark
}


class Config:
    def __init__(self) -> None:
        self._data: dict[str, object] = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        if CONFIG_FILE.exists():
            try:
                stored = json.loads(CONFIG_FILE.read_text())
                self._data.update({k: v for k, v in stored.items() if k in DEFAULTS})
            except (json.JSONDecodeError, OSError):
                pass

    def save(self) -> None:
        CONFIG_FILE.write_text(json.dumps(self._data, indent=2))

    def get(self, key: str):
        env = os.environ.get(f"WISPERMO_{key.upper()}")
        if env is not None:
            default = DEFAULTS[key]
            if isinstance(default, bool):
                return env not in ("0", "false", "False", "")
            return env
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value) -> None:
        if key in DEFAULTS:
            self._data[key] = value

    def __getitem__(self, key):
        return self.get(key)

    def as_dict(self) -> dict:
        return {k: self.get(k) for k in DEFAULTS}


# module-level singleton
config = Config()
