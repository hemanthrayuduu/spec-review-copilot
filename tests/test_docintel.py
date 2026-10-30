import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from spec_review.config import Settings
from spec_review.ingest.azure_docintel import DocIntelClient, DocIntelError, docintel_from_settings
from spec_review.llm.client import LLMConfigError

ENDPOINT = "https://di.cognitiveservices.azure.com/"


def fake_di(responses: list[httpx.Response], seen: list[httpx.Request], cache_dir: Path | None = None) -> DocIntelClient:
    it = iter(responses)

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return next(it)

    return DocIntelClient(ENDPOINT, "k", cache_dir=cache_dir, poll_seconds=0,
                          http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def analyze_result(lines: list[tuple[str, list[float]]], unit: str = "inch") -> dict[str, Any]:
    return {"status": "succeeded", "analyzeResult": {"pages": [
        {"pageNumber": 1, "unit": unit, "lines": [{"content": t, "polygon": p} for t, p in lines]}]}}


ACCEPTED = httpx.Response(202, headers={"Operation-Location": "https://di/op/1"})
TP_LINE = ("Total Phosphorus 0.1 mg/L", [1, 2, 4, 2, 4, 2.25, 1, 2.25])


def test_read_page_posts_polls_and_converts_inches() -> None:
    seen: list[httpx.Request] = []
    di = fake_di([ACCEPTED, httpx.Response(200, json={"status": "running"}),
                  httpx.Response(200, json=analyze_result([TP_LINE]))], seen)
    assert di.read_page(b"%PDF-1.7 page") == [("Total Phosphorus 0.1 mg/L", (72.0, 144.0, 288.0, 162.0))]
    assert str(seen[0].url) == ("https://di.cognitiveservices.azure.com/documentintelligence/documentModels/"
                                "prebuilt-read:analyze?api-version=2024-11-30")
    assert seen[0].method == "POST" and seen[0].content == b"%PDF-1.7 page"
    assert seen[0].headers["Ocp-Apim-Subscription-Key"] == "k"
    assert seen[0].headers["Content-Type"] == "application/pdf"
    assert [str(r.url) for r in seen[1:]] == ["https://di/op/1", "https://di/op/1"]


def test_failed_analysis_raises() -> None:
    di = fake_di([ACCEPTED, httpx.Response(200, json={"status": "failed", "error": {"message": "bad file"}})], [])
    with pytest.raises(DocIntelError, match="bad file"):
        di.read_page(b"x")


def test_rejected_request_raises() -> None:
    di = fake_di([httpx.Response(401, json={"error": {"message": "Access denied"}})], [])
    with pytest.raises(DocIntelError, match="401"):
        di.read_page(b"x")


def test_rate_limit_is_retried() -> None:
    seen: list[httpx.Request] = []
    di = fake_di([httpx.Response(429, headers={"Retry-After": "1"}), ACCEPTED,
                  httpx.Response(200, json=analyze_result([TP_LINE]))], seen)
    assert len(di.read_page(b"x")) == 1 and len(seen) == 3


def test_cache_hit_sends_no_request(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []
    first = fake_di([ACCEPTED, httpx.Response(200, json=analyze_result([TP_LINE]))], seen, tmp_path)
    lines = first.read_page(b"same page")
    again = fake_di([], seen, tmp_path)
    assert again.read_page(b"same page") == lines and len(seen) == 2
    assert json.loads(next(tmp_path.glob("*.json")).read_text())


def test_from_settings() -> None:
    assert docintel_from_settings(Settings(_env_file=None)) is None
    with pytest.raises(LLMConfigError, match="AZURE_DOCINTEL_KEY"):
        docintel_from_settings(Settings(_env_file=None, provider_ocr="azure", azure_docintel_endpoint=ENDPOINT))
    assert docintel_from_settings(Settings(_env_file=None, provider_ocr="azure", azure_docintel_endpoint=ENDPOINT,
                                           azure_docintel_key="k")) is not None


def test_auth_failure_stops_further_requests() -> None:  # final review I4
    seen: list[httpx.Request] = []
    di = fake_di([httpx.Response(401, json={"error": {"message": "Access denied"}})], seen)
    with pytest.raises(DocIntelError, match="AZURE_DOCINTEL_KEY"):
        di.read_page(b"a")
    with pytest.raises(DocIntelError, match="AZURE_DOCINTEL_KEY"):
        di.read_page(b"b")
    assert len(seen) == 1
