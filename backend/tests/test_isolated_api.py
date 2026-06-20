"""隔离测试 API 端点测试。

测试 POST /api/isolated-tests/start 和 POST /api/isolated-tests/attempts/{attempt_id}/submit。
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_database
from app.main import create_app
from app.repositories.isolated_tests import create_isolated_test_item
from app.repositories.training import create_training_session
from app.repositories.users import create_user
from temp_paths import temp_db_path


@pytest.fixture
def db_path() -> str:
    path = str(temp_db_path("isolated_api"))
    init_database(path)
    return path


@pytest.fixture
def settings(db_path: str) -> Settings:
    return Settings(
        app_name="LingoForge Test",
        database_path=db_path,
        cors_origins=[],
        llm_mode="mock",
        llm_provider="deepseek",
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = create_app(settings)
    return TestClient(app)


def _create_active_item(db_path: str, target_ability: str = "VOCABULARY_CONTEXT") -> int:
    return create_isolated_test_item(
        db_path,
        target_ability=target_ability,
        item_version="v1",
        item_payload={
            "prompt": "climate 最接近哪一项？",
            "options": [{"id": "A", "text": "气候"}, {"id": "B", "text": "环境"}],
        },
        answer_key={"correct": "A"},
        answer_rationale={"reason": "climate 意为气候"},
        distractor_rationale={"B": "环境更接近 environment"},
        is_active=True,
    )


class TestIsolatedStart:
    """POST /api/isolated-tests/start 测试。"""

    def test_正常开始_attempt(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "隔离测试用户")
        _create_active_item(db_path)
        _create_active_item(db_path)
        resp = client.post(
            "/api/isolated-tests/start",
            json={"target_ability": "VOCABULARY_CONTEXT", "limit": 2},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["attempt_id"] >= 1
        assert len(data["items"]) >= 1
        for item in data["items"]:
            assert "prompt" in item
            assert "options" in item

    def test_响应不含答案字段(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "防泄漏测试用户")
        _create_active_item(db_path)
        resp = client.post(
            "/api/isolated-tests/start",
            json={"target_ability": "VOCABULARY_CONTEXT", "limit": 1},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        dumped = json.dumps(resp.json(), ensure_ascii=False)
        for forbidden in ("answer_key", "answer_rationale", "distractor_rationale"):
            assert forbidden not in dumped, f"响应包含禁止字段: {forbidden}"

    def test_缺少用户头返回_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/isolated-tests/start",
            json={"target_ability": "VOCABULARY_CONTEXT", "limit": 1},
        )
        assert resp.status_code == 422

    def test_无题目时返回_400(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "无题目用户")
        resp = client.post(
            "/api/isolated-tests/start",
            json={"target_ability": "VOCABULARY_CONTEXT", "limit": 3},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 400


    def test_不能绑定其他用户_session(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "隔离用户")
        other_uid = create_user(db_path, "其他 session 用户")
        other_session_id = create_training_session(
            db_path,
            user_id=other_uid,
            stage="ISOLATED_TEST",
            status="IN_PROGRESS",
        )
        _create_active_item(db_path)

        resp = client.post(
            "/api/isolated-tests/start",
            json={"target_ability": "VOCABULARY_CONTEXT", "limit": 1},
            headers={
                "X-LingoForge-User-Id": str(uid),
                "X-LingoForge-Session-Id": str(other_session_id),
            },
        )

        assert resp.status_code == 403
        assert resp.json()["detail"]["code"] == "SESSION_ACCESS_DENIED"


class TestIsolatedSubmit:
    """POST /api/isolated-tests/attempts/{attempt_id}/submit 测试。"""

    def test_正常提交得到分数和_evidence_id(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "提交测试用户")
        _create_active_item(db_path)
        resp = client.post(
            "/api/isolated-tests/start",
            json={"target_ability": "VOCABULARY_CONTEXT", "limit": 1},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        attempt_id = resp.json()["attempt_id"]

        submit_resp = client.post(
            f"/api/isolated-tests/attempts/{attempt_id}/submit",
            json={
                "answers": [{"item_id": 1, "answer": "A"}],
                "time_spent_seconds": 30,
            },
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert submit_resp.status_code == 200
        data = submit_resp.json()
        assert data["attempt_id"] == attempt_id
        assert data["evidence_id"] >= 1
        assert data["score"]["total"] >= 1

    def test_其他用户提交_attempt_被拒绝(self, client: TestClient, db_path: str) -> None:
        uid1 = create_user(db_path, "提交所有者")
        _create_active_item(db_path)
        resp = client.post(
            "/api/isolated-tests/start",
            json={"target_ability": "VOCABULARY_CONTEXT", "limit": 1},
            headers={"X-LingoForge-User-Id": str(uid1)},
        )
        attempt_id = resp.json()["attempt_id"]
        uid2 = create_user(db_path, "非所有者")
        submit_resp = client.post(
            f"/api/isolated-tests/attempts/{attempt_id}/submit",
            json={"answers": [{"item_id": 1, "answer": "A"}]},
            headers={"X-LingoForge-User-Id": str(uid2)},
        )
        assert submit_resp.status_code == 403

    def test_重复提交返回_409(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "重复提交用户")
        _create_active_item(db_path)
        resp = client.post(
            "/api/isolated-tests/start",
            json={"target_ability": "VOCABULARY_CONTEXT", "limit": 1},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        attempt_id = resp.json()["attempt_id"]
        # 第一次提交
        client.post(
            f"/api/isolated-tests/attempts/{attempt_id}/submit",
            json={"answers": [{"item_id": 1, "answer": "A"}]},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        # 第二次提交
        submit_resp = client.post(
            f"/api/isolated-tests/attempts/{attempt_id}/submit",
            json={"answers": [{"item_id": 1, "answer": "B"}]},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert submit_resp.status_code == 409

    def test_响应不含答案字段(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "防泄漏提交")
        _create_active_item(db_path)
        resp = client.post(
            "/api/isolated-tests/start",
            json={"target_ability": "VOCABULARY_CONTEXT", "limit": 1},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        attempt_id = resp.json()["attempt_id"]
        submit_resp = client.post(
            f"/api/isolated-tests/attempts/{attempt_id}/submit",
            json={"answers": [{"item_id": 1, "answer": "A"}]},
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert submit_resp.status_code == 200
        dumped = json.dumps(submit_resp.json(), ensure_ascii=False)
        for forbidden in ("answer_key", "answer_rationale", "distractor_rationale"):
            assert forbidden not in dumped, f"提交响应包含禁止字段: {forbidden}"
