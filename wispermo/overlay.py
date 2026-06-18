"""Floating 'pill' overlay — the signature dictation indicator.

Frameless, translucent, always-on-top. Shows a live scrolling waveform driven
by the real microphone level while recording, an animated shimmer while
transcribing, and a brief confirmation when done.
"""
from __future__ import annotations

import collections
import math

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget

N_BARS = 26


class Overlay(QWidget):
    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
            | Qt.Tool | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.resize(280, 60)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)

        self._state = "idle"
        self._label = ""
        self._phase = 0.0
        self._target = 0.0
        self._bars = collections.deque([0.06] * N_BARS, maxlen=N_BARS)
        self._elapsed = 0

        self._anim = QTimer(self)
        self._anim.timeout.connect(self._tick)
        self._clock = QTimer(self)
        self._clock.timeout.connect(self._tick_clock)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    # -- public API ----------------------------------------------------
    def show_state(self, state: str, label: str = "", auto_hide_ms: int = 0) -> None:
        self._state = state
        defaults = {"recording": "", "transcribing": "Transcribing…",
                    "done": "Done", "error": "Error", "loading": "Loading…"}
        self._label = label or defaults.get(state, "")
        if state == "recording":
            self._elapsed = 0
            self._bars = collections.deque([0.06] * N_BARS, maxlen=N_BARS)
            self._clock.start(1000)
        else:
            self._clock.stop()
        self._place()
        if not self.isVisible():
            self.show()
        if not self._anim.isActive():
            self._anim.start(33)
        self._hide_timer.stop()
        if auto_hide_ms:
            self._hide_timer.start(auto_hide_ms)

    def set_level(self, level: float) -> None:
        self._target = max(0.04, min(1.0, level))

    def hide(self) -> None:  # type: ignore[override]
        self._anim.stop()
        self._clock.stop()
        super().hide()

    # -- internals -----------------------------------------------------
    def _place(self) -> None:
        try:
            geo = self.screen().availableGeometry()
            self.move(geo.center().x() - self.width() // 2,
                      geo.bottom() - self.height() - 90)
        except Exception:
            pass

    def _tick_clock(self) -> None:
        self._elapsed += 1

    def _tick(self) -> None:
        self._phase += 0.16
        if self._state == "recording":
            # ease current edge bar toward the live target, then scroll
            edge = self._bars[-1]
            edge += (self._target - edge) * 0.5
            self._bars.append(edge)
            self._target *= 0.85  # decay so silence settles down
        self.update()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(6, 6, -6, -6)
        # the HUD is always a dark ink capsule (instrument-grade), independent
        # of the app's light/dark theme, so its paper waveform always reads.
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(18, 18, 17, 236))
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        p.setPen(QPen(QColor(255, 255, 255, 26), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5),
                          rect.height() / 2, rect.height() / 2)

        color = QColor("#FAFAF8")     # paper — monochrome, contrast not hue

        if self._state == "recording":
            self._paint_dot(p, color)
            self._paint_wave(p, color)
            self._paint_time(p)
        elif self._state == "transcribing":
            self._paint_shimmer(p, color)
            self._paint_label(p)
        else:
            self._paint_check(p, color)
            self._paint_label(p)

    def _paint_dot(self, p: QPainter, color: QColor) -> None:
        pulse = 0.5 + 0.5 * math.sin(self._phase * 1.4)
        c = QColor(color); c.setAlphaF(0.5 + 0.5 * pulse)
        p.setPen(Qt.NoPen); p.setBrush(c)
        p.drawEllipse(QRectF(22, self.height() / 2 - 5, 10, 10))

    def _paint_wave(self, p: QPainter, color: QColor) -> None:
        x0, x1 = 44, self.width() - 70
        cy = self.height() / 2
        n = len(self._bars)
        bw = (x1 - x0) / n
        p.setPen(Qt.NoPen); p.setBrush(color)
        for i, lv in enumerate(self._bars):
            h = 4 + lv * 30
            x = x0 + i * bw
            p.drawRoundedRect(QRectF(x, cy - h / 2, bw * 0.55, h), 2, 2)

    def _paint_time(self, p: QPainter) -> None:
        p.setPen(QColor("#9C9C97"))   # steel
        f = QFont(); f.setPointSize(10)
        f.setFamilies(["Berkeley Mono", "JetBrains Mono", "DejaVu Sans Mono"])
        f.setStyleHint(QFont.Monospace)
        p.setFont(f)
        m, s = divmod(self._elapsed, 60)
        p.drawText(QRectF(self.width() - 64, 0, 50, self.height()),
                   Qt.AlignVCenter | Qt.AlignRight, f"{m}:{s:02d}")

    def _paint_shimmer(self, p: QPainter, color: QColor) -> None:
        cx, cy = 34, self.height() / 2
        for i in range(3):
            a = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(self._phase * 2 - i * 0.9))
            c = QColor(color); c.setAlphaF(a)
            p.setPen(Qt.NoPen); p.setBrush(c)
            p.drawEllipse(QRectF(cx - 16 + i * 13, cy - 4, 8, 8))

    def _paint_check(self, p: QPainter, color: QColor) -> None:
        cx, cy = 36, self.height() / 2
        if self._state == "done":
            pen = QPen(color, 3); pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            path = QPainterPath()
            path.moveTo(cx - 7, cy)
            path.lineTo(cx - 2, cy + 6)
            path.lineTo(cx + 8, cy - 6)
            p.drawPath(path)
        else:
            pen = QPen(color, 3); pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.drawLine(cx - 6, cy - 6, cx + 6, cy + 6)
            p.drawLine(cx + 6, cy - 6, cx - 6, cy + 6)

    def _paint_label(self, p: QPainter) -> None:
        p.setPen(QColor("#FAFAF8"))   # paper on the ink capsule
        f = QFont(); f.setPointSize(11); f.setBold(True); p.setFont(f)
        p.drawText(QRectF(58, 0, self.width() - 70, self.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, self._label)
