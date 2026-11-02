#!/usr/bin/env bash
# Lakeview end to end in mock mode: no keys, no network, no cost (Phase 4).
# Builds the synthetic Lakeview package in a temporary folder, runs every stage, and writes the five outputs.
# Mock mode checks the plumbing. Its replies are placeholders that are never built from golden labels (spec 5),
# so it finds no requirements and the checklist stays empty. Real results: run the Lakeview sample in the app with
# Azure set in .env, which replays cached replies at $0. The scores are in README.md.
set -euo pipefail
cd "$(dirname "$0")/.."

export PROVIDER_LLM=mock PROVIDER_OCR=local PROVIDER_SEARCH=memory  # overrides whatever .env says
export LLM_PRICE_INPUT_PER_MTOK=0 LLM_PRICE_OUTPUT_PER_MTOK=0 EMBED_PRICE_PER_MTOK=0  # mock calls cost nothing
work="$(mktemp -d)"
run_id="demo-$(date -u +%Y%m%dT%H%M%SZ)"

echo "Building the Lakeview package in $work ..."
uv run python -c "import sys; from pathlib import Path; sys.path.insert(0, 'scripts'); \
from make_lakeview import build_lakeview; build_lakeview(Path(sys.argv[1]))" "$work/lakeview"

echo "Running every stage (mock mode) as run $run_id ..."
uv run specreview run "$work/lakeview" --run-id "$run_id"

echo "Writing the outputs ..."
uv run specreview outputs "$run_id"

echo
echo "Done. Stage files and outputs: runs/$run_id/ (outputs in runs/$run_id/outputs/)."
echo "Mock mode found no requirements on purpose: it proves every stage runs with no keys and no network."
echo "Review it in the app: uv run specreview serve, then uv run streamlit run app/streamlit_app.py"
