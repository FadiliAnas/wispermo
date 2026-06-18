"""Professional main window: sidebar navigation + stacked pages."""
from __future__ import annotations

import time

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QFrame, QGridLayout,
                               QHBoxLayout, QKeySequenceEdit, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPlainTextEdit,
                               QPushButton, QScrollArea, QStackedWidget,
                               QVBoxLayout, QWidget)

from . import assets, keys, sysintegration, theme
from .config import config
from .history import History
from .widgets import ActivityChart, FieldRow, NavButton, StatCard, ToggleSwitch

MODELS = [("tiny", "Tiny — fastest"), ("base", "Base — fast (recommended)"),
          ("small", "Small — more accurate"), ("medium", "Medium — slow on CPU"),
          ("large-v3", "Large v3 — best, GPU advised")]
LANGS = [("", "Auto-detect"), ("en", "English"), ("fr", "French"), ("ar", "Arabic"),
         ("es", "Spanish"), ("de", "German"), ("it", "Italian"),
         ("pt", "Portuguese"), ("nl", "Dutch"), ("ru", "Russian"),
         ("zh", "Chinese"), ("ja", "Japanese"), ("hi", "Hindi"), ("tr", "Turkish")]
OUTPUTS = [("paste", "Paste instantly (Ctrl+V)"),
           ("type", "Type with writing effect"),
           ("clipboard", "Copy to clipboard only")]
SPEEDS = [(2, "Very fast"), (6, "Fast"), (14, "Natural"), (28, "Relaxed")]


def _combo(items, value) -> QComboBox:
    c = QComboBox()
    for v, label in items:
        c.addItem(label, v)
    i = c.findData(value)
    c.setCurrentIndex(i if i >= 0 else 0)
    return c


def _scroll(inner: QWidget) -> QScrollArea:
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    inner.setObjectName("pageBody")
    sa.setWidget(inner)
    return sa


