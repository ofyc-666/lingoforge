"""英语分析请求与响应模型测试。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.api.learning_models import (
    ExerciseOption,
    ExerciseQuestion,
    KeywordAnalysis,
    TextAnalysisRequest,
    TextAnalysisResponse,
)


class TestTextAnalysisRequest:
    """TextAnalysisRequest 模型测试。"""

    def test_minimal_valid_request(self):
        """最小有效请求。"""
        req = TextAnalysisRequest(raw_text="The quick brown fox jumps over the lazy dog.")
        assert req.raw_text == "The quick brown fox jumps over the lazy dog."
        assert req.target_abilities == ["VOCABULARY_CONTEXT"]
        assert req.max_keywords == 5
        assert req.generate_exercise is True

    def test_empty_raw_text_rejected(self):
        """空 raw_text 校验失败。"""
        with pytest.raises(ValidationError):
            TextAnalysisRequest(raw_text="")
        with pytest.raises(ValidationError):
            TextAnalysisRequest(raw_text="   ")

    def test_whitespace_only_raw_text_rejected(self):
        """只含空格的 raw_text 校验失败。"""
        with pytest.raises(ValidationError):
            TextAnalysisRequest(raw_text="   \t  \n  ")

    def test_invalid_ability_rejected(self):
        """非法 ability 返回模型校验失败。"""
        with pytest.raises(ValidationError):
            TextAnalysisRequest(raw_text="Hello world.", target_abilities=["INVALID_ABILITY"])

    def test_max_keywords_out_of_range_rejected(self):
        """max_keywords 超出范围校验失败。"""
        with pytest.raises(ValidationError):
            TextAnalysisRequest(raw_text="Hello world.", max_keywords=0)
        with pytest.raises(ValidationError):
            TextAnalysisRequest(raw_text="Hello world.", max_keywords=13)

    def test_user_id_in_body_rejected(self):
        """请求体包含 user_id 校验失败。"""
        with pytest.raises(ValidationError):
            TextAnalysisRequest(raw_text="Hello world.", user_id=1)  # type: ignore[call-arg]

    def test_session_id_in_body_rejected(self):
        """请求体包含 session_id 校验失败。"""
        with pytest.raises(ValidationError):
            TextAnalysisRequest(raw_text="Hello world.", session_id=1)  # type: ignore[call-arg]

    def test_permission_scope_in_body_rejected(self):
        """请求体包含 permission_scope 校验失败。"""
        with pytest.raises(ValidationError):
            TextAnalysisRequest(raw_text="Hello world.", permission_scope="read")  # type: ignore[call-arg]


class TestKeywordAnalysis:
    """KeywordAnalysis 模型测试。"""

    def test_valid_keyword(self):
        kw = KeywordAnalysis(
            text="adapt",
            meaning_zh="适应",
            usage_note="常与 to 搭配。",
            ability="VOCABULARY_CONTEXT",
            selection_reason="高频考点。",
        )
        assert kw.text == "adapt"
        assert kw.meaning_zh == "适应"


    def test_invalid_keyword_ability_rejected(self):
        with pytest.raises(ValidationError):
            KeywordAnalysis(
                text="adapt",
                meaning_zh="适应",
                usage_note="",
                ability="INVALID_ABILITY",
                selection_reason="test",
            )


class TestExerciseOption:
    """ExerciseOption 模型测试。"""

    def test_valid_option(self):
        opt = ExerciseOption(id="A", text="adjust to")
        assert opt.id == "A"
        assert opt.text == "adjust to"


class TestExerciseQuestion:
    """ExerciseQuestion 模型测试。"""

    def test_valid_multiple_choice_question(self):
        q = ExerciseQuestion(
            question_id="q1",
            question_type="MULTIPLE_CHOICE",
            prompt="adapt 最接近哪一项？",
            options=[ExerciseOption(id="A", text="adjust to"), ExerciseOption(id="B", text="remove")],
            answer="A",
            explanation="adapt 表示适应。",
            target_ability="VOCABULARY_CONTEXT",
        )
        assert q.question_id == "q1"
        assert len(q.options) == 2


    def test_non_multiple_choice_question_type_rejected(self):
        with pytest.raises(ValidationError):
            ExerciseQuestion(
                question_id="q2",
                question_type="ESSAY",
                prompt="Write something.",
                options=[ExerciseOption(id="A", text="yes"), ExerciseOption(id="B", text="no")],
                answer="A",
                explanation="test",
                target_ability="VOCABULARY_CONTEXT",
            )

    def test_invalid_target_ability_rejected(self):
        with pytest.raises(ValidationError):
            ExerciseQuestion(
                question_id="q3",
                question_type="MULTIPLE_CHOICE",
                prompt="Choose one.",
                options=[ExerciseOption(id="A", text="yes"), ExerciseOption(id="B", text="no")],
                answer="A",
                explanation="test",
                target_ability="INVALID_ABILITY",
            )


class TestTextAnalysisResponse:
    """TextAnalysisResponse 模型测试。"""

    def test_full_response(self):
        resp = TextAnalysisResponse(
            analysis_id="analysis_abc",
            raw_text="The fox jumps.",
            keywords=[
                KeywordAnalysis(
                    text="fox",
                    meaning_zh="狐狸",
                    usage_note="常见名词。",
                    ability="VOCABULARY_CONTEXT",
                    selection_reason="文本关键词。",
                )
            ],
            exercise=ExerciseQuestion(
                question_id="q1",
                question_type="MULTIPLE_CHOICE",
                prompt="fox 的含义是？",
                options=[ExerciseOption(id="A", text="狐狸"), ExerciseOption(id="B", text="兔子")],
                answer="A",
                explanation="fox = 狐狸。",
                target_ability="VOCABULARY_CONTEXT",
            ),
            agent_feedback="先抓关键词，再看语境。",
            source="MOCK_DETERMINISTIC",
            warnings=[],
        )
        assert resp.analysis_id == "analysis_abc"
        assert resp.source == "MOCK_DETERMINISTIC"

    def test_exercise_null_when_not_generated(self):
        """无练习时 exercise 可为 None。"""
        resp = TextAnalysisResponse(
            analysis_id="analysis_abc",
            raw_text="The fox jumps.",
            keywords=[],
            exercise=None,
            agent_feedback="无关键词可分析。",
            source="MOCK_DETERMINISTIC",
            warnings=["文本过短，未找到可分析的关键词。"],
        )
        assert resp.exercise is None
        assert len(resp.warnings) == 1
