"""Testes da fiacao do LLM: `get_model()` e a validacao de startup do gateway.

Tudo aqui e offline — `GatewayChat` so guarda os argumentos, nenhum cliente HTTP
sobe e nenhuma chamada sai. O que estes testes protegem e a montagem: se o
`reasoning_effort` deixar de ser enviado, se a `temperature` vazar para um modelo
que so aceita o default dela, ou se o startup parar de reclamar de gateway mal
configurado, quebra aqui em vez de virar 400/401 no primeiro chat.
"""

import asyncio

import pytest

from src.ai_modules.llm_settings import (
    DEFAULT_TEMPERATURE,
    _supports_temperature,
    get_model,
)
from src.api.core.config import get_app_settings, require_ai_gateway


@pytest.fixture(autouse=True)
def gateway_env(monkeypatch):
    """Ambiente minimo de gateway, com o cache de settings zerado nas duas pontas."""
    monkeypatch.setenv("PROXY_AI_BASE_URL", "https://gateway.local/v1")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-teste")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    monkeypatch.setenv("ANTHROPIC_MAX_TOKENS", "16000")
    monkeypatch.setenv("ANTHROPIC_EFFORT", "medium")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.5")
    get_app_settings.cache_clear()
    yield
    get_app_settings.cache_clear()


def test_anthropic_manda_reasoning_effort_e_max_completion_tokens():
    """Sem `max_completion_tokens` a Anthropic recusa a request com thinking."""
    model = asyncio.run(get_model())

    assert model.id == "claude-sonnet-4-6"
    assert model.api_key == "sk-teste"
    assert model.base_url == "https://gateway.local/v1"
    assert model.extra_body == {"reasoning_effort": "medium"}
    assert model.max_completion_tokens == 16000
    assert model.temperature is None


def test_openai_nao_manda_reasoning_effort():
    model = asyncio.run(get_model("openai"))

    assert model.id == "gpt-5.5"
    assert model.extra_body is None
    assert model.max_completion_tokens is None


def test_openai_com_modelo_de_temperatura_livre_usa_o_default(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1-nano")
    get_app_settings.cache_clear()

    model = asyncio.run(get_model("openai"))

    assert model.temperature == DEFAULT_TEMPERATURE


def test_provider_desconhecido_cai_no_anthropic():
    model = asyncio.run(get_model("gemini"))

    assert model.id == "claude-sonnet-4-6"
    assert model.extra_body == {"reasoning_effort": "medium"}


def test_provider_vem_do_ambiente_quando_nao_passado(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    get_app_settings.cache_clear()

    model = asyncio.run(get_model())

    assert model.id == "gpt-5.5"


@pytest.mark.parametrize("model_id", ["gpt-5.5", "o1-preview", "o3-mini", "o4-mini"])
def test_modelos_de_temperatura_fixa(model_id):
    assert _supports_temperature(model_id) is False


@pytest.mark.parametrize("model_id", ["claude-sonnet-4-6", "gpt-4.1-nano"])
def test_modelos_que_aceitam_temperatura(model_id):
    assert _supports_temperature(model_id) is True


def test_gateway_configurado_nao_derruba_o_startup():
    require_ai_gateway()


def test_sem_base_url_derruba_o_startup(monkeypatch):
    monkeypatch.setenv("PROXY_AI_BASE_URL", "")
    get_app_settings.cache_clear()

    with pytest.raises(RuntimeError, match="PROXY_AI_BASE_URL"):
        require_ai_gateway()


def test_sem_api_key_derruba_o_startup(monkeypatch):
    """Chave vazia passava o boot e so falhava com 401 no primeiro chat."""
    monkeypatch.setenv("LITELLM_API_KEY", "")
    get_app_settings.cache_clear()

    with pytest.raises(RuntimeError, match="LITELLM_API_KEY"):
        require_ai_gateway()
