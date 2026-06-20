"""训练任务质量校验服务。

确定性校验生成训练任务的内容结构和答案有效性。
不调用 LLM，不把模型自称"校验通过"当成真实校验。

扩展支持 TARGETED_PRACTICE 和 COMPREHENSIVE_SIMULATION 专项校验。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.constants import PracticeMode, is_valid_ability
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

    if not isinstance(content, dict):
        return {
            "status": "FAILED",
            "error_codes": ["MISSING_CONTENT"],
            "error_details": {"reason": "content 不是 dict"},
        }

    # 检查练习模式
    practice_mode = content.get("practice_mode", "")
    if practice_mode:
        _validate_practice_mode_specific(content, practice_mode, error_codes, error_details)

    if not content.get("title") and not practice_mode:
        error_codes.append("MISSING_TITLE")
        error_details["title"] = "缺少标题"

    if not content.get("instructions") and not practice_mode:
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

        q_type = q.get("question_type")
        if q_type != "MULTIPLE_CHOICE":
            error_codes.append("UNSUPPORTED_QUESTION_TYPE")
            error_details[prefix] = f"不支持题型: {q_type}"

        qid = q.get("question_id", "")
        if qid in seen_ids:
            error_codes.append("DUPLICATE_QUESTION_ID")
            error_details[prefix] = f"重复 question_id: {qid}"
        seen_ids.add(qid)

        answer = q.get("answer", "")
        options = q.get("options", [])
        option_ids = {opt.get("id", "") for opt in options} if isinstance(options, list) else set()
        if answer and option_ids and answer not in option_ids:
            error_codes.append("ANSWER_NOT_IN_OPTIONS")
            error_details[prefix] = f"答案 '{answer}' 不在选项 {option_ids} 中"

        ability = q.get("target_ability", "")
        if ability and not is_valid_ability(ability):
            error_codes.append("INVALID_TARGET_ABILITY")
            error_details[prefix] = f"非法 target_ability: {ability}"

    # 练习模式专项校验
    if practice_mode:
        _validate_practice_questions(content, questions, practice_mode, error_codes, error_details)

    error_codes = list(dict.fromkeys(error_codes))
    return _build_result(error_codes, error_details)


def _validate_practice_mode_specific(
    content: dict[str, Any],
    practice_mode: str,
    error_codes: list[str],
    error_details: dict[str, Any],
) -> None:
    """按练习模式校验任务结构。"""
    selected_skills = content.get("selected_skills", [])
    target_abilities = content.get("target_abilities", [])

    if practice_mode == PracticeMode.TARGETED_PRACTICE:
        # 1-2 Skill
        if len(selected_skills) < 1 or len(selected_skills) > 2:
            error_codes.append("TARGETED_PRACTICE_SKILL_COUNT")
        # 至少 1 个目标能力
        if len(set(target_abilities)) < 1:
            error_codes.append("MISSING_TARGET_ABILITY")
    elif practice_mode == PracticeMode.COMPREHENSIVE_SIMULATION:
        # 2-4 Skill
        if len(selected_skills) < 2 or len(selected_skills) > 4:
            error_codes.append("SIMULATION_SKILL_COUNT")
        # 至少覆盖两个能力
        if len(set(target_abilities)) < 2:
            error_codes.append("SIMULATION_LESS_THAN_TWO_ABILITIES")


def _validate_practice_questions(
    content: dict[str, Any],
    questions: list[dict[str, Any]],
    practice_mode: str,
    error_codes: list[str],
    error_details: dict[str, Any],
) -> None:
    """按练习模式校验题目内容。"""
    target_abilities = set(content.get("target_abilities", []))
    selected_skills = content.get("selected_skills", [])

    for i, q in enumerate(questions):
        prefix = f"questions[{i}]"

        # 每题应有 skill_id 和 target_ability
        if practice_mode:
            if not q.get("skill_id"):
                error_codes.append("MISSING_SKILL_ID")
                error_details[prefix] = "缺少 skill_id"
            if not q.get("target_ability"):
                error_codes.append("MISSING_TARGET_ABILITY_IN_QUESTION")
                error_details[prefix] = "缺少 target_ability"

    # COMPREHENSIVE_SIMULATION: 不能全部题属于同一能力
    if practice_mode == PracticeMode.COMPREHENSIVE_SIMULATION:
        question_abilities = {q.get("target_ability", "") for q in questions}
        if len(question_abilities) < 2:
            error_codes.append("ALL_QUESTIONS_SAME_ABILITY")


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
    """将校验结果写入 generated_task_validations。"""
    return create_task_validation(
        database_path,
        task_id=task_id,
        validation_status=validation_result.get("status", "FAILED"),
        error_codes=validation_result.get("error_codes", []),
        error_details=validation_result.get("error_details", {}),
        attempt_number=attempt_number,
    )
