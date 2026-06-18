"""Convert between Qt key sequences and GNOME accelerator strings.

The tricky part is the key NAME: GNOME/GTK accelerators use exact GDK keysym
names (``End``, ``Page_Up``, ``space``, ``F9``…). Qt's display names differ
(``Del``, ``PgUp``, ``Space``, ``Esc``) and must be mapped, or the binding is
silently invalid and the shortcut never fires.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

# Qt display name -> GDK/GNOME keysym name
_KEYMAP = {
    "Space": "space",
    "Page Up": "Page_Up", "PgUp": "Page_Up",
    "Page Down": "Page_Down", "PgDown": "Page_Down",
    "Del": "Delete", "Ins": "Insert",
    "Esc": "Escape", "Return": "Return", "Enter": "Return",
    "Backspace": "BackSpace", "Tab": "Tab",
    "Home": "Home", "End": "End",
    "Up": "Up", "Down": "Down", "Left": "Left", "Right": "Right",
    "Print": "Print", "ScrollLock": "Scroll_Lock", "Pause": "Pause",
}


def _gnome_key(qt_key: int) -> str:
    name = QKeySequence(qt_key).toString()
    if not name:
        return ""
    if len(name) == 1:           # letters / digits / punctuation
        return name.lower()
    if name in _KEYMAP:
        return _KEYMAP[name]
    return name.replace(" ", "_")  # F-keys stay "F9", etc.


def qt_to_gnome(seq: QKeySequence) -> str:
    """'Ctrl+Alt+D' -> '<Ctrl><Alt>d'  (GNOME gsettings accelerator format)."""
    if seq.isEmpty():
        return ""
    combo = seq[0]  # QKeyCombination in PySide6 >= 6.x
    if hasattr(combo, "keyboardModifiers"):
        mods = combo.keyboardModifiers()
        key = int(combo.key())
    else:  # very old binding: plain int with modifier bits packed in
        packed = int(combo)
        mods = Qt.KeyboardModifier(packed & int(Qt.KeyboardModifierMask))
        key = packed & ~int(Qt.KeyboardModifierMask)

    parts = []
    if mods & Qt.ControlModifier:
        parts.append("<Ctrl>")
    if mods & Qt.AltModifier:
        parts.append("<Alt>")
    if mods & Qt.ShiftModifier:
        parts.append("<Shift>")
    if mods & Qt.MetaModifier:
        parts.append("<Super>")

    name = _gnome_key(key)
    if not name:
        return ""
    return "".join(parts) + name


def gnome_to_display(accel: str) -> str:
    """'<Ctrl><Alt>d' -> 'Ctrl+Alt+D' for showing in the UI."""
    if not accel:
        return "(none)"
    out = accel.replace("<", "").replace(">", "+").replace("Primary+", "Ctrl+")
    if "+" in out:
        head, _, tail = out.rpartition("+")
        tail = tail.replace("_", " ")
        tail = tail.upper() if len(tail) == 1 else tail
        return f"{head}+{tail}"
    return out.upper() if len(out) == 1 else out
