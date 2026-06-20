"""Agent 最终输出的最小校验。"""

from __future__ import annotations

import json
from typing import Any

from app.agent.models import DecisionValidationResult, RuntimeContext


class DecisionValidator:
    """校验最终模型输出是否可作为本轮 AgentRun 决策记录。"""

    required_fields = ("decision_type", "next_step")
    default_fields: dict[str, Any] = {
        "objective": "",
        "target_abilities": [],
        "selected_skills": [],
        "training_parameters": {},
        "adaptation_action": "CONTINUE",
        "decision_basis": [],
        "profile_refs": [],
        "memory_refs": [],
        "evidence_refs": [],
        "tool_result_refs": [],
        "expected_observations": [],
        "uncertainties": [],
        "plan_delta": {},
    }

    def validate(
        self,
        content: str,
        context: RuntimeContext,
        tool_results: list[dict[str, Any]],
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
            return self._normalize(decision, context, tool_results), DecisionValidationResult(status="PASSED")

        if not isinstance(parsed, dict):
            decision = {
                "decision_type": "MODEL_TEXT",
                "next_step": "DONE",
                "final_answer": content,
                "decision_basis": [],
            }
            return self._normalize(decision, context, tool_results), DecisionValidationResult(status="PASSED")

        missing = tuple(field for field in self.required_fields if field not in parsed)
        errors = [f"MISSING_FIELD:{field}" for field in missing]
        if parsed.get("workflow_stage") not in (None, context.workflow_stage):
            errors.append("WORKFLOW_STAGE_MISMATCH")
        if not isinstance(parsed.get("decision_basis", []), list):
            errors.append("INVALID_DECISION_BASIS")
        if parsed.get("direct_profile_write") is True:
            errors.append("DIRECT_PROFILE_WRITE_FORBIDDEN")

        normalized = self._normalize(parsed, context, tool_results)
        if errors:
            return normalized, DecisionValidationResult(
                status="FAILED",
                errors=tuple(errors),
            )
        return normalized, DecisionValidationResult(status="PASSED")

    def _normalize(
        self,
        decision: dict[str, Any],
        context: RuntimeContext,
        tool_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        normalized = dict(self.default_fields)
        normalized.update(decision)
        normalized["workflow_stage"] = context.workflow_stage
        if not normalized.get("objective"):
            normalized["objective"] = context.objective
        if not isinstance(normalized.get("tool_result_refs"), list) or not normalized["tool_result_refs"]:
            normalized["tool_result_refs"] = [
                result["log_id"] for result in tool_results if isinstance(result.get("log_id"), int)
            ]
        if not isinstance(normalized.get("decision_basis"), list):
            normalized["decision_basis"] = []
        return normalized

