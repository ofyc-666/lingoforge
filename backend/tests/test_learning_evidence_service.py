"""学习证据写入服务测试。"""

from __future__ import annotations

import pytest

from app.database import init_database
from app.repositories.training import (
    create_generated_task,
    create_training_session,
    get_learning_evidence_by_task,
)
from app.repositories.users import create_user
from app.services.learning_evidence import record_training_submission_evidence
from temp_paths import temp_db_path


@pytest.fixture
def db_path():
    path = temp_db_path("evidence_svc")
    init_database(path)
    return path


@pytest.fixture
def user_id(db_path):
    return create_user(db_path, "证据服务测试用户")


@pytest.fixture
def session_id(db_path, user_id):
    return create_training_session(db_path, user_id=user_id, stage="FIRST_MAIN")


@pytest.fixture
def task_id(db_path, user_id, session_id):
    return create_generated_task(
        db_path,
        session_id=session_id,
        user_id=user_id,
        task_type="LOW_PRESSURE_LEARNING",
        target_ability="VOCABULARY_CONTEXT",
    )


def _sample_answers() -> list[dict]:
    return [{"question_id": "q1", "answer": "A"}]


def _sample_score() -> dict:
    return {
        "total": 1,
        "correct": 1,
        "accuracy": 1.0,
        "passed": True,
        "question_results": [
            {
                "question_id": "q1",
                "user_answer": "A",
                "standard_answer": "A",
                "is_correct": True,
                "error_type": None,
                "target_ability": "VOCABULARY_CONTEXT",
                "explanation": "测试解释。",
            }
        ],
        "error_types": [],
        "used_hints": [],
    }


class TestRecordTrainingSubmissionEvidence:
    """record_training_submission_evidence 测试。"""

    def test_writes_evidence_and_reads_back(self, db_path, user_id, session_id, task_id):
        evidence_id = record_training_submission_evidence(
            db_path,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            answers=_sample_answers(),
            score_result=_sample_score(),
            time_spent_seconds=45,
        )
        assert evidence_id >= 1

        records = get_learning_evidence_by_task(db_path, task_id)
        assert len(records) == 1
        record = records[0]
        assert record["evidence_type"] == "TRAINING_ANSWER"
        assert record["user_id"] == user_id
        assert record["session_id"] == session_id

        payload = record["payload_json"]
        assert payload["event"] == "TRAINING_SUBMISSION_SCORED"
        assert payload["task_id"] == task_id
        assert payload["session_id"] == session_id
        assert payload["time_spent_seconds"] == 45
        assert len(payload["answers"]) == 1
        assert payload["score"]["passed"] is True

    def test_two_writes_produce_two_evidence(self, db_path, user_id, session_id, task_id):
        eid1 = record_training_submission_evidence(
            db_path, user_id=user_id, session_id=session_id,
            task_id=task_id, answers=_sample_answers(), score_result=_sample_score(),
        )
        eid2 = record_training_submission_evidence(
            db_path, user_id=user_id, session_id=session_id,
            task_id=task_id, answers=_sample_answers(), score_result=_sample_score(),
        )
        assert eid1 != eid2
        records = get_learning_evidence_by_task(db_path, task_id)
        assert len(records) == 2

    def test_payload_includes_error_types_and_target_abilities(self, db_path, user_id, session_id, task_id):
        score = {
            "total": 2,
            "correct": 1,
            "accuracy": 0.5,
            "passed": False,
            "question_results": [],
            "error_types": ["VOCABULARY_CONTEXT_ERROR"],
            "used_hints": ["definition_hint"],
        }
        evidence_id = record_training_submission_evidence(
            db_path, user_id=user_id, session_id=session_id,
            task_id=task_id, answers=_sample_answers(), score_result=score,
            used_hints=["definition_hint"],
        )
        records = get_learning_evidence_by_task(db_path, task_id)
        payload = records[0]["payload_json"]
        assert "VOCABULARY_CONTEXT_ERROR" in payload["error_types"]
        assert "definition_hint" in payload["used_hints"]
