"""Agent Runtime 最小 Function Calling 闭环测试。"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import pytest

from app.agent.models import RuntimeContext
from app.agent.runtime import AgentRuntime
from app.agent.tools import ToolDefinition, ToolRegistry, get_user_profile_tool_spec
from app.database import init_database
from app.llm.types import LLMMessage, LLMResponse, LLMToolCall, LLMToolSpec
from app.repositories.logs import get_agent_decisions_by_session, get_tool_logs_by_session
from app.repositories.training import create_training_session
from app.repositories.users import create_profile_snapshot, create_user, save_user_goal
from temp_paths import temp_db_path


class RecordingProvider:
    """记录 Runtime 调用顺序的测试 Provider。"""

    name = "mock"

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

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
        if not self._responses:
            raise AssertionError("测试 Provider 响应队列已耗尽")
        return self._responses.pop(0)


@pytest.fixture
def db_path():
    path = temp_db_path("agent_runtime")
    init_database(path)
    return path


@pytest.fixture
def seeded_users(db_path):
    bound_user_id = create_user(db_path, "绑定用户")
    other_user_id = create_user(db_path, "其他用户")

    save_user_goal(
        db_path,
        user_id=bound_user_id,
        target_score=550,
        daily_minutes=45,
        self_reported_weaknesses=["词汇"],
        interest_topics=["科技"],
    )
    create_profile_snapshot(
        db_path,
        user_id=bound_user_id,
        source="DIAGNOSTIC",
        profile={"vocabulary_context": {"level": "weak"}},
        evidence_refs=[101, 102],
    )

    save_user_goal(
        db_path,
        user_id=other_user_id,
        target_score=700,
        daily_minutes=90,
        self_reported_weaknesses=["不应泄漏"],
        interest_topics=["other-secret-topic"],
    )
    create_profile_snapshot(
        db_path,
        user_id=other_user_id,
        source="DIAGNOSTIC",
        profile={"vocabulary_context": {"level": "other-secret-profile"}},
        evidence_refs=[201],
    )

    session_id = create_training_session(
        db_path,
        user_id=bound_user_id,
        stage="FIRST_MAIN",
        status="IN_PROGRESS",
    )
    return {
        "bound_user_id": bound_user_id,
        "other_user_id": other_user_id,
        "session_id": session_id,
    }


def runtime_context(seeded_users) -> RuntimeContext:
    return RuntimeContext(
        user_id=seeded_users["bound_user_id"],
        session_id=seeded_users["session_id"],
        workflow_stage="FIRST_MAIN",
        objective="读取当前用户画像并继续主线训练",
        allowed_tools=("get_user_profile",),
    )


def final_response(content: str = "已完成画像读取") -> LLMResponse:
    return LLMResponse(
        content=json.dumps({
            "decision_type": "PROFILE_READ",
            "next_step": "DONE",
            "final_answer": content,
            "decision_basis": [
                {"summary": "使用工具读取 Runtime 绑定用户画像", "refs": ["tool_result"]}
            ],
        }, ensure_ascii=False)
    )


def run_with_tool_call(db_path, seeded_users, tool_call: LLMToolCall):
    provider = RecordingProvider([
        LLMResponse(tool_calls=(tool_call,)),
        final_response(),
    ])
    result = AgentRuntime(database_path=db_path, provider=provider).run(runtime_context(seeded_users))
    return result, provider


def test_completes_minimal_function_calling_agent_run(db_path, seeded_users):
    result, provider = run_with_tool_call(
        db_path,
        seeded_users,
        LLMToolCall(id="call-1", name="get_user_profile", arguments={}),
    )

    assert result.status == "COMPLETED"
    assert len(provider.calls) == 2
    assert provider.calls[0]["tools"][0].name == "get_user_profile"
    assert "user_id" not in provider.calls[0]["tools"][0].parameters["properties"]
    assert any(message.role == "tool" for message in provider.calls[1]["messages"])

    tool_result = result.tool_results[0]
    assert tool_result["status"] == "SUCCESS"
    assert tool_result["output"]["bound_user_id"] == seeded_users["bound_user_id"]
    assert tool_result["output"]["goal"]["data"]["target_score"] == 550
    assert tool_result["output"]["profile_snapshot"]["data"]["profile_json"] == {
        "vocabulary_context": {"level": "weak"}
    }
    assert result.decision["decision_type"] == "PROFILE_READ"
    assert result.agent_decision_log_id is not None


def test_model_cannot_override_runtime_user_id(db_path, seeded_users):
    result, _provider = run_with_tool_call(
        db_path,
        seeded_users,
        LLMToolCall(
            id="call-override",
            name="get_user_profile",
            arguments={"user_id": seeded_users["other_user_id"]},
        ),
    )

    assert result.status == "COMPLETED_WITH_TOOL_ERRORS"
    tool_result = result.tool_results[0]
    assert tool_result["status"] == "FAILED"
    assert tool_result["error_code"] == "IDENTITY_ARGUMENT_FORBIDDEN"
    assert "other-secret-profile" not in json.dumps(tool_result, ensure_ascii=False)


def test_tool_reads_only_runtime_bound_user_data(db_path, seeded_users):
    result, _provider = run_with_tool_call(
        db_path,
        seeded_users,
        LLMToolCall(id="call-bound", name="get_user_profile", arguments={}),
    )

    serialized = json.dumps(result.tool_results[0], ensure_ascii=False)
    assert "other-secret-topic" not in serialized
    assert "other-secret-profile" not in serialized
    assert '"target_score": 550' in serialized
    assert '"target_score": 700' not in serialized


def test_get_user_profile_returns_stable_empty_result(db_path):
    user_id = create_user(db_path, "空画像用户")
    session_id = create_training_session(
        db_path,
        user_id=user_id,
        stage="FIRST_MAIN",
        status="IN_PROGRESS",
    )
    context = RuntimeContext(
        user_id=user_id,
        session_id=session_id,
        workflow_stage="FIRST_MAIN",
        objective="读取空画像",
        allowed_tools=("get_user_profile",),
    )
    provider = RecordingProvider([
        LLMResponse(tool_calls=(LLMToolCall(id="call-empty", name="get_user_profile", arguments={}),)),
        final_response(),
    ])

    result = AgentRuntime(database_path=db_path, provider=provider).run(context)

    output = result.tool_results[0]["output"]
    assert output["user"]["found"] is True
    assert output["goal"] == {"found": False, "data": None}
    assert output["profile_snapshot"] == {"found": False, "data": None}


def test_unknown_tool_is_rejected_and_logged(db_path, seeded_users):
    result, _provider = run_with_tool_call(
        db_path,
        seeded_users,
        LLMToolCall(id="call-unknown", name="delete_everything", arguments={}),
    )

    assert result.status == "COMPLETED_WITH_TOOL_ERRORS"
    assert result.tool_results[0]["error_code"] == "TOOL_NOT_FOUND"
    logs = get_tool_logs_by_session(db_path, seeded_users["session_id"])
    assert logs[0]["call_name"] == "delete_everything"
    assert logs[0]["status"] == "FAILED"


def test_invalid_tool_arguments_are_rejected(db_path, seeded_users):
    result, _provider = run_with_tool_call(
        db_path,
        seeded_users,
        LLMToolCall(
            id="call-invalid",
            name="get_user_profile",
            arguments={"include_goal": "yes"},
        ),
    )

    assert result.status == "COMPLETED_WITH_TOOL_ERRORS"
    assert result.tool_results[0]["error_code"] == "INVALID_TOOL_ARGUMENTS"


def test_tool_and_decision_logs_are_written(db_path, seeded_users):
    result, _provider = run_with_tool_call(
        db_path,
        seeded_users,
        LLMToolCall(id="call-log", name="get_user_profile", arguments={}),
    )

    tool_logs = get_tool_logs_by_session(db_path, seeded_users["session_id"])
    decision_logs = get_agent_decisions_by_session(db_path, seeded_users["session_id"])

    assert len(tool_logs) == 1
    assert tool_logs[0]["call_name"] == "get_user_profile"
    assert tool_logs[0]["status"] == "SUCCESS"
    assert tool_logs[0]["output_json"]["bound_user_id"] == seeded_users["bound_user_id"]
    assert len(decision_logs) == 1
    assert decision_logs[0]["id"] == result.agent_decision_log_id
    assert decision_logs[0]["decision_json"]["decision"]["decision_type"] == "PROFILE_READ"


def test_context_manifest_records_loaded_context_and_tool_refs(db_path, seeded_users):
    result, _provider = run_with_tool_call(
        db_path,
        seeded_users,
        LLMToolCall(id="call-manifest", name="get_user_profile", arguments={}),
    )

    manifest = result.context_manifest
    included = {(ref["type"], ref["id"]) for ref in manifest["included_refs"]}
    assert ("runtime_context", result.run_id) in included
    assert ("allowed_tool", "get_user_profile") in included
    assert ("user_goal", result.tool_results[0]["output"]["goal"]["data"]["id"]) in included
    assert ("profile_snapshot", result.tool_results[0]["output"]["profile_snapshot"]["data"]["id"]) in included
    assert manifest["tool_result_refs"] == [result.tool_results[0]["log_id"]]
    assert manifest["context_hash"]


def test_tool_execution_exception_returns_controlled_error(db_path, seeded_users):
    def broken_handler(_context, _arguments):
        raise RuntimeError("secret internal stack details")

    registry = ToolRegistry({
        "get_user_profile": ToolDefinition(
            name="get_user_profile",
            description="故意失败的测试工具",
            parameters=get_user_profile_tool_spec().parameters,
            handler=broken_handler,
        )
    })
    provider = RecordingProvider([
        LLMResponse(tool_calls=(
            LLMToolCall(id="call-broken", name="get_user_profile", arguments={}),
        )),
        final_response("工具失败后仍返回受控结果"),
    ])

    result = AgentRuntime(
        database_path=db_path,
        provider=provider,
        tool_registry=registry,
    ).run(runtime_context(seeded_users))

    tool_result = result.tool_results[0]
    assert tool_result["status"] == "FAILED"
    assert tool_result["error_code"] == "TOOL_EXECUTION_FAILED"
    serialized = json.dumps(tool_result, ensure_ascii=False)
    assert "secret internal stack details" not in serialized
    assert "Traceback" not in serialized


def test_mock_two_stage_response_order_is_preserved(db_path, seeded_users):
    provider = RecordingProvider([
        LLMResponse(tool_calls=(
            LLMToolCall(id="call-order", name="get_user_profile", arguments={}),
        )),
        final_response("第二次响应"),
    ])

    result = AgentRuntime(database_path=db_path, provider=provider).run(runtime_context(seeded_users))

    assert len(provider.calls) == 2
    assert provider.calls[0]["messages"][-1].role == "user"
    assert provider.calls[1]["messages"][-1].role == "tool"
    assert "第二次响应" in result.final_response
    assert result.decision["final_answer"] == "第二次响应"
