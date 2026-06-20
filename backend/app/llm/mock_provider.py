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

        # 检测 DAILY_PLAN 上下文并输出合规计划
        if isinstance(last_user_message, str) and "候选词事件" in last_user_message:
            return _mock_daily_plan_response(last_user_message)

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


def _mock_daily_plan_response(context_str: str) -> LLMResponse:
    """输出合规的 DAILY_LEARNING_PLAN 决策。

    Mock 使用 1-based 词 ID，假设候选池至少有 6 个词。
    实际环境由 daily_plan 服务校验并自动修正。
    """
    decision = {
        "decision_type": "DAILY_LEARNING_PLAN",
        "workflow_stage": "DAILY_PLAN",
        "next_step": "START_VOCABULARY",
        "practice_mode": "TARGETED_PRACTICE",
        "objective": "基于候选词事件生成今日背词与针对性训练计划",
        "daily_vocabulary_plan": {
            "new_word_ids": [1, 2, 3],
            "review_word_ids": [4, 5],
            "priority_word_ids": [],
            "selection_rationale": "根据最近语境错误与到期复习安排",
        },
        "target_abilities": ["PARAPHRASE_LOCATION"],
        "selected_skills": [
            {
                "skill_id": "paraphrase_location",
                "version": "1.0.0",
                "reason": "历史分析显示同义替换定位持续存在问题",
            }
        ],
        "difficulty_params": {"hint_level": "MEDIUM", "difficulty": "MEDIUM"},
        "hint_strategy": {"max_hints_per_word": 2, "hint_granularity": "medium"},
        "estimated_minutes": 25,
        "decision_basis": [
            {
                "summary": "基于候选词事件和用户画像生成计划",
                "refs": ["candidate_event_ref", "profile_ref"],
            }
        ],
        "evidence_refs": [],
        "profile_refs": [],
        "memory_refs": [],
        "tool_result_refs": [],
        "expected_observations": ["用户在新词学习中是否依赖提示", "复习词的正确率变化"],
        "uncertainties": ["样本量较小，仅基于一次诊断"],
    }
    return LLMResponse(
        content=json.dumps(decision, ensure_ascii=False),
        raw={
            "mode": "mock",
            "type": "DAILY_LEARNING_PLAN",
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
                "intended_use": "DAILY_PLAN",
            }
        ],
        "reason": "需要确认同义替换定位错误是否持续存在",
        "intended_use": "DAILY_PLAN",
        "priority": "HIGH",
    }
    return LLMResponse(
        content=json.dumps(request, ensure_ascii=False),
        raw={
            "mode": "mock",
            "type": "CONTEXT_EXPANSION_REQUEST",
        },
    )
