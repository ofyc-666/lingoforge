"""确定性英语文本分析服务。

使用确定性规则从英文文本中抽取关键词、生成中文释义和练习题。
不调用 LLM，不访问数据库。
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from app.api.learning_models import (
    ExerciseOption,
    ExerciseQuestion,
    KeywordAnalysis,
    TextAnalysisRequest,
    TextAnalysisResponse,
)

# ------ 小型内置词典 ------
_BUILTIN_DICT: dict[str, tuple[str, str]] = {
    "climate": ("气候", "常与 change、warming 搭配，表示气候状况或变化。"),
    "change": ("变化/改变", "用途广泛，可作动词或名词。"),
    "pressing": ("紧迫的", "形容词，常修饰 issue、challenge、need。"),
    "challenge": ("挑战", "可作名词或动词，搭配 face、meet、pose。"),
    "temperature": ("温度", "常见搭配：rising/high/low temperatures。"),
    "ecosystem": ("生态系统", "常与 biodiversity、habitat、balance 连用。"),
    "biodiversity": ("生物多样性", "学术词汇，常在环境类文章中出现。"),
    "technology": ("技术", "常见搭配：shapes、drives、advances、digital technology。"),
    "communicate": ("交流", "常与 with、effectively 搭配。"),
    "learn": ("学习", "可作及物或不及物动词。"),
    "artificial": ("人工的", "常见搭配：artificial intelligence、artificial light。"),
    "intelligence": ("智能/情报", "常用搭配：artificial intelligence、intelligence agency。"),
    "transform": ("转变/改造", "常见搭配：transform into、transform industries。"),
    "industry": ("行业/工业", "常见搭配：industries worldwide、manufacturing industry。"),
    "worldwide": ("全球", "副词或形容词，相当于 globally。"),
    "research": ("研究", "可作名词或动词，搭配 conduct、demonstrate、research on。"),
    "demonstrate": ("展示/证明", "常见搭配：demonstrate a correlation、demonstrate skills。"),
    "significant": ("显著的/重大的", "常见搭配：significant correlation/impact/difference。"),
    "correlation": ("相关性", "学术词汇，常与 between、significant 搭配。"),
    "variable": ("变量", "数学/统计用语，常与 dependent、independent 搭配。"),
    "adapt": ("适应", "常与 to 搭配，表示适应环境或变化。"),
    "biology": ("生物学", "常见搭配：molecular biology、biology research。"),
    "context": ("语境/上下文", "常见搭配：in context、context clue。"),
    "vocabulary": ("词汇", "语言学习核心词，搭配 build、expand、vocabulary list。"),
    "fox": ("狐狸", "一种犬科动物。"),
    "brown": ("棕色的", "颜色形容词。"),
    "lazy": ("懒惰的", "形容词。"),
    "dog": ("狗", "常见家养动物。"),
    "cat": ("猫", "常见家养动物。"),
    "mat": ("垫子", "常见家具用品。"),
}

# 英文 token 正则（至少 3 个字母）
_TOKEN_RE = re.compile(r"\b[a-zA-Z]{3,}\b")

# 常见功能词（停用词）
_STOP_WORDS: frozenset[str] = frozenset({
    "the", "and", "for", "are", "was", "has", "had", "its", "all",
    "not", "but", "his", "her", "who", "how", "can", "did", "she",
    "him", "our", "out", "its", "may", "too", "any", "does",
    "will", "with", "from", "that", "this", "have", "been", "their",
    "these", "those", "which", "than", "them", "into", "through",
    "also", "over", "what", "when", "where", "would", "could",
    "most", "very", "than", "more", "some", "like", "just", "then",
    "each", "such", "only", "other", "they", "about", "after", "still",
    "make", "well", "much", "being", "even", "without",
})


def _extract_english_tokens(text: str) -> list[str]:
    """从文本中提取英文 token（>=3 字母、非停用词、去重保序）。"""
    tokens = _TOKEN_RE.findall(text.lower())
    seen: set[str] = set()
    result: list[str] = []
    for t in tokens:
        if t not in _STOP_WORDS and t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _lookup_meaning(token: str) -> tuple[str, str]:
    """查词典，返回 (meaning_zh, usage_note)。"""
    if token in _BUILTIN_DICT:
        return _BUILTIN_DICT[token]
    return ("待学习词汇", "词汇待后续教学 Skill 补充释义。")


def _pick_ability(abilities: list[str], index: int) -> str:
    """从 abilities 列表中轮选能力维度。"""
    return abilities[index % len(abilities)] if abilities else "VOCABULARY_CONTEXT"


def _generate_multiple_choice(keyword: KeywordAnalysis, raw_text: str) -> ExerciseQuestion:
    """基于关键词生成一道 MULTIPLE_CHOICE 练习题。"""
    # 生成干扰项（简单词典翻找）
    distractors = [
        w for w, _ in _BUILTIN_DICT.items()
        if w != keyword.text and w[:2] != keyword.text[:2]
    ][:3]
    if len(distractors) < 3:
        distractors = ["option_x", "option_y", "option_z"]

    correct_id = "A"
    options = [ExerciseOption(id="A", text=keyword.meaning_zh)]
    for i, w in enumerate(distractors):
        letter = chr(ord("B") + i)
        d_meaning = _BUILTIN_DICT.get(w, ("未知", ""))[0]
        options.append(ExerciseOption(id=letter, text=d_meaning if d_meaning != "未知" else f"选项 {letter}"))

    return ExerciseQuestion(
        question_id="q1",
        question_type="MULTIPLE_CHOICE",
        prompt=f'根据原文语境，"{keyword.text}" 最接近哪一项？',
        options=options,
        answer=correct_id,
        explanation=f'"{keyword.text}" 在文中表示"{keyword.meaning_zh}"。{keyword.usage_note}',
        target_ability=keyword.ability,
    )


def analyze_english_text(request: TextAnalysisRequest) -> TextAnalysisResponse:
    """确定性英语文本分析。"""
    warnings: list[str] = []
    tokens = _extract_english_tokens(request.raw_text)

    if len(tokens) == 0:
        warnings.append("文本过短，未找到可用于分析的关键词。请提供更长的英文段落。")

    elif len(tokens) < 3:
        warnings.append(f"只找到 {len(tokens)} 个候选词，文本较短，分析结果可能不充分。")

    if len(request.raw_text.strip()) < 20:
        warnings.append("输入文本较短，建议提供更完整的英文段落以获得更准确的分析。")

    max_kw = min(request.max_keywords, len(tokens))
    keywords: list[KeywordAnalysis] = []
    for i, token in enumerate(tokens[:max_kw]):
        meaning, note = _lookup_meaning(token)
        ability = _pick_ability(request.target_abilities, i)
        keywords.append(KeywordAnalysis(
            text=token,
            meaning_zh=meaning,
            usage_note=note,
            ability=ability,
            selection_reason=f"文本中出现的关键词，适合训练{ability}。",
        ))

    exercise: ExerciseQuestion | None = None
    if request.generate_exercise and keywords:
        exercise = _generate_multiple_choice(keywords[0], request.raw_text)

    analysis_id = f"analysis_{uuid.uuid4().hex[:12]}"
    agent_feedback = (
        "这段材料可先抓关键词把握大意，再回到句子判断具体词义和上下文逻辑关系。"
        "（注意：此为 Mock 确定性分析反馈，不来自 Agent 实时决策。）"
    )

    return TextAnalysisResponse(
        analysis_id=analysis_id,
        raw_text=request.raw_text,
        keywords=keywords,
        exercise=exercise,
        agent_feedback=agent_feedback,
        source="MOCK_DETERMINISTIC",
        warnings=warnings,
    )
