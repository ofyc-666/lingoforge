"""后端枚举常量与基础校验。

集中定义当前 Schema 和规格已经明确的枚举常量，
供 repository 和普通校验复用。
"""

from __future__ import annotations

from typing import Any


class Ability:
    """4 类 CET-6 阅读能力维度。"""

    VOCABULARY_CONTEXT = "VOCABULARY_CONTEXT"
    SENTENCE_LOGIC = "SENTENCE_LOGIC"
    PARAPHRASE_LOCATION = "PARAPHRASE_LOCATION"
    DISTRACTOR_JUDGEMENT = "DISTRACTOR_JUDGEMENT"


class WorkflowStage:
    """Workflow 阶段。"""

    DIAGNOSTIC = "DIAGNOSTIC"
    FIRST_MAIN = "FIRST_MAIN"
    SIDEQUEST = "SIDEQUEST"
    SECOND_PLAN = "SECOND_PLAN"
    SHORT_TRAINING = "SHORT_TRAINING"
    ISOLATED_TEST = "ISOLATED_TEST"


class SessionStatus:
    """训练会话状态。"""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class CallType:
    """调用类型。"""

    LLM_TOOL = "LLM_TOOL"
    WORKFLOW_SERVICE = "WORKFLOW_SERVICE"


class CallStatus:
    """调用状态。"""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ProfileSuggestionStatus:
    """画像建议校验状态。"""

    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class MemoryStatus:
    """记忆状态。"""

    ACTIVE = "ACTIVE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    DISPUTED = "DISPUTED"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class ProfileSuggestionDirection:
    """画像建议变化方向。"""

    IMPROVE = "IMPROVE"
    DECLINE = "DECLINE"
    UNCERTAIN = "UNCERTAIN"
    NO_CHANGE = "NO_CHANGE"


class TaskType:
    """生成任务类型。"""

    LOW_PRESSURE_LEARNING = "LOW_PRESSURE_LEARNING"
    TRANSFER_PRACTICE = "TRANSFER_PRACTICE"
    REMEDIATION = "REMEDIATION"
    SHORT_TRAINING = "SHORT_TRAINING"
    VOCABULARY_LEARNING = "VOCABULARY_LEARNING"
    VOCABULARY_REVIEW = "VOCABULARY_REVIEW"


class EvidenceType:
    """学习证据类型。"""

    DIAGNOSTIC_ANSWER = "DIAGNOSTIC_ANSWER"
    TRAINING_ANSWER = "TRAINING_ANSWER"
    PROMPT_USAGE = "PROMPT_USAGE"
    CLICK_EVENT = "CLICK_EVENT"
    GRADING_RESULT = "GRADING_RESULT"


class ValidationStatus:
    """生成任务校验状态。"""

    PASSED = "PASSED"
    FAILED = "FAILED"
    FALLBACK_USED = "FALLBACK_USED"


class SignalType:
    """副线信号类型。"""

    EXPOSURE = "EXPOSURE"
    CLICKED_HINT = "CLICKED_HINT"
    MISRECOGNIZED = "MISRECOGNIZED"
    TASK_SUCCESS = "TASK_SUCCESS"
    TASK_FAILED = "TASK_FAILED"


class VocabSourceType:
    """词汇来源类型。"""

    CET6_VOCAB = "CET6_VOCAB"
    SIDEQUEST_ENV = "SIDEQUEST_ENV"
    SEED_DEMO = "SEED_DEMO"


class SnapshotSource:
    """画像快照来源。"""

    DIAGNOSTIC = "DIAGNOSTIC"
    MAIN_TRAINING = "MAIN_TRAINING"
    ISOLATED_TEST = "ISOLATED_TEST"


class DecisionType:
    """Agent 决策类型。"""

    PLAN = "PLAN"
    SKILL_SELECTION = "SKILL_SELECTION"
    ERROR_ANALYSIS = "ERROR_ANALYSIS"
    REMEDIATION = "REMEDIATION"
    SECOND_PLAN = "SECOND_PLAN"
    DAILY_LEARNING_PLAN = "DAILY_LEARNING_PLAN"


