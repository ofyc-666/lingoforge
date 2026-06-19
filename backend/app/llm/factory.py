from __future__ import annotations

from app.config import Settings, load_settings
from app.llm.deepseek_provider import DeepSeekProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.provider import LLMProvider, LLMProviderConfigurationError


def create_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or load_settings()
    if settings.llm_mode.lower() == "mock":
        return MockLLMProvider()

    if settings.llm_provider.lower() == "deepseek":
        return DeepSeekProvider(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
            thinking_enabled=settings.deepseek_thinking_enabled,
        )

    raise LLMProviderConfigurationError(f"Unsupported LLM provider: {settings.llm_provider}")
