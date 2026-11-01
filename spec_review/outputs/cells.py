"""Spreadsheet cells hold PDF text and reviewer notes, which are untrusted: none of them may become a formula."""

from collections.abc import Iterable

from openpyxl.cell.cell import Cell


def keep_text(cells: Iterable[Cell]) -> None:
    """openpyxl stores a string that starts with "=" as a formula; store it as text instead."""
    for cell in cells:
        if isinstance(cell.value, str) and cell.value.startswith("="):
            cell.data_type = "s"
