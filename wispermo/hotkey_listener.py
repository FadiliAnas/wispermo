"""Global hotkey listener that reads /dev/input directly (pure Python).

GNOME/Wayland custom shortcuts are unreliable, so instead of depending on them
we watch the kernel's evdev keyboard stream ourselves. Requires membership in
the ``input`` group (already needed for ydotool). Works on Wayland and X11,
independent of the desktop environment.

We only *monitor* (never grab) the devices, so keystrokes still reach apps.
"""
from __future__ import annotations

import glob
import os
import selectors
import struct
import threading

EV_KEY = 0x01
_EVENT = struct.Struct("llHHi")        # input_event on 64-bit Linux (24 bytes)

# modifier name -> acceptable keycodes (left/right)
_MODS = {
    "<Ctrl>": {29, 97}, "<Primary>": {29, 97},
    "<Alt>": {56, 100},
    "<Shift>": {42, 54},
    "<Super>": {125, 126},
}

# GNOME accel key token (lowercased) -> Linux input keycode
_KEYS = {
    "a": 30, "b": 48, "c": 46, "d": 32, "e": 18, "f": 33, "g": 34, "h": 35,
    "i": 23, "j": 36, "k": 37, "l": 38, "m": 50, "n": 49, "o": 24, "p": 25,
    "q": 16, "r": 19, "s": 31, "t": 20, "u": 22, "v": 47, "w": 17, "x": 45,
    "y": 21, "z": 44,
    "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9, "9": 10, "0": 11,
    "space": 57, "return": 28, "tab": 15, "escape": 1, "backspace": 14,
    "end": 107, "home": 102, "page_up": 104, "page_down": 109,
    "delete": 111, "insert": 110, "up": 103, "down": 108, "left": 105, "right": 106,
    "pause": 119, "print": 99, "scroll_lock": 70,
    "f1": 59, "f2": 60, "f3": 61, "f4": 62, "f5": 63, "f6": 64, "f7": 65,
    "f8": 66, "f9": 67, "f10": 68, "f11": 87, "f12": 88,
    "/": 53, ".": 52, ",": 51, ";": 39, "-": 12, "=": 13, "`": 41,
    "\\": 43, "[": 26, "]": 27, "'": 40,
}


def parse_accel(accel: str) -> tuple[list[set[int]], int | None]:
    """'<Ctrl><Alt>d' -> ([{29,97},{56,100}], 32)."""
    mods: list[set[int]] = []
    rest = accel
    for tok, codes in _MODS.items():
        if tok in rest:
            mods.append(codes)
            rest = rest.replace(tok, "")
    key = _KEYS.get(rest.strip().lower())
    return mods, key


def can_listen() -> bool:
    for path in glob.glob("/dev/input/event*"):
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            os.close(fd)
            return True
        except OSError:
            continue
    return False


class HotkeyListener(threading.Thread):
    def __init__(self, accel: str, on_press, on_release=None) -> None:
        super().__init__(daemon=True)
        self.on_press = on_press
        self.on_release = on_release
        self._stop = threading.Event()
        self._pressed: set[int] = set()
        self._active = False          # hotkey chord currently held
        self._lock = threading.Lock()
        self.set_accel(accel)

    def set_accel(self, accel: str) -> None:
        with self._lock:
            self.mods, self.key = parse_accel(accel)
            self._active = False
            self._pressed.clear()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        sel = selectors.DefaultSelector()
        fds: list[int] = []
        for path in sorted(glob.glob("/dev/input/event*")):
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
                sel.register(fd, selectors.EVENT_READ)
                fds.append(fd)
            except OSError:
                continue
        if not fds:
            return
        try:
            while not self._stop.is_set():
                for key, _ in sel.select(timeout=0.5):
                    self._drain(key.fd)
        finally:
            for fd in fds:
                try:
                    os.close(fd)
                except OSError:
                    pass

    def _drain(self, fd: int) -> None:
        try:
            data = os.read(fd, _EVENT.size * 64)
        except (OSError, BlockingIOError):
            return
        for off in range(0, len(data) - _EVENT.size + 1, _EVENT.size):
            _, _, etype, code, val = _EVENT.unpack_from(data, off)
            if etype != EV_KEY:
                continue
            if val == 1:                       # key down
                self._pressed.add(code)
                self._press(code)
            elif val == 0:                     # key up
                self._pressed.discard(code)
                self._release(code)
            # val == 2 (auto-repeat) is ignored

    def _press(self, code: int) -> None:
        with self._lock:
            key, mods, active = self.key, self.mods, self._active
        if not key or code != key or active:
            return
        if all(any(c in self._pressed for c in mset) for mset in mods):
            with self._lock:
                self._active = True
            self._safe(self.on_press)

    def _release(self, code: int) -> None:
        with self._lock:
            key, active = self.key, self._active
        # the chord ends when the main key is released
        if not active or code != key:
            return
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
