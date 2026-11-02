# syntax=docker/dockerfile:1.7-labs
# One image for the API and the review app (Phase 4). Build and run with: docker compose up --build
# The image carries the Lakeview sample, the knowledge documents and the reply caches, so the Lakeview sample
# replays at $0 with Azure settings. Those include public product brochures: keep any pushed image private.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app \
    && mkdir /app && chown app:app /app
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /uvx /usr/local/bin/

ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 UV_PYTHON_DOWNLOADS=never UV_NO_CACHE=1 PYTHONUNBUFFERED=1
WORKDIR /app
USER app
COPY --chown=app:app pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project
# Large and rarely changing (cached replies, the Lakeview sample, brochure pages) in layers of their own,
# so a code change pushes a small layer. The glob makes .cache optional: a fresh clone has none.
COPY --chown=app:app .cach[e] .cache/
COPY --chown=app:app data data
COPY --chown=app:app --exclude=.cache --exclude=data . .
RUN uv sync --locked --no-dev && mkdir -p runs data/uploads
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000 8501
CMD ["specreview", "serve", "--host", "0.0.0.0", "--port", "8000"]