class Confidence:
    """置信度等级。"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# --------------- 校验函数 ---------------

_ABILITY_VALUES: frozenset[str] = frozenset({
    Ability.VOCABULARY_CONTEXT,
    Ability.SENTENCE_LOGIC,
    Ability.PARAPHRASE_LOCATION,
    Ability.DISTRACTOR_JUDGEMENT,
})

_WORKFLOW_STAGE_VALUES: frozenset[str] = frozenset({
    WorkflowStage.DIAGNOSTIC,
    WorkflowStage.FIRST_MAIN,
    WorkflowStage.SIDEQUEST,
    WorkflowStage.SECOND_PLAN,
    WorkflowStage.SHORT_TRAINING,
    WorkflowStage.ISOLATED_TEST,
})

_SESSION_STATUS_VALUES: frozenset[str] = frozenset({
    SessionStatus.PENDING,
    SessionStatus.IN_PROGRESS,
    SessionStatus.COMPLETED,
})

_CALL_TYPE_VALUES: frozenset[str] = frozenset({
    CallType.LLM_TOOL,
    CallType.WORKFLOW_SERVICE,
})

_CALL_STATUS_VALUES: frozenset[str] = frozenset({
    CallStatus.SUCCESS,
    CallStatus.FAILED,
})

_PROFILE_SUGGESTION_STATUS_VALUES: frozenset[str] = frozenset({
    ProfileSuggestionStatus.ACCEPTED,
    ProfileSuggestionStatus.REJECTED,
})

_MEMORY_STATUS_VALUES: frozenset[str] = frozenset({
    MemoryStatus.ACTIVE,
    MemoryStatus.NEEDS_REVIEW,
    MemoryStatus.DISPUTED,
    MemoryStatus.SUPERSEDED,
    MemoryStatus.REJECTED,
})

_TASK_TYPE_VALUES: frozenset[str] = frozenset({
    TaskType.LOW_PRESSURE_LEARNING,
    TaskType.TRANSFER_PRACTICE,
    TaskType.REMEDIATION,
    TaskType.SHORT_TRAINING,
    TaskType.VOCABULARY_LEARNING,
    TaskType.VOCABULARY_REVIEW,
})

_EVIDENCE_TYPE_VALUES: frozenset[str] = frozenset({
    EvidenceType.DIAGNOSTIC_ANSWER,
    EvidenceType.TRAINING_ANSWER,
    EvidenceType.PROMPT_USAGE,
    EvidenceType.CLICK_EVENT,
    EvidenceType.GRADING_RESULT,
})

_VALIDATION_STATUS_VALUES: frozenset[str] = frozenset({
    ValidationStatus.PASSED,
    ValidationStatus.FAILED,
    ValidationStatus.FALLBACK_USED,
})

_SIGNAL_TYPE_VALUES: frozenset[str] = frozenset({
    SignalType.EXPOSURE,
    SignalType.CLICKED_HINT,
    SignalType.MISRECOGNIZED,
    SignalType.TASK_SUCCESS,
    SignalType.TASK_FAILED,
})

_VOCAB_SOURCE_TYPE_VALUES: frozenset[str] = frozenset({
    VocabSourceType.CET6_VOCAB,
    VocabSourceType.SIDEQUEST_ENV,
    VocabSourceType.SEED_DEMO,
})

_SNAPSHOT_SOURCE_VALUES: frozenset[str] = frozenset({
    SnapshotSource.DIAGNOSTIC,
    SnapshotSource.MAIN_TRAINING,
    SnapshotSource.ISOLATED_TEST,
})

_DECISION_TYPE_VALUES: frozenset[str] = frozenset({
    DecisionType.PLAN,
    DecisionType.SKILL_SELECTION,
    DecisionType.ERROR_ANALYSIS,
    DecisionType.REMEDIATION,
    DecisionType.SECOND_PLAN,
    DecisionType.DAILY_LEARNING_PLAN,
})

_CONFIDENCE_VALUES: frozenset[str] = frozenset({
    Confidence.LOW,
    Confidence.MEDIUM,
    Confidence.HIGH,
})


def is_valid_ability(value: Any) -> bool:
    return isinstance(value, str) and value in _ABILITY_VALUES


def is_valid_workflow_stage(value: Any) -> bool:
    return isinstance(value, str) and value in _WORKFLOW_STAGE_VALUES


def is_valid_session_status(value: Any) -> bool:
    return isinstance(value, str) and value in _SESSION_STATUS_VALUES


def is_valid_call_type(value: Any) -> bool:
    return isinstance(value, str) and value in _CALL_TYPE_VALUES


def is_valid_call_status(value: Any) -> bool:
    return isinstance(value, str) and value in _CALL_STATUS_VALUES


def is_valid_profile_suggestion_status(value: Any) -> bool:
    return isinstance(value, str) and value in _PROFILE_SUGGESTION_STATUS_VALUES


def is_valid_memory_status(value: Any) -> bool:
    return isinstance(value, str) and value in _MEMORY_STATUS_VALUES


def is_valid_task_type(value: Any) -> bool:
    return isinstance(value, str) and value in _TASK_TYPE_VALUES


def is_valid_evidence_type(value: Any) -> bool:
    return isinstance(value, str) and value in _EVIDENCE_TYPE_VALUES


def is_valid_validation_status(value: Any) -> bool:
    return isinstance(value, str) and value in _VALIDATION_STATUS_VALUES


def is_valid_signal_type(value: Any) -> bool:
    return isinstance(value, str) and value in _SIGNAL_TYPE_VALUES


def is_valid_vocab_source_type(value: Any) -> bool:
    return isinstance(value, str) and value in _VOCAB_SOURCE_TYPE_VALUES


def is_valid_snapshot_source(value: Any) -> bool:
    return isinstance(value, str) and value in _SNAPSHOT_SOURCE_VALUES


def is_valid_decision_type(value: Any) -> bool:
    return isinstance(value, str) and value in _DECISION_TYPE_VALUES


def is_valid_confidence(value: Any) -> bool:
    return isinstance(value, str) and value in _CONFIDENCE_VALUES


