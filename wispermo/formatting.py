"""Post-processing for transcribed text.

Stage A — process(): user dictionary, filler removal, de-stutter, tidy
                     (capitalisation, "i"->"I", spacing/punctuation).
Stage B — smart_format(): voice commands (new paragraph/line), spoken email,
                     numbered/bullet lists, email shaping. Gated by a setting.

Pure logic, no platform deps, instant, offline.
"""
from __future__ import annotations

import re

# ---- Stage A data ---------------------------------------------------------
FILLERS = ("um", "uh", "erm", "uhh", "umm", "er", "ah", "hmm", "mm")
FILLER_PHRASES = ("you know", "i mean", "sort of", "kind of")
# words that get doubled by stutter/repeat in speech
DESTUTTER = ("the", "a", "an", "i", "to", "and", "of", "is", "it",
             "we", "you", "but", "so", "in", "on", "my", "with", "that")


def apply_dictionary(text: str, mapping: dict[str, str]) -> str:
    """Replace spoken phrases with their written form, case-insensitively,
    on whole-word boundaries. Longer phrases first."""
    if not mapping:
        return text
    for spoken in sorted(mapping, key=len, reverse=True):
        written = mapping[spoken]
        if not spoken.strip():
            continue
        pattern = re.compile(rf"\b{re.escape(spoken)}\b", re.IGNORECASE)
        text = pattern.sub(lambda _m, w=written: w, text)
    return text


def strip_fillers(text: str) -> str:
    """Remove standalone filler words and common filler phrases."""
    for f in FILLERS:
        text = re.sub(rf"(?i)\s\b{f}\b\s", " ", text)
        text = re.sub(rf"(?i)^\b{f}\b\s", "", text)
        text = re.sub(rf"(?i)\s\b{f}\b$", "", text)
    for p in FILLER_PHRASES:
        text = re.sub(rf"(?i)\s{re.escape(p)}\s", " ", text)
    return text


def _destutter(text: str) -> str:
    for w in DESTUTTER:
        text = re.sub(rf"(?i)\b({w})\s+\1\b", r"\1", text)
    return text


def tidy(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return text
    text = _destutter(text)
    text = re.sub(r"\bi\b", "I", text)            # standalone i -> I
    text = re.sub(r"\bi'", "I'", text)            # i'm / i'll / i've
    text = re.sub(r" {2,}", " ", text)
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)  # no space before punctuation

    def _cap(m: re.Match) -> str:
        return m.group(0).upper()

    text = re.sub(r"(^\s*[a-z])|([.!?]\s+[a-z])", _cap, text)
    return text.strip()


def process(text: str, *, formatting: bool, mapping: dict[str, str],
            remove_fillers: bool = False) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    text = apply_dictionary(text, mapping or {})
    if remove_fillers:
        text = strip_fillers(text)
    if formatting:
        text = tidy(text)
    return text.strip()


# ---- Stage B: structure detection -----------------------------------------
_NUM = (r"(?i)\b(?:number|point|step)\s+"
        r"(\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)\b[\s,:.\-–]*")
_ALT = (r"(?i)(?:^|[.\n]\s*)(first(?:ly)?|second(?:ly)?|third(?:ly)?|fourth(?:ly)?|"
        r"fifth(?:ly)?|sixth(?:ly)?|seventh|eighth|ninth|tenth|lastly|finally)\b[\s,:.\-–]*")
_BULLET = r"(?i)\b(?:bullet\s*point|bullet)\b[\s,:.\-–]*"
_GREET = ("dear ", "hi ", "hello ", "hey ")
_SIGN = ["best regards", "kind regards", "warm regards", "best wishes",
         "regards", "sincerely", "cheers", "thanks so much", "thank you",
         "thanks", "best"]


def smart_format(raw: str) -> str:
    t = (raw or "").strip()
    if not t:
        return t
    t = _apply_commands(t)
    t = _spoken_email(t)
    lst = _numbered_list(t)
    if lst:
        return lst
    b = _bullet_list(t)
    if b:
        return b
    e = _email_shape(t)
    if e:
        return e
    return _collapse(t)


def _apply_commands(s: str) -> str:
    s = re.sub(r"(?i)[\s,]*\bnew paragraph\b[\s,]*", "\n\n", s)
    s = re.sub(r"(?i)[\s,]*\b(?:new|next) line\b[\s,]*", "\n", s)
    return s


def _spoken_email(s: str) -> str:
    return re.sub(r"(?i)\b([a-z0-9._%+-]+)\s+at\s+([a-z0-9-]+)\s+dot\s+"
                  r"(com|org|net|edu|io|co|gov|me|app|dev|ai)\b", r"\1@\2.\3", s)


def _split_by(text: str, pattern: str):
    ms = list(re.finditer(pattern, text))
    if not ms:
        return None
    preamble = text[:ms[0].start()].strip(" ,.;:-–\n")
    items = []
    for i, m in enumerate(ms):
        start = m.end()
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        item = text[start:end].strip(" ,.;:-–\n")
        if item:
            items.append(item)
    return preamble, items


def _numbered_list(text: str):
    res = _split_by(text, _NUM) or _split_by(text, _ALT)
    if not res or len(res[1]) < 2:
        return None
    preamble, items = res
    out = (_sentence(preamble) + "\n") if preamble else ""
    out += "".join(f"{i+1}. {_sentence(it)}\n" for i, it in enumerate(items))
    return out.strip()


def _bullet_list(text: str):
    if not re.search(r"(?i)\bbullet\b", text):
        return None
    res = _split_by(text, _BULLET)
    if not res or len(res[1]) < 1:
        return None
    preamble, items = res
    out = (_sentence(preamble) + "\n") if preamble else ""
    out += "".join(f"• {_sentence(it)}\n" for it in items if it)
    return out.strip()


def _email_shape(text: str):
    low = text.lower()
    if not (any(low.startswith(g) for g in _GREET) and any(s in low for s in _SIGN)):
        return None
    t = text
    m = re.search(r"[,.]", t)
    if m and m.start() < 40:
        t = t[:m.start()].strip() + ",\n\n" + t[m.start() + 1:].strip()
    for phrase in _SIGN:
        idx = t.lower().rfind(phrase)
        if idx != -1:
            t = t[:idx].strip() + "\n\n" + _sentence(t[idx:].strip())
            break
    return t


def _sentence(s: str) -> str:
    s = _collapse(s.strip())
    return (s[0].upper() + s[1:]) if s and s[0].islower() else s


def _collapse(s: str) -> str:
    return re.sub(r" {2,}", " ", s).replace(" ,", ",").replace(" .", ".")
