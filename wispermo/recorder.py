"""Streaming microphone capture (raw s16le mono @16kHz on stdout).

Picks the first capture tool that actually works on the system — system ffmpeg
with PulseAudio, then PipeWire/Pulse's own `parec`/`pw-record` (present on
essentially every modern desktop). The bundled static ffmpeg lacks PulseAudio
support, so it's only a last resort.

Reads raw PCM in a background thread so we can both report a live RMS level
(waveform) and hand the audio straight to faster-whisper as a numpy array.
"""
from __future__ import annotations

import shutil
import subprocess
import threading

import numpy as np

from . import bundled

SAMPLE_RATE = 16000
CHUNK_SAMPLES = 800            # 0.05s -> ~20 level updates/sec
CHUNK_BYTES = CHUNK_SAMPLES * 2  # s16le mono

_pulse_ok: bool | None = None   # cache: does the chosen ffmpeg support pulse?


def _ffmpeg_has_pulse(ff: str) -> bool:
    global _pulse_ok
    if _pulse_ok is None:
        try:
            out = subprocess.run([ff, "-hide_banner", "-devices"],
                                 capture_output=True, text=True, timeout=5).stdout
            _pulse_ok = "pulse" in out.lower()
        except Exception:
            _pulse_ok = False
    return _pulse_ok


def capture_command(source: str) -> list[str]:
    """Return an argv that writes raw s16le mono @16kHz to stdout."""
    src = source or "default"
    sys_ff = shutil.which("ffmpeg")
    if sys_ff and _ffmpeg_has_pulse(sys_ff):
        return [sys_ff, "-hide_banner", "-loglevel", "error",
                "-f", "pulse", "-i", src,
                "-ar", str(SAMPLE_RATE), "-ac", "1", "-f", "s16le", "-"]
    if shutil.which("parec"):
        cmd = ["parec", f"--rate={SAMPLE_RATE}", "--channels=1", "--format=s16le"]
        if src and src != "default":
            cmd += ["-d", src]
        return cmd
    if shutil.which("pw-record"):
        return ["pw-record", "--rate", str(SAMPLE_RATE), "--channels", "1",
                "--format", "s16", "-"]
    # last resort (may not support pulse capture)
    return [bundled.ffmpeg(), "-hide_banner", "-loglevel", "error",
            "-f", "pulse", "-i", src,
            "-ar", str(SAMPLE_RATE), "-ac", "1", "-f", "s16le", "-"]


class Recorder:
    """Captures mic audio to a float32 mono @16kHz numpy array, with live RMS.

    Linux: streams raw PCM from a capture subprocess (ffmpeg/parec/pw-record).
    macOS: uses sounddevice (CoreAudio) — no external tools needed.
    """

    def __init__(self, source: str = "default", on_level=None) -> None:
        from .osplat import IS_MAC
        self.source = source or "default"
        self.on_level = on_level          # callable(float 0..1) or None
        self._mac = IS_MAC
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stream = None               # sounddevice InputStream (macOS)
        self._chunks: list = []
        self._stop = threading.Event()

    @property
    def active(self) -> bool:
        return self._proc is not None or self._stream is not None

    def start(self) -> None:
        if self.active:
            return
        self._chunks = []
        self._stop.clear()
        if self._mac:
            self._start_stream()
        else:
            self._start_subprocess()

    # -- Linux: capture subprocess ------------------------------------
    def _start_subprocess(self) -> None:
        self._proc = subprocess.Popen(
            capture_command(self.source),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=CHUNK_BYTES,
        )
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self) -> None:
        stream = self._proc.stdout
        while not self._stop.is_set():
            data = stream.read(CHUNK_BYTES)
            if not data:
                break
            self._chunks.append(data)
            if self.on_level:
                arr = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                if arr.size:
                    rms = float(np.sqrt(np.mean(arr * arr)))
                    self.on_level(min(1.0, rms * 4.0))

    # -- macOS: sounddevice / CoreAudio -------------------------------
    def _start_stream(self) -> None:
        import sounddevice as sd

        def _cb(indata, _frames, _time, _status):
            self._chunks.append(indata.copy())        # float32 mono
            if self.on_level and indata.size:
                rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
                self.on_level(min(1.0, rms * 4.0))

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32",
            blocksize=CHUNK_SAMPLES, callback=_cb)
        self._stream.start()

    # -- stop ---------------------------------------------------------
    def stop(self) -> "np.ndarray | None":
        """Stop recording; return the captured audio as float32 mono @16kHz."""
        if self._stream is not None:
            try:
                self._stream.stop(); self._stream.close()
            except Exception:
                pass
            self._stream = None
            if not self._chunks:
                return None
            return np.concatenate(self._chunks).astype(np.float32).flatten()

        if self._proc is None:
            return None
        self._stop.set()
        try:
            self._proc.terminate()
            self._proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait()
        if self._thread:
            self._thread.join(timeout=2)
        self._proc = None
        self._thread = None
        raw = b"".join(self._chunks)
        self._chunks = []
        if not raw:
            return None
        return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    def cancel(self) -> None:
        self.stop()
