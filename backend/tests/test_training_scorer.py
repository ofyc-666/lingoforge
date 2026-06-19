"""确定性训练评分器测试。"""

from __future__ import annotations

from app.services.training_scorer import score_training_submission


def _make_task_content(*questions: dict) -> dict:
    """构造标准 task_content。"""
    return {"questions": list(questions)}


def _q(
    question_id: str,
    answer: str = "A",
    target_ability: str = "VOCABULARY_CONTEXT",
    error_type_on_wrong: str | None = "VOCABULARY_CONTEXT_ERROR",
) -> dict:
    return {
        "question_id": question_id,
        "question_type": "MULTIPLE_CHOICE",
        "answer": answer,
        "target_ability": target_ability,
        "explanation": f"{question_id} 的解释。",
        **({"error_type_on_wrong": error_type_on_wrong} if error_type_on_wrong else {}),
    }


def _a(question_id: str, answer: str) -> dict:
    return {"question_id": question_id, "answer": answer}


class TestScoreAllCorrect:
    """全对场景。"""

    def test_all_correct(self):
        task = _make_task_content(_q("q1", "A"), _q("q2", "B"))
        answers = [_a("q1", "A"), _a("q2", "B")]
        result = score_training_submission(task, answers)
        assert result["total"] == 2
        assert result["correct"] == 2
        assert result["accuracy"] == 1.0
        assert result["passed"] is True
        assert len(result["question_results"]) == 2
        assert all(r["is_correct"] for r in result["question_results"])
        assert result["error_types"] == []


class TestPartialErrors:
    """部分错误场景。"""

    def test_one_wrong_one_correct(self):
        task = _make_task_content(_q("q1", "A"), _q("q2", "B"))
        answers = [_a("q1", "A"), _a("q2", "C")]
        result = score_training_submission(task, answers)
        assert result["total"] == 2
        assert result["correct"] == 1
        assert result["accuracy"] == 0.5
        assert result["passed"] is False
        results = result["question_results"]
        assert results[0]["is_correct"] is True
        assert results[1]["is_correct"] is False
        assert results[1]["error_type"] == "VOCABULARY_CONTEXT_ERROR"


class TestUnanswered:
    """未答题场景——记错。"""

    def test_unanswered_question_is_wrong(self):
        task = _make_task_content(_q("q1", "A"), _q("q2", "B"))
        answers = [_a("q1", "A")]
        result = score_training_submission(task, answers)
        assert result["total"] == 2
        assert result["correct"] == 1
        assert result["accuracy"] == 0.5
        # q2 未答，应记错
        q2_result = next(r for r in result["question_results"] if r["question_id"] == "q2")
        assert q2_result["is_correct"] is False
        assert q2_result["error_type"] == "VOCABULARY_CONTEXT_ERROR"
        assert q2_result["user_answer"] == ""

    def test_unanswered_no_error_type_falls_back_to_unknown(self):
        task = _make_task_content(_q("q1", "A", error_type_on_wrong=None))
        answers = []
        result = score_training_submission(task, answers)
        q = result["question_results"][0]
        assert q["error_type"] == "UNKNOWN_ERROR"


class TestExtraAnswers:
    """多余答案场景。"""

    def test_extra_answer_does_not_affect_correctness(self):
        task = _make_task_content(_q("q1", "A"))
        answers = [_a("q1", "A"), _a("q2", "B")]  # q2 不存在
        result = score_training_submission(task, answers)
        assert result["total"] == 1
        assert result["correct"] == 1
        assert result["accuracy"] == 1.0
        # q2 多余，不影响已有题目正确性
        assert len(result["question_results"]) == 1
        # 多余答案应可审计
        extra = result.get("extra_answers", [])
        assert len(extra) == 1
        assert extra[0]["question_id"] == "q2"


class TestOutOfOrderAnswers:
    """乱序答案场景——按 question_id 匹配。"""

    def test_answers_in_different_order(self):
        task = _make_task_content(_q("q1", "A"), _q("q2", "B"), _q("q3", "C"))
        answers = [_a("q3", "C"), _a("q1", "A"), _a("q2", "B")]
        result = score_training_submission(task, answers)
        assert result["total"] == 3
        assert result["correct"] == 3
        assert result["accuracy"] == 1.0


class TestUsedHints:
    """used_hints 记录。"""

    def test_hints_passed_through(self):
        task = _make_task_content(_q("q1", "A"))
        answers = [_a("q1", "A")]
        result = score_training_submission(task, answers, used_hints=["definition_hint"])
        assert result["used_hints"] == ["definition_hint"]

    def test_no_hints_default(self):
        task = _make_task_content(_q("q1", "A"))
        answers = [_a("q1", "B")]
        result = score_training_submission(task, answers)
        assert result["used_hints"] == []
