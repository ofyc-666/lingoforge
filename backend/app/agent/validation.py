"""Agent 最终输出的最小校验。

包括 DAILY_LEARNING_PLAN 的专项校验：
  - 所有词属于候选池
  - 同一个词不能出现在多个角色
  - Skill 真实存在
  - rationale 和 decision_basis 非空
  - 不允许直接写画像
"""

from __future__ import annotations

import json
from typing import Any

from app.agent.models import DecisionValidationResult, RuntimeContext
from app.agent.skills import skill_exists


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

        # DAILY_LEARNING_PLAN 专项校验
        if parsed.get("decision_type") == "DAILY_LEARNING_PLAN":
            _validate_daily_plan_fields(parsed, errors)
        if context.workflow_stage == "DAILY_PLAN":
            _validate_daily_plan_context(parsed, errors)
        if context.workflow_stage == "ISOLATED_TEST":
            if parsed.get("decision_type") in ("DAILY_LEARNING_PLAN", "PLAN"):
                errors.append("DAILY_PLAN_FORBIDDEN_IN_ISOLATION")

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


def _validate_daily_plan_fields(decision: dict[str, Any], errors: list[str]) -> None:
    """校验 DAILY_LEARNING_PLAN 特有字段。"""
    vocab_plan = decision.get("daily_vocabulary_plan", {})
    if not isinstance(vocab_plan, dict):
        errors.append("MISSING_DAILY_VOCABULARY_PLAN")
        return

    # rationale 非空
    if not vocab_plan.get("selection_rationale", "").strip():
        errors.append("MISSING_RATIONALE")

    # decision_basis 非空
    if not decision.get("decision_basis"):
        errors.append("MISSING_DECISION_BASIS")

    # next_step 合理
    next_step = decision.get("next_step", "")
    if next_step not in ("START_VOCABULARY", "START_PRACTICE", "DONE"):
        errors.append(f"INVALID_NEXT_STEP:{next_step}")

    # 不允许直接写画像
    if decision.get("direct_profile_write") is True or decision.get("profile_update"):
        errors.append("DIRECT_PROFILE_WRITE_FORBIDDEN")

    # Skill 真实存在
    selected_skills = decision.get("selected_skills", [])
    if isinstance(selected_skills, list):
        for skill in selected_skills:
            if not isinstance(skill, dict):
                errors.append("INVALID_SKILL_ENTRY_TYPE")
                continue
            sid = skill.get("skill_id", "")
            if not skill_exists(sid):
                errors.append(f"SKILL_NOT_FOUND:{sid}")

    # Practice mode 校验
    practice_mode = decision.get("practice_mode", "")
    if not practice_mode:
        errors.append("MISSING_PRACTICE_MODE")


def _validate_daily_plan_context(decision: dict[str, Any], errors: list[str]) -> None:
    """DAILY_PLAN 阶段的 Context 级校验。"""
    # 不允许直接写画像
    if decision.get("direct_profile_write") is True:
        errors.append("DIRECT_PROFILE_WRITE_FORBIDDEN")

    # 必须包含 daily_vocabulary_plan
    if decision.get("decision_type") == "DAILY_LEARNING_PLAN":
        if "daily_vocabulary_plan" not in decision:
            errors.append("MISSING_DAILY_VOCABULARY_PLAN")
