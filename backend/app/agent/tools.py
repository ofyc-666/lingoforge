"""Agent 可调用工具的注册与执行。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agent.models import RuntimeContext
from app.llm.types import LLMToolCall, LLMToolSpec
from app.repositories.logs import create_tool_call_log
from app.repositories.users import get_latest_profile, get_latest_user_goal, get_user


ToolHandler = Callable[[RuntimeContext, dict[str, Any]], dict[str, Any]]

IDENTITY_ARGUMENTS = frozenset({
    "user_id",
    "current_user_id",
    "session_id",
    "current_session_id",
    "permission_scope",
    "permissions",
})


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    def spec(self) -> LLMToolSpec:
        return LLMToolSpec(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )


class ToolRegistry:
    """最小工具注册表。"""

    def __init__(self, tools: dict[str, ToolDefinition]) -> None:
        self._tools = dict(tools)

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def specs_for(self, allowed_tools: tuple[str, ...]) -> list[LLMToolSpec]:
        specs: list[LLMToolSpec] = []
        for name in allowed_tools:
            tool = self.get(name)
            if tool is not None:
                specs.append(tool.spec())
        return specs


def get_user_profile_tool_spec() -> LLMToolSpec:
    return LLMToolSpec(
        name="get_user_profile",
        description="读取 Runtime 绑定用户的目标和最新画像快照；参数中不得包含 user_id。",
        parameters={
            "type": "object",
            "properties": {
                "include_goal": {
                    "type": "boolean",
                    "description": "是否返回最新用户目标，默认 true。",
                },
                "include_profile": {
                    "type": "boolean",
                    "description": "是否返回最新画像快照，默认 true。",
                },
            },
            "additionalProperties": False,
        },
    )


def _validate_get_user_profile_arguments(
    arguments: dict[str, Any],
) -> tuple[dict[str, bool] | None, str | None]:
    if not isinstance(arguments, dict):
        return None, "INVALID_TOOL_ARGUMENTS"
    if IDENTITY_ARGUMENTS.intersection(arguments):
        return None, "IDENTITY_ARGUMENT_FORBIDDEN"
    allowed = {"include_goal", "include_profile"}
    if any(key not in allowed for key in arguments):
        return None, "INVALID_TOOL_ARGUMENTS"
    include_goal = arguments.get("include_goal", True)
    include_profile = arguments.get("include_profile", True)
    if not isinstance(include_goal, bool) or not isinstance(include_profile, bool):
        return None, "INVALID_TOOL_ARGUMENTS"
    return {"include_goal": include_goal, "include_profile": include_profile}, None


def _wrap_optional_row(row: dict[str, Any] | None) -> dict[str, Any]:
    return {"found": row is not None, "data": row}


def build_get_user_profile_handler(database_path: str | Path) -> ToolHandler:
    """创建只读取 Runtime 绑定用户数据的工具处理函数。"""

    def handler(context: RuntimeContext, arguments: dict[str, Any]) -> dict[str, Any]:
        sanitized, error_code = _validate_get_user_profile_arguments(arguments)
        if error_code is not None:
            raise ToolArgumentError(error_code)

        user = get_user(database_path, context.user_id)
        goal = get_latest_user_goal(database_path, context.user_id) if sanitized["include_goal"] else None
        profile = get_latest_profile(database_path, context.user_id) if sanitized["include_profile"] else None
        refs: list[dict[str, Any]] = []
        if goal is not None:
            refs.append({"type": "user_goal", "id": goal["id"]})
        if profile is not None:
            refs.append({"type": "profile_snapshot", "id": profile["id"]})
            refs.extend({"type": "learning_evidence", "id": ref_id} for ref_id in profile.get("evidence_refs", []))

        return {
            "bound_user_id": context.user_id,
            "bound_session_id": context.session_id,
            "permission_scope": list(context.permission_scope),
            "user": _wrap_optional_row(user),
            "goal": _wrap_optional_row(goal),
            "profile_snapshot": _wrap_optional_row(profile),
            "source_refs": refs,
        }

    return handler


def create_default_tool_registry(database_path: str | Path) -> ToolRegistry:
    spec = get_user_profile_tool_spec()
    return ToolRegistry({
        "get_user_profile": ToolDefinition(
            name=spec.name,
            description=spec.description,
            parameters=spec.parameters,
            handler=build_get_user_profile_handler(database_path),
        )
    })


class ToolArgumentError(ValueError):
    """工具参数校验失败。"""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class ToolExecutor:
    """执行模型请求的工具调用，并记录审计日志。"""

    def __init__(self, database_path: str | Path, registry: ToolRegistry) -> None:
        self.database_path = database_path
        self.registry = registry

    def execute(self, context: RuntimeContext, tool_call: LLMToolCall) -> dict[str, Any]:
        raw_arguments = tool_call.arguments
        input_json = {
            "tool_call_id": tool_call.id,
            "model_arguments": raw_arguments,
            "runtime_bound_user_id": context.user_id,
            "runtime_bound_session_id": context.session_id,
        }

        tool = self.registry.get(tool_call.name)
        if tool is None:
            return self._failure(context, tool_call, input_json, "TOOL_NOT_FOUND")
        if tool.name not in context.allowed_tools:
            return self._failure(context, tool_call, input_json, "TOOL_NOT_ALLOWED")

        try:
            output = tool.handler(context, raw_arguments)
        except ToolArgumentError as exc:
            return self._failure(context, tool_call, input_json, exc.code)
        except Exception:
            return self._failure(context, tool_call, input_json, "TOOL_EXECUTION_FAILED")

        log_id = create_tool_call_log(
            self.database_path,
            call_name=tool_call.name,
            call_type="LLM_TOOL",
            input_json=input_json,
            output_json=output,
            status="SUCCESS",
            user_id=context.user_id,
            session_id=context.session_id,
        )
        return {
            "tool_call_id": tool_call.id,
            "tool_name": tool_call.name,
            "status": "SUCCESS",
            "input": input_json,
            "output": output,
            "error_code": None,
            "log_id": log_id,
        }

    def _failure(
        self,
        context: RuntimeContext,
        tool_call: LLMToolCall,
        input_json: dict[str, Any],
        error_code: str,
    ) -> dict[str, Any]:
        output = {
            "error": {
                "code": error_code,
                "message": "工具调用被拒绝或执行失败，未暴露内部异常细节。",
            },
            "bound_user_id": context.user_id,
            "bound_session_id": context.session_id,
        }
        log_id = create_tool_call_log(
            self.database_path,
            call_name=tool_call.name,
            call_type="LLM_TOOL",
            input_json=input_json,
            output_json=output,
            status="FAILED",
            user_id=context.user_id,
            session_id=context.session_id,
            error_code=error_code,
        )
        return {
            "tool_call_id": tool_call.id,
            "tool_name": tool_call.name,
            "status": "FAILED",
            "input": input_json,
            "output": output,
            "error_code": error_code,
            "log_id": log_id,
        }
