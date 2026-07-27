"""Unica fonte de instanciacao de modelo LLM do projeto.

Nenhum outro modulo deve construir um `Claude` ou um `OpenAIChat`.

Nao ha sobrescrita de modelo por usuario aqui: esta aplicacao nao tem banco
(ver decisao de escopo no CLAUDE.md). O parametro `user_id` permanece na
assinatura porque e o ponto de extensao natural caso isso mude.
"""

from agno.models.anthropic import Claude
from agno.models.base import Model
from agno.models.openai import OpenAIChat

from src.api.core.config import get_app_settings
from src.api.logger import logger

# Modelos que so aceitam temperature=1 (o default deles). Checado via startswith.
_FIXED_TEMP_MODELS = ("o1", "o3", "o4", "gpt-5.5")

DEFAULT_TEMPERATURE = 0.3


async def get_model(
    provider: str | None = None,
    user_id: str | None = None,
) -> Model:
    """Instancia o modelo do provider pedido, ou do configurado no ambiente."""
    settings = get_app_settings()
    chosen = (provider or settings.LLM_PROVIDER).lower()

    match chosen:
        case "anthropic":
            return _anthropic_model()
        case "openai":
            return _openai_model()
        case _:
            logger.warning("provider '%s' nao suportado — usando anthropic", chosen)
            return _anthropic_model()


def _anthropic_model() -> Claude:
    settings = get_app_settings()

    return Claude(
        id=settings.ANTHROPIC_MODEL,
        api_key=settings.ANTHROPIC_API_KEY,
        max_tokens=settings.ANTHROPIC_MAX_TOKENS,
        # Raciocinio resumido: o painel de chat o expoe num toggle "mostrar
        # raciocinio", entao pedimos o resumo e nao o bloco completo.
        thinking={"type": "adaptive", "display": "summarized"},
        output_config={"effort": settings.ANTHROPIC_EFFORT},
        # O resumo do desenho e um prefixo estavel enquanto o mesmo arquivo
        # estiver aberto — cachear evita repagar por ele a cada pergunta.
        cache_system_prompt=True,
    )


def _openai_model() -> OpenAIChat:
    settings = get_app_settings()

    args: dict = {
        "id": settings.OPENAI_MODEL,
        "api_key": settings.OPENAI_API_KEY,
    }

    if _supports_temperature(settings.OPENAI_MODEL):
        args["temperature"] = DEFAULT_TEMPERATURE

    return OpenAIChat(**args)


def _supports_temperature(model_id: str) -> bool:
    return not any(model_id.startswith(prefix) for prefix in _FIXED_TEMP_MODELS)
