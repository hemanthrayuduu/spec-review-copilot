"""Download the public sources listed in data/sources.yaml into data/raw/.

File sources land at data/raw/<role>/<id>/<id>.pdf. Landing pages need a
person: the script prints the URL and the folder to save the attachments into.
Raw files are gitignored and never committed.

Usage: uv run python scripts/download_sources.py [--role dev] [--force]
"""

from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Literal

import httpx
import typer
import yaml
from pydantic import BaseModel, ConfigDict, HttpUrl

Role = Literal["dev", "test", "stretch", "context", "knowledge", "reference"]

USER_AGENT = "spec-review-copilot/0.1 (public-data research prototype)"
PDF_MAGIC = b"%PDF-"
PDF_EOF = b"%%EOF"
PDF_WINDOW = 1024  # PDF readers accept the header in the first KB and %%EOF in the last KB


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    role: Role
    kind: Literal["file", "landing_page"]
    url: HttpUrl
    notes: str | None = None


class DuplicateSourceError(ValueError):
    pass


class DownloadResult(BaseModel):
    source_id: str
    outcome: Literal["downloaded", "skipped", "landing_page", "failed"]
    path: Path | None = None
    detail: str = ""


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate keys; plain PyYAML silently keeps the last one."""


def _construct_unique_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise DuplicateSourceError(f"duplicate key in sources file: {key!r}")
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


def load_sources(path: Path) -> list[Source]:
    data = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    return [Source(id=source_id, **entry) for source_id, entry in data["sources"].items()]


def target_dir(raw_root: Path, source: Source) -> Path:
    return raw_root / source.role / source.id


def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(transport=transport, follow_redirects=True, timeout=60.0,
                        headers={"User-Agent": USER_AGENT})


def download_file(client: httpx.Client, source: Source, raw_root: Path, *, force: bool = False) -> DownloadResult:
    """Fetch one file source. Only a complete, real PDF ever reaches the final path."""
    final = target_dir(raw_root, source) / f"{source.id}.pdf"
    if final.exists() and not force:
        return DownloadResult(source_id=source.id, outcome="skipped", path=final, detail="already downloaded")
    final.parent.mkdir(parents=True, exist_ok=True)
    part = final.with_name(final.name + ".part")
    try:
        with client.stream("GET", str(source.url)) as response:
            if not response.is_success:
                return DownloadResult(source_id=source.id, outcome="failed", detail=f"HTTP {response.status_code}")
            content_type = response.headers.get("content-type", "unknown")
            with part.open("wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
        with part.open("rb") as f:
            head = f.read(PDF_WINDOW)
            f.seek(max(0, part.stat().st_size - PDF_WINDOW))
            tail = f.read()
        if PDF_MAGIC not in head:
            return DownloadResult(source_id=source.id, outcome="failed",
                                  detail=f"not a PDF (content-type {content_type})")
        # Without a Content-Length, httpx cannot tell a body that stopped early from a complete one.
        if PDF_EOF not in tail:
            return DownloadResult(source_id=source.id, outcome="failed", detail="truncated PDF (no %%EOF)")
        part.replace(final)
    except httpx.HTTPError as exc:
        return DownloadResult(source_id=source.id, outcome="failed", detail=f"{type(exc).__name__}: {exc}")
    finally:
        # Covers every exit, including Ctrl-C, so a rerun never trusts a partial file.
        part.unlink(missing_ok=True)
    size_mb = final.stat().st_size / 1_000_000
    return DownloadResult(source_id=source.id, outcome="downloaded", path=final, detail=f"{size_mb:.1f} MB")


def landing_page_instructions(source: Source, raw_root: Path) -> DownloadResult:
    folder = target_dir(raw_root, source)
    folder.mkdir(parents=True, exist_ok=True)
    return DownloadResult(source_id=source.id, outcome="landing_page", path=folder,
                          detail=f"Open {source.url} and save the attachments into {folder}/")


def download_all(sources: list[Source], raw_root: Path, client: httpx.Client, *,
                 roles: set[str] | None = None, force: bool = False,
                 on_result: Callable[[DownloadResult], None] | None = None) -> list[DownloadResult]:
    """Handle each source on its own, so one failure never stops the rest."""
    results = []
    for source in sources:
        if roles and source.role not in roles:
            continue
        if source.kind == "landing_page":
            result = landing_page_instructions(source, raw_root)
        else:
            result = download_file(client, source, raw_root, force=force)
        if on_result is not None:
            on_result(result)
        results.append(result)
    return results


app = typer.Typer()


@app.command()
def main(
    sources: Path = Path("data/sources.yaml"),
    raw_root: Path = Path("data/raw"),
    role: Annotated[list[str] | None, typer.Option(help="Only sources with this role (repeatable).")] = None,
    force: bool = False,
) -> None:
    """Download every direct file in the sources list and print instructions for landing pages."""
    def report(result: DownloadResult) -> None:
        typer.echo(f"{result.outcome:<13}{result.source_id}  {result.detail}")

    with make_client() as client:
        results = download_all(load_sources(sources), raw_root, client,
                               roles=set(role) if role else None, force=force, on_result=report)
    counts = Counter(result.outcome for result in results)
    typer.echo(f"downloaded {counts['downloaded']}, skipped {counts['skipped']}, "
               f"landing pages {counts['landing_page']}, failed {counts['failed']}")
    if counts["failed"]:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
