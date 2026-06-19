"""英语分析确定性服务测试。"""

from __future__ import annotations

from app.api.learning_models import TextAnalysisRequest
from app.services.learning_analysis import analyze_english_text


class TestAnalyzeEnglishText:
    """analyze_english_text 确定性服务测试。"""

    def test_regular_paragraph_returns_keywords_and_exercise(self):
        request = TextAnalysisRequest(
            raw_text="Climate change is one of the most pressing challenges of our time. "
                     "Rising temperatures affect ecosystems and biodiversity across the globe.",
            target_abilities=["VOCABULARY_CONTEXT"],
            max_keywords=5,
            generate_exercise=True,
        )
        result = analyze_english_text(request)
        assert result.source == "MOCK_DETERMINISTIC"
        assert len(result.keywords) >= 1
        assert len(result.keywords) <= 5
        # 每个关键词有完整字段
        for kw in result.keywords:
            assert kw.text
            assert kw.meaning_zh
            assert kw.ability in ("VOCABULARY_CONTEXT", "SENTENCE_LOGIC", "PARAPHRASE_LOCATION", "DISTRACTOR_JUDGEMENT")
        # 有练习题
        assert result.exercise is not None
        assert result.exercise.question_type == "MULTIPLE_CHOICE"
        assert len(result.exercise.options) >= 2
        # agent_feedback 为中文模板
        assert result.agent_feedback
        assert len(result.agent_feedback) > 0

    def test_keywords_do_not_exceed_max_keywords(self):
        request = TextAnalysisRequest(
            raw_text="The cat sat on the mat. " * 20,
            target_abilities=["VOCABULARY_CONTEXT"],
            max_keywords=3,
            generate_exercise=False,
        )
        result = analyze_english_text(request)
        assert len(result.keywords) <= 3

    def test_generate_exercise_false_returns_null_exercise(self):
        request = TextAnalysisRequest(
            raw_text="Technology shapes the way people communicate and learn.",
            target_abilities=["VOCABULARY_CONTEXT"],
            max_keywords=5,
            generate_exercise=False,
        )
        result = analyze_english_text(request)
        assert result.exercise is None

    def test_short_text_returns_warnings(self):
        request = TextAnalysisRequest(
            raw_text="Hi.",
            target_abilities=["VOCABULARY_CONTEXT"],
            max_keywords=5,
            generate_exercise=False,
        )
        result = analyze_english_text(request)
        assert len(result.warnings) >= 1
        # 短文本可能没有有效关键词
        assert len(result.keywords) >= 0

    def test_source_is_always_mock_deterministic(self):
        request = TextAnalysisRequest(
            raw_text="Artificial intelligence is transforming industries worldwide.",
        )
        result = analyze_english_text(request)
        assert result.source == "MOCK_DETERMINISTIC"
        # agent_feedback 不声称来自真实 Agent
        assert "Agent" not in result.agent_feedback or "Mock" in result.agent_feedback

    def test_raw_text_preserved_in_response(self):
        text = "The quick brown fox."
        request = TextAnalysisRequest(raw_text=text)
        result = analyze_english_text(request)
        assert result.raw_text == text

    def test_returns_analysis_id(self):
        request = TextAnalysisRequest(raw_text="Hello world example text here.")
        result = analyze_english_text(request)
        assert result.analysis_id.startswith("analysis_")

    def test_no_keywords_for_very_short_tokens_only(self):
        """全是短词时可能返回空 keywords 且带 warning。"""
        request = TextAnalysisRequest(
            raw_text="a an the is at on in",
            target_abilities=["VOCABULARY_CONTEXT"],
            max_keywords=5,
            generate_exercise=False,
        )
        result = analyze_english_text(request)
        # 应该产出 warnings
        assert len(result.warnings) >= 1

    def test_multiple_abilities_accepted(self):
        """接受多个 target_abilities。"""
        request = TextAnalysisRequest(
            raw_text="The research demonstrates a significant correlation between variables.",
            target_abilities=["VOCABULARY_CONTEXT", "SENTENCE_LOGIC"],
            max_keywords=4,
            generate_exercise=True,
        )
        result = analyze_english_text(request)
        assert result.source == "MOCK_DETERMINISTIC"
        # 关键词 ability 应属于指定能力之一
        for kw in result.keywords:
            assert kw.ability in ("VOCABULARY_CONTEXT", "SENTENCE_LOGIC")
