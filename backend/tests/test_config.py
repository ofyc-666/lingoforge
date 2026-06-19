from app.config import load_settings
from temp_paths import temp_db_path


def test_default_settings(monkeypatch):
    for key in (
        "APP_NAME",
        "DATABASE_PATH",
        "LLM_MODE",
        "LLM_PROVIDER",
        "DEEPSEEK_API_KEY",
        "DEEPSEEK_MODEL",
        "DEEPSEEK_THINKING_ENABLED",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = load_settings()

    assert settings.app_name == "LingoForge"
    assert settings.database_path.endswith("lingoforge.sqlite3")
    assert settings.llm_mode == "mock"
    assert settings.llm_provider == "deepseek"
    assert settings.deepseek_model == "deepseek-v4-flash"
    assert settings.deepseek_thinking_enabled is False


def test_settings_override(monkeypatch):
    db_path = temp_db_path("config")
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("DEEPSEEK_THINKING_ENABLED", "true")

    settings = load_settings()

    assert settings.database_path == str(db_path)
    assert settings.deepseek_thinking_enabled is True
    assert "DEEPSEEK_API_KEY" not in settings.public_summary()
