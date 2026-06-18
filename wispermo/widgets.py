"""Reusable styled widgets for the WISPERMO UI."""
from __future__ import annotations

from PySide6.QtCore import (Property, QEasingCurve, QPropertyAnimation, QSize,
                            Qt, Signal)
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QAbstractButton, QFrame, QHBoxLayout, QLabel,
                               QVBoxLayout, QWidget)

from . import theme


class ToggleSwitch(QAbstractButton):
    """An iOS-style animated on/off switch."""

    def __init__(self, checked: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(46, 26)
        self._offset = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, on: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._offset)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def get_offset(self) -> float:
        return self._offset

    def set_offset(self, v: float) -> None:
        self._offset = v
        self.update()

    offset = Property(float, get_offset, set_offset)

    def sizeHint(self) -> QSize:
        return QSize(46, 26)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(1, 1, -1, -1)
        track_off = QColor(theme.BORDER)
        track_on = QColor(theme.ACCENT)
        track = QColor(
            int(track_off.red() + (track_on.red() - track_off.red()) * self._offset),
            int(track_off.green() + (track_on.green() - track_off.green()) * self._offset),
            int(track_off.blue() + (track_on.blue() - track_off.blue()) * self._offset),
        )
        p.setPen(Qt.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)
        d = r.height() - 6
        x = r.left() + 3 + self._offset * (r.width() - d - 6)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(int(x), r.top() + 3, d, d)


def card() -> QFrame:
    f = QFrame()
    f.setObjectName("card")
    return f


class StatCard(QFrame):
    def __init__(self, value: str, label: str) -> None:
        super().__init__()
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(2)
        self.value = QLabel(value); self.value.setObjectName("statValue")
        self.label = QLabel(label); self.label.setObjectName("statLabel")
        lay.addWidget(self.value)
        lay.addWidget(self.label)

    def set_value(self, v: str) -> None:
        self.value.setText(v)


class ActivityChart(QFrame):
    """A small monochrome 7-day dictation bar chart."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("card")
        self.setMinimumHeight(120)
        self._counts: list[int] = [0] * 7

    def set_data(self, counts: list[int]) -> None:
        self._counts = counts or [0] * 7
        self.update()

    def paintEvent(self, _e) -> None:
        from PySide6.QtGui import QFont, QPainter
        from PySide6.QtCore import QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(18, 16, -18, -16)
        # title
        p.setPen(QColor(theme.MUTED))
        f = QFont(); f.setPointSize(9); f.setBold(True); p.setFont(f)
        p.drawText(r.left(), r.top(), r.width(), 16,
                   Qt.AlignLeft | Qt.AlignVCenter, "LAST 7 DAYS")
        top = r.top() + 22
        floor = r.bottom() - 14
        peak = max(self._counts + [1])
        n = len(self._counts)
        slot = r.width() / n
        bw = min(26, slot * 0.5)
        labels = ["6d", "5d", "4d", "3d", "2d", "1d", "·"]
        for i, c in enumerate(self._counts):
            cx = r.left() + slot * (i + 0.5)
            h = max(3, (c / peak) * (floor - top))
            on = c > 0
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme.TEXT if on else theme.BORDER))
            p.drawRoundedRect(QRectF(cx - bw / 2, floor - h, bw, h), 3, 3)
            p.setPen(QColor(theme.FAINT))
            f2 = QFont(); f2.setPointSize(8); p.setFont(f2)
            p.drawText(QRectF(cx - slot / 2, floor + 1, slot, 12),
                       Qt.AlignCenter, labels[i] if i < len(labels) else "")


class NavButton(QAbstractButton):
    """Sidebar navigation item: icon + label, with a selected state."""

    def __init__(self, icon_char: str, label: str) -> None:
        super().__init__()
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(44)
        self._icon = icon_char
        self._label = label

    def sizeHint(self) -> QSize:
        return QSize(190, 44)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = self.rect().adjusted(8, 4, -8, -4)
        if self.isChecked():
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme.ACCENT))
            p.drawRoundedRect(r, 12, 12)
            fg = QColor("#FFFFFF")
        elif self.underMouse():
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme.SURFACE2))
            p.drawRoundedRect(r, 12, 12)
            fg = QColor(theme.TEXT)
        else:
            fg = QColor(theme.MUTED)
        p.setPen(fg)
        f = self.font(); f.setPointSize(13); p.setFont(f)
        p.drawText(r.adjusted(14, 0, 0, 0), Qt.AlignVCenter | Qt.AlignLeft,
                   f"{self._icon}   {self._label}")


class FieldRow(QWidget):
    """A settings row: title + description on the left, control on the right."""

    def __init__(self, title: str, description: str, control: QWidget) -> None:
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 8)
        text = QVBoxLayout(); text.setSpacing(1)
        t = QLabel(title); t.setStyleSheet("font-weight:600;")
        d = QLabel(description); d.setObjectName("muted"); d.setWordWrap(True)
        text.addWidget(t); text.addWidget(d)
        lay.addLayout(text, 1)
        lay.addWidget(control, 0, Qt.AlignRight | Qt.AlignVCenter)
