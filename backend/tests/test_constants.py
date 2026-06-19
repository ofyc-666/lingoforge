"""后端枚举常量与校验测试。"""

from __future__ import annotations

import pytest

from app.constants import (
    Ability,
    CallStatus,
    CallType,
    Confidence,
    DecisionType,
    EvidenceType,
    ProfileSuggestionDirection,
    ProfileSuggestionStatus,
    SessionStatus,
    SignalType,
    SnapshotSource,
    TaskType,
    ValidationStatus,
    VocabSourceType,
    WorkflowStage,
    is_valid_ability,
    is_valid_call_status,
    is_valid_call_type,
    is_valid_confidence,
    is_valid_decision_type,
    is_valid_evidence_type,
    is_valid_profile_suggestion_status,
    is_valid_session_status,
    is_valid_signal_type,
    is_valid_snapshot_source,
    is_valid_task_type,
    is_valid_validation_status,
    is_valid_vocab_source_type,
    is_valid_workflow_stage,
)


class TestAbility:
    """能力维度测试。"""

    def test_four_abilities_defined(self):
        abilities = {
            Ability.VOCABULARY_CONTEXT,
            Ability.SENTENCE_LOGIC,
            Ability.PARAPHRASE_LOCATION,
            Ability.DISTRACTOR_JUDGEMENT,
        }
        assert len(abilities) == 4

    def test_is_valid_ability_accepts_all_four(self):
        assert is_valid_ability("VOCABULARY_CONTEXT")
        assert is_valid_ability("SENTENCE_LOGIC")
        assert is_valid_ability("PARAPHRASE_LOCATION")
        assert is_valid_ability("DISTRACTOR_JUDGEMENT")

    def test_is_valid_ability_rejects_invalid(self):
        assert not is_valid_ability("READING")
        assert not is_valid_ability("")
        assert not is_valid_ability("vocabulary_context")  # 大小写敏感

    def test_is_valid_ability_no_exception_on_none(self):
        # 非法值返回 False，不抛异常
        assert not is_valid_ability(None)


class TestWorkflowStage:
    """Workflow Stage 测试。"""

    def test_expected_stages(self):
        stages = {
            WorkflowStage.DIAGNOSTIC,
            WorkflowStage.FIRST_MAIN,
            WorkflowStage.SIDEQUEST,
            WorkflowStage.SECOND_PLAN,
            WorkflowStage.SHORT_TRAINING,
            WorkflowStage.ISOLATED_TEST,
        }
        assert len(stages) == 6

    def test_is_valid_workflow_stage(self):
        assert is_valid_workflow_stage("DIAGNOSTIC")
        assert is_valid_workflow_stage("FIRST_MAIN")
        assert is_valid_workflow_stage("ISOLATED_TEST")

    def test_is_valid_workflow_stage_rejects_invalid(self):
        assert not is_valid_workflow_stage("UNKNOWN")
        assert not is_valid_workflow_stage("")

    def test_is_valid_workflow_stage_no_exception(self):
        assert not is_valid_workflow_stage(None)


class TestSessionStatus:
    """Session 状态测试。"""

    def test_expected_statuses(self):
        statuses = {
            SessionStatus.PENDING,
            SessionStatus.IN_PROGRESS,
            SessionStatus.COMPLETED,
        }
        assert len(statuses) == 3

    def test_is_valid_session_status(self):
        assert is_valid_session_status("PENDING")
        assert is_valid_session_status("IN_PROGRESS")
        assert is_valid_session_status("COMPLETED")

    def test_is_valid_session_status_rejects_invalid(self):
        assert not is_valid_session_status("ACTIVE")
        assert not is_valid_session_status("")

    def test_is_valid_session_status_no_exception(self):
        assert not is_valid_session_status(None)


class TestCallType:
    """调用类型测试。"""

    def test_expected_call_types(self):
        types = {CallType.LLM_TOOL, CallType.WORKFLOW_SERVICE}
        assert len(types) == 2

    def test_is_valid_call_type(self):
        assert is_valid_call_type("LLM_TOOL")
        assert is_valid_call_type("WORKFLOW_SERVICE")

    def test_is_valid_call_type_rejects_invalid(self):
        assert not is_valid_call_type("TOOL")
        assert not is_valid_call_type("")

    def test_is_valid_call_type_no_exception(self):
        assert not is_valid_call_type(None)


