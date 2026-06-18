"""First-run setup wizard: typing permission, hotkey, optional tray support."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QLabel, QMessageBox, QPushButton, QVBoxLayout, QWizard, QWizardPage,
)

from . import assets, sysintegration
from .config import config
from .keys import gnome_to_display


class _Page(QWizardPage):
    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__()
        self.setTitle(title)
        if subtitle:
            self.setSubTitle(subtitle)
        self.box = QVBoxLayout(self)


class WelcomePage(_Page):
    def __init__(self) -> None:
        super().__init__("Welcome to WISPERMO",
                         "Local, offline dictation — your voice, typed anywhere.")
        logo = QLabel()
        logo.setPixmap(assets.app_logo(96).scaled(96, 96, Qt.KeepAspectRatio,
                                                  Qt.SmoothTransformation))
        logo.setAlignment(Qt.AlignCenter)
        self.box.addWidget(logo)
        self.box.addWidget(QLabel(
            "A few quick steps to set things up. Everything runs on your machine — "
            "nothing is sent to the cloud."))


class TypingPage(_Page):
    def __init__(self) -> None:
        super().__init__("Allow typing into other apps",
                         "WISPERMO types your words using ydotool, which needs "
                         "one-time permission to the input device.")
        self.status = QLabel()
        self.status.setWordWrap(True)
        fix = QPushButton("Grant permission (asks for your password)…")
        fix.clicked.connect(self._fix)
        self.box.addWidget(self.status)
        self.box.addWidget(fix)
        self._refresh()

    def _refresh(self) -> None:
        ok = sysintegration.typing_ready()
        if ok:
            self.status.setText("✅ Typing is ready.")
        else:
            issues = []
            if not sysintegration.ydotool_installed():
                issues.append("• ydotool is not installed (install the 'ydotool' package).")
            if not sysintegration.uinput_ready():
                issues.append("• /dev/uinput needs group access (click below).")
            if not sysintegration.in_input_group():
                issues.append("• your user must join the 'input' group (click below; "
                              "then log out/in once).")
            if not sysintegration.ydotoold_running():
                issues.append("• the ydotoold service needs to be started (click below).")
            self.status.setText("Not ready yet:\n" + "\n".join(issues) +
                                "\n\nYou can also skip this and use clipboard mode.")

    def _fix(self) -> None:
        sysintegration.enable_ydotoold()
        ok, msg = sysintegration.run_privileged_setup()
        if ok:
            QMessageBox.information(
                self, "Almost done",
                "Permission granted. If typing still doesn't work, log out and back "
                "in once so the 'input' group applies, then restart WISPERMO.")
        else:
            QMessageBox.warning(self, "Setup failed", msg)
        self._refresh()

    def isComplete(self) -> bool:  # allow proceeding regardless (clipboard fallback)
        return True


class HotkeyPage(_Page):
    def __init__(self) -> None:
        super().__init__("Your dictation hotkey",
                         "Press this key to start dictating; press it again to type "
                         "what you said.")
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setStyleSheet("font-size:22px; font-weight:bold; color:#6C5CE7;")
        register = QPushButton("Register this shortcut in GNOME")
        register.clicked.connect(self._register)
        self.result = QLabel()
        self.box.addWidget(self.label)
        self.box.addWidget(register)
        self.box.addWidget(self.result)

    def initializePage(self) -> None:
        self.label.setText(gnome_to_display(config["hotkey"]))

    def _register(self) -> None:
        ok = sysintegration.register_hotkey(sysintegration.toggle_command(), config["hotkey"])
        self.result.setText("✅ Shortcut registered." if ok else
                            "Could not register (not GNOME?). You can add it manually "
                            "in Settings ▸ Keyboard.")


class FinishPage(_Page):
    def __init__(self) -> None:
        super().__init__("You're all set",
                         "The first time you dictate, the speech model downloads "
                         "(~150 MB) and loads — after that it stays instant.")
        tray = QLabel()
        tray.setWordWrap(True)
        from PySide6.QtWidgets import QSystemTrayIcon
        if not QSystemTrayIcon.isSystemTrayAvailable():
            tray.setText(
                "ℹ️ Your desktop (GNOME) hides tray icons by default. WISPERMO will "
                "run in the background and show a floating indicator while you speak. "
                "For a tray icon, install the GNOME extension "
                "'AppIndicator and KStatusNotifierItem Support' and log out/in.")
        else:
            tray.setText("WISPERMO will live in your system tray.")
        self.box.addWidget(tray)
        self.box.addWidget(QLabel("Press your hotkey any time to dictate. Enjoy!"))


class Onboarding(QWizard):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("WISPERMO Setup")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setMinimumSize(560, 420)
        self.addPage(WelcomePage())
        self.addPage(TypingPage())
        self.addPage(HotkeyPage())
        self.addPage(FinishPage())
        self.finished.connect(self._done)

    def _done(self, _result) -> None:
        config.set("onboarded", True)
        config.save()
