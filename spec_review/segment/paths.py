"""Section keys and paragraph paths such as 2.03.B.4 (spec 8.2, 9)."""

import re

from spec_review.models import Part

PART_RE = re.compile(r"^PART\s+([1-9])\b")
LEVELS: tuple[tuple[int, re.Pattern[str]], ...] = (
    (1, re.compile(r"^(\d\.\d{2})(?=\s|$)")),  # CSI article: 2.03
    (1, re.compile(r"^(\d+(?:\.\d+)+)(?=\s|$)")),  # dotted, UFGS and RFP style: 1.2.1
    (2, re.compile(r"^([A-Z])\.(?=\s|$)")),
    (3, re.compile(r"^(\d{1,2})\.(?=\s|$)")),
    (4, re.compile(r"^([a-z])\.(?=\s|$)")),
    (5, re.compile(r"^\((\d{1,2})\)(?=\s|$)|^(\d{1,2})\)(?=\s|$)")),
    (6, re.compile(r"^\(([a-z])\)(?=\s|$)|^([a-z])\)(?=\s|$)")),
)
PARTS: dict[str, Part] = {"1": "general", "2": "products", "3": "execution"}


def section_key(number: str) -> str:
    """Matching key: 46 21 00, 462100, and 46_21_00 are the same section."""
    return re.sub(r"[\s_.\-]", "", number).upper()


def display_number(raw: str) -> str:
    """46_51_42.01 → 46 51 42.01; repeated spaces collapse."""
    return " ".join(raw.replace("_", " ").split())


def path_key(path: str) -> str:
    """2.03.B.4 and 2.3.b.4 compare equal."""
    return ".".join(str(int(p)) if p.isdigit() else p.upper() for p in path.split("."))


def part_of(path: str | None) -> Part:
    return PARTS.get(path[0], "none") if path else "none"


class PathBuilder:
    """Tracks the marker stack through a section. A dotted number is a complete path on its own."""

    def __init__(self) -> None:
        self.stack: dict[int, str] = {}
        self.part: str | None = None

    def start_section(self) -> None:
        self.stack, self.part = {}, None

    def feed(self, text: str) -> str | None:
        """The paragraph path for a block; text without a marker keeps the current path."""
        part = PART_RE.match(text)
        if part:
            self.stack, self.part = {}, part.group(1)
            return None
        if text.startswith("END OF SECTION"):
            return None
        for level, rx in LEVELS:
            m = rx.match(text)
            if not m:
                continue
            token = next(g for g in m.groups() if g is not None)
            if level == 1:
                first = token.split(".")[0]
                # A sentence continued from the previous page can start with "0.1 mg/L"; inside PART 2 only
                # 2.x numbers are articles.
                if first == "0" or (self.part is not None and first != self.part):
                    break
                self.stack = {1: token}
            else:
                self.stack = {k: v for k, v in self.stack.items() if k < level}
                self.stack[level] = token
            break
        return ".".join(self.stack[k] for k in sorted(self.stack)) or None
