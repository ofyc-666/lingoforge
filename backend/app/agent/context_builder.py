"""最小 ContextBuilder。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.agent.memory import list_memory_items
from app.agent.models import ContextBuildResult, ContextManifest, RuntimeContext
from app.agent.skills import get_skill_definition, list_skill_catalog
from app.agent.tools import (
    history_analysis_algorithm_version,
    history_analysis_cache_key,
)
from app.llm.types import LLMMessage
from app.repositories.logs import create_tool_call_log
from app.services.learning_history import analyze_learning_history


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

    def __init__(self, database_path: str | Path | None = None) -> None:
        self.database_path = database_path

    def build_initial_context(self, run_id: str, context: RuntimeContext) -> ContextBuildResult:
        context_policy = self._context_policy(context)
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
            "context_policy": context_policy,
            "skill_catalog": list_skill_catalog(),
            "memory_catalog": self._memory_catalog(context),
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
        for skill in context_pack["skill_catalog"]:
            manifest.add_included_ref(
                "skill_catalog_item",
                skill["skill_id"],
                version=skill["version"],
            )
        for memory in context_pack["memory_catalog"]:
            manifest.add_included_ref(
                "memory_catalog_item",
                memory["memory_id"],
                status=memory.get("status"),
                memory_type=memory.get("memory_type"),
            )
        if not context_policy["context_expansion_enabled"]:
            manifest.add_excluded_ref("context_expansion", context_policy["disabled_reason"])
        if not context_policy["memory_expansion_enabled"]:
            manifest.add_excluded_ref("memory_detail", context_policy["disabled_reason"])
        if context.workflow_stage == "ISOLATED_TEST":
            manifest.add_excluded_ref(
                "isolated_test_content",
                "isolated_test_in_progress_no_answers_or_rationales",
            )
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

    def parse_context_expansion_request(self, content: str) -> dict[str, Any] | None:
        try:
            parsed = json.loads(content) if content else {}
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        if parsed.get("decision_type") != "CONTEXT_EXPANSION_REQUEST":
            request_keys = {"requested_memory_ids", "requested_skill_ids", "requested_history_analyses"}
            if not request_keys.intersection(parsed):
                return None
        return {
            "requested_memory_ids": parsed.get("requested_memory_ids", []),
            "requested_skill_ids": parsed.get("requested_skill_ids", []),
            "requested_history_analyses": parsed.get("requested_history_analyses", []),
            "reason": parsed.get("reason", ""),
            "intended_use": parsed.get("intended_use", ""),
            "priority": parsed.get("priority", "NORMAL"),
        }

    def expand_context(
        self,
        run_id: str,
        context: RuntimeContext,
        manifest: ContextManifest,
        request: dict[str, Any],
        result_cache: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        policy = self._context_policy(context)
        if not policy["context_expansion_enabled"]:
            manifest.add_excluded_ref("context_expansion_request", policy["disabled_reason"])
            manifest.context_hash = compute_hash(_manifest_hash_payload(manifest))
            return {
                "run_id": run_id,
                "status": "DENIED",
                "reason": policy["disabled_reason"],
            }

        expansion: dict[str, Any] = {
            "run_id": run_id,
            "status": "COMPLETED",
            "reason": request.get("reason", ""),
            "intended_use": request.get("intended_use", ""),
            "priority": request.get("priority", "NORMAL"),
            "skill_details": [],
            "memory_details": [],
            "history_analyses": [],
        }
        manifest.add_included_ref("context_expansion_request", run_id)

        for skill_id in self._safe_str_list(request.get("requested_skill_ids")):
            skill = get_skill_definition(skill_id)
            if skill is None:
                manifest.add_excluded_ref("skill_detail", "skill_not_found", id=skill_id)
                continue
            expansion["skill_details"].append(skill)
            manifest.add_included_ref("skill_detail", skill["skill_id"], version=skill["version"])

        if policy["memory_expansion_enabled"]:
            requested_memory_ids = set(self._safe_int_list(request.get("requested_memory_ids")))
            for memory in self._memory_details(context):
                if requested_memory_ids and memory["memory_id"] not in requested_memory_ids:
                    continue
                expansion["memory_details"].append(memory)
                manifest.add_included_ref(
                    "memory_detail",
                    memory["memory_id"],
                    status=memory.get("status"),
                    memory_type=memory.get("memory_type"),
                )
        elif request.get("requested_memory_ids"):
            manifest.add_excluded_ref("memory_detail", policy["disabled_reason"])

        for analysis_request in self._safe_dict_list(request.get("requested_history_analyses")):
            analysis_result = self._run_history_analysis_for_expansion(
                context,
                analysis_request,
                result_cache,
            )
            expansion["history_analyses"].append(analysis_result["output"])
            manifest.add_included_ref(
                "history_analysis",
                analysis_result["log_id"],
                analysis_type=analysis_result["output"].get("analysis_type"),
                algorithm_version=analysis_result["output"].get("algorithm_version"),
            )
            manifest.add_tool_result_ref(analysis_result["log_id"])
            for ref in analysis_result["output"].get("source_refs", []):
                if isinstance(ref, dict) and "type" in ref and "id" in ref:
                    manifest.add_included_ref(ref["type"], ref["id"])

        manifest.context_hash = compute_hash(_manifest_hash_payload(manifest))
        return expansion

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

    def _context_policy(self, context: RuntimeContext) -> dict[str, Any]:
        if context.workflow_stage == "ISOLATED_TEST":
            return {
                "mode": "isolated_test_locked",
                "context_expansion_enabled": False,
                "memory_expansion_enabled": False,
                "history_analysis_enabled": False,
                "disabled_reason": "isolated_test_in_progress",
            }
        return {
            "mode": "fast_path_with_optional_expansion",
            "context_expansion_enabled": True,
            "memory_expansion_enabled": True,
            "history_analysis_enabled": "read_learning_history" in context.permission_scope,
            "disabled_reason": "",
        }

    def _memory_catalog(self, context: RuntimeContext) -> list[dict[str, Any]]:
        return [
            {
                "memory_id": item["memory_id"],
                "memory_type": item.get("memory_type"),
                "status": item.get("status"),
                "source_refs": item.get("source_refs", []),
                "created_at": item.get("created_at"),
            }
            for item in self._memory_details(context)
        ]

    def _memory_details(self, context: RuntimeContext) -> list[dict[str, Any]]:
        if self.database_path is None:
            return []
        if context.workflow_stage == "ISOLATED_TEST":
            return []
        return list_memory_items(self.database_path, user_id=context.user_id, limit=20)

    def _run_history_analysis_for_expansion(
        self,
        context: RuntimeContext,
        analysis_request: dict[str, Any],
        result_cache: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        if self.database_path is None:
            raise RuntimeError("ContextBuilder 需要 database_path 才能执行历史分析扩展")
        arguments = {
            "analysis_type": analysis_request.get("analysis_type"),
            "target": analysis_request.get("target", {}),
            "time_window": analysis_request.get("time_window"),
            "intended_use": analysis_request.get("intended_use", ""),
        }
        cache_key = history_analysis_cache_key(context, arguments)
        cached = result_cache.get(cache_key) if cache_key else None
        if cached is not None:
            return cached

        analysis = analyze_learning_history(
            self.database_path,
            user_id=context.user_id,
            analysis_type=arguments["analysis_type"],
            target=arguments["target"],
            time_window=arguments["time_window"],
        )
        algorithm_version = (
            analysis.get("algorithm_version")
            if isinstance(analysis, dict) and analysis.get("algorithm_version")
            else history_analysis_algorithm_version(str(arguments["analysis_type"]))
        )
        source_refs = self._analysis_source_refs(analysis)
        output = {
            "bound_user_id": context.user_id,
            "bound_session_id": context.session_id,
            "permission_scope": list(context.permission_scope),
            "analysis_type": arguments["analysis_type"],
            "target": arguments["target"],
            "time_window": arguments["time_window"],
            "intended_use": arguments["intended_use"],
            "algorithm_version": algorithm_version,
            "analysis": analysis,
            "source_refs": source_refs,
        }
        input_json = {
            "tool_call_id": "context-expansion",
            "model_arguments": arguments,
            "runtime_bound_user_id": context.user_id,
            "runtime_bound_session_id": context.session_id,
        }
        log_id = create_tool_call_log(
            self.database_path,
            call_name="analyze_learning_history",
            call_type="CONTEXT_EXPANSION_TOOL",
            input_json=input_json,
            output_json=output,
            status="SUCCESS",
            user_id=context.user_id,
            session_id=context.session_id,
        )
        result = {
            "tool_call_id": "context-expansion",
            "tool_name": "analyze_learning_history",
            "status": "SUCCESS",
            "input": input_json,
            "output": output,
            "error_code": None,
            "log_id": log_id,
        }
        if cache_key:
            result_cache[cache_key] = result
        return result

    def _analysis_source_refs(self, analysis: dict[str, Any]) -> list[dict[str, int]]:
        refs: list[dict[str, int]] = []
        seen: set[int] = set()
        for ref_id in analysis.get("evidence_refs", []) if isinstance(analysis, dict) else []:
            if isinstance(ref_id, int) and ref_id not in seen:
                refs.append({"type": "learning_evidence", "id": ref_id})
                seen.add(ref_id)
        for item in analysis.get("problem_items", []) if isinstance(analysis, dict) else []:
            if not isinstance(item, dict):
                continue
            for ref_id in item.get("evidence_refs", []):
                if isinstance(ref_id, int) and ref_id not in seen:
                    refs.append({"type": "learning_evidence", "id": ref_id})
                    seen.add(ref_id)
        return refs

    def _safe_str_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, str)]

    def _safe_int_list(self, value: Any) -> list[int]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, int)]

    def _safe_dict_list(self, value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict)]
