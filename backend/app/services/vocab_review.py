"""背词流程服务。

处理前端驱动的背词事件，确定性更新词汇状态。
客户端不得直接提交 familiarity_level、next_review_time、correct_count、wrong_count、learning_status。
这些字段只能由本服务根据原始事件更新。
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from app.constants import (
    FamiliarityLevel,
    LearningStatus,
    PromptDependency,
    ReviewEventType,
    SelfRating,
)
from app.repositories.base import fetch_one
from app.repositories.daily_plan import (
    create_review_event,
    get_user_vocabulary_state,
    update_plan_status,
    upsert_user_vocabulary_state,
)
from app.repositories.training import create_learning_evidence
from app.storage.json_fields import from_json_text

ALGORITHM_VERSION = "vocab-review-mvp-v1"


def process_review_events(
    database_path: str | Path,
    *,
    user_id: int,
    plan_id: int,
    events: list[dict[str, Any]],
    now: datetime.datetime | None = None,
) -> dict[str, Any]:
    """处理一批背词事件，返回更新后的词汇状态列表。

    now 参数允许测试注入固定时钟。
    """
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()

    # 校验计划归属
    plan = fetch_one(
        database_path,
        "SELECT * FROM daily_learning_plans WHERE id = ? AND user_id = ?",
        (plan_id, user_id),
    )
    if plan is None:
        raise ValueError("PLAN_NOT_FOUND_OR_ACCESS_DENIED")

    updated_states: list[dict[str, Any]] = []
    evidence_refs: list[int] = []

    for event in events:
        vocab_id = event["vocabulary_item_id"]
        event_type = event.get("event_type", "")

        # 保存原始背词事件
        review_event_id = create_review_event(
            database_path,
            user_id=user_id,
            vocabulary_item_id=vocab_id,
            event_type=event_type,
            plan_id=plan_id,
            answer_json=event.get("answer", {}),
            is_correct=event.get("is_correct"),
            self_rating=event.get("self_rating"),
            used_hint=event.get("used_hint", False),
            time_spent_seconds=event.get("time_spent_seconds"),
            occurred_at=now_iso,
        )

        # 获取或初始化词汇状态
        current_state = get_user_vocabulary_state(database_path, user_id, vocab_id)
        new_state = _compute_new_state(current_state, event, now_iso)
        new_state["evidence_refs"] = (current_state.get("evidence_refs", []) if current_state else []) + [review_event_id]

        state_id = upsert_user_vocabulary_state(
            database_path,
            user_id=user_id,
            vocabulary_item_id=vocab_id,
            learning_status=new_state["learning_status"],
            familiarity_level=new_state["familiarity_level"],
            first_seen_at=new_state.get("first_seen_at", now_iso if current_state is None else None),
            last_reviewed_at=new_state.get("last_reviewed_at", now_iso),
            last_success_at=new_state.get("last_success_at"),
            next_review_at=new_state.get("next_review_at"),
            correct_count=new_state.get("correct_count", 0),
            wrong_count=new_state.get("wrong_count", 0),
            context_error_count=new_state.get("context_error_count", 0),
            consecutive_correct=new_state.get("consecutive_correct", 0),
            consecutive_wrong=new_state.get("consecutive_wrong", 0),
            prompt_dependency=new_state.get("prompt_dependency", "LOW"),
            evidence_refs=new_state["evidence_refs"],
            algorithm_version=ALGORITHM_VERSION,
        )

        updated_states.append({
            "vocabulary_item_id": vocab_id,
            "state_id": state_id,
            "learning_status": new_state["learning_status"],
            "familiarity_level": new_state["familiarity_level"],
            "next_review_at": new_state.get("next_review_at"),
        })
        evidence_refs.append(review_event_id)

    # 记录学习证据
    evidence_id = create_learning_evidence(
        database_path,
        user_id=user_id,
        evidence_type="TRAINING_ANSWER",
        session_id=plan.get("session_id"),
        payload={
            "plan_id": plan_id,
            "event_count": len(events),
            "review_event_ids": evidence_refs,
            "algorithm_version": ALGORITHM_VERSION,
        },
    )

    return {
        "plan_id": plan_id,
        "processed_events": len(events),
        "updated_states": updated_states,
        "evidence_id": evidence_id,
        "algorithm_version": ALGORITHM_VERSION,
    }


def complete_vocabulary_phase(
    database_path: str | Path,
    plan_id: int,
    user_id: int,
) -> dict[str, Any]:
    """完成背词阶段。"""
    update_plan_status(database_path, plan_id, "VOCABULARY_COMPLETED")
    from app.repositories.daily_plan import get_daily_plan, get_plan_vocabulary_items
    plan = get_daily_plan(database_path, plan_id)
    vocab = get_plan_vocabulary_items(database_path, plan_id)
    return {
        "plan_id": plan_id,
        "status": "VOCABULARY_COMPLETED",
        "vocabulary_items_count": len(vocab),
    }


def _compute_new_state(
    current_state: dict[str, Any] | None,
    event: dict[str, Any],
    now_iso: str,
) -> dict[str, Any]:
    """根据原始事件计算新词汇状态。"""
    if current_state is None:
        state = {
            "learning_status": LearningStatus.NEW,
            "familiarity_level": FamiliarityLevel.UNKNOWN,
            "first_seen_at": now_iso,
            "last_reviewed_at": None,
            "last_success_at": None,
            "next_review_at": None,
            "correct_count": 0,
            "wrong_count": 0,
            "context_error_count": 0,
            "consecutive_correct": 0,
            "consecutive_wrong": 0,
            "prompt_dependency": PromptDependency.LOW,
            "evidence_refs": [],
        }
    else:
        state = dict(current_state)

    event_type = event.get("event_type", "")
    is_correct = event.get("is_correct")
    self_rating = event.get("self_rating")
    used_hint = event.get("used_hint", False)

    # 更新 last_reviewed_at
    state["last_reviewed_at"] = now_iso

    # WORD_SHOWN: 标记为见过
    if event_type == ReviewEventType.WORD_SHOWN:
        if state["learning_status"] == LearningStatus.NEW:
            state["learning_status"] = LearningStatus.LEARNING

    # SELF_RATING: 用户自评
    if event_type == ReviewEventType.SELF_RATING:
        if self_rating == SelfRating.KNOWN:
            state["familiarity_level"] = FamiliarityLevel.HIGH
            state["consecutive_correct"] = min(state.get("consecutive_correct", 0) + 1, 99)
            state["consecutive_wrong"] = 0
        elif self_rating == SelfRating.FUZZY:
            state["familiarity_level"] = FamiliarityLevel.MEDIUM
        elif self_rating == SelfRating.UNKNOWN:
            state["familiarity_level"] = FamiliarityLevel.LOW
            state["consecutive_wrong"] = min(state.get("consecutive_wrong", 0) + 1, 99)
            state["consecutive_correct"] = max(state.get("consecutive_correct", 0) - 1, 0)

    # MEANING_CHECK / CONTEXT_CHECK: 客观题
    if event_type in (ReviewEventType.MEANING_CHECK, ReviewEventType.CONTEXT_CHECK):
        if is_correct is True:
            state["correct_count"] = state.get("correct_count", 0) + 1
            state["consecutive_correct"] = min(state.get("consecutive_correct", 0) + 1, 99)
            state["consecutive_wrong"] = 0
            state["last_success_at"] = now_iso
        elif is_correct is False:
            state["wrong_count"] = state.get("wrong_count", 0) + 1
            state["consecutive_wrong"] = min(state.get("consecutive_wrong", 0) + 1, 99)
            state["consecutive_correct"] = max(state.get("consecutive_correct", 0) - 1, 0)
            if event_type == ReviewEventType.CONTEXT_CHECK:
                state["context_error_count"] = state.get("context_error_count", 0) + 1

    # 提示依赖
    if used_hint:
        state["prompt_dependency"] = PromptDependency.HIGH
    elif state.get("consecutive_correct", 0) >= 3:
        state["prompt_dependency"] = PromptDependency.LOW

    # 更新学习状态
    cc = state.get("consecutive_correct", 0)
    cw = state.get("consecutive_wrong", 0)
    if cc >= 5 and state.get("correct_count", 0) >= 10:
        state["learning_status"] = LearningStatus.MASTERED
    elif cc >= 3 and is_correct is True:
        state["learning_status"] = LearningStatus.REVIEWING
    elif cw >= 3:
        state["learning_status"] = LearningStatus.WEAK

    # 设置 next_review_at（简单规则）
    _set_next_review(state, now_iso)

    return state


def _set_next_review(state: dict[str, Any], now_iso: str) -> None:
    """设置下次复习时间（简单 MVP 规则，不宣称艾宾浩斯）。"""
    now = datetime.datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
    status = state.get("learning_status", "")

    if status == LearningStatus.NEW:
        delta = datetime.timedelta(hours=4)
    elif status == LearningStatus.LEARNING:
        delta = datetime.timedelta(hours=12)
    elif status == LearningStatus.WEAK:
        delta = datetime.timedelta(hours=6)
    elif status == LearningStatus.MASTERED:
        delta = datetime.timedelta(days=7)
    else:
        delta = datetime.timedelta(days=1)

    state["next_review_at"] = (now + delta).isoformat()
