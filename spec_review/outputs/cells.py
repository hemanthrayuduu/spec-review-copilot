"""Spreadsheet cells hold PDF text and reviewer notes, which are untrusted: none of them may become a formula."""

from collections.abc import Iterable
from typing import Any


def keep_text(cells: Iterable[Any]) -> None:
    """openpyxl stores a string that starts with "=" as a formula; store it as text instead."""
    for cell in cells:
        if isinstance(cell.value, str) and cell.value.startswith("="):
            cell.data_type = "s"
