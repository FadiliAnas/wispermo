"""Design system — strict warm-neutral monochrome, instrument-grade.

No colour accent: the live/recording state is expressed with motion + contrast.
Two palettes (light = Paper, dark = off-black). Module-level colour constants
are set by apply() so the rest of the app can read e.g. ``theme.ACCENT``.
"""
from __future__ import annotations

from PySide6.QtGui import QColor

from .config import config

# warm-neutral ramp (the token sheet)
PAPER   = "#FAFAF8"
WHITE   = "#FFFFFF"
MIST    = "#F2F2EF"
CLOUD   = "#E6E6E2"
SILVER  = "#CDCDC8"
STEEL   = "#9C9C97"
GRAPHITE = "#5E5E5A"
SLATE   = "#2E2E2C"
INK     = "#121211"
OFFBLACK = "#0C0C0B"

# fonts — named faces first, clean system fallbacks (never Inter)
SANS = '"SF Pro Text", "Söhne", "Neue Montréal", "Cantarell", "Helvetica Neue", sans-serif'
MONO = '"Berkeley Mono", "JetBrains Mono", "Commit Mono", "SF Mono", "DejaVu Sans Mono", monospace'

PALETTES = {
    "light": dict(
        BG=PAPER, SURFACE=WHITE, SURFACE2=MIST, BORDER=CLOUD,
        TEXT=INK, MUTED=GRAPHITE, FAINT=STEEL,
        ACCENT=INK, ACCENT_HI=SLATE, ACCENT_DK=OFFBLACK, ON_ACCENT=PAPER,
    ),
    "dark": dict(
        BG=OFFBLACK, SURFACE="#151514", SURFACE2="#1E1E1C", BORDER=SLATE,
        TEXT=PAPER, MUTED=STEEL, FAINT=GRAPHITE,
        ACCENT=PAPER, ACCENT_HI=CLOUD, ACCENT_DK=SILVER, ON_ACCENT=INK,
    ),
}

# defaults (overwritten by apply); recording/transcribing/done are monochrome —
# differentiation comes from motion, not hue.
BG = SURFACE = SURFACE2 = BORDER = TEXT = MUTED = FAINT = ""
ACCENT = ACCENT_HI = ACCENT_DK = ON_ACCENT = ""
REC = BUSY = OK = ""
_current = "light"


def _set(name: str) -> None:
    global BG, SURFACE, SURFACE2, BORDER, TEXT, MUTED, FAINT
    global ACCENT, ACCENT_HI, ACCENT_DK, ON_ACCENT, REC, BUSY, OK, _current
    p = PALETTES.get(name, PALETTES["light"])
    _current = name if name in PALETTES else "light"
    BG, SURFACE, SURFACE2, BORDER = p["BG"], p["SURFACE"], p["SURFACE2"], p["BORDER"]
    TEXT, MUTED, FAINT = p["TEXT"], p["MUTED"], p["FAINT"]
    ACCENT, ACCENT_HI, ACCENT_DK, ON_ACCENT = p["ACCENT"], p["ACCENT_HI"], p["ACCENT_DK"], p["ON_ACCENT"]
    # state colours = max-contrast ink/paper; motion carries the meaning
    REC = TEXT
    BUSY = MUTED
    OK = TEXT


def current() -> str:
    return _current


def qcolor(hex_: str, a: int = 255) -> QColor:
    c = QColor(hex_); c.setAlpha(a); return c


def _qss() -> str:
    return f"""
* {{ outline: none; }}
QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: {SANS};
    font-size: 13px;
}}
QLabel {{ background: transparent; }}
QToolTip {{
    background: {INK}; color: {PAPER};
    border: none; border-radius: 6px; padding: 5px 9px;
    font-family: {SANS};
}}

QFrame#card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#sidebar {{ background: {SURFACE}; border: none; border-right: 1px solid {BORDER}; }}

QLabel#h1 {{ font-size: 23px; font-weight: 700; letter-spacing: -0.3px; }}
QLabel#h2 {{ font-size: 15px; font-weight: 600; }}
QLabel#muted {{ color: {MUTED}; }}
QLabel#statValue {{ font-family: {MONO}; font-size: 26px; font-weight: 600; color: {TEXT}; }}
QLabel#statLabel {{ color: {MUTED}; font-size: 11px; letter-spacing: 0.4px; text-transform: uppercase; }}
QLabel#mono {{ font-family: {MONO}; color: {MUTED}; }}

QPushButton {{
    background: transparent; color: {TEXT};
    border: 1px solid {BORDER}; border-radius: 9px;
    padding: 9px 16px; font-weight: 500;
}}
QPushButton:hover {{ border-color: {TEXT}; }}
QPushButton#primary {{ background: {ACCENT}; border: none; color: {ON_ACCENT}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {ACCENT_HI}; }}
QPushButton#danger:hover {{ border-color: {TEXT}; color: {TEXT}; }}
QPushButton:disabled {{ color: {FAINT}; border-color: {BORDER}; }}

QLineEdit, QComboBox, QPlainTextEdit {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 9px; padding: 8px 10px; color: {TEXT};
    selection-background-color: {ACCENT}; selection-color: {ON_ACCENT};
}}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus {{ border-color: {TEXT}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {SURFACE}; border: 1px solid {BORDER};
    selection-background-color: {ACCENT}; selection-color: {ON_ACCENT};
    outline: none; border-radius: 8px;
}}
QKeySequenceEdit QLineEdit {{ font-family: {MONO}; font-weight: 600; }}

QListWidget {{ background: transparent; border: none; }}
QListWidget::item {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 11px; margin-bottom: 7px;
}}
QListWidget::item:selected {{ border-color: {TEXT}; color: {TEXT}; }}
QListWidget::item:hover {{ border-color: {TEXT}; }}

QScrollBar:vertical {{ background: transparent; width: 9px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {SILVER}; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {STEEL}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollArea {{ border: none; background: transparent; }}
QWidget#pageBody {{ background: {BG}; }}

QWizard, QWizardPage {{ background: {BG}; }}
"""


def apply(qapp=None, appearance: str | None = None) -> None:
    from PySide6.QtWidgets import QApplication
    _set(appearance or config["appearance"])
    (qapp or QApplication.instance()).setStyleSheet(_qss())
