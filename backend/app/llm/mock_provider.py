from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Sequence

from app.llm.types import LLMMessage, LLMResponse, LLMToolSpec


class MockLLMProvider:
    name = "mock"

    def __init__(self, responses: Iterable[LLMResponse] | None = None) -> None:
        self._responses: deque[LLMResponse] = deque(responses or [])

    def generate(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[LLMToolSpec] | None = None,
        timeout_seconds: float | None = None,
    ) -> LLMResponse:
        if self._responses:
            return self._responses.popleft()

        last_user_message = next((message.content for message in reversed(messages) if message.role == "user"), "")
        tool_names = [tool.name for tool in tools or ()]
        return LLMResponse(
            content=f"Mock response for: {last_user_message}".strip(),
            raw={
                "mode": "mock",
                "tool_names": tool_names,
                "timeout_seconds": timeout_seconds,
            },
        )

