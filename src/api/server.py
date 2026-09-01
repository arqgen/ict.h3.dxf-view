from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.core.config import get_app_settings, require_ai_gateway
from src.api.logger import logger
from src.api.observability import init_observability
from src.api.routers import chat, documents


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_app_settings()
    require_ai_gateway()
    init_observability()
    logger.info(
        "cad_viewer no ar — ambiente %s, provider %s",
        settings.ENVIRONMENT,
        settings.LLM_PROVIDER,
    )
    yield


def create_app() -> FastAPI:
    settings = get_app_settings()

    app = FastAPI(
        title="CAD Viewer AI API",
        description="Indexa desenhos DXF e responde perguntas sobre eles",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS permissivo somente fora de producao. Em producao o frontend e servido
    # pelo mesmo host, ou as origens precisam ser declaradas.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_local else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(documents.router)
    app.include_router(chat.router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "environment": settings.ENVIRONMENT,
            "provider": settings.LLM_PROVIDER,
            "has_key": bool(settings.PROXY_AI_BASE_URL and settings.LITELLM_API_KEY),
        }

    return app


app = create_app()
