"""文本分析 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException

from app.api.learning_models import TextAnalysisRequest, TextAnalysisResponse
from app.services.learning_analysis import analyze_english_text

router = APIRouter(prefix="/api/learning", tags=["learning"])


@router.post("/analyze-text", response_model=TextAnalysisResponse)
def analyze_text(
    request: TextAnalysisRequest,
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
    session_id: int | None = Header(None, alias="X-LingoForge-Session-Id"),
) -> TextAnalysisResponse:
    """对英文文本进行确定性分析，返回关键词、练习题和反馈。"""
    return analyze_english_text(request)
