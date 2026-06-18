"""Post-processing for transcribed text: tidy-up + user dictionary."""
from __future__ import annotations

import re


def apply_dictionary(text: str, mapping: dict[str, str]) -> str:
    """Replace spoken phrases with their written form, case-insensitively,
    on whole-word boundaries. Longer phrases are applied first."""
    if not mapping:
        return text
    for spoken in sorted(mapping, key=len, reverse=True):
        written = mapping[spoken]
        if not spoken.strip():
            continue
        pattern = re.compile(rf"\b{re.escape(spoken)}\b", re.IGNORECASE)
        text = pattern.sub(written, text)
    return text


FILLERS = ("um", "uh", "erm", "ah", "hmm", "uhh", "umm", "mm")


def strip_fillers(text: str) -> str:
    """Remove standalone filler words (conservative list)."""
    pattern = re.compile(rf"\b(?:{'|'.join(FILLERS)})\b[\s,]*", re.IGNORECASE)
    return re.sub(pattern, "", text)


def tidy(text: str) -> str:
    """Light clean-up: collapse whitespace, capitalise sentence starts."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return text
    # capitalise first letter and letters after sentence-ending punctuation
    def _cap(m: re.Match) -> str:
        return m.group(0).upper()

    text = re.sub(r"(^\s*[a-z])|([.!?]\s+[a-z])", _cap, text)
    return text


def process(text: str, *, formatting: bool, mapping: dict[str, str],
            remove_fillers: bool = False) -> str:
    if remove_fillers:
        text = strip_fillers(text)
    text = apply_dictionary(text, mapping or {})
    if formatting:
        text = tidy(text)
    return text
