"""Tracing via Arize Phoenix / OTLP.

Unico lugar do projeto autorizado a chamar `phoenix.otel.register` ou o
instrumentor do agno.
"""

from typing import Any

from src.api.core.config import get_app_settings
from src.api.logger import logger

# Guardado para o flush no shutdown. None enquanto o tracing nao subiu.
_provider: Any | None = None


def init_observability() -> None:
    """Instrumenta as chamadas do agno. Silencioso se nao houver collector.

    Em desenvolvimento local sem Docker basta deixar `COLLECTOR_ENDPOINT` vazio —
    a funcao retorna sem efeito e sem erro. Com Docker, `make phoenix-up` sobe o
    collector em http://localhost:6006.
    """
    global _provider

    settings = get_app_settings()
    if not settings.COLLECTOR_ENDPOINT:
        logger.debug("COLLECTOR_ENDPOINT vazio — observabilidade desligada")
        return

    try:
        from openinference.instrumentation.agno import AgnoInstrumentor
        from phoenix.otel import register

        provider = register(
            project_name=settings.COLLECTOR_PROJECT_NAME,
            endpoint=f"{settings.COLLECTOR_ENDPOINT.rstrip('/')}/v1/traces",
            auto_instrument=False,
        )
        AgnoInstrumentor().instrument(tracer_provider=provider)
        _provider = provider
        logger.info(
            "observabilidade ativa — projeto %s em %s",
            settings.COLLECTOR_PROJECT_NAME,
            settings.COLLECTOR_ENDPOINT,
        )
    except Exception as exc:
        # Tracing indisponivel nao pode impedir a API de subir.
        logger.warning("falha ao inicializar observabilidade: %s", exc)


def shutdown_observability() -> None:
    """Descarrega os spans pendentes. Silencioso se o tracing nunca subiu.

    Sem isso o buffer do exporter se perde quando o processo cai — comum em
    desenvolvimento, onde o reload derruba o servidor a cada alteracao.
    """
    global _provider

    if _provider is None:
        return

    try:
        _provider.shutdown()
        logger.debug("observabilidade encerrada — spans pendentes enviados")
    except Exception as exc:
        # Mesma regra do startup: falha de tracing nao derruba a API.
        logger.warning("falha ao encerrar observabilidade: %s", exc)
    finally:
        _provider = None