# ===========================================================================
class HomePage(QWidget):
    toggle = Signal()

    def __init__(self, history: History) -> None:
        super().__init__()
        self.history = history
        body = QWidget()
        root = QVBoxLayout(body)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(18)

        title = QLabel("Dictate anywhere"); title.setObjectName("h1")
        sub = QLabel("Press your hotkey or click the mic, speak, and your words "
                     "are typed into the focused app.")
        sub.setObjectName("muted"); sub.setWordWrap(True)
        root.addWidget(title); root.addWidget(sub)

        # hero card with big mic button
        hero = QFrame(); hero.setObjectName("card")
        hl = QVBoxLayout(hero); hl.setContentsMargins(24, 24, 24, 24); hl.setSpacing(12)
        hl.setAlignment(Qt.AlignCenter)
        self.mic = QPushButton(); self.mic.setObjectName("primary")
        self.mic.setFixedSize(96, 96)
        self.mic.setIcon(assets.mic_icon(theme.ON_ACCENT, 48))
        self.mic.setIconSize(QSize(48, 48))
        self.mic.setStyleSheet(f"border-radius:48px; background:{theme.ACCENT};")
        self.mic.setCursor(Qt.PointingHandCursor)
        self.mic.clicked.connect(self.toggle.emit)
        self.state_lbl = QLabel("Ready"); self.state_lbl.setObjectName("h2")
        self.state_lbl.setAlignment(Qt.AlignCenter)
        self.hint = QLabel(""); self.hint.setObjectName("muted")
        self.hint.setAlignment(Qt.AlignCenter)
        hl.addWidget(self.mic, 0, Qt.AlignCenter)
        hl.addWidget(self.state_lbl)
        hl.addWidget(self.hint)
        root.addWidget(hero)

        # metrics grid (3 x 2)
        grid = QGridLayout(); grid.setSpacing(14)
        self.c_words = StatCard("0", "Words dictated")
        self.c_gained = StatCard("0m", "Time gained")
        self.c_wpm = StatCard("0", "Avg WPM")
        self.c_count = StatCard("0", "Dictations")
        self.c_avg = StatCard("0", "Avg words / take")
        self.c_streak = StatCard("0", "Day streak")
        cells = [self.c_words, self.c_gained, self.c_wpm,
                 self.c_count, self.c_avg, self.c_streak]
        for i, c in enumerate(cells):
            grid.addWidget(c, i // 3, i % 3)
        root.addLayout(grid)

        # 7-day activity
        self.chart = ActivityChart()
        root.addWidget(self.chart)

        root.addStretch(1)
        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(_scroll(body))
        self.refresh()

    def set_state(self, state: str) -> None:
        labels = {"idle": "Ready", "loading": "Loading model…",
                  "recording": "● Listening…", "transcribing": "Transcribing…",
                  "error": "Something went wrong"}
        self.state_lbl.setText(labels.get(state, state))
        rec = state == "recording"
        self.mic.setIcon(assets.stop_icon(theme.ON_ACCENT, 40) if rec
                         else assets.mic_icon(theme.ON_ACCENT, 48))
        self.mic.setStyleSheet(f"border-radius:48px; background:{theme.ACCENT};")
        self.hint.setText(f"Hotkey:  {keys.gnome_to_display(config['hotkey'])}")

    def refresh(self) -> None:
        s = self.history.stats()
        self.c_words.set_value(f"{s['words']:,}")
        self.c_gained.set_value(self._fmt_minutes(s["gained_min"]))
        self.c_wpm.set_value(f"{s['wpm']}" if s["wpm"] else "–")
        self.c_count.set_value(f"{s['count']:,}")
        self.c_avg.set_value(f"{s['avg_words']}")
        self.c_streak.set_value(f"{s['streak']}")
        self.chart.set_data(self.history.daily_counts(7))

    @staticmethod
    def _fmt_minutes(minutes: float) -> str:
        if minutes < 1:
            return f"{round(minutes * 60)}s"
        if minutes < 60:
            return f"{round(minutes)}m"
        return f"{minutes / 60:.1f}h"


# ===========================================================================
class HistoryPage(QWidget):
    def __init__(self, history: History) -> None:
        super().__init__()
        self.history = history
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28); root.setSpacing(14)
        head = QHBoxLayout()
        t = QLabel("History"); t.setObjectName("h1")
        head.addWidget(t); head.addStretch(1)
        clear = QPushButton("Clear all"); clear.setObjectName("danger")
        clear.clicked.connect(self._clear)
        head.addWidget(clear)
        root.addLayout(head)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search transcriptions…")
        self.search.textChanged.connect(self._filter)
        root.addWidget(self.search)
        self.list = QListWidget()
        self.list.itemClicked.connect(self._copy)
        root.addWidget(self.list, 1)
        self.hint = QLabel("Tip: click an entry to copy it."); self.hint.setObjectName("muted")
        root.addWidget(self.hint)
        self.refresh()

    def refresh(self) -> None:
        self._filter(self.search.text())

    def _filter(self, q: str) -> None:
        q = q.lower().strip()
        self.list.clear()
        for e in self.history.all():
            if q and q not in e.text.lower():
                continue
            preview = e.text if len(e.text) <= 90 else e.text[:87] + "…"
            it = QListWidgetItem(f"{preview}\n{self._ago(e.when)} · {e.language or '–'} · {e.chars} chars")
            it.setData(Qt.UserRole, e.text)
            self.list.addItem(it)
        if self.list.count() == 0:
            self.list.addItem(QListWidgetItem("Nothing yet — start dictating!"))

    def _copy(self, item: QListWidgetItem) -> None:
        txt = item.data(Qt.UserRole)
        if txt:
            QGuiApplication.clipboard().setText(txt)
            self.hint.setText("Copied to clipboard ✓")

    def _clear(self) -> None:
        self.history.clear(); self.refresh()

    @staticmethod
    def _ago(when: float) -> str:
        d = max(0, int(time.time() - when))
        if d < 60: return "just now"
        if d < 3600: return f"{d // 60}m ago"
        if d < 86400: return f"{d // 3600}h ago"
        return f"{d // 86400}d ago"


