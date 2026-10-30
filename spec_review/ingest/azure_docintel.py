"""Azure AI Document Intelligence OCR for scanned pages (spec 8.1, design 6).

Each scanned page goes as its own one-page PDF to the prebuilt-read model: the
free F0 tier reads only the first two pages of a request. Results are cached by
a hash of the page bytes, so a page is never paid for twice.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Protocol

import httpx

from spec_review.config import Settings
from spec_review.llm.client import LLMConfigError
from spec_review.models import BBox

API_VERSION = "2024-11-30"
MODEL = "prebuilt-read"
POINTS_PER_INCH = 72.0
MAX_RATE_RETRIES = 5


class DocIntelError(Exception):
    pass


class PageReader(Protocol):
    def read_page(self, pdf_bytes: bytes) -> list[tuple[str, BBox]]: ...


class DocIntelClient:
    def __init__(self, endpoint: str, key: str, *, http_client: httpx.Client | None = None,
                 cache_dir: Path | None = Path(".cache/docintel"), poll_seconds: float = 1.0,
                 timeout_seconds: float = 120.0) -> None:
        self.url = (f"{endpoint.rstrip('/')}/documentintelligence/documentModels/{MODEL}:analyze"
                    f"?api-version={API_VERSION}")
        self.headers = {"Ocp-Apim-Subscription-Key": key}
        self.http = http_client or httpx.Client(timeout=60.0)
        self.cache_dir = cache_dir
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds

    def read_page(self, pdf_bytes: bytes) -> list[tuple[str, BBox]]:
        """One-page PDF in; its text lines with bounding boxes in PDF points out."""
        cache = self.cache_dir / f"{hashlib.sha256(pdf_bytes).hexdigest()}.json" if self.cache_dir else None
        if cache is not None and cache.is_file():
            return [(t, tuple(b)) for t, b in json.loads(cache.read_text())]  # type: ignore[misc]
        lines = self._lines(self._analyze(pdf_bytes))
        if cache is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps([[t, list(b)] for t, b in lines]))
        return lines

    def _sleep(self, seconds: float) -> None:
        if self.poll_seconds:
            time.sleep(seconds)

    def _analyze(self, pdf_bytes: bytes) -> dict[str, Any]:
        for _ in range(MAX_RATE_RETRIES + 1):
            resp = self.http.post(self.url, content=pdf_bytes,
                                  headers={**self.headers, "Content-Type": "application/pdf"})
            if resp.status_code != 429:
                break
            self._sleep(min(float(resp.headers.get("Retry-After", "1")), 30.0))
        if resp.status_code != 202 or "Operation-Location" not in resp.headers:
            raise DocIntelError(f"analyze request failed: HTTP {resp.status_code}: {resp.text[:200]}")
        operation = resp.headers["Operation-Location"]
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            poll = self.http.get(operation, headers=self.headers)
            if poll.status_code == 429:
                self._sleep(min(float(poll.headers.get("Retry-After", "1")), 30.0))
                continue
            body = poll.json()
            status = body.get("status")
            if status == "succeeded":
                return body  # type: ignore[no-any-return]
            if status == "failed" or poll.status_code >= 400:
                raise DocIntelError(f"analysis failed: {body.get('error', {}).get('message', poll.text[:200])}")
            if time.monotonic() > deadline:
                raise DocIntelError(f"analysis still {status} after {self.timeout_seconds:.0f} s")
            self._sleep(self.poll_seconds)

    @staticmethod
    def _lines(body: dict[str, Any]) -> list[tuple[str, BBox]]:
        out: list[tuple[str, BBox]] = []
        for page in body.get("analyzeResult", {}).get("pages", []):
            if page.get("unit", "inch") != "inch":
                raise DocIntelError(f"unexpected unit {page.get('unit')!r}; PDF input reports inches")
            for line in page.get("lines", []):
                xs, ys = line["polygon"][0::2], line["polygon"][1::2]
                out.append((line["content"], (round(min(xs) * POINTS_PER_INCH, 2), round(min(ys) * POINTS_PER_INCH, 2),
                                              round(max(xs) * POINTS_PER_INCH, 2), round(max(ys) * POINTS_PER_INCH, 2))))
        return out


def docintel_from_settings(settings: Settings) -> DocIntelClient | None:
    """The client when PROVIDER_OCR=azure; None for local OCR."""
    if settings.provider_ocr != "azure":
        return None
    key = settings.azure_docintel_key.get_secret_value()
    missing = [env for env, value in (("AZURE_DOCINTEL_ENDPOINT", settings.azure_docintel_endpoint),
                                      ("AZURE_DOCINTEL_KEY", key)) if not value.strip()]
    if missing:
        raise LLMConfigError(missing)
    return DocIntelClient(settings.azure_docintel_endpoint, key)
