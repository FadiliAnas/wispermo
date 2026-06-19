"""A small always-on-top, draggable mic button to start/stop dictation.

On GNOME/Wayland the compositor controls window placement, so the button
appears floating and the user drags it where they like (we remember the spot
best-effort). Click toggles recording.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

SIZE = 56


class MiniButton(QWidget):
    clicked = Signal()

    def __init__(self) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint
            | Qt.Tool | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(SIZE, SIZE)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Click to dictate · drag to move")

        self._state = "idle"
        self._phase = 0.0
        self._press_pos: QPoint | None = None
        self._moved = False

        self._pulse = QTimer(self)
        self._pulse.timeout.connect(self._tick)

    def set_state(self, state: str) -> None:
        self._state = state
        if state == "recording":
            if not self._pulse.isActive():
                self._pulse.start(40)
        else:
            self._pulse.stop()
        self.update()

    def _tick(self) -> None:
        self._phase += 0.12
        self.update()

    # -- placement -----------------------------------------------------
    def place(self, pos) -> None:
        if pos and len(pos) == 2:
            self.move(int(pos[0]), int(pos[1]))
        else:
            try:
                geo = self.screen().availableGeometry()
                self.move(geo.left() + 24, geo.center().y() - SIZE // 2)
            except Exception:
                pass

    # -- drag + click --------------------------------------------------
    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.LeftButton:
            self._press_pos = e.globalPosition().toPoint()
            self._moved = False

    def mouseMoveEvent(self, e) -> None:
        if self._press_pos is None:
            return
        delta = e.globalPosition().toPoint() - self._press_pos
        if delta.manhattanLength() > 4:
            self._moved = True
            handle = self.windowHandle()
            if handle is not None:
                handle.startSystemMove()        # Wayland-friendly drag

    def mouseReleaseEvent(self, e) -> None:
        if e.button() == Qt.LeftButton and self._press_pos is not None:
            if not self._moved:
                self.clicked.emit()
            self._press_pos = None

    def current_pos(self) -> list[int]:
        return [self.x(), self.y()]

    # -- paint ---------------------------------------------------------
    def paintEvent(self, _e) -> None:
        # monochrome: always an ink circle with a paper glyph. Recording is
        # expressed with a pulsing paper ring (motion + contrast), not colour.
        INK = QColor("#121211")
        PAPER = QColor("#FAFAF8")
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(4, 4, SIZE - 8, SIZE - 8)
        rec = self._state == "recording"

        if rec:
            pulse = 0.5 + 0.5 * math.sin(self._phase)
            ring = QColor(PAPER); ring.setAlphaF(0.18 + 0.22 * pulse)
            p.setPen(Qt.NoPen); p.setBrush(ring)
            grow = 5 * pulse
            p.drawEllipse(r.adjusted(-grow, -grow, grow, grow))

        p.setPen(Qt.NoPen); p.setBrush(INK)
        p.drawEllipse(r)

        cx, cy = r.center().x(), r.center().y()
        if rec:
            # stop square
            p.setBrush(PAPER); p.setPen(Qt.NoPen)
            p.drawRoundedRect(QRectF(cx - 8, cy - 8, 16, 16), 3, 3)
        else:
            # mic glyph (paper)
            p.setPen(Qt.NoPen); p.setBrush(PAPER)
            p.drawRoundedRect(QRectF(cx - 5, r.top() + 12, 10, 16), 5, 5)
            pen = QPen(PAPER, 2.4); pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen); p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(cx - 9, r.top() + 12, 18, 20), 200 * 16, 140 * 16)
            p.drawLine(int(cx), int(r.top() + 32), int(cx), int(r.top() + 38))
