"""Convert UFGS SpecsIntact .SEC files (XML, Windows-1252) to plain lines, and write the test fixtures.

UFGS guide specifications are public domain. The committed fixtures are the first lines of two sections.

    uv run python scripts/ufgs_to_text.py
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import typer

SKIP = {"HDR", "NTE", "DTE", "MTA", "TTL"}  # header block, editor's notes, date, metadata; titles go with parents
FIXTURES = (("46 61 00.SEC", "46_61_00.txt"), ("46 51 00.00 10.SEC", "46_51_00_00_10.txt"))
FIXTURE_LINES = 250
LINES_PER_PAGE = 60


def _text(el: ET.Element) -> str:
    """Inline text with <BRK/> as a space and metric alternates (<MET>) dropped, whitespace collapsed."""
    parts = [el.text or ""]
    for child in el:
        if child.tag == "BRK":
            parts.append(" ")
        elif child.tag not in ("MET", "NTE"):
            parts.append(_text(child))
        parts.append(child.tail or "")
    return " ".join("".join(parts).split())


def _title(el: ET.Element) -> str:
    ttl = el.find("TTL")  # an Element with no children is falsy, so never write `el.find(...) or ...`
    return _text(ttl) if ttl is not None else ""


def sec_to_lines(xml_text: str) -> list[str]:
    root = ET.fromstring(re.sub(r"^\s*<\?xml[^>]*\?>", "", xml_text))
    lines: list[str] = []

    def add(text: str) -> None:
        if text:
            lines.append(text)

    def walk(el: ET.Element, number: list[int]) -> None:
        sub = item = 0
        for ch in el:
            if ch.tag in SKIP:
                continue
            if ch.tag in ("SCN", "STL", "TXT"):
                add(_text(ch))
            elif ch.tag == "PRT":
                title = _title(ch)
                add(title)
                m = re.match(r"PART\s+(\d+)", title)
                walk(ch, [int(m.group(1)) if m else 0])
            elif ch.tag == "SPT":
                sub += 1
                path = [*number, sub]
                add(f"{'.'.join(map(str, path))} {_title(ch)}")
                walk(ch, path)
            elif ch.tag == "LST":
                add(_text(ch))
                item = 0
            elif ch.tag in ("ITM", "OLI"):
                add(f"{chr(ord('a') + item % 26)}. {_text(ch)}")
                item += 1
            elif ch.tag == "REF":
                rid = ""
                for part in ch:
                    if part.tag == "ORG":
                        add(_text(part))
                    elif part.tag == "RID":
                        rid = _text(part)
                    elif part.tag == "RTL":
                        add(f"{rid} {_text(part)}".strip())
            elif ch.tag == "TAB":
                for row in ch.iter("ROW"):
                    add(" | ".join(t for t in (_text(c) for c in row.iter("CEL")) if t))
            else:
                walk(ch, number)

    walk(root, [])
    return lines


def main(src_dir: Path = Path("data/raw/dev/ufgs_division_46"), out_dir: Path = Path("tests/fixtures/ufgs")) -> None:
    """Write the first FIXTURE_LINES lines of two sections, with a form feed every LINES_PER_PAGE lines."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for src_name, out_name in FIXTURES:
        lines = sec_to_lines((src_dir / src_name).read_text(encoding="cp1252"))[:FIXTURE_LINES]
        pages = ["\n".join(lines[i:i + LINES_PER_PAGE]) for i in range(0, len(lines), LINES_PER_PAGE)]
        (out_dir / out_name).write_text("\n\f\n".join(pages) + "\n")
        typer.echo(f"wrote {len(lines)} lines to {out_dir / out_name}")


if __name__ == "__main__":
    typer.run(main)
