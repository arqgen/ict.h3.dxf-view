"""Testes do tracing via Arize Phoenix.

`init_observability()` engole qualquer excecao para nao derrubar a API — o que
torna a falha invisivel em runtime. Estes testes sao a rede que sobra: se o
instrumentor sumir do lock ou o endpoint for montado errado, quebram aqui em vez
de o tracing morrer em silencio.
"""

from unittest.mock import MagicMock, patch

import pytest

import src.api.observability as observability
from src.api.core.config import get_app_settings
from src.api.observability import init_observability, shutdown_observability


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    """Zera o cache de settings e o provider guardado entre os testes."""
    monkeypatch.setattr(observability, "_provider", None)
    get_app_settings.cache_clear()
    yield
    get_app_settings.cache_clear()


def test_instrumentor_do_agno_esta_instalado():
    """O import e lazy e protegido por try/except — sem isto some sem aviso."""
    from openinference.instrumentation.agno import AgnoInstrumentor  # noqa: F401


def test_sem_endpoint_nao_registra(monkeypatch):
    monkeypatch.setenv("COLLECTOR_ENDPOINT", "")
    with patch("phoenix.otel.register") as mock_register:
        init_observability()
        mock_register.assert_not_called()


def test_register_recebe_endpoint_de_traces(monkeypatch):
    monkeypatch.setenv("COLLECTOR_ENDPOINT", "http://localhost:6006")
    monkeypatch.setenv("COLLECTOR_PROJECT_NAME", "TEST_PROJECT")
    with (
        patch("phoenix.otel.register", return_value=MagicMock()) as mock_register,
        patch("openinference.instrumentation.agno.AgnoInstrumentor"),
    ):
        init_observability()
        mock_register.assert_called_once_with(
            project_name="TEST_PROJECT",
            endpoint="http://localhost:6006/v1/traces",
            auto_instrument=False,
        )


def test_barra_final_no_endpoint_nao_duplica(monkeypatch):
    monkeypatch.setenv("COLLECTOR_ENDPOINT", "http://localhost:6006/")
    with (
        patch("phoenix.otel.register", return_value=MagicMock()) as mock_register,
        patch("openinference.instrumentation.agno.AgnoInstrumentor"),
    ):
        init_observability()
        assert (
            mock_register.call_args.kwargs["endpoint"]
            == "http://localhost:6006/v1/traces"
        )


def test_instrumentor_recebe_o_provider(monkeypatch):
    monkeypatch.setenv("COLLECTOR_ENDPOINT", "http://localhost:6006")
    fake_provider = MagicMock()
    with (
        patch("phoenix.otel.register", return_value=fake_provider),
        patch("openinference.instrumentation.agno.AgnoInstrumentor") as mock_class,
    ):
        init_observability()
        mock_class.return_value.instrument.assert_called_once_with(
            tracer_provider=fake_provider
        )


def test_shutdown_faz_flush_do_provider(monkeypatch):
    monkeypatch.setenv("COLLECTOR_ENDPOINT", "http://localhost:6006")
    fake_provider = MagicMock()
    with (
        patch("phoenix.otel.register", return_value=fake_provider),
        patch("openinference.instrumentation.agno.AgnoInstrumentor"),
    ):
        init_observability()

    shutdown_observability()
    fake_provider.shutdown.assert_called_once()


def test_shutdown_sem_tracing_ativo_e_no_op():
    """Ninguem chamou init com collector — nao pode explodir no shutdown."""
    shutdown_observability()
