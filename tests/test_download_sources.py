from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from scripts import download_sources
from scripts.download_sources import (
    DuplicateSourceError,
    Source,
    app,
    download_all,
    download_file,
    landing_page_instructions,
    load_sources,
    make_client,
)

REPO = Path(__file__).parents[1]
PDF = b"%PDF-1.7\n%test\n%%EOF\n"
SRC = Source(id="mr_specs", role="dev", kind="file", url="https://example.org/specs.pdf")
LANDING = Source(id="sandy", role="test", kind="landing_page", url="https://example.org/sandy")

Handler = Callable[[httpx.Request], httpx.Response]


def client_for(handler: Handler) -> httpx.Client:
    return make_client(httpx.MockTransport(handler))


def pdf_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "application/pdf"}, content=PDF)


def no_request(request: httpx.Request) -> httpx.Response:
    raise AssertionError(f"unexpected request to {request.url}")


def write_yaml(path: Path, body: str) -> Path:
    path.write_text(body)
    return path


def test_repo_sources_yaml_is_valid() -> None:
    sources = load_sources(REPO / "data" / "sources.yaml")
    assert len({s.id for s in sources}) == len(sources) > 0
    assert {s.kind for s in sources} == {"file", "landing_page"}


def test_duplicate_source_id_is_rejected(tmp_path: Path) -> None:
    entry = "    role: dev\n    kind: file\n    url: https://example.org/a.pdf\n"
    path = write_yaml(tmp_path / "sources.yaml", f"sources:\n  mountain:\n{entry}  mountain:\n{entry}")
    with pytest.raises(DuplicateSourceError, match="mountain"):
        load_sources(path)


def test_unknown_role_is_rejected(tmp_path: Path) -> None:
    path = write_yaml(tmp_path / "sources.yaml",
                      "sources:\n  x:\n    role: training\n    kind: file\n    url: https://example.org/a.pdf\n")
    with pytest.raises(ValidationError):
        load_sources(path)


def test_file_saved_under_role_and_id(tmp_path: Path) -> None:
    result = download_file(client_for(pdf_response), SRC, tmp_path)
    assert result.outcome == "downloaded"
    assert (tmp_path / "dev" / "mr_specs" / "mr_specs.pdf").read_bytes() == PDF


def test_html_response_is_not_saved(tmp_path: Path) -> None:
    def html(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>Access denied</html>")

    result = download_file(client_for(html), SRC, tmp_path)
    assert result.outcome == "failed" and "not a PDF" in result.detail
    assert not any(tmp_path.rglob("*.pdf*"))


def test_interrupted_download_leaves_no_file(tmp_path: Path) -> None:
    class Broken(httpx.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            yield PDF[:8]
            raise httpx.ReadError("connection reset")

    result = download_file(client_for(lambda request: httpx.Response(200, stream=Broken())), SRC, tmp_path)
    assert result.outcome == "failed"
    assert not any(tmp_path.rglob("*.pdf*"))


def test_truncated_pdf_without_length_is_not_saved(tmp_path: Path) -> None:
    class CutShort(httpx.SyncByteStream):
        # No Content-Length, so httpx cannot tell the server stopped early.
        def __iter__(self) -> Iterator[bytes]:
            yield b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog"

    result = download_file(client_for(lambda request: httpx.Response(200, stream=CutShort())), SRC, tmp_path)
    assert result.outcome == "failed" and "truncated" in result.detail
    assert not any(tmp_path.rglob("*.pdf*"))


def test_existing_file_is_skipped_without_a_request(tmp_path: Path) -> None:
    final = tmp_path / "dev" / "mr_specs" / "mr_specs.pdf"
    final.parent.mkdir(parents=True)
    final.write_bytes(PDF)
    assert download_file(client_for(no_request), SRC, tmp_path).outcome == "skipped"


def test_force_downloads_again(tmp_path: Path) -> None:
    final = tmp_path / "dev" / "mr_specs" / "mr_specs.pdf"
    final.parent.mkdir(parents=True)
    final.write_bytes(b"%PDF-1.0 old")
    result = download_file(client_for(pdf_response), SRC, tmp_path, force=True)
    assert result.outcome == "downloaded" and final.read_bytes() == PDF


def test_http_error_does_not_stop_other_sources(tmp_path: Path) -> None:
    missing = Source(id="a", role="dev", kind="file", url="https://example.org/a.pdf")
    present = Source(id="b", role="dev", kind="file", url="https://example.org/b.pdf")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404) if request.url.path == "/a.pdf" else pdf_response(request)

    results = download_all([missing, present], tmp_path, client_for(handler))
    assert [r.outcome for r in results] == ["failed", "downloaded"]
    assert "404" in results[0].detail


def test_landing_page_gives_folder_and_makes_no_request(tmp_path: Path) -> None:
    result = download_all([LANDING], tmp_path, client_for(no_request))[0]
    assert result == landing_page_instructions(LANDING, tmp_path)
    assert result.outcome == "landing_page"
    assert str(LANDING.url) in result.detail and str(tmp_path / "test" / "sandy") in result.detail
    assert (tmp_path / "test" / "sandy").is_dir()


def test_role_filter(tmp_path: Path) -> None:
    brochure = Source(id="brochure", role="knowledge", kind="file", url="https://example.org/b.pdf")
    results = download_all([SRC, brochure], tmp_path, client_for(pdf_response), roles={"knowledge"})
    assert [r.source_id for r in results] == ["brochure"]


def test_main_exits_nonzero_when_any_source_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_make_client = download_sources.make_client
    monkeypatch.setattr(download_sources, "make_client",
                        lambda transport=None: real_make_client(httpx.MockTransport(lambda r: httpx.Response(500))))
    sources = write_yaml(tmp_path / "sources.yaml",
                         "sources:\n  x:\n    role: dev\n    kind: file\n    url: https://example.org/a.pdf\n")
    result = CliRunner().invoke(app, ["--sources", str(sources), "--raw-root", str(tmp_path / "raw")])
    assert result.exit_code == 1
    assert "HTTP 500" in result.output and "failed 1" in result.output
