"""Rule 7: tests never see the developer's .env or shell keys, in fixtures of every scope."""

import pytest

from spec_review.config import Settings


@pytest.fixture(scope="module")
def module_settings() -> Settings:
    return Settings(_env_file=None)  # type: ignore[call-arg]


def test_module_scoped_fixtures_see_mock_defaults(module_settings: Settings) -> None:
    """Found when the shell exported PROVIDER_SEARCH=azure: a module fixture ran before the per-test cleanup and
    the pipeline tried to reach Azure AI Search."""
    s = module_settings
    assert (s.provider_llm, s.provider_ocr, s.provider_search) == ("mock", "local", "memory")
    assert not s.azure_openai_key.get_secret_value() and not s.azure_search_key.get_secret_value()
