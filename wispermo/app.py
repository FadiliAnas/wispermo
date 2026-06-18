"""WISPERMO application controller.

Ties together the engine worker thread, the system tray (when available), the
floating overlay, the control window, and the Unix-socket command channel used
by the GNOME hotkey (and for single-instance handoff).
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from . import assets, formatting, sysintegration, theme, typist
from .config import config, socket_path
from .history import History
from .main_window import MainWindow
from .osplat import IS_LINUX, IS_MAC
from .mini_button import MiniButton
from .onboarding import Onboarding
from .overlay import Overlay
from .recorder import Recorder
from .transcriber import Transcriber


# --------------------------------------------------------------------------
def _notify(title: str, body: str = "", urgency: str = "low") -> None:
    if not config["notify"]:
        return
    try:
        subprocess.Popen(["notify-send", "-a", "WISPERMO", "-u", urgency,
                          "-t", "2000", title, body],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass


def _beep(kind: str) -> None:
    if not config["beep"]:
        return
    path = {
        "start": "/usr/share/sounds/freedesktop/stereo/dialog-information.oga",
        "stop": "/usr/share/sounds/freedesktop/stereo/message.oga",
    }.get(kind)
    if not path or not os.path.exists(path):
        return
    for player in ("pw-play", "paplay"):
        try:
            subprocess.Popen([player, path],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue


# --------------------------------------------------------------------------
class EngineWorker(QObject):
    """Owns the model + recorder. Lives in its own thread; all blocking work
    (model load, transcription, typing) happens here so the UI never freezes."""

    model_loaded = Signal(float)
    state_changed = Signal(str)
    result_ready = Signal(str, str, float, str, float)   # text, lang, dur, delivery, speech_secs
    failed = Signal(str)
    level = Signal(float)          # live mic RMS, 0..1, while recording

    def __init__(self) -> None:
        super().__init__()
        self.recorder = Recorder(config["audio_source"], on_level=self.level.emit)
        self.transcriber = Transcriber(config["model"], config["device"],
                                       config["compute_type"])

    @Slot()
    def load(self) -> None:
        try:
            dt = self.transcriber.load()
            self.model_loaded.emit(dt)
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Could not load model: {e}")

    @Slot()
    def start_recording(self) -> None:
        if self.recorder.active:
            return
        self.recorder.source = config["audio_source"]
        try:
            self.recorder.start()
            self.state_changed.emit("recording")
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Could not start recording: {e}")

    @Slot()
    def stop_and_transcribe(self) -> None:
        if not self.recorder.active:
            self.state_changed.emit("idle")
            return
        audio = self.recorder.stop()
        # speech duration for WPM / time-gained metrics (16kHz mono)
        speech_secs = (len(audio) / 16000.0) if audio is not None else 0.0
        self.state_changed.emit("transcribing")
        beam = {"fast": 1, "balanced": 3, "accurate": 5}.get(config["accuracy"], 3)
        try:
            res = self.transcriber.transcribe(
                audio,
                language=config["language"] or None,
                vad=bool(config["vad"]),
                beam_size=beam,
                initial_prompt=self._vocab_prompt(),
                reduce_hallucination=bool(config["reduce_hallucination"]),
            )
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Transcription failed: {e}")
            self.state_changed.emit("idle")
            return
        text = formatting.process(
            res.text, formatting=bool(config["formatting"]),
            mapping=config["dictionary"] or {},
            remove_fillers=bool(config["remove_fillers"]))
        if text and config["trailing_space"]:
            text += " "
        delivery = "empty"
        if text:
            try:
                delivery = typist.deliver(text, config["output"],
                                          int(config["type_delay_ms"]))
            except typist.TypistError as e:
                delivery = f"delivery failed: {e}"
        self.result_ready.emit(text.strip(), res.language, res.duration, delivery, speech_secs)
        self.state_changed.emit("idle")

    @staticmethod
    def _vocab_prompt() -> str | None:
        """Bias recognition toward user terms: the vocabulary box plus the
        written forms from the dictionary."""
        parts = []
        vocab = (config["vocabulary"] or "").strip()
        if vocab:
            parts.append(vocab)
        written = [v for v in (config["dictionary"] or {}).values() if v]
        if written:
            parts.append(", ".join(written))
        prompt = "; ".join(parts).strip()
        return prompt[:480] or None      # keep the prompt short

    @Slot()
    def reconfigure(self) -> None:
        try:
            self.transcriber.reconfigure(config["model"], config["device"],
                                         config["compute_type"])
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Could not switch model: {e}")


# --------------------------------------------------------------------------
class SocketServer(threading.Thread):
    """Plain AF_UNIX server for hotkey/single-instance commands.

    Runs as a daemon thread; dispatches commands to the GUI thread via a
    thread-safe callback that uses QTimer.singleShot(0, ...)."""

    def __init__(self, on_command, state_getter) -> None:
        super().__init__(daemon=True)
        self.on_command = on_command
        self.state_getter = state_getter
        self._srv: socket.socket | None = None
        self._running = True

    def run(self) -> None:
        path = socket_path()
        if os.path.exists(path):
            os.remove(path)
        self._srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._srv.bind(path)
        os.chmod(path, 0o600)
        self._srv.listen(8)
        while self._running:
            try:
                conn, _ = self._srv.accept()
            except OSError:
                break
            with conn:
                try:
                    cmd = conn.recv(64).decode(errors="replace").strip()
                except OSError:
                    continue
                if cmd == "status":
                    reply = self.state_getter()
                elif cmd == "ping":
                    reply = "pong"
                else:
                    self.on_command(cmd)
                    reply = "ok"
                try:
                    conn.sendall(reply.encode())
                except OSError:
                    pass

    def stop(self) -> None:
        self._running = False
        try:
            if self._srv:
                self._srv.close()
        except OSError:
            pass
        p = socket_path()
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass


# --------------------------------------------------------------------------
class App(QObject):
    req_load = Signal()
    req_start = Signal()
    req_stop = Signal()
    req_reconfigure = Signal()
    # emitted from the socket thread; auto-queued onto the GUI thread
    command_received = Signal(str)

    def __init__(self, qapp: QApplication) -> None:
        super().__init__()
        self.qapp = qapp
        self.state = "loading"
        self.history = History(int(config["max_history"]))
        self.command_received.connect(self._handle)

        # UI
        self.overlay = Overlay()
        self.window = MainWindow(self.history)
        self.window.toggle_requested.connect(self.toggle)
        self.window.settings_changed.connect(self._apply_settings)
        self.window.open_onboarding.connect(self.open_onboarding)
        self.window.quit_requested.connect(self.quit)

        self.mini = MiniButton()
        self.mini.clicked.connect(self.toggle)
        self.mini.place(config["mini_button_pos"])
        if config["show_mini_button"]:
            self.mini.show()

        self.tray = self._build_tray()

        # engine worker thread
        self.thread = QThread()
        self.worker = EngineWorker()
        self.worker.moveToThread(self.thread)
        self.req_load.connect(self.worker.load)
        self.req_start.connect(self.worker.start_recording)
        self.req_stop.connect(self.worker.stop_and_transcribe)
        self.req_reconfigure.connect(self.worker.reconfigure)
        self.worker.model_loaded.connect(self._on_loaded)
        self.worker.state_changed.connect(self._on_state)
        self.worker.result_ready.connect(self._on_result)
        self.worker.failed.connect(self._on_failed)
        self.worker.level.connect(self.overlay.set_level)
        self.thread.start()

        # command channel (hotkey + single instance)
        self.server = SocketServer(self._dispatch_command, lambda: self.state)
        self.server.start()

        # global hotkey — primary path is our own evdev listener (reliable on
        # Wayland); the GNOME custom shortcut is kept as a fallback.
        self._ensure_hotkey()
        self.hotkeys = None
        self._start_hotkey_listener()

        self._set_state("loading")
        self.req_load.emit()

    def _start_hotkey_listener(self) -> None:
        on_press = lambda: self.command_received.emit("hk_press")
        on_release = lambda: self.command_received.emit("hk_release")
        if IS_MAC:
            from .mac_hotkey import MacHotkeyListener, can_listen
            if not can_listen():
                return
            self.hotkeys = MacHotkeyListener(config["hotkey"], on_press, on_release)
        else:
            from .hotkey_listener import HotkeyListener, can_listen
            if not can_listen():
                _notify("Hotkey needs permission",
                        "Add your user to the 'input' group to use the global hotkey "
                        "(the setup wizard can do this), then log out and back in.",
                        "normal")
                return
            self.hotkeys = HotkeyListener(config["hotkey"], on_press, on_release)
        self.hotkeys.start()

    def _ensure_hotkey(self) -> None:
        # GNOME custom-shortcut registration is Linux-only; on macOS the in-app
        # pynput listener handles the global hotkey directly.
        if not IS_LINUX:
            return
        from .keys import gnome_to_display
        sysintegration.register_hotkey(sysintegration.toggle_command(), config["hotkey"])
        conflict = sysintegration.keybinding_conflict(config["hotkey"])
        if conflict:
            _notify("Hotkey already in use",
                    f"{gnome_to_display(config['hotkey'])} is also bound to "
                    f"“{conflict}”. Pick another in Settings ▸ General.", "normal")

    # -- tray ----------------------------------------------------------
    def _build_tray(self) -> QSystemTrayIcon | None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return None
        tray = QSystemTrayIcon(assets.state_icon("loading"))
        menu = QMenu()
        self.act_toggle = menu.addAction("Start dictation", self.toggle)
        menu.addAction("Open WISPERMO", self.window.present)
        menu.addAction("Settings…", self.open_settings)
        menu.addSeparator()
        menu.addAction("Quit", self.quit)
        tray.setContextMenu(menu)
        tray.activated.connect(self._tray_activated)
        tray.setToolTip("WISPERMO — loading…")
        tray.show()
        return tray

    def _tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:        # left click
            self.toggle()
        elif reason == QSystemTrayIcon.MiddleClick:
            self.window.present()

    # -- command dispatch (from socket thread) -------------------------
    def _dispatch_command(self, cmd: str) -> None:
        # emit a queued signal so the command runs on the GUI thread
        self.command_received.emit(cmd)

    @Slot(str)
    def _handle(self, cmd: str) -> None:
        if cmd == "toggle":
            self.toggle()
        elif cmd == "hk_press":
            self._hotkey_press()
        elif cmd == "hk_release":
            self._hotkey_release()
        elif cmd == "start":
            self.start()
        elif cmd == "stop":
            self.stop()
        elif cmd == "show":
            self.window.present()
        elif cmd == "quit":
            self.quit()

    # -- hotkey press/release (push-to-talk or toggle) -----------------
    def _hotkey_press(self) -> None:
        if config["hotkey_mode"] == "toggle":
            self.toggle()
        else:                       # push-to-talk: hold to record
            self.start()

    def _hotkey_release(self) -> None:
        if config["hotkey_mode"] != "toggle":
            self.stop()             # release ends push-to-talk

    # -- core actions --------------------------------------------------
    def toggle(self) -> None:
        if self.state == "recording":
            self.stop()
        elif self.state == "idle":
            self.start()
        # ignore while loading/transcribing

    def start(self) -> None:
        if self.state != "idle":
            return
        _beep("start")
        # optimistic state so a fast push-to-talk release can't race the worker;
        # the worker processes start then stop in queued order regardless.
        self._set_state("recording")
        self.req_start.emit()

    def stop(self) -> None:
        if self.state != "recording":
            return
        _beep("stop")
        self.req_stop.emit()

    # -- worker callbacks ----------------------------------------------
    @Slot(float)
    def _on_loaded(self, dt: float) -> None:
        self._set_state("idle")
        if self.tray:
            self.tray.setToolTip("WISPERMO — ready")
        _notify("WISPERMO ready", "Press your hotkey to dictate")

    @Slot(str)
    def _on_state(self, state: str) -> None:
        self._set_state(state)

    @Slot(str, str, float, str, float)
    def _on_result(self, text: str, lang: str, dur: float, delivery: str,
                   speech_secs: float) -> None:
        if text:
            if config["keep_history"]:
                self.history.add(text, lang, speech_secs)
                self.window.refresh()
            self.overlay.show_state("done", f"{len(text)} chars", auto_hide_ms=1000)
            if delivery.startswith(("delivery failed", "auto-paste failed",
                                    "typing failed")):
                _notify("Text ready on clipboard", delivery, "normal")
        else:
            self.overlay.show_state("done", "No speech", auto_hide_ms=1200)

    @Slot(str)
    def _on_failed(self, msg: str) -> None:
        self._set_state("idle")
        self.overlay.show_state("error", msg[:40], auto_hide_ms=2500)
        _notify("WISPERMO", msg, "critical")

    # -- state propagation ---------------------------------------------
    def _set_state(self, state: str) -> None:
        self.state = state
        self.window.set_state(state)
        self.mini.set_state(state)
        if self.tray:
            self.tray.setIcon(assets.state_icon(state))
            if hasattr(self, "act_toggle"):
                self.act_toggle.setText(
                    "Stop & type" if state == "recording" else "Start dictation")
        if state == "recording":
            self.overlay.show_state("recording")
        elif state == "transcribing":
            self.overlay.show_state("transcribing")
        # 'done'/'error' overlay handled in result/failed callbacks

    # -- windows -------------------------------------------------------
    def open_settings(self) -> None:
        self.window.show_settings()

    def _apply_settings(self) -> None:
        self.req_reconfigure.emit()
        # live appearance switch (light/dark)
        theme.apply(self.qapp, config["appearance"])
        self.window.set_state(self.state)   # re-evaluate inline-styled widgets
        self._ensure_hotkey()
        if self.hotkeys:
            self.hotkeys.set_accel(config["hotkey"])
        sysintegration.set_autostart(bool(config["autostart"]),
                                     sysintegration.app_executable())
        # floating mic button visibility
        if config["show_mini_button"] and not self.mini.isVisible():
            self.mini.place(config["mini_button_pos"])
            self.mini.show()
        elif not config["show_mini_button"] and self.mini.isVisible():
            self.mini.hide()
        self.window.refresh()

    def open_onboarding(self) -> None:
        Onboarding(self.window).exec()
        self._apply_settings()

    def quit(self) -> None:
        try:
            config.set("mini_button_pos", self.mini.current_pos())
            config.save()
        except Exception:
            pass
        try:
            if self.hotkeys:
                self.hotkeys.stop()
        except Exception:
            pass
        try:
            self.worker.recorder.cancel()
        except Exception:
            pass
        self.mini.hide()
        self.overlay.hide()
        self.server.stop()
        self.thread.quit()
        self.thread.wait(2000)
        self.qapp.quit()


# --------------------------------------------------------------------------
def _try_handoff() -> bool:
    """If an instance is already running, tell it to show its window. Returns
    True if handed off (this process should exit)."""
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        s.connect(socket_path())
    except (FileNotFoundError, ConnectionRefusedError):
        return False
    try:
        s.sendall(b"ping")
        if s.recv(16).strip() == b"pong":
            s.close()
            s2 = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            s2.connect(socket_path())
            s2.sendall(b"show")
            s2.close()
            return True
    except OSError:
        pass
    return False


CLIENT_COMMANDS = {"toggle", "start", "stop", "show", "quit", "status", "ping"}


def main() -> int:
    # client mode: `wispermo toggle` etc. talk to the running instance and exit
    if len(sys.argv) > 1 and sys.argv[1] in CLIENT_COMMANDS:
        from .client import send
        print(send(sys.argv[1]))
        return 0

    if _try_handoff():
        print("WISPERMO is already running — opening its window.")
        return 0

    # Linux/GNOME-Wayland refuses always-on-top + edge placement, so prefer
    # XWayland (xcb) there. macOS (cocoa) honours both natively — leave default.
    if IS_LINUX:
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb;wayland")

    qapp = QApplication(sys.argv)
    qapp.setApplicationName("WISPERMO")
    qapp.setApplicationDisplayName("WISPERMO")
    qapp.setQuitOnLastWindowClosed(False)
    qapp.setWindowIcon(assets.state_icon("idle"))
    theme.apply(qapp)

    app = App(qapp)

    first_run = not config["onboarded"]
    no_tray = not QSystemTrayIcon.isSystemTrayAvailable()
    if first_run:
        app.open_onboarding()
        app.window.present()
    elif no_tray:
        # no tray to live in — show the window so the user can reach the app
        app.window.present()

    return qapp.exec()


if __name__ == "__main__":
    sys.exit(main())
