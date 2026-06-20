"""训练提交编排服务测试。"""

from __future__ import annotations

import pytest

from app.database import init_database
from app.repositories.training import create_generated_task, get_learning_evidence_by_task
from app.repositories.users import create_user, get_user_profile_suggestions
from app.services.training_submission import (
    TrainingSubmissionError,
    submit_training_task,
)
from factories import create_multiple_choice_task, create_user_with_session
from temp_paths import temp_db_path


@pytest.fixture
def db_path():
    path = temp_db_path("submission_svc")
    init_database(path)
    return path


@pytest.fixture
def ctx(db_path):
    return create_user_with_session(db_path)


@pytest.fixture
def user_id(ctx):
    return ctx["user_id"]


@pytest.fixture
def session_id(ctx):
    return ctx["session_id"]


@pytest.fixture
def other_user_id(db_path):
    return create_user(db_path, "其他用户")


class TestSubmitTrainingTask:
    """submit_training_task 测试。"""

    def test_normal_submission_full_loop(self, db_path, user_id, session_id):
        task_id = create_multiple_choice_task(db_path, user_id=user_id, session_id=session_id)
        answers = [
            {"question_id": "q1", "answer": "A"},
            {"question_id": "q2", "answer": "B"},
        ]
        result = submit_training_task(
            db_path,
            user_id=user_id,
            task_id=task_id,
            answers=answers,
            time_spent_seconds=60,
        )
        assert result["task_id"] == task_id
        assert result["session_id"] == session_id
        assert result["score"]["total"] == 2
        assert result["score"]["correct"] == 2
        assert result["score"]["passed"] is True
        assert result["evidence_id"] >= 1
        assert result["profile_suggestion_id"] is not None
        assert result["profile_suggestion_id"] >= 1

    def test_other_user_submission_rejected(self, db_path, user_id, other_user_id, session_id):
        task_id = create_multiple_choice_task(db_path, user_id=user_id, session_id=session_id)
        answers = [{"question_id": "q1", "answer": "A"}]
        with pytest.raises(TrainingSubmissionError) as exc:
            submit_training_task(db_path, user_id=other_user_id, task_id=task_id, answers=answers)
        assert exc.value.code == "TASK_ACCESS_DENIED"

    def test_nonexistent_task_returns_error(self, db_path, user_id):
        with pytest.raises(TrainingSubmissionError) as exc:
            submit_training_task(db_path, user_id=user_id, task_id=999, answers=[])
        assert exc.value.code == "TASK_NOT_FOUND"

    def test_writes_evidence_and_suggestion(self, db_path, user_id, session_id):
        task_id = create_multiple_choice_task(db_path, user_id=user_id, session_id=session_id)
        answers = [{"question_id": "q1", "answer": "A"}, {"question_id": "q2", "answer": "B"}]
        result = submit_training_task(db_path, user_id=user_id, task_id=task_id, answers=answers)

        # 证据存在
        records = get_learning_evidence_by_task(db_path, task_id)
        assert len(records) == 1
        assert records[0]["id"] == result["evidence_id"]

        # 画像建议存在
        suggestions = get_user_profile_suggestions(db_path, user_id)
        assert any(s["id"] == result["profile_suggestion_id"] for s in suggestions)

    def test_with_hints(self, db_path, user_id, session_id):
        task_id = create_multiple_choice_task(db_path, user_id=user_id, session_id=session_id)
        answers = [{"question_id": "q1", "answer": "A"}, {"question_id": "q2", "answer": "A"}]
        result = submit_training_task(
            db_path, user_id=user_id, task_id=task_id,
            answers=answers, used_hints=["definition_hint"],
        )
        assert result["score"]["correct"] == 1

    def test_unsupported_question_type_returns_stable_error(self, db_path, user_id, session_id):
        task_id = create_generated_task(
            db_path,
            session_id=session_id,
            user_id=user_id,
            task_type="LOW_PRESSURE_LEARNING",
            target_ability="VOCABULARY_CONTEXT",
            content_json={
                "questions": [
                    {
                        "question_id": "q1",
                        "question_type": "ESSAY",
                        "answer": "A",
                        "target_ability": "VOCABULARY_CONTEXT",
                    }
                ]
            },
            quality_check_result={"status": "PASSED"},
        )
        with pytest.raises(TrainingSubmissionError) as exc:
            submit_training_task(
                db_path,
                user_id=user_id,
                task_id=task_id,
                answers=[{"question_id": "q1", "answer": "A"}],
            )
        assert exc.value.code == "INVALID_TASK_CONTENT"
        assert exc.value.details["question_type"] == "ESSAY"

    def test_artifacts_are_rolled_back_when_profile_suggestion_fails(
        self,
        db_path,
        user_id,
        session_id,
        monkeypatch,
    ):
        task_id = create_multiple_choice_task(db_path, user_id=user_id, session_id=session_id)

        def fail_build_profile_suggestion_from_score(*, evidence_id, score_result):
            raise RuntimeError("simulated suggestion failure")

        monkeypatch.setattr(
            "app.services.training_submission.build_profile_suggestion_from_score",
            fail_build_profile_suggestion_from_score,
        )

        with pytest.raises(RuntimeError, match="simulated suggestion failure"):
            submit_training_task(
                db_path,
                user_id=user_id,
                task_id=task_id,
                answers=[{"question_id": "q1", "answer": "A"}],
            )

        assert get_learning_evidence_by_task(db_path, task_id) == []
        assert get_user_profile_suggestions(db_path, user_id) == []
