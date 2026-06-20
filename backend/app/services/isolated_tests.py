"""隔离测试业务服务。

提供隔离测试题项安全 sanitizer、attempt 创建和评分逻辑。
不调用 Agent，不访问禁止字段。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.repositories.isolated_tests import (
    add_item_to_attempt,
    create_isolated_test_attempt,
    get_attempt_with_items,
    get_items_for_attempt,
    list_active_items_by_ability,
)
from app.repositories.base import fetch_one
from app.repositories.training import create_learning_evidence


# --------------- sanitizer ---------------

_ALLOWED_ITEM_KEYS: frozenset[str] = frozenset({
    "item_id", "item_order", "target_ability", "item_version", "prompt", "options",
})


def sanitize_isolated_item(item: dict[str, Any]) -> dict[str, Any]:
    """清理隔离测试题项，只保留安全字段。

    输出不得包含 answer_key、answer_rationale、distractor_rationale、
    explanation、standard_answer 或其他可能泄露答案的字段。
    """
    return {k: v for k, v in item.items() if k in _ALLOWED_ITEM_KEYS}


# --------------- attempt 创建 ---------------


def start_isolated_test(
    database_path: str | Path,
    *,
    user_id: int,
    target_ability: str,
    limit: int = 3,
    session_id: int | None = None,
) -> dict[str, Any]:
    """创建隔离测试 attempt 并返回 sanitized items。

    Args:
        database_path: 数据库路径。
        user_id: 当前用户 ID（由调用方绑定）。
        target_ability: 目标能力维度。
        limit: 最多返回的题目数。
        session_id: 可选绑定的 session。

    Returns:
        {"attempt_id": int, "items": [...]}
    """
    # 按 target_ability 读取 active items
    if session_id is not None:
        session = fetch_one(
            database_path,
            "SELECT id, user_id FROM training_sessions WHERE id = ?",
            (session_id,),
        )
        if session is None:
            raise ValueError("SESSION_NOT_FOUND")
        if session.get("user_id") != user_id:
            raise ValueError("SESSION_ACCESS_DENIED")

    active_items = list_active_items_by_ability(database_path, target_ability)
    selected = active_items[:limit]

    if not selected:
        raise _no_items_error(target_ability)

    # 创建 attempt
    attempt_id = create_isolated_test_attempt(
        database_path,
        user_id=user_id,
        session_id=session_id,
    )

    # 关联 items
    sanitized_items: list[dict[str, Any]] = []
    for idx, item_row in enumerate(selected):
        item_id = item_row["id"]
        item_version = item_row.get("item_version", "v1")
        add_item_to_attempt(
            database_path,
            attempt_id=attempt_id,
            item_id=item_id,
            item_order=idx + 1,
            item_version=item_version,
        )
        # 组装 item 数据供 sanitize
        payload = item_row.get("item_payload", {})
        if isinstance(payload, dict):
            full_item = {
                "item_id": item_id,
                "item_order": idx + 1,
                "target_ability": item_row.get("target_ability", target_ability),
                "item_version": item_version,
                "prompt": payload.get("prompt", ""),
                "options": payload.get("options", []),
            }
        else:
            full_item = {
                "item_id": item_id,
                "item_order": idx + 1,
                "target_ability": item_row.get("target_ability", target_ability),
                "item_version": item_version,
                "prompt": "",
                "options": [],
            }
        sanitized_items.append(sanitize_isolated_item(full_item))

    return {"attempt_id": attempt_id, "items": sanitized_items}


# --------------- 提交评分 ---------------


def submit_isolated_test(
    database_path: str | Path,
    *,
    user_id: int,
    attempt_id: int,
    answers: list[dict[str, Any]],
    time_spent_seconds: int | None = None,
) -> dict[str, Any]:
    """提交隔离测试答案并评分。

    Args:
        database_path: 数据库路径。
        user_id: 当前用户 ID。
        attempt_id: 尝试 ID。
        answers: 用户答案列表 [{"item_id": 1, "answer": "A"}, ...]
        time_spent_seconds: 用时。

    Returns:
        受控结果包 dict。

    Raises:
        ValueError: attempt 不存在、不属于当前用户、或已提交。
    """
    result = get_attempt_with_items(database_path, attempt_id)
    if result is None:
        raise ValueError("ATTEMPT_NOT_FOUND")

    attempt = result["attempt"]
    if attempt.get("user_id") != user_id:
        raise ValueError("ATTEMPT_ACCESS_DENIED")

    # 检查是否已提交（重复提交检测）
    existing_answers = attempt.get("user_answers", {})
    if isinstance(existing_answers, dict) and existing_answers:
        raise ValueError("ATTEMPT_ALREADY_SUBMITTED")

    items = result["items"]
    if not items:
        raise ValueError("NO_ITEMS_IN_ATTEMPT")

    # 确定性评分
    answer_map: dict[int, str] = {}
    for a in answers:
        answer_map[a.get("item_id", a.get("item_id"))] = str(a.get("answer", ""))

    item_results: list[dict[str, Any]] = []
    correct_count = 0
    total = len(items)

    # 需要为每个 item 查询 isolated_test_items 获取 answer_key
    from app.repositories.base import fetch_one

    for link in items:
        item_row_id = link["isolated_test_item_id"]
        item_row = fetch_one(
            database_path,
            "SELECT * FROM isolated_test_items WHERE id = ?",
            (item_row_id,),
        )
        if item_row is None:
            continue

        answer_key = item_row.get("answer_key", {})
        if isinstance(answer_key, str):
            from app.storage.json_fields import from_json_text
            answer_key = from_json_text(answer_key, {})

        correct_answer = str(answer_key.get("correct", answer_key.get("answer", "")))
        user_answer = answer_map.get(item_row_id, "")

        is_correct = user_answer.upper() == correct_answer.upper()
        if is_correct:
            correct_count += 1

        item_results.append({
            "item_id": item_row_id,
            "target_ability": item_row.get("target_ability", ""),
            "is_correct": is_correct,
        })

    accuracy = correct_count / total if total > 0 else 0.0

    # 更新 attempt
    from app.repositories.base import execute
    from app.storage.json_fields import to_json_text

    execute(
        database_path,
        "UPDATE isolated_test_attempts SET user_answers = ?, score_json = ?, time_spent_seconds = ? WHERE id = ?",
        (
            to_json_text(answer_map),
            to_json_text({"total": total, "correct": correct_count, "accuracy": accuracy}),
            time_spent_seconds,
            attempt_id,
        ),
    )

    # 写入学习证据
    evidence_id = create_learning_evidence(
        database_path,
        user_id=user_id,
        evidence_type="ISOLATED_TEST_RESULT",
        session_id=attempt.get("session_id"),
        payload={
            "attempt_id": attempt_id,
            "score": {"total": total, "correct": correct_count, "accuracy": accuracy},
            "item_results": item_results,
            "time_spent_seconds": time_spent_seconds,
        },
    )

    # 生成安全摘要
    safe_explanation = (
        f"隔离测试完成：共 {total} 题，答对 {correct_count} 题，"
        f"正确率 {accuracy:.0%}。"
        "详细解析不在此处提供，请参考后续教学反馈。"
    )

    return {
        "attempt_id": attempt_id,
        "score": {"total": total, "correct": correct_count, "accuracy": accuracy},
        "item_results": item_results,
        "evidence_id": evidence_id,
        "safe_explanation": safe_explanation,
    }


def _no_items_error(target_ability: str) -> ValueError:
    return ValueError(f"NO_ACTIVE_ITEMS:{target_ability}")
