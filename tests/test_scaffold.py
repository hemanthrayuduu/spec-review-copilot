import importlib
import socket

import pytest
import pytest_socket

STAGE_PACKAGES = ["llm", "ingest", "segment", "filter", "extract", "brief",
                  "knowledge", "match", "outputs", "eval"]


@pytest.mark.parametrize("name", STAGE_PACKAGES)
def test_stage_package_imports(name: str) -> None:
    importlib.import_module(f"spec_review.{name}")


@pytest.mark.filterwarnings("ignore:A test tried to use socket.socket")
def test_network_is_blocked() -> None:
    with pytest.raises(pytest_socket.SocketBlockedError):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
