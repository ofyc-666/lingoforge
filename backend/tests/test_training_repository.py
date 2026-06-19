"""训练会话、生成任务和学习证据 Repository 测试。"""

from __future__ import annotations

import pytest

from app.database import init_database
from app.repositories.users import create_user
from app.repositories.vocabulary import create_skill_version
from app.repositories.training import (
    create_generated_task,
    create_learning_evidence,
    create_training_session,
    create_task_validation,
    get_generated_task,
    get_learning_evidence_by_session,
    get_learning_evidence_by_task,
    get_learning_evidence_by_user,
    update_session_status,
)
from temp_paths import temp_db_path


@pytest.fixture
def db_path():
    path = temp_db_path("training_repo")
    init_database(path)
    return path


@pytest.fixture
def user_id(db_path):
    return create_user(db_path, "训练测试用户")


@pytest.fixture
def session_id(db_path, user_id):
    return create_training_session(db_path, user_id=user_id, stage="FIRST_MAIN", status="IN_PROGRESS")


@pytest.fixture
def skill_id(db_path):
    return create_skill_version(
        db_path, skill_id="vocab_context", version="1.0.0",
        target_ability="VOCABULARY_CONTEXT",
    )


@pytest.fixture
def task_id(db_path, user_id, session_id, skill_id):
    return create_generated_task(
        db_path,
        session_id=session_id,
        user_id=user_id,
        task_type="LOW_PRESSURE_LEARNING",
        skill_version_id=skill_id,
        target_ability="VOCABULARY_CONTEXT",
        difficulty_params={"level": 1},
        content_json={"text": "test content"},
        quality_requirements={"min_words": 50},
    )


class TestTrainingSessionRepository:
    """训练会话 Repository 测试。"""

    def test_create_session(self, db_path, user_id):
        sid = create_training_session(db_path, user_id=user_id, stage="DIAGNOSTIC")
        assert sid >= 1

    def test_create_with_default_status(self, db_path, user_id):
        sid = create_training_session(db_path, user_id=user_id, stage="DIAGNOSTIC")
        # 验证默认状态为 PENDING
        from app.repositories.base import fetch_one
        session = fetch_one(db_path, "SELECT * FROM training_sessions WHERE id = ?", (sid,))
        assert session["status"] == "PENDING"

    def test_update_status(self, db_path, session_id):
        update_session_status(db_path, session_id, status="COMPLETED")
        from app.repositories.base import fetch_one
        session = fetch_one(db_path, "SELECT * FROM training_sessions WHERE id = ?", (session_id,))
        assert session["status"] == "COMPLETED"
        assert session["completed_at"] is not None

    def test_update_nonexistent_session_does_not_raise(self, db_path):
        # 不应抛出异常
        update_session_status(db_path, 999, status="COMPLETED")


class TestGeneratedTaskRepository:
    """生成任务 Repository 测试。"""

    def test_create_and_get_task(self, db_path, task_id, session_id, user_id, skill_id):
        task = get_generated_task(db_path, task_id)
        assert task is not None
        assert task["session_id"] == session_id
        assert task["user_id"] == user_id
        assert task["task_type"] == "LOW_PRESSURE_LEARNING"
        assert task["skill_version_id"] == skill_id
        assert task["target_ability"] == "VOCABULARY_CONTEXT"
        assert task["difficulty_params"] == {"level": 1}
        assert task["content_json"] == {"text": "test content"}
        assert task["quality_requirements"] == {"min_words": 50}

    def test_get_nonexistent_task_returns_none(self, db_path):
        assert get_generated_task(db_path, 999) is None

    def test_json_defaults(self, db_path, session_id, user_id):
        tid = create_generated_task(
            db_path, session_id=session_id, user_id=user_id,
            task_type="TRANSFER_PRACTICE", target_ability="SENTENCE_LOGIC",
        )
        task = get_generated_task(db_path, tid)
        assert task["difficulty_params"] == {}
        assert task["content_json"] == {}
        assert task["quality_requirements"] == {}
        assert task["quality_check_result"] == {}

    def test_foreign_key_enforcement(self, db_path, user_id):
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            create_generated_task(
                db_path, session_id=999, user_id=user_id,
                task_type="SHORT_TRAINING", target_ability="VOCABULARY_CONTEXT",
            )


