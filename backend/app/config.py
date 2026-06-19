from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def default_database_path() -> str:
    return str(Path(tempfile.gettempdir()) / "lingoforge" / "lingoforge.sqlite3")


@dataclass(frozen=True)
class Settings:
    app_name: str = "LingoForge"
    app_env: str = "development"
    database_path: str = default_database_path()
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    llm_mode: str = "mock"
    llm_provider: str = "deepseek"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_thinking_enabled: bool = False

    @property
    def database_file(self) -> Path:
        return Path(self.database_path)

    def public_summary(self) -> dict[str, object]:
        return {
            "app_name": self.app_name,
            "app_env": self.app_env,
            "database_path": self.database_path,
            "llm_mode": self.llm_mode,
            "llm_provider": self.llm_provider,
            "deepseek_base_url": self.deepseek_base_url,
            "deepseek_model": self.deepseek_model,
            "deepseek_thinking_enabled": self.deepseek_thinking_enabled,
        }


def load_settings() -> Settings:
    cors = _as_list(os.getenv("CORS_ORIGINS"))
    return Settings(
        app_name=os.getenv("APP_NAME", "LingoForge"),
        app_env=os.getenv("APP_ENV", "development"),
        database_path=os.getenv("DATABASE_PATH") or default_database_path(),
        cors_origins=tuple(cors) if cors else ("http://localhost:5173", "http://127.0.0.1:5173"),
        llm_mode=os.getenv("LLM_MODE", "mock"),
        llm_provider=os.getenv("LLM_PROVIDER", "deepseek"),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        deepseek_thinking_enabled=_as_bool(os.getenv("DEEPSEEK_THINKING_ENABLED"), default=False),
    )