class TestCallStatus:
    """调用状态测试。"""

    def test_expected_statuses(self):
        statuses = {CallStatus.SUCCESS, CallStatus.FAILED}
        assert len(statuses) == 2

    def test_is_valid_call_status(self):
        assert is_valid_call_status("SUCCESS")
        assert is_valid_call_status("FAILED")

    def test_is_valid_call_status_rejects_invalid(self):
        assert not is_valid_call_status("ERROR")
        assert not is_valid_call_status("")

    def test_is_valid_call_status_no_exception(self):
        assert not is_valid_call_status(None)


class TestProfileSuggestionStatus:
    """画像建议状态测试。"""

    def test_expected_statuses(self):
        statuses = {
            ProfileSuggestionStatus.ACCEPTED,
            ProfileSuggestionStatus.REJECTED,
            ProfileSuggestionStatus.NEEDS_REVIEW,
        }
        assert len(statuses) == 3

    def test_needs_review_is_included(self):
        # NEEDS_REVIEW 仅作为合法记忆状态被包含
        assert ProfileSuggestionStatus.NEEDS_REVIEW == "NEEDS_REVIEW"

    def test_is_valid_profile_suggestion_status(self):
        assert is_valid_profile_suggestion_status("ACCEPTED")
        assert is_valid_profile_suggestion_status("REJECTED")
        assert is_valid_profile_suggestion_status("NEEDS_REVIEW")

    def test_is_valid_profile_suggestion_status_rejects_invalid(self):
        assert not is_valid_profile_suggestion_status("APPROVED")
        assert not is_valid_profile_suggestion_status("")

    def test_is_valid_profile_suggestion_status_no_exception(self):
        assert not is_valid_profile_suggestion_status(None)


class TestProfileSuggestionDirection:
    """画像建议方向测试。"""

    def test_expected_directions(self):
        directions = {
            ProfileSuggestionDirection.IMPROVE,
            ProfileSuggestionDirection.DECLINE,
            ProfileSuggestionDirection.UNCERTAIN,
            ProfileSuggestionDirection.NO_CHANGE,
        }
        assert len(directions) == 4

    # 此字段当前只有常量，无独立校验函数要求


class TestTaskType:
    """任务类型测试。"""

    def test_expected_types(self):
        types = {
            TaskType.LOW_PRESSURE_LEARNING,
            TaskType.TRANSFER_PRACTICE,
            TaskType.REMEDIATION,
            TaskType.SHORT_TRAINING,
        }
        assert len(types) == 4

    def test_is_valid_task_type(self):
        assert is_valid_task_type("LOW_PRESSURE_LEARNING")
        assert is_valid_task_type("TRANSFER_PRACTICE")
        assert is_valid_task_type("REMEDIATION")
        assert is_valid_task_type("SHORT_TRAINING")

    def test_is_valid_task_type_rejects_invalid(self):
        assert not is_valid_task_type("ESSAY")
        assert not is_valid_task_type("")

    def test_is_valid_task_type_no_exception(self):
        assert not is_valid_task_type(None)


class TestEvidenceType:
    """证据类型测试。"""

    def test_expected_types(self):
        types = {
            EvidenceType.DIAGNOSTIC_ANSWER,
            EvidenceType.TRAINING_ANSWER,
            EvidenceType.PROMPT_USAGE,
            EvidenceType.CLICK_EVENT,
            EvidenceType.GRADING_RESULT,
        }
        assert len(types) == 5

    def test_is_valid_evidence_type(self):
        assert is_valid_evidence_type("DIAGNOSTIC_ANSWER")
        assert is_valid_evidence_type("TRAINING_ANSWER")
        assert is_valid_evidence_type("GRADING_RESULT")

    def test_is_valid_evidence_type_rejects_invalid(self):
        assert not is_valid_evidence_type("ANSWER")
        assert not is_valid_evidence_type("")

    def test_is_valid_evidence_type_no_exception(self):
        assert not is_valid_evidence_type(None)


class TestValidationStatus:
    """校验状态测试。"""

    def test_expected_statuses(self):
        statuses = {
            ValidationStatus.PASSED,
            ValidationStatus.FAILED,
            ValidationStatus.FALLBACK_USED,
        }
        assert len(statuses) == 3

    def test_is_valid_validation_status(self):
        assert is_valid_validation_status("PASSED")
        assert is_valid_validation_status("FAILED")
        assert is_valid_validation_status("FALLBACK_USED")

    def test_is_valid_validation_status_rejects_invalid(self):
        assert not is_valid_validation_status("OK")
        assert not is_valid_validation_status("")

    def test_is_valid_validation_status_no_exception(self):
        assert not is_valid_validation_status(None)


