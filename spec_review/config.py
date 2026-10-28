"""Settings read from the environment and .env (spec section 11)."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE: Path | None = Path(".env")


class Settings(BaseSettings):
    # Blank values in .env mean "use the default", so .env.example can be copied unchanged.
    model_config = SettingsConfigDict(env_ignore_empty=True, extra="ignore")

    provider_ocr: Literal["local", "azure"] = "local"
    provider_llm: Literal["mock", "azure"] = "mock"
    azure_docintel_endpoint: str = ""
    azure_docintel_key: SecretStr = SecretStr("")
    azure_openai_endpoint: str = ""
    azure_openai_key: SecretStr = SecretStr("")
    azure_openai_chat_deployment: str = ""
    azure_openai_embed_deployment: str = ""
    azure_search_endpoint: str = ""
    azure_search_key: SecretStr = SecretStr("")
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    llm_price_input_per_mtok: float = Field(default=0.0, ge=0.0)
    llm_price_output_per_mtok: float = Field(default=0.0, ge=0.0)
    mock_fixtures_dir: Path = Path(__file__).parent / "llm" / "fixtures"


def get_settings() -> Settings:
    """Read settings from the environment and ENV_FILE. Always use this, never Settings()."""
    return Settings(_env_file=ENV_FILE)  # type: ignore[call-arg]
