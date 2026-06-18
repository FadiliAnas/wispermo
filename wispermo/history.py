"""Transcription history + metrics, stored as JSON lines under the data dir."""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import date, datetime

from .config import data_dir

TYPING_WPM = 40.0   # assumed manual typing speed, for "time gained"


@dataclass
class Entry:
    text: str
    language: str
    when: float            # epoch seconds
    chars: int
    words: int = 0
    seconds: float = 0.0   # speech duration


class History:
    def __init__(self, max_entries: int = 200) -> None:
        self.path = data_dir() / "history.jsonl"
        self.max_entries = max_entries
        self._entries: list[Entry] = []
        self.load()

    def load(self) -> None:
        self._entries = []
        if not self.path.exists():
            return
        try:
            for line in self.path.read_text().splitlines():
                if line.strip():
                    d = json.loads(line)
                    self._entries.append(Entry(
                        text=d.get("text", ""), language=d.get("language", ""),
                        when=d.get("when", 0.0), chars=d.get("chars", 0),
                        words=d.get("words", 0), seconds=d.get("seconds", 0.0)))
        except (json.JSONDecodeError, OSError, TypeError):
            self._entries = []

    def add(self, text: str, language: str, seconds: float = 0.0) -> Entry:
        e = Entry(text=text, language=language, when=time.time(),
                  chars=len(text), words=len(text.split()), seconds=float(seconds))
        self._entries.append(e)
        self._entries = self._entries[-self.max_entries:]
        self._flush()
        return e

    def all(self) -> list[Entry]:
        return list(reversed(self._entries))  # newest first

    def clear(self) -> None:
        self._entries = []
        self._flush()

    # --- metrics ------------------------------------------------------
    @staticmethod
    def _words(e: Entry) -> int:
        return e.words or (e.chars // 5)

    @staticmethod
    def _ord(ts: float) -> int:
        return datetime.fromtimestamp(ts).date().toordinal()

    def stats(self) -> dict:
        n = len(self._entries)
        words = sum(self._words(e) for e in self._entries)
        chars = sum(e.chars for e in self._entries)
        speech = sum(e.seconds for e in self._entries)   # seconds spoken
        speak_min = speech / 60.0
        type_min = words / TYPING_WPM
        gained_min = max(0.0, type_min - speak_min) if speech > 0 else type_min
        wpm = round(words / (speech / 60.0)) if speech > 0 else 0
        today_ord = date.today().toordinal()
        today = sum(1 for e in self._entries if self._ord(e.when) == today_ord)
        return {
            "count": n,
            "words": words,
            "chars": chars,
            "wpm": wpm,
            "gained_min": gained_min,
            "avg_words": round(words / n) if n else 0,
            "today": today,
            "streak": self._streak(),
        }

    def _streak(self) -> int:
        days = {self._ord(e.when) for e in self._entries}
        if not days:
            return 0
        today = date.today().toordinal()
        if today not in days and (today - 1) not in days:
            return 0
        cur = max(d for d in days if d <= today)
        streak = 0
        while cur in days:
            streak += 1
            cur -= 1
        return streak

    def daily_counts(self, n: int = 7) -> list[int]:
        """Dictation counts for the last `n` days, oldest -> newest."""
        today = date.today().toordinal()
        counts: dict[int, int] = {}
        for e in self._entries:
            o = self._ord(e.when)
            counts[o] = counts.get(o, 0) + 1
        return [counts.get(today - i, 0) for i in range(n - 1, -1, -1)]

    def _flush(self) -> None:
        with open(self.path, "w") as f:
            for e in self._entries:
                f.write(json.dumps(asdict(e)) + "\n")
