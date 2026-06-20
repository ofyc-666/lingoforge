"""训练任务质量校验服务。

确定性校验生成训练任务的内容结构和答案有效性。
不调用 LLM，不把模型自称"校验通过"当成真实校验。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.constants import is_valid_ability
from app.repositories.training import create_task_validation


def validate_training_task_content(content: dict[str, Any]) -> dict[str, Any]:
    """校验训练任务内容结构。

    Args:
        content: generated_tasks.content_json 的 dict 形式。

    Returns:
        {
            "status": "PASSED" | "FAILED",
            "error_codes": [...],
            "error_details": {...}
        }
    """
    error_codes: list[str] = []
    error_details: dict[str, Any] = {}

    # 校验基本结构
    if not isinstance(content, dict):
        return {
            "status": "FAILED",
            "error_codes": ["MISSING_CONTENT"],
            "error_details": {"reason": "content 不是 dict"},
        }

    if not content.get("title"):
        error_codes.append("MISSING_TITLE")
        error_details["title"] = "缺少标题"

    if not content.get("instructions"):
        error_codes.append("MISSING_INSTRUCTIONS")
        error_details["instructions"] = "缺少答题说明"

    questions = content.get("questions")
    if not questions or not isinstance(questions, list) or len(questions) == 0:
        error_codes.append("NO_QUESTIONS")
        error_details["questions"] = "题目列表为空"
        return _build_result(error_codes, error_details)

    # 校验单题
    seen_ids: set[str] = set()
    for i, q in enumerate(questions):
        prefix = f"questions[{i}]"

        # 题型校验
        q_type = q.get("question_type")
        if q_type != "MULTIPLE_CHOICE":
            error_codes.append("UNSUPPORTED_QUESTION_TYPE")
            error_details[prefix] = f"不支持题型: {q_type}"

        # question_id 重复校验
        qid = q.get("question_id", "")
        if qid in seen_ids:
            error_codes.append("DUPLICATE_QUESTION_ID")
            error_details[prefix] = f"重复 question_id: {qid}"
        seen_ids.add(qid)

        # 答案校验
        answer = q.get("answer", "")
        options = q.get("options", [])
        option_ids = {opt.get("id", "") for opt in options} if isinstance(options, list) else set()
        if answer and option_ids and answer not in option_ids:
            error_codes.append("ANSWER_NOT_IN_OPTIONS")
            error_details[prefix] = f"答案 '{answer}' 不在选项 {option_ids} 中"

        # 能力维度校验
        ability = q.get("target_ability", "")
        if ability and not is_valid_ability(ability):
            error_codes.append("INVALID_TARGET_ABILITY")
            error_details[prefix] = f"非法 target_ability: {ability}"

    # 去重
    error_codes = list(dict.fromkeys(error_codes))

    return _build_result(error_codes, error_details)


def _build_result(error_codes: list[str], error_details: dict[str, Any]) -> dict[str, Any]:
    """构建校验结果 dict。"""
    return {
        "status": "PASSED" if len(error_codes) == 0 else "FAILED",
        "error_codes": error_codes,
        "error_details": error_details,
    }


def record_task_validation_result(
    database_path: str | Path,
    *,
    task_id: int,
    validation_result: dict[str, Any],
    attempt_number: int = 1,
) -> int:
    """将校验结果写入 generated_task_validations。

    Args:
        database_path: 数据库路径。
        task_id: 被校验的任务 ID。
        validation_result: validate_training_task_content 的返回值。
        attempt_number: 校验尝试次数。

    Returns:
        新创建的 validation 记录 ID。
    """
    return create_task_validation(
        database_path,
        task_id=task_id,
        validation_status=validation_result.get("status", "FAILED"),
        error_codes=validation_result.get("error_codes", []),
        error_details=validation_result.get("error_details", {}),
        attempt_number=attempt_number,
    )
