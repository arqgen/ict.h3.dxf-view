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

    # Gateway LiteLLM. Todo provider passa por aqui — nao existe caminho direto
    # para api.openai.com/api.anthropic.com. Vazio derruba o startup, ver
    # `require_ai_gateway()`.
    PROXY_AI_BASE_URL: str = ""
    LITELLM_API_KEY: str = ""

    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    ANTHROPIC_MAX_TOKENS: int = 16000
    ANTHROPIC_EFFORT: Literal["low", "medium", "high", "xhigh", "max"] = "medium"

    OPENAI_MODEL: str = "gpt-5.5"

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


def require_ai_gateway() -> None:
    """Falha o startup sem gateway configurado.

    Todo trafego de LLM passa pelo gateway LiteLLM e nao ha caminho direto
    para os providers — melhor falhar cedo do que so na primeira mensagem
    de chat.
    """
    settings = get_app_settings()

    if not settings.PROXY_AI_BASE_URL:
        raise RuntimeError(
            "PROXY_AI_BASE_URL não configurada — todo tráfego de LLM passa pelo "
            "gateway LiteLLM e não há caminho direto para os providers."
        )

    if not settings.LITELLM_API_KEY:
        raise RuntimeError(
            "LITELLM_API_KEY não configurada — o gateway recusaria toda chamada "
            "com 401 na primeira mensagem de chat."
        )
