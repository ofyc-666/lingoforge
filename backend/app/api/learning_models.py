"""英语分析请求与响应模型。

Pydantic v2 模型，字段与 docs/IMPLEMENTATION_CONTRACTS.md 第 2 节一致。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.constants import _ABILITY_VALUES, is_valid_ability


class ExerciseOption(BaseModel):
    """练习题选项。"""

    id: str = Field(..., min_length=1, description="选项标识，如 A/B/C/D")
    text: str = Field(..., min_length=1, description="选项文本")


class ExerciseQuestion(BaseModel):
    """练习题（MVP 仅 MULTIPLE_CHOICE）。"""

    question_id: str = Field(..., min_length=1)
    question_type: Literal["MULTIPLE_CHOICE"] = "MULTIPLE_CHOICE"
    prompt: str = Field(..., min_length=1)
    options: list[ExerciseOption] = Field(..., min_length=2)
    answer: str = Field(..., min_length=1)
    explanation: str = Field(..., min_length=1)
    target_ability: str = Field(..., min_length=1)

    @field_validator("target_ability")
    @classmethod
    def _validate_target_ability(cls, value: str) -> str:
        if not is_valid_ability(value):
            raise ValueError(f"target_ability 必须是合法能力维度：{sorted(_ABILITY_VALUES)}")
        return value


class KeywordAnalysis(BaseModel):
    """单个关键词分析结果。"""

    text: str = Field(..., min_length=1, description="英文关键词")
    meaning_zh: str = Field(..., min_length=1, description="中文释义")
    usage_note: str = Field(default="", description="用法说明")
    ability: str = Field(..., min_length=1, description="所属能力维度")
    selection_reason: str = Field(default="", description="选取理由")

    @field_validator("ability")
    @classmethod
    def _validate_ability(cls, value: str) -> str:
        if not is_valid_ability(value):
            raise ValueError(f"ability 必须是合法能力维度：{sorted(_ABILITY_VALUES)}")
        return value


class TextAnalysisRequest(BaseModel):
    """文本分析请求体。"""

    model_config = ConfigDict(extra="forbid")

    raw_text: str = Field(..., min_length=1)
    target_abilities: list[str] = Field(default_factory=lambda: ["VOCABULARY_CONTEXT"])
    max_keywords: int = Field(default=5, ge=1, le=12)
    generate_exercise: bool = Field(default=True)

    @model_validator(mode="after")
    def _raw_text_must_not_be_blank(self) -> "TextAnalysisRequest":
        if not self.raw_text.strip():
            raise ValueError("raw_text 不能为空或全空白。")
        return self

    @model_validator(mode="after")
    def _validate_target_abilities(self) -> "TextAnalysisRequest":
        for ability in self.target_abilities:
            if ability not in _ABILITY_VALUES:
                raise ValueError(
                    f"target_abilities 中包含非法值 '{ability}'，"
                    f"必须为 {sorted(_ABILITY_VALUES)} 之一。"
                )
        return self


class TextAnalysisResponse(BaseModel):
    """文本分析响应体。"""

    analysis_id: str = Field(..., min_length=1)
    raw_text: str = Field(..., min_length=1)
    keywords: list[KeywordAnalysis] = Field(default_factory=list)
    exercise: ExerciseQuestion | None = Field(default=None)
    agent_feedback: str = Field(default="")
    source: str = Field(default="MOCK_DETERMINISTIC")
    warnings: list[str] = Field(default_factory=list)
