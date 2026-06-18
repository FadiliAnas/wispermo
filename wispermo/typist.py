"""Deliver transcribed text to the focused window.

Strategies:
  paste     -> wl-copy to clipboard, then simulate Ctrl+V via ydotool (default)
  type      -> ydotool types each character
  clipboard -> only copy to clipboard; the user pastes manually
"""
from __future__ import annotations

import subprocess


class TypistError(Exception):
    pass


def _wl_copy(text: str) -> bool:
    try:
        subprocess.run(["wl-copy", "--", text], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        # fall back to xclip on X11
        try:
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(),
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False


def _ydotool(args: list[str]) -> tuple[bool, str]:
    try:
        r = subprocess.run(["ydotool", *args], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return True, ""
    except FileNotFoundError:
        return False, "ydotool not installed"
    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode(errors="replace").strip() or "ydotool failed"


def _pbcopy(text: str) -> bool:
    try:
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _mac_deliver(text: str, mode: str, type_delay_ms: int) -> str:
    """macOS delivery: pbcopy clipboard, Cmd+V paste, or pynput typing effect."""
    if mode == "clipboard":
        if _pbcopy(text):
            return "copied to clipboard"
        raise TypistError("could not copy to clipboard")

    if mode == "type":
        try:
            from pynput.keyboard import Controller
            import time
            kb = Controller()
            delay = max(0, int(type_delay_ms)) / 1000.0
            for ch in text:
                kb.type(ch)
                if delay:
                    time.sleep(delay)
            return "typed"
        except Exception as e:  # noqa: BLE001 — needs Accessibility permission
            if _pbcopy(text):
                return f"typing failed ({e}); copied to clipboard"
            raise TypistError(str(e))

    # paste: pbcopy then Cmd+V via AppleScript (needs Accessibility permission)
    if not _pbcopy(text):
        raise TypistError("could not copy to clipboard")
    try:
        subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to keystroke "v" using command down'],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return "pasted"
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        return "auto-paste needs Accessibility permission — text is on the clipboard"


def deliver(text: str, mode: str = "paste", type_delay_ms: int = 6) -> str:
    """Deliver `text`; returns a short human-readable status string.

    Raises TypistError if nothing could be delivered.
    """
    if not text:
        return "empty"

    from .osplat import IS_MAC
    if IS_MAC:
        return _mac_deliver(text, mode, type_delay_ms)

    if mode == "clipboard":
        if _wl_copy(text):
            return "copied to clipboard"
        raise TypistError("could not copy to clipboard")

    if mode == "type":
        # types character-by-character — a fast "writing" effect. key-delay is
        # the per-character delay in ms (smaller = faster).
        delay = str(max(0, int(type_delay_ms)))
        ok, err = _ydotool(["type", "--key-delay", delay, "--", text])
        if ok:
            return "typed"
        if _wl_copy(text):
            return f"typing failed ({err}); copied to clipboard"
        raise TypistError(err)

    # default: paste (clipboard + Ctrl+V)
    if not _wl_copy(text):
        raise TypistError("could not copy to clipboard")
    # keycodes: 29=LEFTCTRL, 47=V  (down then up)
    ok, err = _ydotool(["key", "29:1", "47:1", "47:0", "29:0"])
    if ok:
        return "pasted"
    return f"auto-paste failed ({err}); text is on the clipboard"
