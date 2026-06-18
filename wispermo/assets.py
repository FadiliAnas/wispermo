"""Branding: an embedded SVG logo rendered crisply at any size (no external
files, so it works the same from source and inside the frozen AppImage).

- `app_logo()` / `export_png()` -> the full product logo (gradient tile + mic)
- `state_icon(state)` -> a mic glyph tinted by state, for the tray/overlay
"""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

WHITE = QColor("#FFFFFF")

# Brand mark: the text caret "|" fused with a voice ripple. Monochrome,
# instrument-grade. Ink tile + paper mark (works on any background).
INK_HEX = "#121211"
PAPER_HEX = "#FAFAF8"

_LOGO_SVG = f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect x="4" y="4" width="120" height="120" rx="28" fill="{INK_HEX}"/>
  <rect x="40" y="36" width="13" height="56" rx="6.5" fill="{PAPER_HEX}"/>
  <path d="M68 46 q 18 18 0 36" fill="none" stroke="{PAPER_HEX}"
        stroke-width="10" stroke-linecap="round"/>
  <path d="M85 38 q 27 26 0 52" fill="none" stroke="{PAPER_HEX}"
        stroke-width="10" stroke-linecap="round" opacity="0.45"/>
</svg>
"""

# Mic-only glyph; COLOR is substituted per state.
_MIC_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect x="49" y="20" width="30" height="56" rx="15" fill="COLOR"/>
  <g fill="none" stroke="COLOR" stroke-width="9" stroke-linecap="round">
    <path d="M34 60 a30 30 0 0 0 60 0"/>
    <line x1="64" y1="90" x2="64" y2="106"/>
    <line x1="46" y1="106" x2="82" y2="106"/>
  </g>
</svg>
"""


def _render(svg: str, size: int) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(p, QRectF(0, 0, size, size))
    p.end()
    return pm


def app_logo(size: int = 256) -> QPixmap:
    return _render(_LOGO_SVG, size)


def state_icon(state: str = "idle", size: int = 128) -> QIcon:
    # window / tray icon = the brand mark (monochrome, state-independent)
    return QIcon(_render(_LOGO_SVG, size))


def mic_pixmap(color: str = "#FFFFFF", size: int = 128) -> QPixmap:
    return _render(_MIC_SVG.replace("COLOR", color), size)


def mic_icon(color: str = "#FFFFFF", size: int = 128) -> QIcon:
    return QIcon(mic_pixmap(color, size))


_STOP_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect x="34" y="34" width="60" height="60" rx="14" fill="COLOR"/>
</svg>
"""


def stop_icon(color: str = "#FFFFFF", size: int = 128) -> QIcon:
    return QIcon(_render(_STOP_SVG.replace("COLOR", color), size))


def export_png(path: str, size: int = 256) -> None:
    app_logo(size).save(path, "PNG")
