"""确定性候选词筛选服务。

输入 CET-6 词表、用户词汇状态、复习时间、历史错误、用户画像和目标，
输出候选词事件和结构化候选词列表。

不调用 LLM，使用简单透明可测试的 MVP 规则。
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from app.constants import CandidateRole, LearningStatus, ReviewStatus
from app.repositories.base import fetch_all, fetch_one
from app.repositories.vocabulary import create_candidate_event, list_vocabulary_by_source
from app.storage.json_fields import from_json_text, to_json_text

ALGORITHM_VERSION = "candidate-filter-mvp-v1"


def generate_candidate_vocabulary(
    database_path: str | Path,
    *,
    user_id: int,
    workflow_stage: str = "DAILY_PLAN",
    max_new_words: int = 8,
    max_review_words: int = 12,
    max_priority_words: int = 10,
    now: datetime.datetime | None = None,
) -> dict[str, Any]:
    """生成候选词事件并返回结构化结果。

    now 参数允许测试注入固定时钟，默认使用当前 UTC 时间。
    """
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()

    # 1. 获取所有 CET-6 词汇
    cet6_words = list_vocabulary_by_source(database_path, "CET6_VOCAB")
    if not cet6_words:
        # fallback: 尝试获取所有词汇（包括 demo seed）
        from app.repositories.vocabulary import list_all_vocabulary
        cet6_words = list_all_vocabulary(database_path)

    # 2. 获取用户词汇状态
    user_states = _get_user_vocabulary_states(database_path, user_id)

    # 3. 获取用户画像
    from app.repositories.users import get_latest_profile
    profile = get_latest_profile(database_path, user_id)
    profile_data = profile.get("profile_json", {}) if profile else {}

    # 4. 获取用户目标
    from app.repositories.users import get_latest_user_goal
    goal = get_latest_user_goal(database_path, user_id)

    # 5. 获取副线待验证信号
    sidequest_signals = _get_pending_sidequest_signals(database_path, user_id)

    # 6. 构建每个词的候选信息
    candidate_items: list[dict[str, Any]] = []
    state_map = {s["vocabulary_item_id"]: s for s in user_states}

    for word in cet6_words:
        word_id = word["id"]
        state = state_map.get(word_id)

        learning_status = state.get("learning_status", "NEW") if state else "NEW"
        candidate_role = _determine_candidate_role(word_id, state, sidequest_signals, now_iso)
        review_priority, review_status = _calculate_review_priority(state, now_iso)
        selection_reason = _build_selection_reason(learning_status, candidate_role, review_status, profile_data)

        candidate_items.append({
            "vocabulary_item_id": word_id,
            "text": word["text"],
            "meaning_zh": word.get("meaning_zh", ""),
            "part_of_speech": word.get("part_of_speech", ""),
            "tags": word.get("tags", []),
            "learning_status": learning_status,
            "candidate_role": candidate_role,
            "review_status": review_status,
            "review_priority": round(review_priority, 2),
            "last_reviewed_at": state.get("last_reviewed_at") if state else None,
            "next_review_at": state.get("next_review_at") if state else None,
            "correct_count": state.get("correct_count", 0) if state else 0,
            "wrong_count": state.get("wrong_count", 0) if state else 0,
            "context_error_count": state.get("context_error_count", 0) if state else 0,
            "recent_error_types": _get_recent_error_types(state),
            "evidence_refs": from_json_text(state.get("evidence_refs"), []) if state else [],
            "selection_reason": selection_reason,
        })

    # 7. 排序：PRIORITY > REVIEW > NEW，同级按 review_priority 降序
    role_order = {CandidateRole.PRIORITY: 0, CandidateRole.REVIEW: 1, CandidateRole.NEW: 2}
    candidate_items.sort(key=lambda x: (role_order.get(x["candidate_role"], 99), -x["review_priority"]))

    # 8. 数量限制
    new_items = [c for c in candidate_items if c["candidate_role"] == CandidateRole.NEW][:max_new_words]
    review_items = [c for c in candidate_items if c["candidate_role"] == CandidateRole.REVIEW][:max_review_words]
    priority_items = [c for c in candidate_items if c["candidate_role"] == CandidateRole.PRIORITY][:max_priority_words]
    limited_candidates = priority_items + review_items + new_items

    # 9. 获取副线信号 ID 列表
    signal_ids = [s["id"] for s in sidequest_signals] if sidequest_signals else []

    # 10. 生成选择原因摘要
    summary_reason = (
        f"基于 CET-6 词表 {len(cet6_words)} 词，用户 {len(user_states)} 条词汇状态，"
        f"画像 {list(profile_data.keys()) if profile_data else '无'}，"
        f"副线信号 {len(signal_ids)} 条，"
        f"生成候选词 NEW={len(new_items)} REVIEW={len(review_items)} PRIORITY={len(priority_items)}。"
        f"算法版本: {ALGORITHM_VERSION}"
    )

    # 11. 持久化候选词事件
    event_id = create_candidate_event(
        database_path,
        user_id=user_id,
        workflow_stage=workflow_stage,
        ability=None,
        candidate_items=limited_candidates,
        included_sidequest_signal_ids=signal_ids,
        selection_reason=summary_reason,
    )

    return {
        "candidate_event_id": event_id,
        "user_id": user_id,
        "workflow_stage": workflow_stage,
        "total_vocabulary": len(cet6_words),
        "total_candidates": len(limited_candidates),
        "new_count": len(new_items),
        "review_count": len(review_items),
        "priority_count": len(priority_items),
        "algorithm_version": ALGORITHM_VERSION,
        "generated_at": now_iso,
        "candidate_items": limited_candidates,
        "selection_summary": summary_reason,
    }


def _get_user_vocabulary_states(
    database_path: str | Path, user_id: int
) -> list[dict[str, Any]]:
    """获取用户词汇状态。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM user_vocabulary_states WHERE user_id = ?",
        (user_id,),
    )
    return rows


