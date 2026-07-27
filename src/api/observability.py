"""Tracing via Arize Phoenix / OTLP.

Unico lugar do projeto autorizado a chamar `phoenix.otel.register` ou o
instrumentor do agno.
"""

from src.api.core.config import get_app_settings
from src.api.logger import logger


def init_observability() -> None:
    """Instrumenta as chamadas do agno. Silencioso se nao houver collector.

    Em desenvolvimento local sem Docker basta deixar `COLLECTOR_ENDPOINT` vazio —
    a funcao retorna sem efeito e sem erro.
    """
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
        logger.info(
            "observabilidade ativa — projeto %s em %s",
            settings.COLLECTOR_PROJECT_NAME,
            settings.COLLECTOR_ENDPOINT,
        )
    except Exception as exc:
        # Tracing indisponivel nao pode impedir a API de subir.
        logger.warning("falha ao inicializar observabilidade: %s", exc)
