import uvicorn

from src.api.core.config import get_app_settings


def main():
    settings = get_app_settings()
    uvicorn.run(
        "src.api.server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT in ["dev", "local"],
        loop="uvloop",
    )


if __name__ == "__main__":
    main()
