from functools import lru_cache
from typing import Any

from agno.db.base import BaseDb
from agno.db.in_memory import InMemoryDb

from src.api.core.config import get_app_settings


@lru_cache
def get_agent_db() -> BaseDb:
    """Sessoes do agno em memoria, um store por processo.

    Sem `db` o agno nao guarda historico e o chat perde o contexto entre
    perguntas — o usuario nao poderia dizer "e a maior delas?" na segunda frase.
    `InMemoryDb` da esse historico sem exigir banco externo, o que e coerente
    com o documento tambem viver so em memoria: as duas coisas somem juntas
    quando o processo cai.
    """
    return InMemoryDb()


def get_base_agent_kwargs(db: BaseDb | None = None) -> dict[str, Any]:
    """Defaults de plataforma comuns a todo `Agent` do projeto."""
    settings = get_app_settings()

    return {
        "db": db or get_agent_db(),
        "markdown": True,
        "stream": True,
        "add_history_to_context": True,
        "num_history_runs": 10,
        "add_datetime_to_context": True,
        "tool_call_limit": 20,
        "cache_session": True,
        "debug_mode": settings.is_local,
        "debug_level": 1,
        "store_media": False,
    }
