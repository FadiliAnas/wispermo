"""Desktop integration: GNOME global hotkey, uinput/ydotool status, autostart.

GNOME on Wayland does not allow apps to grab arbitrary global hotkeys, so we
register a GNOME *custom keyboard shortcut* that runs `wispermo-toggle`, which
talks to the running app over a Unix socket.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
KEYPATH = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/wispermo/"
CUSTOM = f"{SCHEMA}.custom-keybinding"

_BIN = Path(__file__).resolve().parent.parent / "bin"


def app_executable() -> str:
    """Command that launches the GUI (AppImage path / frozen exe when bundled)."""
    ai = os.environ.get("APPIMAGE")
    if ai:
        return ai
    if getattr(sys, "frozen", False):       # macOS .app / frozen build
        return sys.executable
    return str(_BIN / "wispermo")


def toggle_command() -> str:
    """Command the GNOME hotkey runs to toggle dictation."""
    ai = os.environ.get("APPIMAGE")
    return f'"{ai}" toggle' if ai else str(_BIN / "wispermo-toggle")


def _gsettings(*args: str) -> str:
    return subprocess.run(["gsettings", *args], capture_output=True, text=True).stdout.strip()


def gnome_available() -> bool:
    return shutil.which("gsettings") is not None


def register_hotkey(command: str, hotkey: str, name: str = "WISPERMO toggle dictation") -> bool:
    """Register/update the GNOME custom shortcut. Returns True on success."""
    if not gnome_available():
        return False
    try:
        existing = _gsettings("get", SCHEMA, "custom-keybindings")
        if KEYPATH not in existing:
            if existing in ("@as []", "[]", ""):
                new = f"['{KEYPATH}']"
            else:
                new = existing[:-1] + f", '{KEYPATH}']"
            _gsettings("set", SCHEMA, "custom-keybindings", new)
        path_schema = f"{CUSTOM}:{KEYPATH}"
        _gsettings("set", path_schema, "name", name)
        _gsettings("set", path_schema, "command", command)
        _gsettings("set", path_schema, "binding", hotkey)
        return True
    except Exception:
        return False


def hotkey_registered() -> bool:
    if not gnome_available():
        return False
    return KEYPATH in _gsettings("get", SCHEMA, "custom-keybindings")


def keybinding_conflict(accel: str) -> str | None:
    """If another app's custom GNOME shortcut already uses `accel`, return its
    name (so we can warn the user). Ignores our own binding."""
    if not gnome_available() or not accel:
        return None
    import ast
    try:
        raw = _gsettings("get", SCHEMA, "custom-keybindings")
        paths = ast.literal_eval(raw) if raw.startswith("[") else []
    except (ValueError, SyntaxError):
        return None
    for pth in paths:
        if "wispermo" in pth:
            continue
        b = _gsettings("get", f"{CUSTOM}:{pth}", "binding").strip().strip("'")
        if b == accel:
            name = _gsettings("get", f"{CUSTOM}:{pth}", "name").strip().strip("'")
            return name or pth.rstrip("/").rsplit("/", 1)[-1]
    return None


# --- ydotool / uinput ------------------------------------------------------
def ydotool_installed() -> bool:
    return shutil.which("ydotool") is not None


def uinput_ready() -> bool:
    """True if /dev/uinput is group-accessible (ydotoold can use it)."""
    p = Path("/dev/uinput")
    if not p.exists():
        return False
    mode = p.stat().st_mode
    return bool(mode & stat.S_IRGRP and mode & stat.S_IWGRP)


def in_input_group() -> bool:
    try:
        return "input" in subprocess.run(["id", "-nG"], capture_output=True, text=True).stdout.split()
    except Exception:
        return False


def ydotoold_running() -> bool:
    return subprocess.run(["pgrep", "-x", "ydotoold"], capture_output=True).returncode == 0


def typing_ready() -> bool:
    return ydotool_installed() and uinput_ready() and in_input_group() and ydotoold_running()


# The udev rule is embedded so the privileged script never has to read a file
# from the AppImage's FUSE mount (which root cannot access).
UINPUT_RULE = ('KERNEL=="uinput", GROUP="input", MODE="0660", '
               'OPTIONS+="static_node=uinput"')


def run_privileged_setup() -> tuple[bool, str]:
    """Install the uinput udev rule + add user to input group, via pkexec."""
    user = os.environ.get("USER", "") or os.environ.get("USERNAME", "")
    script = f"""#!/bin/sh
set -e
cat > /etc/udev/rules.d/60-wispermo-uinput.rules <<'WPRULE'
{UINPUT_RULE}
WPRULE
modprobe uinput || true
udevadm control --reload-rules
udevadm trigger /dev/uinput || true
usermod -aG input '{user}'
chgrp input /dev/uinput 2>/dev/null || true
chmod 0660 /dev/uinput 2>/dev/null || true
"""
    try:
        r = subprocess.run(["pkexec", "sh", "-c", script],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return True, "ok"
        return False, (r.stderr.strip() or "pkexec was cancelled or failed")
    except FileNotFoundError:
        return False, "pkexec not found (install polkit)"


def enable_ydotoold() -> bool:
    try:
        subprocess.run(["systemctl", "--user", "enable", "--now", "ydotoold.service"],
                       check=True, capture_output=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


# --- autostart -------------------------------------------------------------
def autostart_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    d = Path(base) / "autostart"
    d.mkdir(parents=True, exist_ok=True)
    return d / "wispermo.desktop"


def set_autostart(enabled: bool, exec_cmd: str, icon: str = "wispermo") -> None:
    if sys.platform == "darwin":
        _set_autostart_mac(enabled, exec_cmd)
        return
    p = autostart_path()
    if not enabled:
        if p.exists():
            p.unlink()
        return
    p.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=WISPERMO\n"
        f"Exec={exec_cmd}\n"
        f"Icon={icon}\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Comment=Local offline dictation\n"
    )


def _set_autostart_mac(enabled: bool, exec_cmd: str) -> None:
    """Launch-on-login via a LaunchAgent plist."""
    d = Path(os.path.expanduser("~/Library/LaunchAgents"))
    d.mkdir(parents=True, exist_ok=True)
    plist = d / "com.wispermo.app.plist"
    if not enabled:
        if plist.exists():
            plist.unlink()
        return
    plist.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0"><dict>\n'
        '  <key>Label</key><string>com.wispermo.app</string>\n'
        f'  <key>ProgramArguments</key><array><string>{exec_cmd}</string></array>\n'
        '  <key>RunAtLoad</key><true/>\n'
        '</dict></plist>\n'
    )


def list_audio_sources() -> list[tuple[str, str]]:
    """Return (name, description) for available input sources."""
    out = []
    try:
        raw = subprocess.run(["pactl", "list", "short", "sources"],
                            capture_output=True, text=True).stdout
        for line in raw.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and not parts[1].endswith(".monitor"):
                out.append((parts[1], parts[1].split(".")[-1]))
    except Exception:
        pass
    return out
