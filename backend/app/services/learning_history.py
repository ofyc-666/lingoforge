"""学习历史分析确定性服务。

实现 PROBLEM_TIMELINE 和 REVIEW_PRIORITY 两类分析。
不接入 Agent Runtime、ToolExecutor、Function Calling。
不使用 memory 创建时间冒充问题发生时间。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.repositories.training import get_learning_evidence_by_user


def analyze_learning_history(
    database_path: str | Path,
    *,
    user_id: int,
    analysis_type: str,
    target: dict[str, Any],
    current_goal: dict[str, Any] | None = None,
    time_window: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """学习历史分析入口。

    只分析当前 user_id 的 learning_evidence。
    user_id 只能由调用方注入，请求体不得提供。
    """
    effective_now = now or datetime.now(timezone.utc)

    # 读取当前用户的学习证据
    evidence_rows = get_learning_evidence_by_user(database_path, user_id, limit=500)

    if not evidence_rows:
        return _insufficient_result(analysis_type)

    if analysis_type == "PROBLEM_TIMELINE":
        return _problem_timeline(evidence_rows, target, time_window, effective_now)
    elif analysis_type == "REVIEW_PRIORITY":
        return _review_priority(evidence_rows, target, current_goal, time_window, effective_now)
    else:
        return {
            "status": "UNSUPPORTED",
            "analysis_type": analysis_type,
            "message": f"不支持的分析类型: {analysis_type}",
        }


def _insufficient_result(analysis_type: str) -> dict[str, Any]:
    return {
        "analysis_type": analysis_type,
        "status": "INSUFFICIENT_EVIDENCE",
        "message": "当前用户没有足够的学习证据。",
    }


# --------------- PROBLEM_TIMELINE ---------------


def _problem_timeline(
    evidence_rows: list[dict[str, Any]],
    target: dict[str, Any],
    time_window: dict[str, Any] | None,
    now: datetime,
) -> dict[str, Any]:
    target_ability = target.get("ability", "")
    target_error_type = target.get("error_type", "")
    target_vocab = target.get("vocabulary_text", "")

    # 按 error_type 分组
    problem_groups: dict[str, dict[str, Any]] = {}

    for row in evidence_rows:
        payload = row.get("payload_json", {})
        if not isinstance(payload, dict):
            continue

        question_results = payload.get("question_results", [])
        if not isinstance(question_results, list):
            continue

        for qr in question_results:
            if not isinstance(qr, dict):
                continue

            ability = qr.get("target_ability", "")
            error_type = qr.get("error_type", "")
            is_correct = qr.get("is_correct", False)
            vocab_text = qr.get("vocabulary_text", qr.get("question_id", ""))

            # 按 target 过滤
            if target_ability and ability != target_ability:
                continue
            if target_error_type and error_type != target_error_type:
                continue
            if target_vocab and vocab_text != target_vocab:
                continue

            if is_correct:
                continue

            group_key = error_type if error_type else f"{ability}_error"

            if group_key not in problem_groups:
                problem_groups[group_key] = {
                    "ability": ability,
                    "error_type": error_type or group_key,
                    "first_observed_at": None,
                    "last_observed_at": None,
                    "occurrence_count": 0,
                    "session_ids": set(),
                    "last_success_at": None,
                    "evidence_refs": [],
                    "confidence": "MEDIUM",
                }

            group = problem_groups[group_key]
            group["occurrence_count"] += 1
            group["session_ids"].add(row.get("session_id"))
            group["evidence_refs"].append(row["id"])

            occurred_at_raw = _resolve_occurred_at(row, qr)
            occurred_at = _parse_datetime(occurred_at_raw)

            if occurred_at is not None:
                if group["first_observed_at"] is None or occurred_at < _parse_datetime(group["first_observed_at"]):
                    group["first_observed_at"] = occurred_at_raw
                if group["last_observed_at"] is None or occurred_at > _parse_datetime(group["last_observed_at"]):
                    group["last_observed_at"] = occurred_at_raw
            else:
                # 降级：使用 evidence created_at
                row_time = _parse_datetime(row.get("created_at", ""))
                if row_time is not None:
                    if group["first_observed_at"] is None:
                        group["first_observed_at"] = row.get("created_at", "")
                    group["last_observed_at"] = row.get("created_at", "")
                    group["confidence"] = "LOW"

        # 检查成功记录
        for qr in question_results:
            if not isinstance(qr, dict):
                continue
            ability = qr.get("target_ability", "")
            if target_ability and ability != target_ability:
                continue
            if qr.get("is_correct", False):
                success_occurred = _resolve_occurred_at(row, qr)
                group_key = qr.get("error_type", f"{ability}_error")
                if group_key in problem_groups:
                    cur = _parse_datetime(problem_groups[group_key].get("last_success_at"))
                    new = _parse_datetime(success_occurred)
                    if new is not None and (cur is None or new > cur):
                        problem_groups[group_key]["last_success_at"] = success_occurred

    items = []
    for key, group in problem_groups.items():
        sid_set = group.pop("session_ids")
        items.append({
            "ability": group["ability"],
            "error_type": group["error_type"],
            "first_observed_at": group["first_observed_at"],
            "last_observed_at": group["last_observed_at"],
            "occurrence_count": group["occurrence_count"],
            "session_count": len(sid_set),
            "last_success_at": group["last_success_at"],
            "recent_trend": _compute_trend(group, now),
            "evidence_refs": group["evidence_refs"][-20:],
            "confidence": group["confidence"],
            "recorded_at_distinct": True,  # occurred_at 与 recorded_at 区分标记
            "memory_created_at": None,     # 本轮不读 memory
        })

    return {
        "analysis_type": "PROBLEM_TIMELINE",
        "status": "COMPLETED" if items else "NO_ISSUES_FOUND",
        "problem_items": items,
        "filter": {
            "ability": target_ability or None,
            "error_type": target_error_type or None,
            "vocabulary_text": target_vocab or None,
        },
        "time_window": time_window,
        "generated_at": now.isoformat(),
    }


def _compute_trend(group: dict[str, Any], now: datetime) -> str:
    """根据首次和最近观察时间以及计数推断趋势。"""
    last = _parse_datetime(group.get("last_observed_at"))
    if last is None:
        return "UNKNOWN"
    days_since_last = (now - last).total_seconds() / 86400.0
    count = group.get("occurrence_count", 0)
    if count >= 3 and days_since_last < 7:
        return "PERSISTENT"
    elif days_since_last > 14:
        return "STALE"
    elif count >= 2:
        return "RECURRING"
    else:
        return "ISOLATED"


# --------------- REVIEW_PRIORITY ---------------


def _review_priority(
    evidence_rows: list[dict[str, Any]],
    target: dict[str, Any],
    current_goal: dict[str, Any] | None,
    time_window: dict[str, Any] | None,
    now: datetime,
) -> dict[str, Any]:
    target_ability = target.get("ability", "")

    # 聚合所有题目结果
    all_qr: list[dict[str, Any]] = []
    latest_practice_at: datetime | None = None
    latest_success_at: datetime | None = None

    for row in evidence_rows:
        payload = row.get("payload_json", {})
        if not isinstance(payload, dict):
            continue
        question_results = payload.get("question_results", [])
        if not isinstance(question_results, list):
            continue
        for qr in question_results:
            if not isinstance(qr, dict):
                continue
            ability = qr.get("target_ability", "")
            if target_ability and ability != target_ability:
                continue
            all_qr.append(qr)

            occurred = _resolve_occurred_at(row, qr)
            occurred_dt = _parse_datetime(occurred)
            if occurred_dt is not None:
                if latest_practice_at is None or occurred_dt > latest_practice_at:
                    latest_practice_at = occurred_dt
                if qr.get("is_correct", False):
                    if latest_success_at is None or occurred_dt > latest_success_at:
                        latest_success_at = occurred_dt

    if not all_qr:
        return _insufficient_result("REVIEW_PRIORITY")

    total = len(all_qr)
    correct = sum(1 for qr in all_qr if qr.get("is_correct", False))
    accuracy = correct / total if total > 0 else 0.0

    # 计算各因子
    factors: dict[str, Any] = {}
    score = 0

    # 1. 距离上次练习越久 +25
    days_since_practice = _days_since(latest_practice_at, now) if latest_practice_at else 30
    practice_factor = min(25, max(0, int(days_since_practice * 1.2)))
    score += practice_factor
    factors["days_since_practice"] = {"days": days_since_practice, "score": practice_factor}

    # 2. 距离上次成功越久或从未成功 +20
    if latest_success_at is None:
        success_gap = 20
    else:
        days_since_success = _days_since(latest_success_at, now)
        success_gap = min(20, max(0, int(days_since_success * 1.0)))
    score += success_gap
    factors["success_gap"] = {"days_since_last_success": _days_since(latest_success_at, now) if latest_success_at else None, "score": success_gap, "never_succeeded": latest_success_at is None}

    # 3. 历史正确率越低 +20
    accuracy_factor = int((1.0 - accuracy) * 20)
    score += accuracy_factor
    factors["accuracy"] = {"accuracy": round(accuracy, 2), "score": accuracy_factor}

    # 4. 提示依赖 +10
    hint_used_count = sum(1 for row in evidence_rows if row.get("payload_json", {}).get("used_hints"))
    hint_factor = min(10, hint_used_count * 3)
    score += hint_factor
    factors["hint_dependency"] = {"hint_used_count": hint_used_count, "score": hint_factor}

    # 5. 连续错误 +10；连续成功最多降 10
    streak = _compute_streak(all_qr)
    if streak < 0:
        streak_factor = min(10, abs(streak) * 3)
        score += streak_factor
        factors["streak"] = {"consecutive_errors": abs(streak), "score": streak_factor}
    else:
        streak_factor = min(10, streak) * -1
        score += streak_factor  # 降低分数
        factors["streak"] = {"consecutive_successes": streak, "score": streak_factor}

    # 6. 当前目标相关性 +10
    relevance_factor = 0
    if current_goal:
        weaknesses = current_goal.get("self_reported_weaknesses", [])
        if target_ability in weaknesses:
            relevance_factor = 10
    score += relevance_factor
    factors["goal_relevance"] = {"target_in_weaknesses": relevance_factor > 0, "score": relevance_factor}

    # 7. 反复出现问题 +10
    recurring_count = len(set(
        qr.get("question_id", "")
        for qr in all_qr
        if qr.get("is_correct") == False  # noqa: E712
    ))
    recurring_factor = min(10, recurring_count * 2)
    score += recurring_factor
    factors["recurring_problems"] = {"distinct_error_questions": recurring_count, "score": recurring_factor}

    # 8. 内容难度 +0 ~ +5
    difficulty_factor = min(5, max(0, 0))  # MVP 暂不评估内容难度
    score += difficulty_factor
    factors["content_difficulty"] = {"score": difficulty_factor}

    # 裁剪到 0-100
    review_priority = max(0, min(100, score))

    # review_status 映射
    if review_priority >= 70:
        review_status = "DUE_NOW"
    elif review_priority >= 40:
        review_status = "SOON"
    else:
        review_status = "STABLE"

    evidence_refs = [row["id"] for row in evidence_rows[-30:]]

    return {
        "analysis_type": "REVIEW_PRIORITY",
        "status": "COMPLETED",
        "review_priority": review_priority,
        "review_status": review_status,
        "recommended_window": _recommended_window(review_status),
        "estimated_decay": _estimate_decay(days_since_practice, accuracy),
        "factors": factors,
        "evidence_refs": evidence_refs,
        "algorithm_version": "review_priority_v1",
        "generated_at": now.isoformat(),
    }


def _recommended_window(review_status: str) -> dict[str, Any]:
    if review_status == "DUE_NOW":
        return {"days": 1, "label": "建议 24 小时内复习"}
    elif review_status == "SOON":
        return {"days": 7, "label": "建议一周内复习"}
    else:
        return {"days": 30, "label": "可延后复习"}


def _estimate_decay(days_since_practice: float, accuracy: float) -> dict[str, Any]:
    decay_rate = 0.05 + (1.0 - accuracy) * 0.03
    estimated_retention = max(0.1, 1.0 - decay_rate * days_since_practice)
    return {
        "rate": round(decay_rate, 3),
        "estimated_retention": round(estimated_retention, 2),
        "note": "确定性估算，不宣称精确模拟人脑遗忘曲线。",
    }


def _compute_streak(qr_list: list[dict[str, Any]]) -> int:
    """计算最近的连续正确/错误数。正数为连续正确，负数为连续错误。"""
    if not qr_list:
        return 0
    # 反转以从最近开始
    recent = list(reversed(qr_list))
    first_correct = recent[0].get("is_correct", False)
    count = 0
    for qr in recent:
        if qr.get("is_correct", False) == first_correct:
            count += 1
        else:
            break
    return count if first_correct else -count


# --------------- helper ---------------


def _resolve_occurred_at(evidence_row: dict[str, Any], qr: dict[str, Any]) -> str:
    """解析学习事件真实发生时间。

    - 优先使用 payload 中的 occurred_at
    - 其次使用 qr 中的 occurred_at
    - 降级使用 evidence created_at（此时 confidence 降低）
    """
    payload = evidence_row.get("payload_json", {})
    if isinstance(payload, dict):
        oa = payload.get("occurred_at", "")
        if oa:
            return str(oa)
    oa = qr.get("occurred_at", "")
    if oa:
        return str(oa)
    return str(evidence_row.get("created_at", ""))


def _parse_datetime(value: str | None) -> datetime | None:
    """尝试解析 ISO 格式日期时间字符串。"""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _days_since(dt: datetime | None, now: datetime) -> float:
    """计算从 dt 到 now 的天数。"""
    if dt is None:
        return 0.0
    return max(0.0, (now - dt).total_seconds() / 86400.0)