# ===========================================================================
class DictionaryPage(QWidget):
    changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28); root.setSpacing(14)
        t = QLabel("Dictionary"); t.setObjectName("h1")
        sub = QLabel("Auto-replace spoken phrases with the exact text you want "
                     "(names, jargon, emails). Case-insensitive.")
        sub.setObjectName("muted"); sub.setWordWrap(True)
        root.addWidget(t); root.addWidget(sub)

        add = QHBoxLayout()
        self.spoken = QLineEdit(); self.spoken.setPlaceholderText("When I say…")
        self.written = QLineEdit(); self.written.setPlaceholderText("Write this")
        b = QPushButton("Add"); b.setObjectName("primary"); b.clicked.connect(self._add)
        add.addWidget(self.spoken); add.addWidget(self.written); add.addWidget(b)
        root.addLayout(add)

        self.list = QListWidget()
        root.addWidget(self.list, 1)
        rm = QPushButton("Remove selected"); rm.setObjectName("danger")
        rm.clicked.connect(self._remove)
        root.addWidget(rm, 0, Qt.AlignLeft)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for spoken, written in (config["dictionary"] or {}).items():
            it = QListWidgetItem(f"“{spoken}”   →   {written}")
            it.setData(Qt.UserRole, spoken)
            self.list.addItem(it)

    def _add(self) -> None:
        s = self.spoken.text().strip()
        w = self.written.text().strip()
        if not s:
            return
        d = dict(config["dictionary"] or {})
        d[s] = w
        config.set("dictionary", d); config.save()
        self.spoken.clear(); self.written.clear()
        self.refresh(); self.changed.emit()

    def _remove(self) -> None:
        it = self.list.currentItem()
        if not it:
            return
        d = dict(config["dictionary"] or {})
        d.pop(it.data(Qt.UserRole), None)
        config.set("dictionary", d); config.save()
        self.refresh(); self.changed.emit()


