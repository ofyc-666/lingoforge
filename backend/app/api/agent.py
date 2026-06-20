from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agent.models import RuntimeContext
from app.agent.runtime import AgentRuntime
from app.agent.workflow import AgentWorkflowError, run_text_training_workflow
from app.config import Settings, load_settings
from app.constants import _ABILITY_VALUES
from app.llm.factory import create_llm_provider
import logging

from app.llm.provider import LLMProvider, LLMProviderError

_logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/agent", tags=["agent"])


class AgentRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_input: str = Field(..., min_length=1)


class TextTrainingWorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_text: str = Field(..., min_length=1)
    target_abilities: list[str] = Field(default_factory=lambda: ["VOCABULARY_CONTEXT"])
    max_keywords: int = Field(default=5, ge=1, le=12)
    generate_exercise: bool = True

    @model_validator(mode="after")
    def _raw_text_must_not_be_blank(self) -> "TextTrainingWorkflowRequest":
        if not self.raw_text.strip():
            raise ValueError("raw_text 不能为空或全空白。")
        return self

    @field_validator("target_abilities")
    @classmethod
    def _validate_target_abilities(cls, value: list[str]) -> list[str]:
        for ability in value:
            if ability not in _ABILITY_VALUES:
                raise ValueError(f"target_abilities 中包含非法值 '{ability}'。")
        return value


class AgentRunResponse(BaseModel):
    run_id: str | None
    status: str
    final_answer: str
    tool_calls: list[dict[str, Any]]
    context_manifest: dict[str, Any]
    error: dict[str, str] | None = None


class TextTrainingWorkflowResponse(BaseModel):
    status: str
    agent_run: AgentRunResponse
    analysis: dict[str, Any]
    task_id: int
    task: dict[str, Any]
    validation: dict[str, Any]
    memory_id: int


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


def _agent_run_response_from_result(result: Any) -> AgentRunResponse:
    final_answer = str(result.decision.get("final_answer") or result.final_response)
    return AgentRunResponse(
        run_id=result.run_id,
        status=result.status,
        final_answer=final_answer,
        tool_calls=_tool_call_summary(result.tool_results),
        context_manifest=_manifest_summary(result.context_manifest),
        error=None,
    )


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
        _logger.error("Agent LLM 调用失败 [%s]: %s", code, exc)
        raise HTTPException(
            status_code=502,
            detail={
                "code": str(code),
                "message": f"模型服务暂时不可用（{code}）。详情请查看后端控制台日志。",
            },
        ) from exc

    return _agent_run_response_from_result(result)


@router.post("/workflow/text-training", response_model=TextTrainingWorkflowResponse)
def run_text_training_agent_workflow(
    request: TextTrainingWorkflowRequest,
    settings: Settings = Depends(get_settings),
    provider: LLMProvider = Depends(get_agent_provider),
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    session_id: int = Header(..., alias="X-LingoForge-Session-Id"),
) -> TextTrainingWorkflowResponse:
    """触发 Agent 主线闭环：决策、文本分析、训练任务生成和质量校验。"""
    try:
        result = run_text_training_workflow(
            settings.database_path,
            provider=provider,
            user_id=user_id,
            session_id=session_id,
            raw_text=request.raw_text,
            target_abilities=request.target_abilities,
            max_keywords=request.max_keywords,
            generate_exercise=request.generate_exercise,
        )
    except LLMProviderError as exc:
        code = getattr(exc, "code", "LLM_PROVIDER_ERROR")
        _logger.error("Agent workflow LLM 调用失败 [%s]: %s", code, exc)
        raise HTTPException(
            status_code=502,
            detail={
                "code": str(code),
                "message": f"模型服务暂时不可用（{code}）。详情请查看后端控制台日志。",
            },
        ) from exc
    except AgentWorkflowError as exc:
        status_map = {
            "SESSION_NOT_FOUND": 404,
            "SESSION_ACCESS_DENIED": 403,
            "AGENT_DECISION_INVALID": 422,
            "TRAINING_TASK_VALIDATION_FAILED": 422,
        }
        raise HTTPException(
            status_code=status_map.get(exc.code, 500),
            detail={"code": exc.code, "message": exc.message, "details": exc.details},
        ) from exc

    return TextTrainingWorkflowResponse(
        status=result["workflow_status"],
        agent_run=_agent_run_response_from_result(result["agent_run"]),
        analysis=result["analysis"],
        task_id=result["task_id"],
        task=result["task"] or {},
        validation=result["validation"],
        memory_id=result["memory_id"],
    )
