"""Agent 核心 Workflow 与 Context Expansion 测试。"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from fastapi.testclient import TestClient

from app.agent.models import RuntimeContext
from app.agent.runtime import AgentRuntime
from app.api.agent import get_agent_provider, get_settings
from app.config import Settings
from app.database import init_database
from app.llm.types import LLMMessage, LLMResponse, LLMToolCall, LLMToolSpec
from app.main import create_app
from app.repositories.logs import get_agent_decisions_by_session, get_tool_logs_by_session
from app.repositories.training import create_learning_evidence, create_training_session
from app.repositories.users import create_user, save_user_goal
from temp_paths import temp_db_path


class RecordingProvider:
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


def _final_decision(text: str = "已生成训练计划。", workflow_stage: str = "FIRST_MAIN") -> LLMResponse:
    return LLMResponse(content=json.dumps({
        "decision_type": "TRAINING_PLAN",
        "workflow_stage": workflow_stage,
        "objective": "生成 CET-6 词汇语境训练",
        "target_abilities": ["VOCABULARY_CONTEXT"],
        "selected_skills": ["vocabulary_context"],
        "training_parameters": {"task_type": "LOW_PRESSURE_LEARNING"},
        "next_step": "GENERATE_TRAINING_TASK",
        "final_answer": text,
        "decision_basis": [{"summary": "结合用户画像和学习历史生成主线训练。"}],
    }, ensure_ascii=False))


def _seed_user_with_session(db_path):
    user_id = create_user(db_path, "核心闭环用户")
    other_user_id = create_user(db_path, "其他用户")
    save_user_goal(
        db_path,
        user_id=user_id,
        target_score=550,
        daily_minutes=30,
        self_reported_weaknesses=["VOCABULARY_CONTEXT"],
        interest_topics=["technology"],
    )
    session_id = create_training_session(db_path, user_id=user_id, stage="FIRST_MAIN", status="IN_PROGRESS")
    other_session_id = create_training_session(
        db_path,
        user_id=other_user_id,
        stage="FIRST_MAIN",
        status="IN_PROGRESS",
    )
    evidence_id = create_learning_evidence(
        db_path,
        user_id=user_id,
        session_id=session_id,
        evidence_type="TRAINING_ANSWER",
        payload={
            "occurred_at": "2026-01-01T00:00:00+00:00",
            "question_results": [
                {
                    "question_id": "q1",
                    "is_correct": False,
                    "target_ability": "VOCABULARY_CONTEXT",
                    "error_type": "VOCABULARY_CONTEXT_ERROR",
                    "vocabulary_text": "climate",
                }
            ],
        },
    )
    create_learning_evidence(
        db_path,
        user_id=other_user_id,
        session_id=other_session_id,
        evidence_type="TRAINING_ANSWER",
        payload={
            "occurred_at": "2026-01-02T00:00:00+00:00",
            "question_results": [
                {
                    "question_id": "other-secret-question",
                    "is_correct": False,
                    "target_ability": "VOCABULARY_CONTEXT",
                    "error_type": "OTHER_SECRET_ERROR",
                    "vocabulary_text": "other-secret-vocab",
                }
            ],
        },
    )
    return user_id, other_user_id, session_id, evidence_id


def test_analyze_learning_history_tool_uses_runtime_bound_user():
    db_path = temp_db_path("agent_history_tool")
    init_database(db_path)
    user_id, other_user_id, session_id, _evidence_id = _seed_user_with_session(db_path)
    provider = RecordingProvider([
        LLMResponse(tool_calls=(LLMToolCall(
            id="history-1",
            name="analyze_learning_history",
            arguments={
                "analysis_type": "PROBLEM_TIMELINE",
                "target": {"ability": "VOCABULARY_CONTEXT"},
                "user_id": other_user_id,
            },
        ),)),
        _final_decision(),
    ])

    result = AgentRuntime(database_path=db_path, provider=provider).run(RuntimeContext(
        user_id=user_id,
        session_id=session_id,
        workflow_stage="FIRST_MAIN",
        objective="分析学习历史",
        allowed_tools=("analyze_learning_history",),
        permission_scope=("read_learning_history",),
    ))

    assert result.status == "COMPLETED_WITH_TOOL_ERRORS"
    assert result.tool_results[0]["error_code"] == "IDENTITY_ARGUMENT_FORBIDDEN"
    serialized = json.dumps(result.tool_results, ensure_ascii=False)
    assert "other-secret-vocab" not in serialized


def test_isolated_test_stage_blocks_history_tool_and_context_expansion():
    db_path = temp_db_path("agent_isolated_context")
    init_database(db_path)
    user_id, _other_user_id, session_id, _evidence_id = _seed_user_with_session(db_path)
    provider = RecordingProvider([
        LLMResponse(tool_calls=(LLMToolCall(
            id="history-isolated",
            name="analyze_learning_history",
            arguments={"analysis_type": "REVIEW_PRIORITY", "target": {"ability": "VOCABULARY_CONTEXT"}},
        ),)),
        _final_decision(workflow_stage="ISOLATED_TEST"),
    ])

    result = AgentRuntime(database_path=db_path, provider=provider).run(RuntimeContext(
        user_id=user_id,
        session_id=session_id,
        workflow_stage="ISOLATED_TEST",
        objective="隔离测试进行中",
        allowed_tools=("analyze_learning_history",),
        permission_scope=("read_learning_history",),
    ))

    assert result.status == "COMPLETED_WITH_TOOL_ERRORS"
    assert result.tool_results[0]["error_code"] == "TOOL_FORBIDDEN_IN_STAGE"
    excluded_types = {ref["type"] for ref in result.context_manifest["excluded_refs"]}
    assert "isolated_test_content" in excluded_types
    assert "context_expansion" in excluded_types


def test_context_expansion_loads_skill_history_and_reuses_same_analysis_log():
    db_path = temp_db_path("agent_context_expansion")
    init_database(db_path)
    user_id, _other_user_id, session_id, evidence_id = _seed_user_with_session(db_path)
    analysis_args = {
        "analysis_type": "PROBLEM_TIMELINE",
        "target": {"ability": "VOCABULARY_CONTEXT"},
        "intended_use": "选择训练重点",
    }
    provider = RecordingProvider([
        LLMResponse(content=json.dumps({
            "decision_type": "CONTEXT_EXPANSION_REQUEST",
            "requested_skill_ids": ["vocabulary_context"],
            "requested_history_analyses": [analysis_args],
            "reason": "需要确认是否复发",
            "intended_use": "生成训练任务",
            "priority": "HIGH",
        }, ensure_ascii=False)),
        LLMResponse(tool_calls=(LLMToolCall(
            id="history-after-expansion",
            name="analyze_learning_history",
            arguments=analysis_args,
        ),)),
        _final_decision("已根据扩展上下文生成计划。"),
    ])

    result = AgentRuntime(database_path=db_path, provider=provider).run(RuntimeContext(
        user_id=user_id,
        session_id=session_id,
        workflow_stage="FIRST_MAIN",
        objective="生成训练计划",
        allowed_tools=("analyze_learning_history",),
        permission_scope=("read_learning_history",),
    ))

    assert result.status == "COMPLETED"
    assert len(provider.calls) == 3
    assert result.tool_results[0]["cached"] is True
    tool_logs = get_tool_logs_by_session(db_path, session_id)
    assert len(tool_logs) == 1
    assert tool_logs[0]["call_type"] == "CONTEXT_EXPANSION_TOOL"
    assert result.tool_results[0]["log_id"] == tool_logs[0]["id"]
    included = {(ref["type"], ref["id"]) for ref in result.context_manifest["included_refs"]}
    assert ("skill_detail", "vocabulary_context") in included
    assert ("history_analysis", tool_logs[0]["id"]) in included
    assert ("learning_evidence", evidence_id) in included
    assert result.context_manifest["tool_result_refs"] == [tool_logs[0]["id"]]


def test_text_training_workflow_api_creates_task_and_submission_closes_loop():
    db_path = temp_db_path("agent_workflow_api")
    init_database(db_path)
    user_id, _other_user_id, session_id, _evidence_id = _seed_user_with_session(db_path)
    provider = RecordingProvider([_final_decision()])
    settings = Settings(database_path=str(db_path))
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_agent_provider] = lambda: provider
    client = TestClient(app)

    workflow_response = client.post(
        "/api/agent/workflow/text-training",
        headers={
            "X-LingoForge-User-Id": str(user_id),
            "X-LingoForge-Session-Id": str(session_id),
        },
        json={
            "raw_text": "Climate change is a pressing challenge for every ecosystem.",
            "target_abilities": ["VOCABULARY_CONTEXT"],
            "max_keywords": 3,
            "generate_exercise": True,
        },
    )

    assert workflow_response.status_code == 200
    workflow_payload = workflow_response.json()
    assert workflow_payload["status"] == "READY_FOR_SUBMISSION"
    assert workflow_payload["task_id"] > 0
    assert workflow_payload["validation"]["status"] == "PASSED"
    assert workflow_payload["memory_id"] > 0

    question = workflow_payload["task"]["content_json"]["questions"][0]
    submit_response = client.post(
        f"/api/training/tasks/{workflow_payload['task_id']}/submit",
        headers={"X-LingoForge-User-Id": str(user_id)},
        json={
            "answers": [{"question_id": question["question_id"], "answer": question["answer"]}],
            "time_spent_seconds": 30,
        },
    )

    assert submit_response.status_code == 200
    submit_payload = submit_response.json()
    assert submit_payload["score"]["accuracy"] == 1.0
    assert submit_payload["evidence_id"] > 0
    assert submit_payload["profile_suggestion_id"] > 0
    decision_logs = get_agent_decisions_by_session(db_path, session_id)
    assert any(log["decision_type"] == "MEMORY_ITEM" for log in decision_logs)
