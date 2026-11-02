"""Spreadsheet cells and letter paragraphs hold PDF text, model replies and reviewer notes, all untrusted: none
of it may become a formula, and none of it may stop a writer."""

import re
from collections.abc import Iterable
from typing import Any

# XML 1.0 refuses these, so openpyxl and python-docx (lxml) raise on them. Tab, newline and return are allowed.
_ILLEGAL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
# gpt-5-mini sometimes writes U+2010 to U+201F (dashes and curly quotes) as \u0010 to \u001f, dropping the high
# byte; on Avila Beach the page's "Proposal Form – Section 3" came back as "Proposal Form \x13 Section 3".
_LOST_HIGH_BYTE = {chr(c): chr(0x2000 + c) for c in range(0x10, 0x20)}


def printable(value: Any) -> Any:
    """Text that every writer accepts: a lost-high-byte dash or quote is restored, any other control character
    becomes a space. Values that are not text pass through."""
    if not isinstance(value, str):
        return value
    return _ILLEGAL.sub(lambda m: _LOST_HIGH_BYTE.get(m.group(), " "), value)


def printable_row(values: Iterable[Any]) -> list[Any]:
    return [printable(v) for v in values]


def keep_text(cells: Iterable[Any]) -> None:
    """openpyxl stores a string that starts with "=" as a formula; store it as text instead."""
    for cell in cells:
        if isinstance(cell.value, str) and cell.value.startswith("="):
            cell.data_type = "s"
