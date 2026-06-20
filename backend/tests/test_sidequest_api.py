"""副线 API 端点测试。

测试 POST /api/sidequest/airport-ticket/complete。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_database
from app.main import create_app
from app.repositories.training import get_learning_evidence_by_user
from app.repositories.users import create_user, get_latest_profile
from app.repositories.sidequest import get_signals_by_run
from temp_paths import temp_db_path


@pytest.fixture
def db_path() -> str:
    path = str(temp_db_path("sidequest_api"))
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


class TestAirportTicketComplete:
    """POST /api/sidequest/airport-ticket/complete 测试。"""

    def test_正常完成副线_run和signal可读回(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "副线测试用户")
        resp = client.post(
            "/api/sidequest/airport-ticket/complete",
            json={
                "selected_expression": "I'd like to book a flight.",
                "scene": "AIRPORT_TICKET",
                "result": {"completed": True},
            },
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sidequest_run_id"] >= 1
        assert data["signal_id"] >= 1
        assert data["is_pending_verification"] is True

        # 从 repository 验证 signal 可读回
        signals = get_signals_by_run(db_path, data["sidequest_run_id"])
        assert len(signals) >= 1
        assert signals[0]["is_pending_verification"] == 1

    def test_请求体含_user_id_返回_422(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "身份测试3")
        resp = client.post(
            "/api/sidequest/airport-ticket/complete",
            json={
                "selected_expression": "test",
                "scene": "AIRPORT_TICKET",
                "result": {"completed": True},
                "user_id": uid,
            },
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 422

    def test_不写入_learning_evidence(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "无证据测试")
        # 记录提交前的 evidence 数量
        before = len(get_learning_evidence_by_user(db_path, uid))
        resp = client.post(
            "/api/sidequest/airport-ticket/complete",
            json={
                "selected_expression": "I'd like to book a flight.",
                "scene": "AIRPORT_TICKET",
                "result": {"completed": True},
            },
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        after = len(get_learning_evidence_by_user(db_path, uid))
        assert after == before, f"不应写入 learning_evidence (前={before}, 后={after})"

    def test_不写入_profile_snapshot(self, client: TestClient, db_path: str) -> None:
        uid = create_user(db_path, "无画像测试")
        resp = client.post(
            "/api/sidequest/airport-ticket/complete",
            json={
                "selected_expression": "I'd like to book a flight.",
                "scene": "AIRPORT_TICKET",
                "result": {"completed": True},
            },
            headers={"X-LingoForge-User-Id": str(uid)},
        )
        assert resp.status_code == 200
        latest_profile = get_latest_profile(db_path, uid)
        assert latest_profile is None, "不应写入 profile_snapshot"

    def test_缺少用户头返回_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/sidequest/airport-ticket/complete",
            json={
                "selected_expression": "test",
                "scene": "AIRPORT_TICKET",
                "result": {"completed": True},
            },
        )
        assert resp.status_code == 422
