"""scripts/demo.sh runs Lakeview end to end in mock mode (Phase 4): no keys, no network, no cost."""

import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts/demo.sh"


def test_demo_script_is_executable_valid_bash_and_forces_mock_mode() -> None:
    assert SCRIPT.is_file() and os.access(SCRIPT, os.X_OK)
    assert subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True).returncode == 0
    text = SCRIPT.read_text()
    assert "PROVIDER_LLM=mock" in text and "PROVIDER_OCR=local" in text and "PROVIDER_SEARCH=memory" in text
