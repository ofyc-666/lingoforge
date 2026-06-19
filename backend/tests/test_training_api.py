"""训练提交与结果查询 API 路由测试。"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_database
from app.main import create_app
from app.repositories.training import create_generated_task, create_training_session
from app.repositories.users import create_user
from temp_paths import temp_db_path


@pytest.fixture
def db_path():
    path = str(temp_db_path("training_api"))
    init_database(path)
    return path


@pytest.fixture
def settings(db_path):
    return Settings(
        app_name="LingoForge Test",
        database_path=db_path,
        cors_origins=[],
        llm_mode="mock",
        llm_provider="deepseek",
    )


@pytest.fixture
def client(settings):
    app = create_app(settings)
    return TestClient(app)


def _create_user_and_task(db_path: str) -> tuple[int, int, int, str]:
    """创建测试用户、session 和 MULTIPLE_CHOICE 任务。返回 (user_id, session_id, task_id, db_path)。"""
    uid = create_user(db_path, "API 测试用户")
    sid = create_training_session(db_path, user_id=uid, stage="FIRST_MAIN")
    content = {
        "title": "词汇语境练习",
        "raw_text": "The climate is changing rapidly.",
        "instructions": "请选择最符合语境的答案。",
        "questions": [
            {
                "question_id": "q1",
                "question_type": "MULTIPLE_CHOICE",
                "prompt": "climate 最接近？",
                "options": [{"id": "A", "text": "气候"}, {"id": "B", "text": "变化"}],
                "answer": "A",
                "explanation": "climate = 气候。",
                "target_ability": "VOCABULARY_CONTEXT",
                "error_type_on_wrong": "VOCABULARY_CONTEXT_ERROR",
            },
        ],
        "agent_feedback": "",
        "source": "TEST",
    }
    tid = create_generated_task(
        db_path, session_id=sid, user_id=uid,
        task_type="LOW_PRESSURE_LEARNING",
        target_ability="VOCABULARY_CONTEXT",
        content_json=content,
        quality_check_result={"status": "PASSED"},
    )
    return uid, sid, tid, db_path


class TestTrainingSubmitAPI:
    """POST /api/training/tasks/{task_id}/submit 测试。"""

    def test_normal_submit_success(self, client, db_path):
        uid, sid, tid, _ = _create_user_and_task(db_path)
        response = client.post(
            f"/api/training/tasks/{tid}/submit",
            json={
                "answers": [{"question_id": "q1", "answer": "A"}],
                "time_spent_seconds": 30,
            },
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == tid
        assert data["session_id"] == sid
        assert data["score"]["total"] == 1
        assert data["evidence_id"] >= 1

    def test_identity_fields_in_body_rejected(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        response = client.post(
            f"/api/training/tasks/{tid}/submit",
            json={
                "answers": [{"question_id": "q1", "answer": "A"}],
                "user_id": uid,
            },
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert response.status_code == 422

    def test_other_user_task_rejected(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        other_uid = create_user(db_path, "其他")
        response = client.post(
            f"/api/training/tasks/{tid}/submit",
            json={"answers": [{"question_id": "q1", "answer": "A"}]},
            headers={"X-LingoForge-User-Id": str(other_uid)},
        )
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "TASK_ACCESS_DENIED"

    def test_invalid_answers_rejected(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        response = client.post(
            f"/api/training/tasks/{tid}/submit",
            json={"answers": []},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert response.status_code == 422

    def test_nonexistent_task_not_found(self, client, db_path):
        uid = create_user(db_path, "测试用户")
        response = client.post(
            "/api/training/tasks/99999/submit",
            json={"answers": [{"question_id": "q1", "answer": "A"}]},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "TASK_NOT_FOUND"

    def test_missing_user_header_rejected(self, client, db_path):
        response = client.post(
            "/api/training/tasks/1/submit",
            json={"answers": [{"question_id": "q1", "answer": "A"}]},
        )
        assert response.status_code == 422


class TestTrainingResultAPI:
    """GET /api/training/tasks/{task_id}/result 测试。"""

    def test_no_submission_returns_null(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        response = client.get(
            f"/api/training/tasks/{tid}/result",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["task"]["task_id"] == tid
        assert data["latest_submission"] is None

    def test_with_submission(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        # 先提交
        client.post(
            f"/api/training/tasks/{tid}/submit",
            json={"answers": [{"question_id": "q1", "answer": "A"}]},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        # 再查询
        response = client.get(
            f"/api/training/tasks/{tid}/result",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["latest_submission"] is not None
        assert data["latest_submission"]["evidence_id"] >= 1

    def test_two_submissions_returns_latest(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        # 两次提交
        client.post(
            f"/api/training/tasks/{tid}/submit",
            json={"answers": [{"question_id": "q1", "answer": "A"}]},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        client.post(
            f"/api/training/tasks/{tid}/submit",
            json={"answers": [{"question_id": "q1", "answer": "B"}]},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        response = client.get(
            f"/api/training/tasks/{tid}/result",
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        data = response.json()
        assert data["latest_submission"]["evidence_id"] >= 2

    def test_other_user_query_rejected(self, client, db_path):
        uid, _, tid, _ = _create_user_and_task(db_path)
        other_uid = create_user(db_path, "其他查询用户")
        response = client.get(
            f"/api/training/tasks/{tid}/result",
            headers={"X-LingoForge-User-Id": str(other_uid)},
        )
        assert response.status_code == 403