class TestSignalType:
    """副线信号类型测试。"""

    def test_expected_types(self):
        types = {
            SignalType.EXPOSURE,
            SignalType.CLICKED_HINT,
            SignalType.MISRECOGNIZED,
            SignalType.TASK_SUCCESS,
            SignalType.TASK_FAILED,
        }
        assert len(types) == 5

    def test_is_valid_signal_type(self):
        assert is_valid_signal_type("EXPOSURE")
        assert is_valid_signal_type("CLICKED_HINT")
        assert is_valid_signal_type("TASK_SUCCESS")

    def test_is_valid_signal_type_rejects_invalid(self):
        assert not is_valid_signal_type("SIGNAL")
        assert not is_valid_signal_type("")

    def test_is_valid_signal_type_no_exception(self):
        assert not is_valid_signal_type(None)


class TestVocabSourceType:
    """词汇来源类型测试。"""

    def test_expected_types(self):
        types = {
            VocabSourceType.CET6_VOCAB,
            VocabSourceType.SIDEQUEST_ENV,
            VocabSourceType.SEED_DEMO,
        }
        assert len(types) == 3

    def test_is_valid_vocab_source_type(self):
        assert is_valid_vocab_source_type("CET6_VOCAB")
        assert is_valid_vocab_source_type("SIDEQUEST_ENV")
        assert is_valid_vocab_source_type("SEED_DEMO")

    def test_is_valid_vocab_source_type_rejects_invalid(self):
        assert not is_valid_vocab_source_type("OTHER")
        assert not is_valid_vocab_source_type("")

    def test_is_valid_vocab_source_type_no_exception(self):
        assert not is_valid_vocab_source_type(None)


class TestSnapshotSource:
    """画像快照来源测试。"""

    def test_expected_sources(self):
        sources = {
            SnapshotSource.DIAGNOSTIC,
            SnapshotSource.MAIN_TRAINING,
            SnapshotSource.ISOLATED_TEST,
        }
        assert len(sources) == 3

    def test_is_valid_snapshot_source(self):
        assert is_valid_snapshot_source("DIAGNOSTIC")
        assert is_valid_snapshot_source("MAIN_TRAINING")
        assert is_valid_snapshot_source("ISOLATED_TEST")

    def test_is_valid_snapshot_source_rejects_invalid(self):
        assert not is_valid_snapshot_source("SIDEQUEST")
        assert not is_valid_snapshot_source("")

    def test_is_valid_snapshot_source_no_exception(self):
        assert not is_valid_snapshot_source(None)


class TestDecisionType:
    """决策类型测试。"""

    def test_expected_types(self):
        types = {
            DecisionType.PLAN,
            DecisionType.SKILL_SELECTION,
            DecisionType.ERROR_ANALYSIS,
            DecisionType.REMEDIATION,
            DecisionType.SECOND_PLAN,
        }
        assert len(types) == 5

    def test_is_valid_decision_type(self):
        assert is_valid_decision_type("PLAN")
        assert is_valid_decision_type("SKILL_SELECTION")
        assert is_valid_decision_type("SECOND_PLAN")

    def test_is_valid_decision_type_rejects_invalid(self):
        assert not is_valid_decision_type("DECISION")
        assert not is_valid_decision_type("")

    def test_is_valid_decision_type_no_exception(self):
        assert not is_valid_decision_type(None)


class TestConfidence:
    """置信度测试。"""

    def test_expected_levels(self):
        levels = {
            Confidence.LOW,
            Confidence.MEDIUM,
            Confidence.HIGH,
        }
        assert len(levels) == 3

    def test_is_valid_confidence(self):
        assert is_valid_confidence("LOW")
        assert is_valid_confidence("MEDIUM")
        assert is_valid_confidence("HIGH")

    def test_is_valid_confidence_rejects_invalid(self):
        assert not is_valid_confidence("VERY_HIGH")
        assert not is_valid_confidence("")

    def test_is_valid_confidence_no_exception(self):
        assert not is_valid_confidence(None)
