"""Agent Runtime 最小 Function Calling 闭环。"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from app.agent.context_builder import ContextBuilder
from app.agent.models import AgentRunResult, RuntimeContext
from app.agent.tools import ToolExecutor, ToolRegistry, create_default_tool_registry
from app.agent.validation import DecisionValidator
from app.llm.provider import LLMProvider
from app.llm.types import LLMMessage
from app.repositories.logs import create_agent_decision_log


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class AgentRuntime:
    """管理一次 Agent 调用的生命周期。"""

    def __init__(
        self,
        database_path: str | Path,
        provider: LLMProvider,
        tool_registry: ToolRegistry | None = None,
        context_builder: ContextBuilder | None = None,
        decision_validator: DecisionValidator | None = None,
        timeout_seconds: float | None = 30.0,
    ) -> None:
        self.database_path = database_path
        self.provider = provider
        self.tool_registry = tool_registry or create_default_tool_registry(database_path)
        self.context_builder = context_builder or ContextBuilder()
        self.decision_validator = decision_validator or DecisionValidator()
        self.timeout_seconds = timeout_seconds

    def run(self, context: RuntimeContext) -> AgentRunResult:
        run_id = uuid.uuid4().hex
        build_result = self.context_builder.build_initial_context(run_id, context)
        manifest = build_result.manifest
        messages = self.context_builder.build_messages(build_result.context_pack)
        tool_specs = self.tool_registry.specs_for(context.allowed_tools)

        first_response = self.provider.generate(
            messages,
            tools=tool_specs,
            timeout_seconds=self.timeout_seconds,
        )

        tool_results: list[dict[str, Any]] = []
        final_response = first_response
        if first_response.tool_calls:
            messages.append(LLMMessage(
                role="assistant",
                content=first_response.content or "模型请求工具调用。",
            ))
            executor = ToolExecutor(self.database_path, self.tool_registry)
            for tool_call in first_response.tool_calls:
                tool_result = executor.execute(context, tool_call)
                tool_results.append(tool_result)
                self.context_builder.record_tool_result(manifest, tool_result)
                messages.append(LLMMessage(
                    role="tool",
                    name=tool_call.name,
                    tool_call_id=tool_call.id,
                    content=_stable_json({
                        "tool_call_id": tool_call.id,
                        "tool_name": tool_call.name,
                        "status": tool_result["status"],
                        "output": tool_result["output"],
                        "error_code": tool_result["error_code"],
                        "log_id": tool_result["log_id"],
                    }),
                ))
            final_response = self.provider.generate(
                messages,
                tools=tool_specs,
                timeout_seconds=self.timeout_seconds,
            )

        decision, validation = self.decision_validator.validate(
            final_response.content,
            context,
            tool_results,
        )
        status = self._run_status(tool_results, validation.status)
        manifest_dict = manifest.to_dict()
        decision_log_id = self._write_decision_log(
            run_id=run_id,
            context=context,
            status=status,
            manifest=manifest_dict,
            final_response=final_response.content,
            decision=decision,
            validation=validation.to_dict(),
            tool_results=tool_results,
        )

        return AgentRunResult(
            run_id=run_id,
            status=status,
            provider_name=self.provider.name,
            workflow_stage=context.workflow_stage,
            final_response=final_response.content,
            decision=decision,
            context_manifest=manifest_dict,
            tool_results=tool_results,
            agent_decision_log_id=decision_log_id,
            validation=validation.to_dict(),
        )

    def _run_status(self, tool_results: list[dict[str, Any]], validation_status: str) -> str:
        if validation_status != "PASSED":
            return "FAILED_VALIDATION"
        if any(result["status"] == "FAILED" for result in tool_results):
            return "COMPLETED_WITH_TOOL_ERRORS"
        return "COMPLETED"

    def _write_decision_log(
        self,
        run_id: str,
        context: RuntimeContext,
        status: str,
        manifest: dict[str, Any],
        final_response: str,
        decision: dict[str, Any],
        validation: dict[str, Any],
        tool_results: list[dict[str, Any]],
    ) -> int:
        evidence_refs = decision.get("evidence_refs", [])
        if not isinstance(evidence_refs, list) or not all(isinstance(ref, int) for ref in evidence_refs):
            evidence_refs = []

        return create_agent_decision_log(
            self.database_path,
            decision_type=str(decision.get("decision_type", "AGENT_RUN")),
            user_id=context.user_id,
            session_id=context.session_id,
            input_summary={
                "run_id": run_id,
                "status": status,
                "workflow_stage": context.workflow_stage,
                "objective": context.objective,
                "provider": self.provider.name,
                "prompt_version": context.prompt_version,
                "context_manifest": manifest,
            },
            decision={
                "run_id": run_id,
                "status": status,
                "decision": decision,
                "final_response": final_response,
                "tool_result_refs": [
                    result["log_id"] for result in tool_results if isinstance(result.get("log_id"), int)
                ],
                "validation": validation,
            },
            evidence_refs=evidence_refs,
        )
