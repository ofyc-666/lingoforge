from __future__ import annotations

import json
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

        last_user_message = next(
            (message.content for message in reversed(messages) if message.role == "user"), ""
        )
        tool_names = [tool.name for tool in tools or ()]

        # 检测是否需要 Context Expansion
        if isinstance(last_user_message, str) and "run_id" in last_user_message:
            return _mock_context_expansion_response(tool_names)

        return LLMResponse(
            content=f"Mock response for: {last_user_message}".strip(),
            raw={
                "mode": "mock",
                "tool_names": tool_names,
                "timeout_seconds": timeout_seconds,
            },
        )


def _mock_context_expansion_response(tool_names: list[str]) -> LLMResponse:
    """输出模拟的 Context Expansion 请求。"""
    request = {
        "decision_type": "CONTEXT_EXPANSION_REQUEST",
        "requested_memory_ids": [],
        "requested_skill_ids": ["paraphrase_location"],
        "requested_history_analyses": [
            {
                "analysis_type": "PROBLEM_TIMELINE",
                "target": {
                    "ability": "PARAPHRASE_LOCATION",
                    "error_type": "SURFACE_MATCH_DISTRACTOR",
                },
                "intended_use": "TEXT_TRAINING",
            }
        ],
        "reason": "需要确认同义替换定位错误是否持续存在",
        "intended_use": "TEXT_TRAINING",
        "priority": "HIGH",
    }
    return LLMResponse(
        content=json.dumps(request, ensure_ascii=False),
        raw={
            "mode": "mock",
            "type": "CONTEXT_EXPANSION_REQUEST",
        },
    )
