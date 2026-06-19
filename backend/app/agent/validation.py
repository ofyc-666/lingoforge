"""Agent 最终输出的最小校验。"""

from __future__ import annotations

import json
from typing import Any

from app.agent.models import DecisionValidationResult, RuntimeContext


class DecisionValidator:
    """校验最终模型输出是否可作为本轮 AgentRun 决策记录。"""

    required_fields = ("decision_type", "next_step")

    def validate(
        self,
        content: str,
        _context: RuntimeContext,
        _tool_results: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], DecisionValidationResult]:
        try:
            parsed = json.loads(content) if content else {}
        except json.JSONDecodeError:
            decision = {
                "decision_type": "MODEL_TEXT",
                "next_step": "DONE",
                "final_answer": content,
                "decision_basis": [],
            }
            return decision, DecisionValidationResult(status="PASSED")

        if not isinstance(parsed, dict):
            decision = {
                "decision_type": "MODEL_TEXT",
                "next_step": "DONE",
                "final_answer": content,
                "decision_basis": [],
            }
            return decision, DecisionValidationResult(status="PASSED")

        missing = tuple(field for field in self.required_fields if field not in parsed)
        if missing:
            return parsed, DecisionValidationResult(
                status="FAILED",
                errors=tuple(f"MISSING_FIELD:{field}" for field in missing),
            )
        return parsed, DecisionValidationResult(status="PASSED")