def _get_pending_sidequest_signals(
    database_path: str | Path, user_id: int
) -> list[dict[str, Any]]:
    """获取用户待验证副线信号。"""
    rows = fetch_all(
        database_path,
        "SELECT * FROM sidequest_signals WHERE user_id = ? AND is_pending_verification = 1",
        (user_id,),
    )
    return rows


def _determine_candidate_role(
    word_id: int,
    state: dict[str, Any] | None,
    sidequest_signals: list[dict[str, Any]],
    now_iso: str,
) -> str:
    """确定候选词角色。"""
    if state is None:
        return CandidateRole.NEW

    # 副线信号中的词标记为 PRIORITY
    for signal in sidequest_signals:
        if signal.get("vocabulary_item_id") == word_id:
            return CandidateRole.PRIORITY

    # next_review_at 已过期或今天 -> REVIEW
    next_review = state.get("next_review_at")
    if next_review and next_review <= now_iso:
        return CandidateRole.REVIEW

    # consecutive_wrong > 0 -> PRIORITY
    if state.get("consecutive_wrong", 0) > 0:
        return CandidateRole.PRIORITY

    # 已学但 mastered -> REVIEW（稀疏复习）
    if state.get("learning_status") in (LearningStatus.MASTERED,):
        return CandidateRole.REVIEW

    # context_error_count > 0 -> PRIORITY
    if state.get("context_error_count", 0) > 0:
        return CandidateRole.PRIORITY

    return CandidateRole.REVIEW if state.get("learning_status") != LearningStatus.NEW else CandidateRole.NEW


def _calculate_review_priority(
    state: dict[str, Any] | None,
    now_iso: str,
) -> tuple[float, str]:
    """计算复习优先级（简单 MVP 算法）。"""
    if state is None:
        return 0.5, ReviewStatus.NOT_DUE

    score = 0.5
    factors = 0

    # 连续错误增加优先级
    cw = state.get("consecutive_wrong", 0)
    if cw > 0:
        score += min(cw * 0.1, 0.3)
        factors += 1

    # context_error 增加优先级
    ce = state.get("context_error_count", 0)
    if ce > 0:
        score += min(ce * 0.05, 0.15)
        factors += 1

    # 高提示依赖增加优先级
    if state.get("prompt_dependency") == "HIGH":
        score += 0.1
        factors += 1

    # 到期复习
    next_review = state.get("next_review_at")
    if next_review and next_review <= now_iso:
        score += 0.15
        factors += 1

    # 总体正确率低
    correct = state.get("correct_count", 0)
    wrong = state.get("wrong_count", 0)
    total = correct + wrong
    if total > 0 and correct / total < 0.5:
        score += 0.1
        factors += 1

    score = min(score, 1.0)

    # 确定复习状态
    if next_review and next_review <= now_iso:
        review_status = ReviewStatus.DUE
    elif state.get("last_reviewed_at") is None:
        review_status = ReviewStatus.NOT_DUE
    else:
        review_status = ReviewStatus.NOT_DUE

    return score, review_status


def _get_recent_error_types(state: dict[str, Any] | None) -> list[str]:
    """从状态中提取最近错误类型。"""
    if state is None:
        return []
    refs = from_json_text(state.get("evidence_refs"), [])
    # 简化：返回空列表；完整实现在后续迭代中补充
    return []


def _build_selection_reason(
    learning_status: str,
    candidate_role: str,
    review_status: str,
    profile_data: dict[str, Any],
) -> str:
    """构建选择原因描述。"""
    if candidate_role == CandidateRole.NEW:
        return "首次学习，纳入今日新词计划"
    if candidate_role == CandidateRole.PRIORITY:
        return "存在错误或待验证信号，优先复习"
    if review_status == ReviewStatus.DUE:
        return f"复习到期（状态: {learning_status}），需要巩固"
    return f"定期复习（状态: {learning_status}）"


def get_candidate_event_detail(
    database_path: str | Path,
    event_id: int,
    user_id: int,
) -> dict[str, Any] | None:
    """获取候选词事件详情（含身份校验）。"""
    row = fetch_one(
        database_path,
        "SELECT * FROM candidate_vocabulary_events WHERE id = ? AND user_id = ?",
        (event_id, user_id),
    )
    if row is None:
        return None
    row["candidate_items"] = from_json_text(row.get("candidate_items"), [])
    row["included_sidequest_signal_ids"] = from_json_text(row.get("included_sidequest_signal_ids"), [])
    return row
