"""每日学习计划服务。

编排 DAILY_PLAN Workflow Stage：
  候选词筛选 → Agent 决策 → 校验 → 保存计划 → 保存计划词关联。
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from app.agent.models import RuntimeContext
from app.agent.runtime import AgentRuntime
from app.agent.skills import skill_exists
from app.constants import PlanStatus, PracticeMode, WordRole, WorkflowStage
from app.llm.provider import LLMProvider
from app.repositories.daily_plan import (
    add_plan_vocabulary_item,
    create_daily_plan,
    get_today_plan,
    update_plan_status,
)
from app.repositories.training import create_training_session
from app.services.candidate_vocab import generate_candidate_vocabulary


def generate_daily_plan(
    database_path: str | Path,
    *,
    provider: LLMProvider,
    user_id: int,
    regenerate: bool = False,
    preferred_practice_mode: str | None = None,
    max_new_words: int = 8,
    max_review_words: int = 12,
    now: datetime.datetime | None = None,
) -> dict[str, Any]:
    """生成或返回当天学习计划。

    同一天重复调用返回现有有效计划（除非 regenerate=True）。
    """
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # 幂等：同日重复调用返回现有计划（regenerate 时删除旧计划重建）
    if not regenerate:
        existing = get_today_plan(database_path, user_id, today_str)
        if existing is not None:
            from app.repositories.daily_plan import get_plan_vocabulary_items
            vocab_items = get_plan_vocabulary_items(database_path, existing["id"])
            return {
                **existing,
                "plan_id": existing.get("id"),
                "vocabulary_items": vocab_items,
                "regenerated": False,
            }
    else:
        # 删除当天旧计划
        existing = get_today_plan(database_path, user_id, today_str)
        if existing is not None:
            from app.repositories.base import execute
            execute(database_path, "DELETE FROM daily_plan_vocabulary_items WHERE plan_id = ?", (existing["id"],))
            execute(database_path, "DELETE FROM vocabulary_review_events WHERE plan_id = ?", (existing["id"],))
            execute(database_path, "DELETE FROM daily_learning_plans WHERE id = ?", (existing["id"],))

    # 1. 创建训练会话
    session_id = create_training_session(
        database_path,
        user_id=user_id,
        stage=WorkflowStage.DAILY_PLAN,
        status="IN_PROGRESS",
    )

    # 2. 确定性服务生成候选词事件
    candidate_result = generate_candidate_vocabulary(
        database_path,
        user_id=user_id,
        workflow_stage=WorkflowStage.DAILY_PLAN,
        max_new_words=max_new_words,
        max_review_words=max_review_words,
        now=now,
    )
    candidate_event_id = candidate_result["candidate_event_id"]

    # 3. Agent 决策：生成今日计划
    practice_mode = preferred_practice_mode or PracticeMode.TARGETED_PRACTICE
    context = RuntimeContext(
        user_id=user_id,
        session_id=session_id,
        workflow_stage=WorkflowStage.DAILY_PLAN,
        objective=f"根据候选词事件 {candidate_event_id} 生成今日学习计划，模式={practice_mode}",
        allowed_tools=("get_user_profile", "get_candidate_vocabulary", "analyze_learning_history"),
        permission_scope=("read_user_profile", "read_learning_history"),
    )
    agent_result = AgentRuntime(database_path=database_path, provider=provider).run(context)
    decision = agent_result.decision

    # 4. 解析 Agent 决策
    target_abilities = _safe_list(decision.get("target_abilities", []))
    selected_skills = _safe_list(decision.get("selected_skills", []))
    vocab_plan = decision.get("daily_vocabulary_plan", {})

    new_word_ids = _safe_int_list(vocab_plan.get("new_word_ids", []))
    review_word_ids = _safe_int_list(vocab_plan.get("review_word_ids", []))
    priority_word_ids = _safe_int_list(vocab_plan.get("priority_word_ids", []))
    rationale = str(vocab_plan.get("selection_rationale", decision.get("objective", "")))
    estimated_minutes = decision.get("estimated_minutes", 25)
    hint_strategy = _safe_dict(decision.get("hint_strategy", {}))
    difficulty_params = _safe_dict(decision.get("difficulty_params", {}))

    # 5. 业务层校验 + 自动修正出池词
    new_word_ids, review_word_ids, priority_word_ids = _validate_and_fix_daily_plan_decision(
        candidate_result["candidate_items"],
        new_word_ids,
        review_word_ids,
        priority_word_ids,
        target_abilities,
        selected_skills,
        practice_mode,
        rationale,
    )

    # 6. 保存计划
    plan_id = create_daily_plan(
        database_path,
        user_id=user_id,
        session_id=session_id,
        plan_date=today_str,
        status=PlanStatus.PLANNED,
        practice_mode=practice_mode,
        target_abilities=target_abilities,
        selected_skills=selected_skills,
        difficulty_params=difficulty_params,
        hint_strategy=hint_strategy,
        rationale=rationale,
        estimated_minutes=estimated_minutes,
        candidate_event_id=candidate_event_id,
        agent_decision_log_id=agent_result.agent_decision_log_id,
    )

    # 7. 保存计划词关联
    _save_plan_vocab(
        database_path, plan_id, new_word_ids, WordRole.NEW, candidate_result["candidate_items"]
    )
    _save_plan_vocab(
        database_path, plan_id, review_word_ids, WordRole.REVIEW, candidate_result["candidate_items"]
    )
    _save_plan_vocab(
        database_path, plan_id, priority_word_ids, WordRole.PRIORITY, candidate_result["candidate_items"]
    )

    from app.repositories.daily_plan import get_plan_vocabulary_items
    vocab_items = get_plan_vocabulary_items(database_path, plan_id)

    from app.repositories.daily_plan import get_daily_plan
    plan = get_daily_plan(database_path, plan_id)
    plan_dict = plan or {}
    return {
        **plan_dict,
        "plan_id": plan_dict.get("id") if plan_dict else plan_id,
        "vocabulary_items": vocab_items,
        "regenerated": False,
        "agent_run_id": agent_result.run_id,
        "candidate_event_id": candidate_event_id,
    }


def complete_vocabulary(
    database_path: str | Path,
    plan_id: int,
) -> dict[str, Any]:
    """完成今日背词阶段。"""
    update_plan_status(database_path, plan_id, PlanStatus.VOCABULARY_COMPLETED)
    from app.repositories.daily_plan import get_daily_plan, get_plan_vocabulary_items
    plan = get_daily_plan(database_path, plan_id)
    vocab = get_plan_vocabulary_items(database_path, plan_id)
    return {"plan_id": plan_id, "status": PlanStatus.VOCABULARY_COMPLETED, "vocabulary_items": vocab}


# ---- 校验 ----

def _validate_and_fix_daily_plan_decision(
    candidate_items: list[dict[str, Any]],
    new_ids: list[int],
    review_ids: list[int],
    priority_ids: list[int],
    target_abilities: list[str],
    selected_skills: list[dict[str, Any]],
    practice_mode: str,
    rationale: str,
) -> tuple[list[int], list[int], list[int]]:
    """校验并修正每日计划决策中的词选择。

    对于 Mock 模式可能产生的出池词 ID，自动从候选池补充合法词。
    返回修正后的 (new_ids, review_ids, priority_ids)。
    """
    from app.constants import Ability, CandidateRole

    candidate_item_ids = {c["vocabulary_item_id"] for c in candidate_items}
    candidate_by_role = {
        CandidateRole.NEW: [c["vocabulary_item_id"] for c in candidate_items if c["candidate_role"] == CandidateRole.NEW],
        CandidateRole.REVIEW: [c["vocabulary_item_id"] for c in candidate_items if c["candidate_role"] == CandidateRole.REVIEW],
        CandidateRole.PRIORITY: [c["vocabulary_item_id"] for c in candidate_items if c["candidate_role"] == CandidateRole.PRIORITY],
    }

    # 过滤出池词
    def fix_ids(ids: list[int], role: str) -> list[int]:
        valid = [i for i in ids if i in candidate_item_ids]
        if len(valid) < len(ids):
            # 从候选池补充
            available = candidate_by_role.get(role, [])
            for cid in available:
                if cid not in valid:
                    valid.append(cid)
                if len(valid) >= len(ids):
                    break
        return valid[:len(ids)] if ids else valid

    new_ids = fix_ids(new_ids, CandidateRole.NEW)
    review_ids = fix_ids(review_ids, CandidateRole.REVIEW)
    priority_ids = fix_ids(priority_ids, CandidateRole.PRIORITY)

    all_ids = set(new_ids + review_ids + priority_ids)

    # 同一个词不能出现在多个角色
    all_ids = set(new_ids + review_ids + priority_ids)
    intersection = (set(new_ids) & set(review_ids)) | (set(new_ids) & set(priority_ids)) | (set(review_ids) & set(priority_ids))
    if intersection:
        raise ValueError(f"WORD_ASSIGNED_MULTIPLE_ROLES:{intersection}")

    # 数量检查
    if len(new_ids) > 20 or len(review_ids) > 30 or len(priority_ids) > 20:
        raise ValueError("PLAN_WORD_COUNT_EXCEEDED")

    # Skill 真实存在
    for skill in selected_skills:
        if not isinstance(skill, dict):
            raise ValueError("INVALID_SKILL_ENTRY")
        sid = skill.get("skill_id", "")
        if not skill_exists(sid):
            raise ValueError(f"SKILL_NOT_FOUND:{sid}")

    # TARGETED_PRACTICE: 1-2 Skill
    if practice_mode == PracticeMode.TARGETED_PRACTICE:
        if len(selected_skills) < 1 or len(selected_skills) > 2:
            raise ValueError("TARGETED_PRACTICE_SKILL_COUNT")

    # COMPREHENSIVE_SIMULATION: 2-4 Skill
    if practice_mode == PracticeMode.COMPREHENSIVE_SIMULATION:
        if len(selected_skills) < 2 or len(selected_skills) > 4:
            raise ValueError("SIMULATION_SKILL_COUNT")
        skill_abilities = set()
        for s in selected_skills:
            if not isinstance(s, dict):
                continue
            from app.agent.skills import get_skill_definition
            full = get_skill_definition(s.get("skill_id", ""))
            if full:
                skill_abilities.add(full.get("target_ability", ""))
        if len(skill_abilities) < 2:
            raise ValueError("SIMULATION_LESS_THAN_TWO_ABILITIES")

    # rationale 非空
    if not rationale.strip():
        raise ValueError("MISSING_RATIONALE")

    return new_ids, review_ids, priority_ids


def _save_plan_vocab(
    database_path: str | Path,
    plan_id: int,
    word_ids: list[int],
    role: str,
    candidate_items: list[dict[str, Any]],
) -> None:
    candidate_map = {c["vocabulary_item_id"]: c for c in candidate_items}
    for idx, word_id in enumerate(word_ids):
        reason = candidate_map.get(word_id, {}).get("selection_reason", "")
        add_plan_vocabulary_item(
            database_path,
            plan_id=plan_id,
            vocabulary_item_id=word_id,
            word_role=role,
            item_order=idx,
            selection_reason=reason,
        )


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_int_list(value: Any) -> list[int]:
    if not isinstance(value, list):
        return []
    return [int(v) for v in value if isinstance(v, (int, float))]


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
