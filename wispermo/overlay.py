"""Floating dictation indicator — a clean Wispr-Flow-style voice rendering.

A small dark pill containing a live waveform. It shows while recording (driven
by the real mic level) and keeps a gentle "processing" motion while the model
runs, then simply disappears — no text, no timer, no drop shadow.
"""
from __future__ import annotations

import collections
import math

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

N_BARS = 28
PAPER = "#FAFAF8"


class Overlay(QWidget):
    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
            | Qt.Tool | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(216, 52)

        self._state = "idle"
        self._phase = 0.0
        self._target = 0.06
        self._bars = collections.deque([0.06] * N_BARS, maxlen=N_BARS)

        self._anim = QTimer(self)
        self._anim.timeout.connect(self._tick)

    # -- public API ----------------------------------------------------
    def show_state(self, state: str, *_a, **_kw) -> None:
        # Wispr-Flow style: only "recording" and "transcribing" are visible;
        # everything else (done/error/idle) simply hides the pill.
        if state not in ("recording", "transcribing"):
            self.hide()
            return
        if state == "recording" and self._state != "recording":
            self._bars = collections.deque([0.06] * N_BARS, maxlen=N_BARS)
        self._state = state
        self._place()
        if not self.isVisible():
            self.show()
        if not self._anim.isActive():
            self._anim.start(33)

    def set_level(self, level: float) -> None:
        self._target = max(0.05, min(1.0, level))

    def hide(self) -> None:  # type: ignore[override]
        self._anim.stop()
        super().hide()

    # -- internals -----------------------------------------------------
    def _place(self) -> None:
        try:
            geo = self.screen().availableGeometry()
            self.move(geo.center().x() - self.width() // 2,
                      geo.bottom() - self.height() - 90)
        except Exception:
            pass

    def _tick(self) -> None:
        self._phase += 0.18
        if self._state == "recording":
            edge = self._bars[-1]
            edge += (self._target - edge) * 0.5
            self._bars.append(edge)
            self._target *= 0.85          # settle toward quiet when silent
        else:  # transcribing — gentle standing-wave "processing" motion
            n = len(self._bars)
            self._bars = collections.deque(
                (0.16 + 0.20 * (0.5 + 0.5 * math.sin(self._phase * 1.6 + i * 0.5)))
                for i in range(n)
            )
            self._bars = collections.deque(self._bars, maxlen=N_BARS)
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        r = rect.height() / 2
        # flat ink pill — no drop shadow
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(18, 18, 17, 240))
        p.drawRoundedRect(rect, r, r)
        p.setPen(QPen(QColor(255, 255, 255, 20), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), r, r)

        # centred, symmetric voice waveform
        color = QColor(PAPER)
        if self._state == "transcribing":
            color.setAlphaF(0.55)         # subtly dimmed while processing
        x0, x1 = 18.0, self.width() - 18.0
        cy = self.height() / 2
        n = len(self._bars)
        slot = (x1 - x0) / n
        bw = min(4.0, slot * 0.6)
        p.setPen(Qt.NoPen)
        p.setBrush(color)
        for i, lv in enumerate(self._bars):
            h = 3 + lv * 30
            x = x0 + i * slot + (slot - bw) / 2
            p.drawRoundedRect(QRectF(x, cy - h / 2, bw, h), bw / 2, bw / 2)
