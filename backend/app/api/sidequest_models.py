"""副线 API 请求与响应 Pydantic 模型。

请求体禁止身份字段。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SidequestCompleteRequest(BaseModel):
    """副线完成请求体。"""

    model_config = ConfigDict(extra="forbid")

    selected_expression: str = Field(..., min_length=1)
    scene: str = Field(..., min_length=1)
    result: dict[str, Any] = Field(default_factory=dict)


class SidequestCompleteResponse(BaseModel):
    """副线完成响应体。"""

    sidequest_run_id: int
    signal_id: int
    is_pending_verification: bool
