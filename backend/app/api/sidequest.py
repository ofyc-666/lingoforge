"""副线 API 路由。

提供机场购票副线完成端点。
只写 sidequest_runs 和 sidequest_signals，不写 learning_evidence 或 profile_snapshots。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from app.api.sidequest_models import SidequestCompleteRequest, SidequestCompleteResponse
from app.config import Settings, load_settings
from app.repositories.sidequest import create_sidequest_run, create_sidequest_signal

router = APIRouter(prefix="/api/sidequest", tags=["sidequest"])


def get_settings() -> Settings:
    return load_settings()


@router.post("/airport-ticket/complete", response_model=SidequestCompleteResponse)
def complete_airport_ticket(
    request: SidequestCompleteRequest,
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    settings: Settings = Depends(get_settings),
) -> SidequestCompleteResponse:
    """记录机场购票副线完成结果。

    写入 sidequest_runs 和 sidequest_signals（is_pending_verification=1）。
    不写 learning_evidence，不写 profile_snapshots。
    """
    # 创建副线运行记录
    run_id = create_sidequest_run(
        settings.database_path,
        user_id=user_id,
        task_name="AIRPORT_TICKET_PURCHASE",
        objective={"scene": request.scene, "expression": request.selected_expression},
        result=request.result,
    )

    # 写入待验证副线信号
    signal_id = create_sidequest_signal(
        settings.database_path,
        user_id=user_id,
        sidequest_run_id=run_id,
        scene=request.scene,
        signal_type="TASK_SUCCESS" if request.result.get("completed") else "EXPOSURE",
        expression_text=request.selected_expression,
        context_json={
            "selected_expression": request.selected_expression,
            "scene": request.scene,
        },
    )

    return SidequestCompleteResponse(
        sidequest_run_id=run_id,
        signal_id=signal_id,
        is_pending_verification=True,
    )
