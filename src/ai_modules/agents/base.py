from typing import Any

from agno.db.mongo import AsyncMongoDb

from src.ai_modules.skills import get_skills
from src.api.core.config import get_app_settings


def get_base_agent_kwargs(db: AsyncMongoDb | None = None) -> dict[str, Any]:
    settings = get_app_settings()
    return {
        "db": db,
        "skills": get_skills(),
        "markdown": True,
        "stream": True,
        "enable_user_memories": True,
        "add_memories_to_context": True,
        "add_history_to_context": True,
        "add_datetime_to_context": True,
        "num_history_runs": 10,
        "tool_call_limit": 20,
        "cache_session": True,
        "debug_mode": settings.ENVIRONMENT in ["local", "dev"],
        "debug_level": 1,
        "send_media_to_model": True,
        "store_media": False,  # impede que links quebrados causem erro na sessao
    }
