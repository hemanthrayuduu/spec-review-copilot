"""Text helpers shared by candidates, verification, the brief, and eval."""

import re
import unicodedata

_PUNCT = str.maketrans({"‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
                        "“": '"', "”": '"', "„": '"', "″": '"',
                        "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
                        "­": ""})
_LINE_END_HYPHEN = re.compile(r"(?<=[A-Za-z])- (?=[a-z])")

# Leading paragraph markers: 2.03, 2.03.B, 3.2, A., 1., a., (1), (a), 1), a). Paths never start with 0, so 0.1 stays.
MARKER = re.compile(r"^\s*(?:[1-9]\d*(?:\.\d+)+(?:\.[A-Za-z0-9]+)*|[A-Z]\.|\d{1,2}\.|[a-z]\.|\(\d{1,2}\)|\([a-z]\)"
                    r"|\d{1,2}\)|[a-z]\))\s+")

# Words that end in a period without ending the sentence.
ABBREVIATIONS = frozenset({"no", "nos", "in", "ft", "e.g", "i.e", "etc", "approx", "min", "max", "inc", "co", "corp",
                           "ltd", "u.s", "mr", "ms", "dr", "st", "ave", "fig", "figs", "sec", "vs", "lb", "lbs", "oz",
                           "sq", "cu", "ea", "ref", "deg", "gal", "hr", "hrs", "yr", "yrs", "mo", "std", "vol", "art",
                           "para", "div", "dia", "nom", "typ", "max", "pt", "ga", "ca"})
_BOUNDARY = re.compile(r"[.!?][\"')\]]?\s+(?=[\"'(\[]?[A-Z])")
_WORD_BEFORE = re.compile(r"([A-Za-z][A-Za-z.]*)\.[\"')\]]?$")

SPELLED = {w: n for n, w in enumerate(("one two three four five six seven eight nine ten eleven twelve thirteen "
                                       "fourteen fifteen sixteen seventeen eighteen nineteen twenty").split(), start=1)}
_TOKEN = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?(?!\d)|\d*\.\d+|\d+|[A-Za-z]+")


def norm_text(s: str) -> str:
    """NFKC, straight quotes, plain dashes, single spaces, and line-end hyphens rejoined. Case is kept."""
    s = unicodedata.normalize("NFKC", s).translate(_PUNCT)
    return _LINE_END_HYPHEN.sub("", " ".join(s.split())).strip()


def strip_marker(s: str) -> str:
    return MARKER.sub("", s, count=1).strip()


def split_sentences(text: str) -> list[str]:
    text = " ".join(text.split())
    out: list[str] = []
    start = 0
    for m in _BOUNDARY.finditer(text):
        word = _WORD_BEFORE.search(text[start:m.end()].rstrip())
        if word and word.group(1).lower().rstrip(".") in ABBREVIATIONS:
            continue
        out.append(text[start:m.end()].strip())
        start = m.end()
    if text[start:].strip():
        out.append(text[start:].strip())
    return out


def numbers_in(text: str) -> list[float]:
    """Every number in reading order: digits (thousands separators dropped) and spelled one to twenty."""
    out: list[float] = []
    for tok in _TOKEN.findall(text):
        if tok[0].isalpha():
            if tok.lower() in SPELLED:
                out.append(float(SPELLED[tok.lower()]))
        else:
            out.append(float(tok.replace(",", "")))
    return out
