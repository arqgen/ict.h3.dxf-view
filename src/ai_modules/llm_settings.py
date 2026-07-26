from agno.db.mongo import AsyncMongoDb
from agno.models.openai import OpenAIChat

from src.api import logger
from src.api.core.config import get_app_settings

# Models that only accept temperature=1 (their default). Checked via startswith.
_FIXED_TEMP_MODELS = ("o1", "o3", "o4", "gpt-5.5")


async def get_model(
    provider: str = "openai",
    user_id: str | None = None,
    db: AsyncMongoDb | None = None,
) -> OpenAIChat:
    settings = get_app_settings()
    custom_settings = await get_custom_settings(user_id, db)

    match provider:
        case "openai":
            openai_args = {
                "id": "gpt-4.1",
                "temperature": 0.3,
                "api_key": settings.OPENAI_API_KEY,
            }

            if custom_settings:
                openai_args = custom_settings

            return OpenAIChat(**openai_args)
        case _:
            return OpenAIChat(id="gpt-4.1", api_key=settings.OPENAI_API_KEY)


async def get_custom_settings(
    user_id: str | None, db: AsyncMongoDb | None
) -> dict | None:
    if not user_id or not db:
        return None

    settings = get_app_settings()
    collection = db.db_client[settings.MONGO_DB_DATABASE]["settings"]
    doc = await collection.find_one({"_id": user_id})

    if not doc:
        return None

    if doc.get("provider", "openai") != "openai":
        logger.warning(
            "provider '%s' not supported yet — using defaults", doc.get("provider")
        )
        return None

    model_id: str = doc.get("model", "gpt-4.1")
    supports_temp = not any(model_id.startswith(p) for p in _FIXED_TEMP_MODELS)

    args: dict = {"id": model_id, "api_key": settings.OPENAI_API_KEY}

    if supports_temp:
        args["temperature"] = doc.get("temperatura", 0.3)

    if doc.get("max_tokens"):
        args["max_completion_tokens"] = doc["max_tokens"]

    if doc.get("url"):
        args["base_url"] = doc["url"]

    return args


async def get_user_instructions(
    user_id: str | None, db: AsyncMongoDb | None
) -> str | None:
    if not user_id or not db:
        return None

    settings = get_app_settings()
    collection = db.db_client[settings.MONGO_DB_DATABASE]["settings"]
    doc = await collection.find_one({"_id": user_id}, {"system_prompt": 1})

    if not doc:
        return None

    return doc.get("system_prompt") or None
