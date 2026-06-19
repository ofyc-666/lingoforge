"""工具调用和 Agent 决策日志 Repository 测试。"""

from __future__ import annotations

import pytest

from app.database import init_database
from app.repositories.users import create_user
from app.repositories.training import create_training_session
from app.repositories.logs import (
    create_agent_decision_log,
    create_tool_call_log,
    get_agent_decisions_by_session,
    get_tool_logs_by_session,
    get_tool_logs_by_user,
)
from temp_paths import temp_db_path


@pytest.fixture
def db_path():
    path = temp_db_path("logs_repo")
    init_database(path)
    return path


@pytest.fixture
def user_id(db_path):
    return create_user(db_path, "日志测试用户")


@pytest.fixture
def session_id(db_path, user_id):
    return create_training_session(db_path, user_id=user_id, stage="FIRST_MAIN")


class TestToolCallLogRepository:
    """工具调用日志 Repository 测试。"""

    def test_create_success_log(self, db_path, user_id, session_id):
        lid = create_tool_call_log(
            db_path,
            user_id=user_id,
            session_id=session_id,
            call_name="get_candidate_words",
            call_type="LLM_TOOL",
            input_json={"ability": "VOCABULARY_CONTEXT"},
            output_json={"words": ["abandon"]},
            status="SUCCESS",
        )
        assert lid >= 1

    def test_create_failed_log(self, db_path, user_id, session_id):
        lid = create_tool_call_log(
            db_path,
            user_id=user_id,
            session_id=session_id,
            call_name="invalid_tool",
            call_type="LLM_TOOL",
            input_json={},
            output_json={},
            status="FAILED",
            error_code="TOOL_NOT_FOUND",
        )
        assert lid >= 1

    def test_log_without_user_and_session(self, db_path):
        lid = create_tool_call_log(
            db_path,
            call_name="health_check",
            call_type="WORKFLOW_SERVICE",
            input_json={},
            output_json={"status": "ok"},
            status="SUCCESS",
        )
        assert lid >= 1

    def test_query_by_user(self, db_path, user_id, session_id):
        create_tool_call_log(db_path, user_id=user_id, session_id=session_id,
                             call_name="tool_a", call_type="LLM_TOOL",
                             input_json={}, output_json={}, status="SUCCESS")
        create_tool_call_log(db_path, user_id=user_id, session_id=session_id,
                             call_name="tool_b", call_type="LLM_TOOL",
                             input_json={}, output_json={}, status="SUCCESS")

        logs = get_tool_logs_by_user(db_path, user_id)
        assert len(logs) == 2

    def test_query_by_session(self, db_path, user_id, session_id):
        create_tool_call_log(db_path, user_id=user_id, session_id=session_id,
                             call_name="tool_x", call_type="LLM_TOOL",
                             input_json={}, output_json={}, status="SUCCESS")
        logs = get_tool_logs_by_session(db_path, session_id)
        assert len(logs) == 1
        assert logs[0]["call_name"] == "tool_x"

    def test_filter_by_call_type(self, db_path, user_id, session_id):
        create_tool_call_log(db_path, user_id=user_id, session_id=session_id,
                             call_name="llm_tool", call_type="LLM_TOOL",
                             input_json={}, output_json={}, status="SUCCESS")
        create_tool_call_log(db_path, user_id=user_id, session_id=session_id,
                             call_name="service", call_type="WORKFLOW_SERVICE",
                             input_json={}, output_json={}, status="SUCCESS")

        from app.repositories.logs import get_tool_logs_by_type
        llm_logs = get_tool_logs_by_type(db_path, "LLM_TOOL")
        svc_logs = get_tool_logs_by_type(db_path, "WORKFLOW_SERVICE")
        assert len(llm_logs) == 1
        assert len(svc_logs) == 1

    def test_json_fields_roundtrip(self, db_path, user_id, session_id):
        inp = {"ability": "VOCABULARY_CONTEXT", "limit": 10}
        out = {"words": [{"text": "abandon", "id": 1}]}
        lid = create_tool_call_log(
            db_path, user_id=user_id, session_id=session_id,
            call_name="get_words", call_type="LLM_TOOL",
            input_json=inp, output_json=out, status="SUCCESS",
        )
        logs = get_tool_logs_by_session(db_path, session_id)
        assert logs[0]["input_json"] == inp
        assert logs[0]["output_json"] == out

    def test_empty_query(self, db_path):
        assert get_tool_logs_by_user(db_path, 999) == []
        assert get_tool_logs_by_session(db_path, 999) == []

    def test_ordered_by_creation(self, db_path, user_id, session_id):
        create_tool_call_log(db_path, user_id=user_id, session_id=session_id,
                             call_name="first", call_type="LLM_TOOL",
                             input_json={}, output_json={}, status="SUCCESS")
        create_tool_call_log(db_path, user_id=user_id, session_id=session_id,
                             call_name="second", call_type="LLM_TOOL",
                             input_json={}, output_json={}, status="SUCCESS")

        logs = get_tool_logs_by_session(db_path, session_id)
        assert logs[0]["call_name"] == "first"
        assert logs[1]["call_name"] == "second"


class TestAgentDecisionLogRepository:
    """Agent 决策日志 Repository 测试。"""

    def test_create_decision_log(self, db_path, user_id, session_id):
        did = create_agent_decision_log(
            db_path,
            user_id=user_id,
            session_id=session_id,
            decision_type="SKILL_SELECTION",
            input_summary={"profile_snapshot_id": 1},
            decision={"selected_skill": "vocab_context"},
            evidence_refs=[10, 11],
        )
        assert did >= 1

    def test_query_by_session(self, db_path, user_id, session_id):
        create_agent_decision_log(
            db_path, user_id=user_id, session_id=session_id,
            decision_type="PLAN", input_summary={}, decision={},
        )
        create_agent_decision_log(
            db_path, user_id=user_id, session_id=session_id,
            decision_type="ERROR_ANALYSIS", input_summary={}, decision={},
        )
        decisions = get_agent_decisions_by_session(db_path, session_id)
        assert len(decisions) == 2

    def test_empty_session(self, db_path):
        assert get_agent_decisions_by_session(db_path, 999) == []

    def test_json_fields_roundtrip(self, db_path, user_id, session_id):
        summary = {"profile": "summary", "weaknesses": ["词汇"]}
        decision = {"action": "retry", "reason": "置信度低"}
        refs = [1, 2, 3]
        create_agent_decision_log(
            db_path, user_id=user_id, session_id=session_id,
            decision_type="SECOND_PLAN",
            input_summary=summary, decision=decision, evidence_refs=refs,
        )
        decisions = get_agent_decisions_by_session(db_path, session_id)
        assert decisions[0]["input_summary_json"] == summary
        assert decisions[0]["decision_json"] == decision
        assert decisions[0]["evidence_refs"] == refs

    def test_defaults(self, db_path, user_id, session_id):
        create_agent_decision_log(
            db_path, user_id=user_id, session_id=session_id,
            decision_type="PLAN",
        )
        decisions = get_agent_decisions_by_session(db_path, session_id)
        assert decisions[0]["input_summary_json"] == {}
        assert decisions[0]["decision_json"] == {}
        assert decisions[0]["evidence_refs"] == []
