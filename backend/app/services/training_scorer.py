"""确定性训练评分器。

纯函数，不依赖 LLM、数据库或外部服务。
只支持 MULTIPLE_CHOICE 题型，按 question_id 匹配用户答案。
"""

from __future__ import annotations

from typing import Any


class UnsupportedQuestionTypeError(ValueError):
    """训练评分器遇到 MVP 不支持的题型。"""

    def __init__(self, question_id: str, question_type: Any):
        self.question_id = question_id
        self.question_type = question_type
        super().__init__(f"Unsupported question_type for {question_id}: {question_type}")


def score_training_submission(
    task_content: dict[str, Any],
    answers: list[dict[str, Any]],
    *,
    used_hints: list[str] | None = None,
) -> dict[str, Any]:
    """对客观题提交评分。

    Args:
        task_content: 训练任务正文，包含 questions 列表。
        answers: 用户提交答案列表 [{question_id, answer}, ...]。
        used_hints: 用户使用的提示列表。

    Returns:
        评分结果 dict:
        {
            total, correct, accuracy, passed,
            question_results: [{question_id, user_answer, standard_answer, is_correct,
                                error_type, target_ability, explanation}, ...],
            error_types: [str],
            used_hints: [str],
            extra_answers: [{question_id, answer}, ...]   # 仅在存在多余答案时出现
        }
    """
    questions: list[dict[str, Any]] = task_content.get("questions", [])
    used = list(used_hints or [])

    # 建立题目索引
    question_map: dict[str, dict[str, Any]] = {}
    for q in questions:
        qid = q.get("question_id", "")
        question_type = q.get("question_type")
        if question_type != "MULTIPLE_CHOICE":
            raise UnsupportedQuestionTypeError(qid, question_type)
        if qid:
            question_map[qid] = q

    # 建立用户答案索引
    answer_map: dict[str, str] = {}
    extra_answers: list[dict[str, Any]] = []
    for a in answers:
        qid = a.get("question_id", "")
        if not qid:
            continue
        if qid in answer_map:
            # 同一题多次作答，保留首次
            extra_answers.append({"question_id": qid, "answer": a.get("answer", ""), "status": "DUPLICATE"})
        elif qid not in question_map:
            extra_answers.append({"question_id": qid, "answer": a.get("answer", ""), "status": "EXTRA"})
        else:
            answer_map[qid] = a.get("answer", "")

    question_results: list[dict[str, Any]] = []
    correct_count = 0
    error_types: list[str] = []

    for q in questions:
        qid = q.get("question_id", "")
        standard = q.get("answer", "")
        user_answer = answer_map.get(qid, "")
        is_correct = bool(user_answer) and user_answer == standard

        if is_correct:
            correct_count += 1
            err_type = None  # type: str | None
        else:
            err_type = q.get("error_type_on_wrong") or "UNKNOWN_ERROR"
            if err_type not in error_types:
                error_types.append(err_type)

        question_results.append({
            "question_id": qid,
            "user_answer": user_answer,
            "standard_answer": standard,
            "is_correct": is_correct,
            "error_type": err_type,
            "target_ability": q.get("target_ability", ""),
            "explanation": q.get("explanation", ""),
        })

    total = len(questions)
    accuracy = correct_count / total if total > 0 else 0.0
    passed = accuracy >= 0.6

    result: dict[str, Any] = {
        "total": total,
        "correct": correct_count,
        "accuracy": round(accuracy, 4),
        "passed": passed,
        "question_results": question_results,
        "error_types": error_types,
        "used_hints": used,
    }

    if extra_answers:
        result["extra_answers"] = extra_answers

    return result
