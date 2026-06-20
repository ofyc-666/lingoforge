from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ENV_FILE = _PROJECT_ROOT / ".env"


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


def _strip_env_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _read_env_file(path: str | Path | None) -> dict[str, str]:
    if path is None:
        return {}
    env_path = Path(path)
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = _strip_env_value(value)
    return values


def _env(name: str, file_values: dict[str, str], default: str | None = None) -> str | None:
    return os.getenv(name, file_values.get(name, default))


@dataclass(frozen=True)
class Settings:
    app_name: str = "LingoForge"
    app_env: str = "development"
    database_path: str = default_database_path()
    cors_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    llm_mode: str = "mock"
    llm_provider: str = "deepseek"
    deepseek_api_key: str | None = None
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


def load_settings(env_file: str | Path | None = _DEFAULT_ENV_FILE) -> Settings:
    file_values = _read_env_file(env_file)
    cors = _as_list(_env("CORS_ORIGINS", file_values))
    return Settings(
        app_name=_env("APP_NAME", file_values, "LingoForge") or "LingoForge",
        app_env=_env("APP_ENV", file_values, "development") or "development",
        database_path=_env("DATABASE_PATH", file_values) or default_database_path(),
        cors_origins=tuple(cors) if cors else ("http://localhost:5173", "http://127.0.0.1:5173"),
        llm_mode=_env("LLM_MODE", file_values, "mock") or "mock",
        llm_provider=_env("LLM_PROVIDER", file_values, "deepseek") or "deepseek",
        deepseek_api_key=_env("DEEPSEEK_API_KEY", file_values),
        deepseek_base_url=_env("DEEPSEEK_BASE_URL", file_values, "https://api.deepseek.com")
        or "https://api.deepseek.com",
        deepseek_model=_env("DEEPSEEK_MODEL", file_values, "deepseek-v4-flash") or "deepseek-v4-flash",
        deepseek_thinking_enabled=_as_bool(_env("DEEPSEEK_THINKING_ENABLED", file_values), default=False),
    )
