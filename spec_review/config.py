"""Settings read from the environment and .env (spec section 11)."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = REPO_ROOT / ".env"  # the repo's .env, whatever the working directory
SOURCES_FILE = REPO_ROOT / "data" / "sources.yaml"
ENV_FILE: Path | None = DEFAULT_ENV_FILE


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
    azure_openai_reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None
    azure_openai_judge_reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None  # None: as above
    azure_search_endpoint: str = ""
    azure_search_key: SecretStr = SecretStr("")
    azure_search_index: str = "idx-knowledge"
    provider_search: Literal["memory", "azure"] = "memory"
    embed_price_per_mtok: float = Field(default=0.0, ge=0.0)
    knowledge_dir: Path = REPO_ROOT / "data" / "knowledge"  # anchored like .env, so any working directory works
    raw_dir: Path = REPO_ROOT / "data" / "raw"
    match_max_requirements: int = Field(default=1000, ge=0)  # bigger packages skip matching unless this is raised
    runs_dir: Path = REPO_ROOT / "runs"
    review_db: Path = REPO_ROOT / "runs" / "reviews.sqlite"  # review decisions, kept next to the runs they review
    uploads_dir: Path = REPO_ROOT / "data" / "uploads"
    api_url: str = "http://127.0.0.1:8000"  # where the review app finds the API
    max_upload_mb: int = Field(default=200, ge=1)
    confidence_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    llm_price_input_per_mtok: float = Field(default=0.0, ge=0.0)
    llm_price_output_per_mtok: float = Field(default=0.0, ge=0.0)
    llm_max_concurrency: int = Field(default=4, ge=1, le=32)
    llm_cache_dir: Path = Path(".cache/llm")
    mock_fixtures_dir: Path = Path(__file__).parent / "llm" / "fixtures"
    tessdata_prefix: Path | None = None  # folder holding eng.traineddata; None means search the usual places


def get_settings() -> Settings:
    """Read settings from the environment and ENV_FILE. Always use this, never Settings()."""
    return Settings(_env_file=ENV_FILE)  # type: ignore[call-arg]
