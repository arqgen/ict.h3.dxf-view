from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    ENVIRONMENT: Literal["local", "dev", "prod"] = "local"
    HOST: str = "0.0.0.0"
    PORT: int = 8787

    LLM_PROVIDER: Literal["anthropic", "openai"] = "anthropic"

    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-opus-5"
    ANTHROPIC_MAX_TOKENS: int = 16000
    ANTHROPIC_EFFORT: Literal["low", "medium", "high", "xhigh", "max"] = "medium"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1"

    MAX_UPLOAD_MB: int = 64
    MAX_DOCUMENTS: int = 8
    DOCUMENT_TTL_SECONDS: int = 7200

    COLLECTOR_ENDPOINT: str = ""
    COLLECTOR_PROJECT_NAME: str = "CAD_VIEWER"

    @property
    def is_local(self) -> bool:
        return self.ENVIRONMENT in ("local", "dev")

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_app_settings() -> Settings:
    return Settings()
