"""Reader import, highlight and vocabulary book API."""

from __future__ import annotations

import base64
import csv
from io import StringIO

from fastapi import APIRouter, Depends, Header, HTTPException, Response

from app.api.errors import business_error
from app.api.learning_models import TextAnalysisRequest
from app.api.reader_models import (
    ReaderImportResponse,
    ReaderPdfImportRequest,
    ReaderTextImportRequest,
    UserVocabularyCreateRequest,
    UserVocabularyItemResponse,
    UserVocabularyListResponse,
)
from app.config import Settings, load_settings
from app.repositories.reader import (
    add_user_vocabulary_item,
    create_reading_document,
    get_reading_document,
    list_user_vocabulary_items,
)
from app.repositories.users import get_user
from app.services.learning_analysis import analyze_english_text
from app.services.pdf_parser import PDFTextExtractionError, extract_text_from_pdf_bytes

router = APIRouter(prefix="/api/reader", tags=["reader"])


def get_settings() -> Settings:
    return load_settings()


def _require_user(settings: Settings, user_id: int) -> None:
    if get_user(settings.database_path, user_id) is None:
        raise business_error(
            status_code=404,
            code="USER_NOT_FOUND",
            message=f"用户 {user_id} 不存在。",
            details={"user_id": user_id},
        )


def _analyze_for_reader(raw_text: str, max_keywords: int) -> dict:
    analysis = analyze_english_text(TextAnalysisRequest(
        raw_text=raw_text,
        target_abilities=["VOCABULARY_CONTEXT"],
        max_keywords=max_keywords,
        generate_exercise=False,
    ))
    return analysis.model_dump()


def _import_response(
    *,
    document_id: int,
    source_type: str,
    file_name: str | None,
    analysis: dict,
) -> ReaderImportResponse:
    return ReaderImportResponse(
        document_id=document_id,
        source_type=source_type,
        file_name=file_name,
        raw_text=analysis["raw_text"],
        keywords=analysis["keywords"],
        warnings=analysis.get("warnings", []),
    )


@router.post("/import-text", response_model=ReaderImportResponse)
def import_text(
    request: ReaderTextImportRequest,
    settings: Settings = Depends(get_settings),
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
) -> ReaderImportResponse:
    _require_user(settings, user_id)
    analysis = _analyze_for_reader(request.raw_text.strip(), request.max_keywords)
    document_id = create_reading_document(
        settings.database_path,
        user_id=user_id,
        source_type="TEXT",
        raw_text=analysis["raw_text"],
        analysis=analysis,
    )
    return _import_response(
        document_id=document_id,
        source_type="TEXT",
        file_name=None,
        analysis=analysis,
    )


@router.post("/import-pdf", response_model=ReaderImportResponse)
def import_pdf(
    request: ReaderPdfImportRequest,
    settings: Settings = Depends(get_settings),
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
) -> ReaderImportResponse:
    _require_user(settings, user_id)
    try:
        pdf_bytes = base64.b64decode(request.content_base64, validate=True)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "INVALID_PDF_BASE64",
                "message": "PDF 内容不是合法 base64。",
                "details": {},
            },
        ) from exc

    try:
        raw_text = extract_text_from_pdf_bytes(pdf_bytes)
    except PDFTextExtractionError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "PDF_TEXT_EXTRACTION_FAILED",
                "message": str(exc),
                "details": {"file_name": request.file_name},
            },
        ) from exc

    analysis = _analyze_for_reader(raw_text, request.max_keywords)
    document_id = create_reading_document(
        settings.database_path,
        user_id=user_id,
        source_type="PDF",
        file_name=request.file_name,
        raw_text=analysis["raw_text"],
        analysis=analysis,
    )
    return _import_response(
        document_id=document_id,
        source_type="PDF",
        file_name=request.file_name,
        analysis=analysis,
    )


@router.get("/documents/{document_id}", response_model=ReaderImportResponse)
def get_document(
    document_id: int,
    settings: Settings = Depends(get_settings),
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
) -> ReaderImportResponse:
    _require_user(settings, user_id)
    document = get_reading_document(settings.database_path, user_id=user_id, document_id=document_id)
    if document is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "DOCUMENT_NOT_FOUND",
                "message": f"阅读文档 {document_id} 不存在。",
                "details": {"document_id": document_id},
            },
        )
    return _import_response(
        document_id=document_id,
        source_type=document["source_type"],
        file_name=document.get("file_name"),
        analysis=document["analysis_json"],
    )


@router.post("/vocabulary", response_model=UserVocabularyItemResponse)
def add_vocabulary(
    request: UserVocabularyCreateRequest,
    settings: Settings = Depends(get_settings),
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
) -> dict:
    _require_user(settings, user_id)
    if request.source_document_id is not None:
        document = get_reading_document(
            settings.database_path,
            user_id=user_id,
            document_id=request.source_document_id,
        )
        if document is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "DOCUMENT_NOT_FOUND",
                    "message": f"阅读文档 {request.source_document_id} 不存在。",
                    "details": {"document_id": request.source_document_id},
                },
            )

    return add_user_vocabulary_item(
        settings.database_path,
        user_id=user_id,
        text=request.text,
        meaning_zh=request.meaning_zh,
        usage_note=request.usage_note,
        ability=request.ability,
        source_document_id=request.source_document_id,
        source_context=request.source_context,
    )


@router.get("/vocabulary", response_model=UserVocabularyListResponse)
def list_vocabulary(
    settings: Settings = Depends(get_settings),
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
) -> UserVocabularyListResponse:
    _require_user(settings, user_id)
    return UserVocabularyListResponse(
        items=list_user_vocabulary_items(settings.database_path, user_id=user_id)
    )


@router.get("/vocabulary/export.csv")
def export_vocabulary_csv(
    settings: Settings = Depends(get_settings),
    user_id: int = Header(..., alias="X-LingoForge-User-Id"),
) -> Response:
    _require_user(settings, user_id)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["text", "meaning_zh", "usage_note", "ability", "source_context", "created_at"])
    for item in list_user_vocabulary_items(settings.database_path, user_id=user_id):
        writer.writerow([
            _safe_csv_cell(item["text"]),
            _safe_csv_cell(item.get("meaning_zh") or ""),
            _safe_csv_cell(item.get("usage_note") or ""),
            _safe_csv_cell(item.get("ability") or ""),
            _safe_csv_cell(item.get("source_context") or ""),
            _safe_csv_cell(item["created_at"]),
        ])
    return Response(
        content="\ufeff" + output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="lingoforge-vocabulary.csv"'},
    )


def _safe_csv_cell(value: str) -> str:
    if value and value[0] in ("=", "+", "-", "@"):
        return f"'{value}"
    return value
