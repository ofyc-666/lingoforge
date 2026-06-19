from __future__ import annotations

from app.config import Settings, load_settings
from app.llm.mock_provider import MockLLMProvider
from app.llm.provider import LLMProvider, LLMProviderConfigurationError


def create_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or load_settings()
    if settings.llm_mode.lower() == "mock":
        return MockLLMProvider()

    if settings.llm_provider.lower() == "deepseek":
        raise LLMProviderConfigurationError(
            "DeepSeekProvider is planned but not implemented in this batch. Use LLM_MODE=mock."
        )

    raise LLMProviderConfigurationError(f"Unsupported LLM provider: {settings.llm_provider}")

