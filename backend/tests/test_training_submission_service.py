"""训练提交编排服务测试。"""

from __future__ import annotations

import pytest

from app.database import init_database
from app.repositories.training import (
    create_generated_task,
    create_training_session,
    get_learning_evidence_by_task,
)
from app.repositories.users import (
    create_user,
    get_user_profile_suggestions,
)
from app.services.training_submission import (
    TrainingSubmissionError,
    submit_training_task,
)
from temp_paths import temp_db_path


@pytest.fixture
def db_path():
    path = temp_db_path("submission_svc")
    init_database(path)
    return path


@pytest.fixture
def user_id(db_path):
    return create_user(db_path, "提交服务测试用户")


@pytest.fixture
def other_user_id(db_path):
    return create_user(db_path, "其他用户")


@pytest.fixture
def session_id(db_path, user_id):
    return create_training_session(db_path, user_id=user_id, stage="FIRST_MAIN")


def _create_mc_task(db_path, user_id, session_id) -> int:
    """创建一个 MULTIPLE_CHOICE 训练任务。"""
    content = {
        "title": "词汇语境练习",
        "raw_text": "The climate is changing rapidly.",
        "instructions": "请选择最符合语境的答案。",
        "questions": [
            {
                "question_id": "q1",
                "question_type": "MULTIPLE_CHOICE",
                "prompt": "climate 最接近哪一项？",
                "options": [
                    {"id": "A", "text": "气候"},
                    {"id": "B", "text": "变化"},
                ],
                "answer": "A",
                "explanation": "climate = 气候。",
                "target_ability": "VOCABULARY_CONTEXT",
                "error_type_on_wrong": "VOCABULARY_CONTEXT_ERROR",
            },
            {
                "question_id": "q2",
                "question_type": "MULTIPLE_CHOICE",
                "prompt": "rapidly 最接近哪一项？",
                "options": [
                    {"id": "A", "text": "缓慢地"},
                    {"id": "B", "text": "迅速地"},
                ],
                "answer": "B",
                "explanation": "rapidly = 迅速地。",
                "target_ability": "VOCABULARY_CONTEXT",
                "error_type_on_wrong": "VOCABULARY_CONTEXT_ERROR",
            },
        ],
        "agent_feedback": "",
        "source": "TEST",
    }
    return create_generated_task(
        db_path,
        session_id=session_id,
        user_id=user_id,
        task_type="LOW_PRESSURE_LEARNING",
        target_ability="VOCABULARY_CONTEXT",
        content_json=content,
        quality_check_result={"status": "PASSED"},
    )


class TestSubmitTrainingTask:
    """submit_training_task 测试。"""

    def test_normal_submission_full_loop(self, db_path, user_id, session_id):
        task_id = _create_mc_task(db_path, user_id, session_id)
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
        task_id = _create_mc_task(db_path, user_id, session_id)
        answers = [{"question_id": "q1", "answer": "A"}]
        with pytest.raises(TrainingSubmissionError) as exc:
            submit_training_task(db_path, user_id=other_user_id, task_id=task_id, answers=answers)
        assert exc.value.code == "TASK_ACCESS_DENIED"

    def test_nonexistent_task_returns_error(self, db_path, user_id):
        with pytest.raises(TrainingSubmissionError) as exc:
            submit_training_task(db_path, user_id=user_id, task_id=999, answers=[])
        assert exc.value.code == "TASK_NOT_FOUND"

    def test_writes_evidence_and_suggestion(self, db_path, user_id, session_id):
        task_id = _create_mc_task(db_path, user_id, session_id)
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
        task_id = _create_mc_task(db_path, user_id, session_id)
        answers = [{"question_id": "q1", "answer": "A"}, {"question_id": "q2", "answer": "A"}]
        result = submit_training_task(
            db_path, user_id=user_id, task_id=task_id,
            answers=answers, used_hints=["definition_hint"],
        )
        assert result["score"]["correct"] == 1
