from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, load_settings
from app.database import database_is_initialized, init_database
from app.llm.factory import create_llm_provider


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_database(app_settings.database_path)
        yield

    app = FastAPI(title=app_settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(app_settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, object]:
        provider = create_llm_provider(app_settings)
        return {
            "status": "ok",
            "service": app_settings.app_name,
            "config": app_settings.public_summary(),
            "database_initialized": database_is_initialized(app_settings),
            "llm_provider": provider.name,
        }

    return app


app = create_app()

