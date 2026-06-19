from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.agent.models import RuntimeContext
from app.agent.runtime import AgentRuntime
from app.config import Settings, load_settings
from app.llm.factory import create_llm_provider
from app.llm.provider import LLMProvider, LLMProviderError


router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_input: str = Field(..., min_length=1)


class AgentRunResponse(BaseModel):
    run_id: str | None
    status: str
    final_answer: str
    tool_calls: list[dict[str, Any]]
    context_manifest: dict[str, Any]
    error: dict[str, str] | None = None


def get_settings() -> Settings:
    return load_settings()


def get_agent_provider(settings: Settings = Depends(get_settings)) -> LLMProvider:
    return create_llm_provider(settings)


def _tool_call_summary(tool_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "tool_call_id": result.get("tool_call_id"),
            "tool_name": result.get("tool_name"),
            "status": result.get("status"),
            "error_code": result.get("error_code"),
            "log_id": result.get("log_id"),
        }
        for result in tool_results
    ]


def _manifest_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": manifest.get("run_id"),
        "workflow_stage": manifest.get("workflow_stage"),
        "prompt_version": manifest.get("prompt_version"),
        "included_refs": manifest.get("included_refs", []),
        "excluded_refs": manifest.get("excluded_refs", []),
        "tool_result_refs": manifest.get("tool_result_refs", []),
        "context_hash": manifest.get("context_hash"),
    }


@router.post("/run", response_model=AgentRunResponse)
def run_agent(
    request: AgentRunRequest,
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_agent_provider),
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    session_id: int | None = Header(None, alias="X-LingoForge-Session-Id"),
) -> AgentRunResponse:
    context = RuntimeContext(
        user_id=user_id,
        session_id=session_id,
        workflow_stage="FIRST_MAIN",
        objective=request.user_input,
        allowed_tools=("get_user_profile",),
        permission_scope=("read_user_profile",),
    )
    runtime = AgentRuntime(database_path=settings.database_path, provider=provider)
    try:
        result = runtime.run(context)
    except LLMProviderError as exc:
        code = getattr(exc, "code", "LLM_PROVIDER_ERROR")
        raise HTTPException(
            status_code=502,
            detail={
                "code": str(code),
                "message": "模型服务暂时不可用，请稍后重试。",
            },
        ) from exc

    final_answer = str(result.decision.get("final_answer") or result.final_response)
    return AgentRunResponse(
        run_id=result.run_id,
        status=result.status,
        final_answer=final_answer,
        tool_calls=_tool_call_summary(result.tool_results),
        context_manifest=_manifest_summary(result.context_manifest),
        error=None,
    )
