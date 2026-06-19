from __future__ import annotations

import json
from collections.abc import Sequence

from fastapi.testclient import TestClient

from app.api.agent import get_agent_provider, get_settings
from app.config import Settings
from app.database import init_database
from app.llm.provider import LLMProviderError
from app.llm.types import LLMMessage, LLMResponse, LLMToolCall, LLMToolSpec
from app.main import create_app
from app.repositories.logs import get_tool_logs_by_session
from app.repositories.training import create_training_session
from app.repositories.users import create_profile_snapshot, create_user, save_user_goal
from temp_paths import temp_db_path


class ApiRecordingProvider:
    name = "mock"

    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def generate(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[LLMToolSpec] | None = None,
        timeout_seconds: float | None = None,
    ) -> LLMResponse:
        self.calls.append({
            "messages": list(messages),
            "tools": list(tools or ()),
            "timeout_seconds": timeout_seconds,
        })
        return self.responses.pop(0)


class BrokenProvider:
    name = "broken"
    code = "TEST_PROVIDER_FAILED"

    def generate(self, *_args, **_kwargs):
        raise LLMProviderError("secret provider traceback details")


def _final_response() -> LLMResponse:
    return LLMResponse(content=json.dumps({
        "decision_type": "PROFILE_READ",
        "next_step": "DONE",
        "final_answer": "已读取当前用户画像。",
    }, ensure_ascii=False))


def _client_with_provider(provider):
    db_path = temp_db_path("agent_api")
    init_database(db_path)
    user_id = create_user(db_path, "绑定用户")
    other_user_id = create_user(db_path, "其他用户")
    save_user_goal(db_path, user_id=user_id, target_score=550, interest_topics=["科技"])
    create_profile_snapshot(
        db_path,
        user_id=user_id,
        source="DIAGNOSTIC",
        profile={"level": "bound-profile"},
        evidence_refs=[11],
    )
    save_user_goal(db_path, user_id=other_user_id, target_score=710, interest_topics=["other-secret-topic"])
    create_profile_snapshot(
        db_path,
        user_id=other_user_id,
        source="DIAGNOSTIC",
        profile={"level": "other-secret-profile"},
        evidence_refs=[99],
    )
    session_id = create_training_session(db_path, user_id=user_id, stage="FIRST_MAIN", status="IN_PROGRESS")
    settings = Settings(database_path=str(db_path))
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_agent_provider] = lambda: provider
    return TestClient(app), db_path, user_id, other_user_id, session_id


def test_agent_api_runs_function_calling_loop_with_runtime_bound_identity():
    provider = ApiRecordingProvider([
        LLMResponse(tool_calls=(LLMToolCall(id="call-1", name="get_user_profile", arguments={}),)),
        _final_response(),
    ])
    client, db_path, user_id, _other_user_id, session_id = _client_with_provider(provider)

    response = client.post(
        "/api/agent/run",
        headers={
            "X-LingoForge-User-Id": str(user_id),
            "X-LingoForge-Session-Id": str(session_id),
        },
        json={"user_input": "读取我的画像"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "COMPLETED"
    assert payload["final_answer"] == "已读取当前用户画像。"
    assert payload["tool_calls"] == [
        {
            "tool_call_id": "call-1",
            "tool_name": "get_user_profile",
            "status": "SUCCESS",
            "error_code": None,
            "log_id": payload["tool_calls"][0]["log_id"],
        }
    ]
    assert payload["context_manifest"]["context_hash"]
    assert any(ref["type"] == "runtime_context" for ref in payload["context_manifest"]["included_refs"])
    logs = get_tool_logs_by_session(db_path, session_id)
    assert logs[0]["user_id"] == user_id
    assert logs[0]["output_json"]["bound_user_id"] == user_id


def test_agent_api_rejects_identity_fields_in_request_body():
    provider = ApiRecordingProvider([])
    client, _db_path, user_id, other_user_id, session_id = _client_with_provider(provider)

    response = client.post(
        "/api/agent/run",
        headers={
            "X-LingoForge-User-Id": str(user_id),
            "X-LingoForge-Session-Id": str(session_id),
        },
        json={"user_input": "读取画像", "user_id": other_user_id},
    )

    assert response.status_code == 422
    assert provider.calls == []


def test_agent_api_tool_reads_only_header_bound_user_even_if_model_requests_other_user():
    provider = ApiRecordingProvider([
        LLMResponse(tool_calls=(
            LLMToolCall(id="call-override", name="get_user_profile", arguments={"user_id": 999}),
        )),
        _final_response(),
    ])
    client, _db_path, user_id, _other_user_id, session_id = _client_with_provider(provider)

    response = client.post(
        "/api/agent/run",
        headers={
            "X-LingoForge-User-Id": str(user_id),
            "X-LingoForge-Session-Id": str(session_id),
        },
        json={"user_input": "读取画像"},
    )

    payload = response.json()
    assert response.status_code == 200
    assert payload["status"] == "COMPLETED_WITH_TOOL_ERRORS"
    assert payload["tool_calls"][0]["error_code"] == "IDENTITY_ARGUMENT_FORBIDDEN"
    assert "other-secret-profile" not in json.dumps(payload, ensure_ascii=False)


def test_agent_api_returns_stable_provider_error_without_internal_details():
    client, _db_path, user_id, _other_user_id, session_id = _client_with_provider(BrokenProvider())

    response = client.post(
        "/api/agent/run",
        headers={
            "X-LingoForge-User-Id": str(user_id),
            "X-LingoForge-Session-Id": str(session_id),
        },
        json={"user_input": "读取画像"},
    )

    assert response.status_code == 502
    payload = response.json()
    assert payload["detail"]["code"] == "LLM_PROVIDER_ERROR"
    assert "secret provider traceback details" not in json.dumps(payload, ensure_ascii=False)


def test_agent_api_missing_user_header_rejected():
    """缺失身份头返回 422。"""
    provider = ApiRecordingProvider([])
    client, _db_path, _user_id, _other_user_id, _session_id = _client_with_provider(provider)

    response = client.post(
        "/api/agent/run",
        json={"user_input": "读取画像"},
    )
    assert response.status_code == 422


def test_agent_api_invalid_user_header_rejected():
    """非法身份头（非整数）返回 422。"""
    provider = ApiRecordingProvider([])
    client, _db_path, user_id, _other_user_id, session_id = _client_with_provider(provider)

    response = client.post(
        "/api/agent/run",
        headers={
            "X-LingoForge-User-Id": "not_a_number",
            "X-LingoForge-Session-Id": str(session_id),
        },
        json={"user_input": "读取画像"},
    )
    assert response.status_code == 422
