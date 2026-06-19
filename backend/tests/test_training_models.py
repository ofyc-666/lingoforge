"""训练任务与提交模型测试。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.training_models import (
    QuestionScoreResult,
    TrainingAnswer,
    TrainingOption,
    TrainingQuestion,
    TrainingResultResponse,
    TrainingScore,
    TrainingSubmitRequest,
    TrainingSubmitResponse,
    TrainingTaskContent,
    TrainingTaskSummary,
)


class TestTrainingOption:
    """TrainingOption 模型测试。"""

    def test_valid_option(self):
        opt = TrainingOption(id="A", text="adjust to")
        assert opt.id == "A"
        assert opt.text == "adjust to"


class TestTrainingQuestion:
    """TrainingQuestion 模型测试。"""

    def test_valid_multiple_choice(self):
        q = TrainingQuestion(
            question_id="q1",
            question_type="MULTIPLE_CHOICE",
            prompt="adapt 最接近哪一项？",
            options=[TrainingOption(id="A", text="adjust to"), TrainingOption(id="B", text="remove")],
            answer="A",
            explanation="adapt 表示适应。",
            target_ability="VOCABULARY_CONTEXT",
            error_type_on_wrong="VOCABULARY_CONTEXT_ERROR",
        )
        assert q.question_type == "MULTIPLE_CHOICE"
        assert len(q.options) == 2

    def test_error_type_on_wrong_null_when_not_provided(self):
        q = TrainingQuestion(
            question_id="q2",
            question_type="MULTIPLE_CHOICE",
            prompt="What does this mean?",
            options=[TrainingOption(id="A", text="X"), TrainingOption(id="B", text="Y")],
            answer="A",
            explanation="test",
            target_ability="VOCABULARY_CONTEXT",
        )
        assert q.error_type_on_wrong is None

    def test_non_multiple_choice_question_type_accepted_in_model(self):
        """模型层面不校验 question_type 枚举——该校验在评分器或 Service 层。
        模型只做结构约束。"""
        q = TrainingQuestion(
            question_id="q3",
            question_type="ESSAY",
            prompt="Write something.",
            options=[TrainingOption(id="A", text="X")],
            answer="A",
            explanation="test",
            target_ability="VOCABULARY_CONTEXT",
        )
        assert q.question_type == "ESSAY"


class TestTrainingTaskContent:
    """TrainingTaskContent 模型测试。"""

    def test_minimal_content(self):
        content = TrainingTaskContent(
            title="词汇语境练习",
            raw_text="英文材料",
            instructions="请选择最符合语境的答案。",
            questions=[
                TrainingQuestion(
                    question_id="q1",
                    question_type="MULTIPLE_CHOICE",
                    prompt="adapt 最接近哪一项？",
                    options=[TrainingOption(id="A", text="adjust to"), TrainingOption(id="B", text="remove")],
                    answer="A",
                    explanation="adapt 表示适应。",
                    target_ability="VOCABULARY_CONTEXT",
                )
            ],
        )
        assert len(content.questions) == 1


class TestTrainingAnswer:
    """TrainingAnswer 模型测试。"""

    def test_valid_answer(self):
        a = TrainingAnswer(question_id="q1", answer="A")
        assert a.question_id == "q1"
        assert a.answer == "A"


class TestTrainingSubmitRequest:
    """TrainingSubmitRequest 模型测试。"""

    def test_minimal_valid_request(self):
        req = TrainingSubmitRequest(answers=[TrainingAnswer(question_id="q1", answer="A")])
        assert len(req.answers) == 1
        assert req.time_spent_seconds is None
        assert req.used_hints is None

    def test_empty_answers_rejected(self):
        """空 answers 校验失败。"""
        with pytest.raises(ValidationError):
            TrainingSubmitRequest(answers=[])

    def test_negative_time_spent_rejected(self):
        """time_spent_seconds=-1 校验失败。"""
        with pytest.raises(ValidationError):
            TrainingSubmitRequest(
                answers=[TrainingAnswer(question_id="q1", answer="A")],
                time_spent_seconds=-1,
            )

    def test_user_id_in_body_rejected(self):
        """请求体包含 user_id 校验失败。"""
        with pytest.raises(ValidationError):
            TrainingSubmitRequest(
                answers=[TrainingAnswer(question_id="q1", answer="A")],
                user_id=1,  # type: ignore[call-arg]
            )

    def test_session_id_in_body_rejected(self):
        """请求体包含 session_id 校验失败。"""
        with pytest.raises(ValidationError):
            TrainingSubmitRequest(
                answers=[TrainingAnswer(question_id="q1", answer="A")],
                session_id=1,  # type: ignore[call-arg]
            )

    def test_with_optional_fields(self):
        req = TrainingSubmitRequest(
            answers=[TrainingAnswer(question_id="q1", answer="A")],
            time_spent_seconds=45,
            used_hints=["definition_hint"],
        )
        assert req.time_spent_seconds == 45
        assert req.used_hints == ["definition_hint"]


class TestQuestionScoreResult:
    """QuestionScoreResult 模型测试。"""

    def test_correct_result(self):
        r = QuestionScoreResult(
            question_id="q1",
            user_answer="A",
            standard_answer="A",
            is_correct=True,
            error_type=None,
            target_ability="VOCABULARY_CONTEXT",
            explanation="adapt 表示适应。",
        )
        assert r.is_correct is True
        assert r.error_type is None

    def test_incorrect_result(self):
        r = QuestionScoreResult(
            question_id="q1",
            user_answer="B",
            standard_answer="A",
            is_correct=False,
            error_type="VOCABULARY_CONTEXT_ERROR",
            target_ability="VOCABULARY_CONTEXT",
            explanation="adapt 表示适应。",
        )
        assert r.is_correct is False
        assert r.error_type == "VOCABULARY_CONTEXT_ERROR"


class TestTrainingScore:
    """TrainingScore 模型测试。"""

    def test_full_score(self):
        s = TrainingScore(total=3, correct=2, accuracy=0.6667, passed=True)
        assert s.total == 3
        assert s.correct == 2
        assert s.passed is True


class TestTrainingSubmitResponse:
    """TrainingSubmitResponse 模型测试。"""

    def test_full_response(self):
        resp = TrainingSubmitResponse(
            task_id=1,
            session_id=2,
            score=TrainingScore(total=1, correct=1, accuracy=1.0, passed=True),
            question_results=[
                QuestionScoreResult(
                    question_id="q1",
                    user_answer="A",
                    standard_answer="A",
                    is_correct=True,
                    error_type=None,
                    target_ability="VOCABULARY_CONTEXT",
                    explanation="adapt 表示适应。",
                )
            ],
            evidence_id=10,
            profile_suggestion_id=11,
            agent_feedback="本题正确！",
        )
        assert resp.task_id == 1
        assert resp.evidence_id == 10


class TestTrainingTaskSummary:
    """TrainingTaskSummary 模型测试。"""

    def test_valid_summary(self):
        summary = TrainingTaskSummary(
            task_id=1,
            session_id=2,
            task_type="LOW_PRESSURE_LEARNING",
            target_ability="VOCABULARY_CONTEXT",
            difficulty_params={},
            content={},
            quality_check_result={"status": "PASSED"},
            created_at="2026-06-20 12:00:00",
        )
        assert summary.task_id == 1
        assert summary.task_type == "LOW_PRESSURE_LEARNING"


class TestTrainingResultResponse:
    """TrainingResultResponse 模型测试。"""

    def test_with_submission(self):
        resp = TrainingResultResponse(
            task=TrainingTaskSummary(
                task_id=1,
                session_id=2,
                task_type="LOW_PRESSURE_LEARNING",
                target_ability="VOCABULARY_CONTEXT",
                difficulty_params={},
                content={},
                quality_check_result={"status": "PASSED"},
                created_at="2026-06-20 12:00:00",
            ),
            latest_submission={
                "evidence_id": 10,
                "score": {"total": 1, "correct": 1, "accuracy": 1.0, "passed": True},
                "question_results": [],
                "profile_suggestion_id": 11,
                "created_at": "2026-06-20 12:01:00",
            },
        )
        assert resp.latest_submission is not None
        assert resp.latest_submission["evidence_id"] == 10

    def test_without_submission(self):
        """无提交时 latest_submission 为 None。"""
        resp = TrainingResultResponse(
            task=TrainingTaskSummary(
                task_id=1,
                session_id=2,
                task_type="LOW_PRESSURE_LEARNING",
                target_ability="VOCABULARY_CONTEXT",
                difficulty_params={},
                content={},
                quality_check_result={},
                created_at="2026-06-20 12:00:00",
            ),
            latest_submission=None,
        )
        assert resp.latest_submission is None