class TestTaskValidationRepository:
    """任务校验 Repository 测试。"""

    def test_write_validation_record(self, db_path, task_id):
        vid = create_task_validation(
            db_path,
            task_id=task_id,
            validation_status="PASSED",
            error_codes=[],
            error_details={},
            attempt_number=1,
            used_seed_fallback=False,
        )
        assert vid >= 1

    def test_failed_validation_with_errors(self, db_path, task_id):
        create_task_validation(
            db_path,
            task_id=task_id,
            validation_status="FAILED",
            error_codes=["MISSING_FIELD", "INVALID_OPTIONS"],
            error_details={"field": "content_json", "reason": "缺少题干"},
            attempt_number=1,
            used_seed_fallback=False,
        )
        from app.repositories.base import fetch_all
        records = fetch_all(db_path, "SELECT * FROM generated_task_validations WHERE task_id = ?", (task_id,))
        assert len(records) == 1
        from app.storage.json_fields import from_json_text
        assert from_json_text(records[0]["error_codes"], []) == ["MISSING_FIELD", "INVALID_OPTIONS"]
        assert from_json_text(records[0]["error_details"], {}) == {"field": "content_json", "reason": "缺少题干"}

    def test_seed_fallback_marked(self, db_path, task_id):
        create_task_validation(
            db_path, task_id=task_id, validation_status="FALLBACK_USED",
            attempt_number=2, used_seed_fallback=True,
        )
        from app.repositories.base import fetch_one
        record = fetch_one(db_path, "SELECT * FROM generated_task_validations WHERE task_id = ?", (task_id,))
        assert record["used_seed_fallback"] == 1
        assert record["attempt_number"] == 2


class TestLearningEvidenceRepository:
    """学习证据 Repository 测试。"""

    def test_write_evidence(self, db_path, user_id, session_id, task_id):
        eid = create_learning_evidence(
            db_path,
            user_id=user_id,
            session_id=session_id,
            task_id=task_id,
            evidence_type="TRAINING_ANSWER",
            payload={"answer": "B", "time_spent": 30},
        )
        assert eid >= 1

    def test_evidence_is_append_only(self, db_path, user_id, session_id, task_id):
        eid1 = create_learning_evidence(
            db_path, user_id=user_id, session_id=session_id, task_id=task_id,
            evidence_type="TRAINING_ANSWER", payload={"answer": "A"},
        )
        eid2 = create_learning_evidence(
            db_path, user_id=user_id, session_id=session_id, task_id=task_id,
            evidence_type="TRAINING_ANSWER", payload={"answer": "B"},
        )
        # 两条记录都存在，不覆盖
        assert eid1 != eid2
        records = get_learning_evidence_by_user(db_path, user_id)
        assert len(records) == 2

    def test_query_by_user(self, db_path, user_id, session_id, task_id):
        create_learning_evidence(db_path, user_id=user_id, session_id=session_id,
                                 task_id=task_id, evidence_type="TRAINING_ANSWER", payload={"q": 1})
        create_learning_evidence(db_path, user_id=user_id, session_id=session_id,
                                 task_id=task_id, evidence_type="PROMPT_USAGE", payload={"hint": True})

        records = get_learning_evidence_by_user(db_path, user_id)
        assert len(records) == 2

    def test_query_by_session(self, db_path, user_id, session_id, task_id):
        create_learning_evidence(db_path, user_id=user_id, session_id=session_id,
                                 task_id=task_id, evidence_type="TRAINING_ANSWER", payload={})
        records = get_learning_evidence_by_session(db_path, session_id)
        assert len(records) == 1

    def test_query_by_task(self, db_path, user_id, session_id, task_id):
        create_learning_evidence(db_path, user_id=user_id, session_id=session_id,
                                 task_id=task_id, evidence_type="TRAINING_ANSWER", payload={})
        records = get_learning_evidence_by_task(db_path, task_id)
        assert len(records) == 1

    def test_empty_query_returns_empty(self, db_path):
        assert get_learning_evidence_by_user(db_path, 999) == []
        assert get_learning_evidence_by_session(db_path, 999) == []
        assert get_learning_evidence_by_task(db_path, 999) == []

    def test_payload_is_object(self, db_path, user_id, session_id, task_id):
        payload = {"answer": "C", "is_correct": True, "time_ms": 45000}
        create_learning_evidence(db_path, user_id=user_id, session_id=session_id,
                                 task_id=task_id, evidence_type="GRADING_RESULT", payload=payload)
        records = get_learning_evidence_by_user(db_path, user_id)
        assert records[0]["payload_json"] == payload
