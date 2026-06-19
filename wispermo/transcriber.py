"""faster-whisper wrapper. Loads the model once and keeps it warm.

Kept free of any GUI dependency so it can be driven from a worker thread or
the command line.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass

from . import bundled


@dataclass
class Result:
    text: str
    language: str
    duration: float  # seconds spent transcribing


class Transcriber:
    def __init__(self, model: str, device: str = "cpu", compute_type: str = "int8") -> None:
        self.model_name = model
        self.device = device
        self.compute_type = compute_type
        self._model = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self) -> float:
        """Load the model; returns load time in seconds."""
        from faster_whisper import WhisperModel

        # Use physical cores: on hyper-threaded CPUs that beats oversubscribing
        # logical cores, which causes contention and is slower.
        threads = max(1, (os.cpu_count() or 4) // 2)
        # prefer a model bundled in the AppImage (offline, no download)
        model = bundled.model_path(self.model_name)
        offline = os.path.isdir(model)        # bundled dir -> never hit the network
        t0 = time.monotonic()
        self._model = WhisperModel(
            model, device=self.device, compute_type=self.compute_type,
            cpu_threads=threads, local_files_only=offline,
        )
        return time.monotonic() - t0

    def reconfigure(self, model: str, device: str, compute_type: str) -> bool:
        """Reload only if the model parameters changed. Returns True if reloaded."""
        if (model, device, compute_type) == (self.model_name, self.device, self.compute_type) and self.loaded:
            return False
        self.model_name, self.device, self.compute_type = model, device, compute_type
        self._model = None
        self.load()
        return True

    def transcribe(self, audio, language: str | None = None, vad: bool = True,
                   beam_size: int = 1, initial_prompt: str | None = None,
                   reduce_hallucination: bool = True) -> Result:
        """`audio` may be a file path or a float32 numpy array @16kHz mono.

        Optimisation levers:
          language            pin to skip auto-detect (faster, more accurate)
          beam_size           1 = fast/greedy, 5 = best accuracy
          initial_prompt      bias recognition toward names/jargon
          reduce_hallucination suppress phantom words on silence/noise
        """
        if self._model is None:
            self.load()
        kwargs = dict(
            language=language or None,
            beam_size=max(1, beam_size),
            vad_filter=vad,
            # single deterministic pass — skips Whisper's slow temperature
            # fallback re-decoding, so it's both faster and repeatable.
            temperature=0.0,
        )
        if initial_prompt:
            kwargs["initial_prompt"] = initial_prompt
        if reduce_hallucination:
            # not carrying prior text forward stops repetition/runaway loops on
            # short dictation; the thresholds drop low-confidence phantom output.
            kwargs.update(
                condition_on_previous_text=False,
                no_speech_threshold=0.6,
                log_prob_threshold=-1.0,
            )
        t0 = time.monotonic()
        segments, info = self._model.transcribe(audio, **kwargs)
        text = "".join(seg.text for seg in segments).strip()
        if isinstance(audio, str):
            try:
                os.remove(audio)
            except OSError:
                pass
        return Result(text=text, language=getattr(info, "language", "") or "",
                      duration=time.monotonic() - t0)