# ===========================================================================
class SettingsPage(QWidget):
    changed = Signal()
    rerun_setup = Signal()

    def __init__(self) -> None:
        super().__init__()
        body = QWidget()
        root = QVBoxLayout(body)
        root.setContentsMargins(28, 28, 28, 28); root.setSpacing(16)
        t = QLabel("Settings"); t.setObjectName("h1")
        root.addWidget(t)

        # --- Speech
        self.model = _combo(MODELS, config["model"])
        self.lang = _combo(LANGS, config["language"])
        self.mic = QComboBox(); self.mic.addItem("System default", "default")
        for name, desc in sysintegration.list_audio_sources():
            self.mic.addItem(desc, name)
        i = self.mic.findData(config["audio_source"]); self.mic.setCurrentIndex(max(0, i))
        root.addWidget(self._section("Speech", [
            ("Model", "Bigger = more accurate, slower (tiny/base = fastest)", self.model),
            ("Language", "Pin a language to skip detection — faster & more accurate", self.lang),
            ("Microphone", "Input device", self.mic),
        ]))

        # --- Recognition (quality / speed tuning)
        self.accuracy = _combo(
            [("fast", "Fast — quickest"), ("balanced", "Balanced (recommended)"),
             ("accurate", "Accurate — best quality")], config["accuracy"])
        self.reduce_hall = ToggleSwitch(bool(config["reduce_hallucination"]))
        rec = self._section("Recognition", [
            ("Speed vs accuracy", "Fast is snappiest; Accurate uses a wider search",
             self.accuracy),
            ("Reduce hallucinations", "Suppress phantom words on silence/noise",
             self.reduce_hall),
        ])
        rl = rec.layout()
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"color:{theme.BORDER};"); rl.addWidget(sep)
        vlab = QLabel("Vocabulary & names"); vlab.setStyleSheet("font-weight:600;")
        vdesc = QLabel("Comma-separated terms WISPERMO should spell correctly "
                       "(names, brands, jargon).")
        vdesc.setObjectName("muted"); vdesc.setWordWrap(True)
        self.vocab = QPlainTextEdit(); self.vocab.setPlainText(config["vocabulary"] or "")
        self.vocab.setPlaceholderText("e.g. Anas Fadili, WISPERMO, faster-whisper, Kubernetes")
        self.vocab.setFixedHeight(64)
        rl.addWidget(vlab); rl.addWidget(vdesc); rl.addWidget(self.vocab)
        root.addWidget(rec)

        # --- Output
        self.output = _combo(OUTPUTS, config["output"])
        self.speed = _combo(SPEEDS, config["type_delay_ms"])
        self.trailing = ToggleSwitch(bool(config["trailing_space"]))
        self.formatting = ToggleSwitch(bool(config["formatting"]))
        self.fillers = ToggleSwitch(bool(config["remove_fillers"]))
        self.vad = ToggleSwitch(bool(config["vad"]))
        root.addWidget(self._section("Output", [
            ("How text appears", "Paste instantly, or type with a writing effect",
             self.output),
            ("Writing speed", "Speed of the typing effect", self.speed),
            ("Add trailing space", "Handy for continuous dictation", self.trailing),
            ("Tidy formatting", "Fix capitalisation & spacing", self.formatting),
            ("Remove filler words", "Drop “um”, “uh”, “erm”…", self.fillers),
            ("Trim silence", "Whisper voice-activity filter", self.vad),
        ]))

        # --- General
        self.hotkey = QKeySequenceEdit(); self.hotkey.setMaximumSequenceLength(1)
        disp = keys.gnome_to_display(config["hotkey"])
        if disp not in ("", "(none)"):
            self.hotkey.setKeySequence(QKeySequence(disp))
        self.autostart = ToggleSwitch(bool(config["autostart"]))
        self.mini = ToggleSwitch(bool(config["show_mini_button"]))
        self.appearance = _combo([("light", "Light"), ("dark", "Dark")],
                                 config["appearance"])
        self.hkmode = _combo([("ptt", "Push-to-talk (hold)"),
                              ("toggle", "Toggle (press on/off)")],
                             config["hotkey_mode"])
        root.addWidget(self._section("General", [
            ("Appearance", "Light paper or dark ink", self.appearance),
            ("Dictation hotkey", "The key that triggers dictation", self.hotkey),
            ("Hotkey mode", "Hold to talk, or press to toggle", self.hkmode),
            ("Floating mic button", "Always-on-top quick button", self.mini),
            ("Start on login", "Launch automatically", self.autostart),
        ]))

        # --- Feedback
        self.notify = ToggleSwitch(bool(config["notify"]))
        self.beep = ToggleSwitch(bool(config["beep"]))
        root.addWidget(self._section("Feedback", [
            ("Notifications", "Desktop notifications", self.notify),
            ("Sounds", "Start/stop cue", self.beep),
        ]))

        setup = QPushButton("Re-run setup wizard")
        setup.clicked.connect(self.rerun_setup.emit)
        root.addWidget(setup, 0, Qt.AlignLeft)
        root.addStretch(1)

        outer = QVBoxLayout(self); outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(_scroll(body))
        self._wire()

    def _section(self, title: str, rows) -> QFrame:
        card = QFrame(); card.setObjectName("card")
        lay = QVBoxLayout(card); lay.setContentsMargins(18, 14, 18, 14); lay.setSpacing(2)
        h = QLabel(title); h.setObjectName("h2")
        lay.addWidget(h)
        for i, (name, desc, ctrl) in enumerate(rows):
            lay.addWidget(FieldRow(name, desc, ctrl))
            if i < len(rows) - 1:
                sep = QFrame(); sep.setFrameShape(QFrame.HLine)
                sep.setStyleSheet(f"color:{theme.BORDER};")
                lay.addWidget(sep)
        return card

    def _wire(self) -> None:
        for combo in (self.model, self.lang, self.mic, self.output, self.speed,
                      self.accuracy, self.appearance, self.hkmode):
            combo.currentIndexChanged.connect(self._apply)
        self.hotkey.editingFinished.connect(self._apply)
        self.hotkey.keySequenceChanged.connect(self._apply)
        for sw in (self.trailing, self.formatting, self.fillers, self.vad,
                   self.reduce_hall, self.autostart, self.mini, self.notify, self.beep):
            sw.toggled.connect(self._apply)
        # vocabulary saves on its own (per-keystroke) without a full re-apply
        self.vocab.textChanged.connect(self._save_vocab)

    def _save_vocab(self) -> None:
        config.set("vocabulary", self.vocab.toPlainText().strip())
        config.save()

    def _apply(self, *_) -> None:
        config.set("model", self.model.currentData())
        config.set("language", self.lang.currentData())
        config.set("audio_source", self.mic.currentData())
        config.set("output", self.output.currentData())
        config.set("type_delay_ms", self.speed.currentData())
        seq = self.hotkey.keySequence()
        if not seq.isEmpty():
            accel = keys.qt_to_gnome(seq)
            if accel:
                config.set("hotkey", accel)
        config.set("appearance", self.appearance.currentData())
        config.set("hotkey_mode", self.hkmode.currentData())
        config.set("accuracy", self.accuracy.currentData())
        config.set("reduce_hallucination", self.reduce_hall.isChecked())
        config.set("trailing_space", self.trailing.isChecked())
        config.set("formatting", self.formatting.isChecked())
        config.set("remove_fillers", self.fillers.isChecked())
        config.set("vad", self.vad.isChecked())
        config.set("autostart", self.autostart.isChecked())
        config.set("show_mini_button", self.mini.isChecked())
        config.set("notify", self.notify.isChecked())
        config.set("beep", self.beep.isChecked())
        config.save()
        self.changed.emit()


