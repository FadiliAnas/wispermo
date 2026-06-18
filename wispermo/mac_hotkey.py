"""macOS global hotkey listener using pynput (CoreGraphics event tap).

Same interface as the Linux evdev HotkeyListener: on_press fires when the chord
goes down, on_release when the main key comes up (push-to-talk). Requires the
app to be granted Accessibility + Input Monitoring permission on macOS.
"""
from __future__ import annotations

import threading


def _normalize(key):
    """A hashable, comparable token for a pynput key."""
    char = getattr(key, "char", None)
    if char:
        return ("c", char.lower())
    return ("k", key)


def _named_key(token: str):
    from pynput import keyboard as kb
    mapping = {
        "space": kb.Key.space, "return": kb.Key.enter, "tab": kb.Key.tab,
        "escape": kb.Key.esc, "backspace": kb.Key.backspace,
        "end": kb.Key.end, "home": kb.Key.home,
        "page_up": kb.Key.page_up, "page_down": kb.Key.page_down,
        "delete": kb.Key.delete, "insert": kb.Key.insert,
        "up": kb.Key.up, "down": kb.Key.down, "left": kb.Key.left, "right": kb.Key.right,
    }
    for i in range(1, 13):
        mapping[f"f{i}"] = getattr(kb.Key, f"f{i}")
    return mapping.get(token)


def _parse(accel: str):
    """'<Ctrl><Alt>d' -> (list of modifier-key-sets, main-key-token)."""
    from pynput import keyboard as kb
    mods_def = {
        "<Ctrl>": {kb.Key.ctrl, kb.Key.ctrl_l, kb.Key.ctrl_r},
        "<Primary>": {kb.Key.ctrl, kb.Key.ctrl_l, kb.Key.ctrl_r},
        "<Alt>": {kb.Key.alt, kb.Key.alt_l, kb.Key.alt_r},
        "<Shift>": {kb.Key.shift, kb.Key.shift_l, kb.Key.shift_r},
        "<Super>": {kb.Key.cmd, kb.Key.cmd_l, kb.Key.cmd_r},  # Command on macOS
    }
    rest = accel
    groups = []
    for tok, keys in mods_def.items():
        if tok in rest:
            groups.append({_normalize(k) for k in keys})
            rest = rest.replace(tok, "")
    token = rest.strip()
    if len(token) == 1:
        main = ("c", token.lower())
    else:
        k = _named_key(token.lower())
        main = _normalize(k) if k is not None else None
    return groups, main


class MacHotkeyListener:
    def __init__(self, accel: str, on_press, on_release=None) -> None:
        self.on_press = on_press
        self.on_release = on_release
        self._listener = None
        self._down = set()
        self._active = False
        self._lock = threading.Lock()
        self.set_accel(accel)

    def set_accel(self, accel: str) -> None:
        with self._lock:
            self._mods, self._main = _parse(accel)
            self._active = False
            self._down.clear()

    def start(self) -> None:
        from pynput import keyboard as kb
        self._listener = kb.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.daemon = True
        self._listener.start()

    def stop(self) -> None:
        if self._listener:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None

    def _mods_ok(self) -> bool:
        return all(any(m in self._down for m in group) for group in self._mods)

    def _on_press(self, key) -> None:
        nk = _normalize(key)
        self._down.add(nk)
        with self._lock:
            main, active = self._main, self._active
        if main and nk == main and not active and self._mods_ok():
            with self._lock:
                self._active = True
            self._safe(self.on_press)

    def _on_release(self, key) -> None:
        nk = _normalize(key)
        self._down.discard(nk)
        with self._lock:
            main, active = self._main, self._active
        if main and nk == main and active:
            with self._lock:
                self._active = False
            if self.on_release:
                self._safe(self.on_release)

    @staticmethod
    def _safe(fn) -> None:
        try:
            fn()
        except Exception:
            pass


def can_listen() -> bool:
    try:
        import pynput  # noqa: F401
        return True
    except Exception:
        return False
