"""Agent Runtime 逻辑对象。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RuntimeContext:
    """一次 AgentRun 的可信运行上下文。

    用户、session 和权限来自 Runtime 调用方，不接受模型覆盖。
    """

    user_id: int
    session_id: int | None
    workflow_stage: str
    objective: str
    allowed_tools: tuple[str, ...]
    token_budget: int = 4000
    prompt_version: str = "agent-runtime-mvp-v1"
    permission_scope: tuple[str, ...] = ("read_user_profile",)


@dataclass
class ContextManifest:
    """ContextBuilder 生成的可审计上下文清单。"""

    run_id: str
    workflow_stage: str
    objective: str
    prompt_version: str
    token_budget: int
    permission_scope: tuple[str, ...]
    included_refs: list[dict[str, Any]] = field(default_factory=list)
    excluded_refs: list[dict[str, Any]] = field(default_factory=list)
    redactions: list[dict[str, Any]] = field(default_factory=list)
    tool_result_refs: list[int] = field(default_factory=list)
    context_hash: str = ""

    def add_included_ref(self, ref_type: str, ref_id: int | str, **extra: Any) -> None:
        ref = {"type": ref_type, "id": ref_id, **extra}
        if ref not in self.included_refs:
            self.included_refs.append(ref)

    def add_excluded_ref(self, ref_type: str, reason: str, **extra: Any) -> None:
        ref = {"type": ref_type, "reason": reason, **extra}
        if ref not in self.excluded_refs:
            self.excluded_refs.append(ref)

    def add_tool_result_ref(self, log_id: int) -> None:
        if log_id not in self.tool_result_refs:
            self.tool_result_refs.append(log_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_stage": self.workflow_stage,
            "objective": self.objective,
            "prompt_version": self.prompt_version,
            "token_budget": self.token_budget,
            "permission_scope": list(self.permission_scope),
            "included_refs": list(self.included_refs),
            "excluded_refs": list(self.excluded_refs),
            "redactions": list(self.redactions),
            "tool_result_refs": list(self.tool_result_refs),
            "context_hash": self.context_hash,
        }


@dataclass(frozen=True)
class ContextBuildResult:
    """ContextBuilder 输出。"""

    context_pack: dict[str, Any]
    manifest: ContextManifest


@dataclass(frozen=True)
class DecisionValidationResult:
    """最终模型输出校验结果。"""

    status: str
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "errors": list(self.errors)}


@dataclass(frozen=True)
class AgentRunResult:
    """Runtime 返回的结构化 AgentRun 结果。"""

    run_id: str
    status: str
    provider_name: str
    workflow_stage: str
    final_response: str
    decision: dict[str, Any]
    context_manifest: dict[str, Any]
    tool_results: list[dict[str, Any]]
    agent_decision_log_id: int | None
    validation: dict[str, Any]
