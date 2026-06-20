"""画像更新建议薄服务。

基于确定性评分结果写入 profile_update_suggestions。
不应用画像，不写 profile snapshot。
不调用 Agent/LLM。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repositories.users import create_profile_suggestion


def build_profile_suggestion_from_score(
    *,
    evidence_id: int,
    score_result: dict[str, Any],
) -> dict[str, Any]:
    """基于确定性评分结果构造画像建议字段，不执行数据库写入。"""
    accuracy = float(score_result.get("accuracy", 0.0) or 0.0)
    total = int(score_result.get("total", 0) or 0)

    ability = ""
    for result in score_result.get("question_results", []):
        candidate = result.get("target_ability")
        if candidate:
            ability = candidate
            break

    if total == 0 or not ability:
        ability = ability or "VOCABULARY_CONTEXT"
        direction = "UNCERTAIN"
        reason = "评分数据不包含足够的题目或能力信息，无法判断能力变化。"
    elif accuracy >= 0.8:
        direction = "IMPROVE"
        reason = f"本次训练正确率较高（{int(accuracy * 100)}%），{ability} 表现良好。"
    elif accuracy < 0.6:
        direction = "DECLINE"
        reason = f"本次训练正确率较低（{int(accuracy * 100)}%），{ability} 需要加强。"
    else:
        direction = "NO_CHANGE"
        reason = f"本次训练正确率 {int(accuracy * 100)}%，{ability} 表现暂未形成明确变化。"

    return {
        "ability": ability,
        "direction": direction,
        "reason": reason,
        "evidence_refs": [evidence_id],
        "agent_payload": {
            "source": "DETERMINISTIC_SCORER",
            "score": {
                "total": score_result.get("total"),
                "correct": score_result.get("correct"),
                "accuracy": score_result.get("accuracy"),
                "passed": score_result.get("passed"),
            },
            "error_types": score_result.get("error_types", []),
            "requires_agent_review": True,
        },
    }


def propose_profile_update_from_score(
    database_path: str | Path,
    *,
    user_id: int,
    evidence_id: int,
    score_result: dict[str, Any],
) -> int:
    """基于确定性评分结果写入一条画像更新建议。

    Args:
        database_path: 数据库路径。
        user_id: 用户 ID。
        evidence_id: 关联学习证据 ID。
        score_result: 评分器输出 dict。

    Returns:
        新画像建议记录 ID。
    """
    suggestion = build_profile_suggestion_from_score(
        evidence_id=evidence_id,
        score_result=score_result,
    )

    return create_profile_suggestion(
        database_path,
        user_id=user_id,
        ability=suggestion["ability"],
        direction=suggestion["direction"],
        reason=suggestion["reason"],
        evidence_refs=suggestion["evidence_refs"],
        agent_payload=suggestion["agent_payload"],
    )
