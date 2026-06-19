"""最小 ContextBuilder。"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.agent.models import ContextBuildResult, ContextManifest, RuntimeContext
from app.llm.types import LLMMessage


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_hash(value: Any) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _manifest_hash_payload(manifest: ContextManifest) -> dict[str, Any]:
    payload = manifest.to_dict()
    payload["context_hash"] = ""
    return payload


class ContextBuilder:
    """构建模型可见的最小上下文和审计 Manifest。"""

    def build_initial_context(self, run_id: str, context: RuntimeContext) -> ContextBuildResult:
        context_pack = {
            "run_id": run_id,
            "workflow_stage": context.workflow_stage,
            "objective": context.objective,
            "allowed_tools": list(context.allowed_tools),
            "identity_boundary": {
                "user_identity": "Runtime 注入，模型不得提供 user_id",
                "session_identity": "Runtime 注入，模型不得提供 session_id",
                "permission_scope": list(context.permission_scope),
            },
            "context_policy": {
                "mode": "fast_path",
                "context_expansion_enabled": False,
                "memory_expansion_enabled": False,
            },
        }
        manifest = ContextManifest(
            run_id=run_id,
            workflow_stage=context.workflow_stage,
            objective=context.objective,
            prompt_version=context.prompt_version,
            token_budget=context.token_budget,
            permission_scope=context.permission_scope,
        )
        manifest.add_included_ref("runtime_context", run_id)
        for tool_name in context.allowed_tools:
            manifest.add_included_ref("allowed_tool", tool_name)
        manifest.add_excluded_ref("context_expansion", "fast_path_minimal_run")
        manifest.add_excluded_ref("memory", "not_in_scope_for_first_vertical_slice")
        manifest.context_hash = compute_hash({
            "context_pack": context_pack,
            "manifest": _manifest_hash_payload(manifest),
        })
        return ContextBuildResult(context_pack=context_pack, manifest=manifest)

    def build_messages(self, context_pack: dict[str, Any]) -> list[LLMMessage]:
        system_prompt = (
            "你是 LingoForge 的单 Agent Runtime 测试竖切。"
            "你只能通过已提供的 Function Calling 工具读取用户数据；"
            "不得在工具参数中提供 user_id、session_id 或权限范围。"
        )
        return [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=_stable_json(context_pack)),
        ]

    def record_tool_result(
        self,
        manifest: ContextManifest,
        tool_result: dict[str, Any],
    ) -> None:
        log_id = tool_result.get("log_id")
        if isinstance(log_id, int):
            manifest.add_tool_result_ref(log_id)
        manifest.add_included_ref(
            "tool_result",
            log_id if isinstance(log_id, int) else tool_result.get("tool_call_id", "unknown"),
            tool_name=tool_result.get("tool_name"),
            status=tool_result.get("status"),
        )
        output = tool_result.get("output")
        if isinstance(output, dict):
            for ref in output.get("source_refs", []):
                if isinstance(ref, dict) and "type" in ref and "id" in ref:
                    manifest.add_included_ref(ref["type"], ref["id"])
        manifest.context_hash = compute_hash(_manifest_hash_payload(manifest))
