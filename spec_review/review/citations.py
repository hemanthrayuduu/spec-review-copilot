"""Where a citation opens (2026-11-03). Evidence from a public source links to that source: a PDF at the cited
page (browsers' PDF viewers honour #page=N), a web page as it is. Synthetic rows and past exceptions cite
fictional documents, so they get no link.
"""

from pathlib import Path

from spec_review.sources import load_sources

SourceLinks = dict[str, tuple[str, str]]  # source id -> (url, kind)


def source_links(path: Path) -> SourceLinks:
    return {s.id: (str(s.url), s.kind) for s in load_sources(path)}


def evidence_url(ref: str, page: int | None, links: SourceLinks) -> str | None:
    found = links.get(ref)
    if found is None:
        return None
    url, kind = found
    return f"{url}#page={page}" if kind == "file" and page else url
