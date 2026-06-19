from __future__ import annotations

from typing import Protocol, Sequence

from app.llm.types import LLMMessage, LLMResponse, LLMToolSpec


class LLMProviderError(RuntimeError):
    """Base error for provider failures."""


class LLMProviderConfigurationError(LLMProviderError):
    """Raised when the configured provider cannot be created."""


class LLMProvider(Protocol):
    name: str

    def generate(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[LLMToolSpec] | None = None,
        timeout_seconds: float | None = None,
    ) -> LLMResponse:
        """Return a model response, optionally containing tool calls."""

