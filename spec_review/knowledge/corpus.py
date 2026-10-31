"""The evidence corpus: capability rows, past exceptions, and product-document page chunks (design 7.2, 7.4)."""

import re
from dataclasses import dataclass
from pathlib import Path

from spec_review.knowledge.capabilities import SYNTHETIC_DOC_ID, read_pages, source_file
from spec_review.models import Capability, Evidence, Origin, PastException
from spec_review.sources import Source


@dataclass
class DocPages:
    source_id: str
    url: str
    origin: Origin
    pages: list[str]


def load_doc_pages(sources: list[Source], raw_dir: Path) -> tuple[list[DocPages], list[str]]:
    """The evidence: true documents plus the synthetic document. A missing file is a note, not an error."""
    docs: list[DocPages] = []
    notes: list[str] = []
    for s in sources:
        if not s.evidence:
            continue
        if (path := source_file(raw_dir, s.id)) is None:
            notes.append(f"{s.id}: product document not found under {raw_dir / 'knowledge'}; not searched")
            continue
        docs.append(DocPages(s.id, str(s.url), "public", read_pages(path)))
    if (path := source_file(raw_dir, SYNTHETIC_DOC_ID)) is None:
        notes.append(f"{SYNTHETIC_DOC_ID}: not rendered (run scripts/make_knowledge.py); not searched")
    else:
        docs.append(DocPages(SYNTHETIC_DOC_ID, f"synthetic:{SYNTHETIC_DOC_ID}", "synthetic", read_pages(path)))
    return docs, notes


def _pieces(paragraph: str, max_chars: int) -> list[str]:
    if len(paragraph) <= max_chars:
        return [paragraph]
    out: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
        while len(sentence) > max_chars:  # a run-on table row: cut at a space
            cut = sentence.rfind(" ", 0, max_chars) if " " in sentence[:max_chars] else max_chars
            out.append(sentence[:cut])
            sentence = sentence[cut:].strip()
        if sentence:
            out.append(sentence)
    return out


def chunk_page(text: str, max_chars: int = 1200) -> list[str]:
    """Paragraphs packed into chunks of at most max_chars, with whitespace collapsed."""
    chunks: list[str] = []
    current = ""
    for para in re.split(r"\n\s*\n", text):
        for piece in _pieces(" ".join(para.split()), max_chars):
            if not piece:
                continue
            if current and len(current) + 1 + len(piece) > max_chars:
                chunks.append(current)
                current = piece
            else:
                current = f"{current} {piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks


def _value(c: Capability) -> str:
    if c.value_text:
        return c.value_text
    lo, hi = c.min_value, c.max_value
    span = f"{lo:g}" if lo == hi else f"{'' if lo is None else f'{lo:g}'} to {'' if hi is None else f'{hi:g}'}".strip()
    return f"{span} {c.unit or ''}".strip()


def build_corpus(caps: list[Capability], exceptions: list[PastException], docs: list[DocPages]) -> list[Evidence]:
    items = [Evidence(evidence_id=f"cap:{c.capability_id}", source="capability", ref=c.source_id, page=c.source_page,
                      text=f'{c.product_line}: {c.parameter}: {_value(c)} ({c.basis}, {c.origin}). "{c.source_text}"',
                      score=0.0, origin=c.origin, basis=c.basis, product_line=c.product_line) for c in caps]
    items += [Evidence(evidence_id=f"pe:{p.exception_id}", source="past_exception", ref="past_exceptions.csv",
                       text=f"Past {p.response_type} (fictional, {p.year}, {p.project}). Requirement: {p.requirement} "
                            f"Response: {p.response} Outcome: {p.outcome}.",
                       score=0.0, origin="synthetic", product_line=p.product_line) for p in exceptions]
    for d in docs:
        for page, text in enumerate(d.pages, start=1):
            for n, chunk in enumerate(chunk_page(text), start=1):
                items.append(Evidence(evidence_id=f"doc:{d.source_id}:p{page}:c{n}", source="product_doc",
                                      ref=d.source_id, page=page, text=chunk, score=0.0, origin=d.origin))
    return items