# ===========================================================================
class AboutPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        from . import __version__
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28); root.setSpacing(12)
        root.setAlignment(Qt.AlignTop)
        logo = QLabel(); logo.setPixmap(assets.app_logo(88))
        root.addWidget(logo)
        name = QLabel("WISPERMO"); name.setObjectName("h1")
        root.addWidget(name)
        root.addWidget(QLabel(f"Version {__version__}", objectName="muted"))
        blurb = QLabel("Local, offline dictation powered by Whisper. Your voice "
                       "never leaves your machine — no cloud, no account.")
        blurb.setObjectName("muted"); blurb.setWordWrap(True)
        root.addWidget(blurb)
        root.addSpacing(8)
        root.addWidget(QLabel("Engine: faster-whisper · UI: PySide6", objectName="muted"))


# ===========================================================================
class MainWindow(QWidget):
    toggle_requested = Signal()
    settings_changed = Signal()
    open_onboarding = Signal()
    quit_requested = Signal()

    def __init__(self, history: History) -> None:
        super().__init__(None)
        self.history = history
        self.setWindowTitle("WISPERMO")
        self.setWindowIcon(assets.state_icon("idle"))
        self.resize(820, 580)
        self.setMinimumSize(720, 500)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0); row.setSpacing(0)
        row.addWidget(self._sidebar())

        self.stack = QStackedWidget()
        self.home = HomePage(history)
        self.history_page = HistoryPage(history)
        self.dictionary = DictionaryPage()
        self.settings = SettingsPage()
        self.about = AboutPage()
        for w in (self.home, self.history_page, self.dictionary, self.settings, self.about):
            self.stack.addWidget(w)
        row.addWidget(self.stack, 1)

        self.home.toggle.connect(self.toggle_requested.emit)
        self.settings.changed.connect(self.settings_changed.emit)
        self.settings.rerun_setup.connect(self.open_onboarding.emit)
        self.dictionary.changed.connect(self.settings_changed.emit)

    def _sidebar(self) -> QFrame:
        bar = QFrame(); bar.setObjectName("sidebar"); bar.setFixedWidth(208)
        lay = QVBoxLayout(bar); lay.setContentsMargins(12, 18, 12, 16); lay.setSpacing(4)

        brand = QHBoxLayout()
        logo = QLabel(); logo.setPixmap(assets.app_logo(30))
        name = QLabel("WISPERMO"); name.setStyleSheet("font-weight:800; font-size:15px;")
        brand.addWidget(logo); brand.addSpacing(8); brand.addWidget(name); brand.addStretch(1)
        lay.addLayout(brand)
        lay.addSpacing(14)

        self.nav = QButtonGroup(self)
        items = [("⌂", "Home"), ("↻", "History"), ("≡", "Dictionary"),
                 ("⚙", "Settings"), ("ⓘ", "About")]
        for idx, (icon, label) in enumerate(items):
            btn = NavButton(icon, label)
            btn.clicked.connect(lambda _=False, i=idx: self._select(i))
            self.nav.addButton(btn, idx)
            lay.addWidget(btn)
        self.nav.button(0).setChecked(True)

        lay.addStretch(1)
        quit_b = QPushButton("Quit"); quit_b.setObjectName("danger")
        quit_b.clicked.connect(self.quit_requested.emit)
        lay.addWidget(quit_b)
        return bar

    def _select(self, i: int) -> None:
        self.stack.setCurrentIndex(i)
        self.nav.button(i).setChecked(True)
        if i == 1:
            self.history_page.refresh()
        elif i == 0:
            self.home.refresh()

    # -- controller hooks ---------------------------------------------
    def set_state(self, state: str) -> None:
        self.home.set_state(state)

    def refresh(self) -> None:
        self.home.refresh()
        self.history_page.refresh()

    def show_settings(self) -> None:
        self._select(3)
        self.present()

    def present(self) -> None:
        self.show(); self.raise_(); self.activateWindow()

    def closeEvent(self, e) -> None:
        e.ignore(); self.hide()
