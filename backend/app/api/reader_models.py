"""Reader workflow API models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.api.learning_models import KeywordAnalysis
from app.constants import is_valid_ability


class ReaderTextImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_text: str = Field(..., min_length=1)
    max_keywords: int = Field(default=8, ge=1, le=12)

    @model_validator(mode="after")
    def _raw_text_must_not_be_blank(self) -> "ReaderTextImportRequest":
        if not self.raw_text.strip():
            raise ValueError("raw_text 不能为空或全空白。")
        return self


class ReaderPdfImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_name: str = Field(default="import.pdf", min_length=1)
    content_base64: str = Field(..., min_length=1)
    max_keywords: int = Field(default=8, ge=1, le=12)

    @field_validator("file_name")
    @classmethod
    def _file_name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("file_name 不能为空或全空白。")
        return value.strip()


class ReaderImportResponse(BaseModel):
    document_id: int
    source_type: str
    file_name: str | None = None
    raw_text: str
    keywords: list[KeywordAnalysis]
    warnings: list[str] = Field(default_factory=list)


class UserVocabularyCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=1)
    meaning_zh: str = Field(..., min_length=1)
    usage_note: str = ""
    ability: str | None = None
    source_document_id: int | None = None
    source_context: str = ""

    @model_validator(mode="after")
    def _text_must_not_be_blank(self) -> "UserVocabularyCreateRequest":
        if not self.text.strip():
            raise ValueError("text 不能为空或全空白。")
        return self

    @field_validator("ability")
    @classmethod
    def _validate_ability(cls, value: str | None) -> str | None:
        if value is not None and not is_valid_ability(value):
            raise ValueError("ability 必须是合法能力维度。")
        return value


class UserVocabularyItemResponse(BaseModel):
    id: int
    user_id: int
    text: str
    meaning_zh: str | None = None
    usage_note: str = ""
    ability: str | None = None
    source_document_id: int | None = None
    source_context: str = ""
    created_at: str


class UserVocabularyListResponse(BaseModel):
    items: list[UserVocabularyItemResponse]
