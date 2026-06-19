import os

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


def test_cors_parsing_with_spaces(monkeypatch):
    """CORS 逗号分隔和空格裁剪。"""
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com, http://b.com , http://c.com")
    settings = load_settings()
    assert "http://a.com" in settings.cors_origins
    assert "http://b.com" in settings.cors_origins
    assert "http://c.com" in settings.cors_origins
    # 验证没有多余空格
    for origin in settings.cors_origins:
        assert origin == origin.strip()


def test_cors_empty_string_uses_default(monkeypatch):
    """空 CORS 字符串使用默认值。"""
    monkeypatch.setenv("CORS_ORIGINS", "")
    settings = load_settings()
    assert len(settings.cors_origins) == 2
    assert "http://localhost:5173" in settings.cors_origins


def test_cors_single_value(monkeypatch):
    """单个 CORS 值正常工作。"""
    monkeypatch.setenv("CORS_ORIGINS", "https://example.com")
    settings = load_settings()
    assert settings.cors_origins == ("https://example.com",)


def test_bool_true_variants(monkeypatch):
    """bool true 常见写法。"""
    for val in ("1", "true", "True", "TRUE", "yes", "YES", "on", "ON"):
        monkeypatch.setenv("DEEPSEEK_THINKING_ENABLED", val)
        settings = load_settings()
        assert settings.deepseek_thinking_enabled is True, f"failed for {val}"


def test_bool_false_variants(monkeypatch):
    """bool false 常见写法。"""
    for val in ("0", "false", "False", "FALSE", "no", "NO", "off", "OFF"):
        monkeypatch.setenv("DEEPSEEK_THINKING_ENABLED", val)
        settings = load_settings()
        assert settings.deepseek_thinking_enabled is False, f"failed for {val}"


def test_bool_unset_defaults_false(monkeypatch):
    """未设置时默认为 False。"""
    monkeypatch.delenv("DEEPSEEK_THINKING_ENABLED", raising=False)
    settings = load_settings()
    assert settings.deepseek_thinking_enabled is False


def test_public_summary_excludes_api_key(monkeypatch):
    """public_summary 不包含 DEEPSEEK_API_KEY。"""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-secret-12345")
    settings = load_settings()
    summary = settings.public_summary()
    assert "DEEPSEEK_API_KEY" not in summary
    assert "sk-secret-12345" not in str(summary)


def test_default_config_unchanged(monkeypatch):
    """默认配置保持不变。"""
    for key in (
        "APP_NAME", "DATABASE_PATH", "LLM_MODE", "LLM_PROVIDER",
        "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "DEEPSEEK_THINKING_ENABLED",
        "CORS_ORIGINS",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = load_settings()
    assert settings.app_name == "LingoForge"
    assert settings.app_env == "development"
    assert settings.llm_mode == "mock"
    assert settings.llm_provider == "deepseek"
    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.deepseek_model == "deepseek-v4-flash"
    assert settings.deepseek_thinking_enabled is False
    assert settings.cors_origins == ("http://localhost:5173", "http://127.0.0.1:5173")
    assert settings.database_path.endswith("lingoforge.sqlite3")
