"""画像更新建议薄服务。

基于确定性评分结果写入 profile_update_suggestions。
不应用画像，不写 profile snapshot。
不调用 Agent/LLM。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repositories.users import create_profile_suggestion


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
    accuracy = score_result.get("accuracy", 0.0)
    total = score_result.get("total", 0)

    # 从第一题的 target_ability 提取能力维度
    question_results = score_result.get("question_results", [])
    ability = question_results[0]["target_ability"] if question_results else "VOCABULARY_CONTEXT"

    # 确定方向
    if total == 0:
        direction = "UNCERTAIN"
        reason = "评分数据不包含有效题目信息，无法判断能力变化。"
    elif accuracy >= 0.8:
        if accuracy >= 1.0:
            direction = "IMPROVE"
            reason = f"本次训练全部正确（正确率 {int(accuracy * 100)}%），{ability} 表现优秀。"
        else:
            direction = "IMPROVE"
            reason = f"本次训练正确率较高（{int(accuracy * 100)}%），{ability} 表现良好。"
    elif accuracy < 0.6:
        direction = "DECLINE"
        reason = f"本次训练正确率较低（{int(accuracy * 100)}%），{ability} 需要加强。"
    else:
        direction = "IMPROVE"
        reason = f"本次训练正确率 {int(accuracy * 100)}%，{ability} 表现尚可。"

    agent_payload: dict[str, Any] = {
        "source": "DETERMINISTIC_SCORER",
        "score": {
            "total": score_result.get("total"),
            "correct": score_result.get("correct"),
            "accuracy": score_result.get("accuracy"),
            "passed": score_result.get("passed"),
        },
        "error_types": score_result.get("error_types", []),
        "requires_agent_review": True,
    }

    return create_profile_suggestion(
        database_path,
        user_id=user_id,
        ability=ability,
        direction=direction,
        reason=reason,
        evidence_refs=[evidence_id],
        agent_payload=agent_payload,
    )
