"""Unica fonte de instanciacao de modelo LLM do projeto.

Nenhum outro modulo deve construir um `GatewayChat`/`OpenAIChat`.

Todo provider passa pelo gateway LiteLLM (`PROXY_AI_BASE_URL`) — nao ha
caminho direto para `api.anthropic.com`/`api.openai.com`. O que muda entre
`anthropic` e `openai` e so o `id` (o alias registrado no gateway); os dois
casos usam o mesmo `GatewayChat`, o `OpenAIChat` do agno sem as tool calls
fantasma (ver `gateway_model.py`).

Nao ha sobrescrita de modelo por usuario aqui: esta aplicacao nao tem banco
(ver decisao de escopo no CLAUDE.md). O parametro `user_id` permanece na
assinatura porque e o ponto de extensao natural caso isso mude.
"""

from src.ai_modules.gateway_model import GatewayChat
from src.api.core.config import get_app_settings
from src.api.logger import logger

# Modelos que so aceitam temperature=1 (o default deles). Checado via startswith.
_FIXED_TEMP_MODELS = ("o1", "o3", "o4", "gpt-5.5")

DEFAULT_TEMPERATURE = 0.3


async def get_model(
    provider: str | None = None,
    user_id: str | None = None,
) -> GatewayChat:
    """Instancia o modelo do provider pedido, ou do configurado no ambiente."""
    settings = get_app_settings()
    chosen = (provider or settings.LLM_PROVIDER).lower()

    match chosen:
        case "anthropic":
            return _gateway_model(settings.ANTHROPIC_MODEL, thinking=True)
        case "openai":
            return _gateway_model(settings.OPENAI_MODEL, thinking=False)
        case _:
            logger.warning("provider '%s' nao suportado — usando anthropic", chosen)
            return _gateway_model(settings.ANTHROPIC_MODEL, thinking=True)


def _gateway_model(model_id: str, thinking: bool) -> GatewayChat:
    settings = get_app_settings()

    args: dict = {
        "id": model_id,
        "api_key": settings.LITELLM_API_KEY,
        "base_url": settings.PROXY_AI_BASE_URL,
    }

    if thinking:
        # O gateway traduz `reasoning_effort` para `thinking.budget_tokens` na
        # Anthropic, que exige `max_tokens` maior que esse orcamento — sem
        # `max_completion_tokens` aqui a Anthropic recusa a request.
        args["extra_body"] = {"reasoning_effort": settings.ANTHROPIC_EFFORT}
        args["max_completion_tokens"] = settings.ANTHROPIC_MAX_TOKENS
    elif _supports_temperature(model_id):
        args["temperature"] = DEFAULT_TEMPERATURE

    return GatewayChat(**args)


def _supports_temperature(model_id: str) -> bool:
    return not any(model_id.startswith(prefix) for prefix in _FIXED_TEMP_MODELS)
