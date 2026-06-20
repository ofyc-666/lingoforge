"""MVP 教学 Skill 注册表。

提供 4 类版本化 CET-6 阅读 Skill：
  1. vocabulary_context   —— 词汇语境识别
  2. sentence_logic       —— 长难句与逻辑关系
  3. paraphrase_location  —— 同义替换与定位
  4. distractor_judgement —— 干扰项判断

每个 Skill 定义 target_ability、supported_task_types、applicable_conditions、
difficulty_params、generation_rules、quality_requirements、observable_evidence、
common_error_types。

Skill 不访问数据库、不判分、不写画像。
"""

from __future__ import annotations

from typing import Any

MVP_SKILL_VERSION = "1.0.0"

# --------------- Skill 目录（紧凑摘要，供 Context Expansion） ---------------

SKILL_CATALOG: list[dict[str, Any]] = [
    {
        "skill_id": "vocabulary_context",
        "version": MVP_SKILL_VERSION,
        "target_ability": "VOCABULARY_CONTEXT",
        "supported_task_types": [
            "LOW_PRESSURE_LEARNING", "SHORT_TRAINING",
        ],
        "summary": "训练用户根据英文上下文判断词义，优先观察上下文线索和干扰项排除理由。",
        "estimated_tokens": 280,
        "status": "ACTIVE",
    },
    {
        "skill_id": "sentence_logic",
        "version": MVP_SKILL_VERSION,
        "target_ability": "SENTENCE_LOGIC",
        "supported_task_types": [
            "LOW_PRESSURE_LEARNING", "SHORT_TRAINING",
        ],
        "summary": "训练理解长句主干、修饰成分、指代关系和句间逻辑（转折/因果/递进/对比）。",
        "estimated_tokens": 300,
        "status": "ACTIVE",
    },
    {
        "skill_id": "paraphrase_location",
        "version": MVP_SKILL_VERSION,
        "target_ability": "PARAPHRASE_LOCATION",
        "supported_task_types": [
            "LOW_PRESSURE_LEARNING", "SHORT_TRAINING",
        ],
        "summary": "训练题干/选项与原文之间的同义替换识别和原文定位能力。",
        "estimated_tokens": 310,
        "status": "ACTIVE",
    },
    {
        "skill_id": "distractor_judgement",
        "version": MVP_SKILL_VERSION,
        "target_ability": "DISTRACTOR_JUDGEMENT",
        "supported_task_types": [
            "LOW_PRESSURE_LEARNING", "SHORT_TRAINING",
        ],
        "summary": "训练识别 CET-6 阅读常见干扰项模式（过度推断/偷换概念/范围变化/无中生有）。",
        "estimated_tokens": 320,
        "status": "ACTIVE",
    },
]


def list_skill_catalog() -> list[dict[str, Any]]:
    return SKILL_CATALOG


def get_skill_definition(skill_id: str, version: str = MVP_SKILL_VERSION) -> dict[str, Any] | None:
    """获取 Skill 完整定义（全文加载）。"""
    definitions: dict[str, dict[str, Any]] = {
        "vocabulary_context": _vocabulary_context_skill(),
        "sentence_logic": _sentence_logic_skill(),
        "paraphrase_location": _paraphrase_location_skill(),
        "distractor_judgement": _distractor_judgement_skill(),
    }
    skill = definitions.get(skill_id)
    if skill is None:
        return None
    if skill.get("version") != version:
        return None
    return skill


def skill_exists(skill_id: str, version: str = MVP_SKILL_VERSION) -> bool:
    return get_skill_definition(skill_id, version) is not None


def get_skills_by_ability(target_ability: str) -> list[dict[str, Any]]:
    """按目标能力获取匹配的 Skill。"""
    results = []
    for skill in SKILL_CATALOG:
        if skill["target_ability"] == target_ability and skill["status"] == "ACTIVE":
            full = get_skill_definition(skill["skill_id"])
            if full:
                results.append(full)
    return results


def get_skills_by_task_mode(practice_mode: str) -> list[dict[str, Any]]:
    """按训练模式获取支持的 Skill。"""
    results = []
    for skill in SKILL_CATALOG:
        if practice_mode in skill["supported_task_types"] and skill["status"] == "ACTIVE":
            full = get_skill_definition(skill["skill_id"])
            if full:
                results.append(full)
    return results


# --------------- Skill 完整定义 ---------------

def _vocabulary_context_skill() -> dict[str, Any]:
    return {
        "skill_id": "vocabulary_context",
        "version": MVP_SKILL_VERSION,
        "target_ability": "VOCABULARY_CONTEXT",
        "supported_task_types": [
            "LOW_PRESSURE_LEARNING", "SHORT_TRAINING",
        ],
        "applicable_conditions": {
            "profile_indicators": [
                "VOCABULARY_CONTEXT 能力评级为 beginner 或 intermediate",
                "用户频繁点击释义",
                "用户在上下文中误解词义",
                "prompt_dependency 标记为 HIGH",
            ],
            "task_scenarios": [
                "主线训练中需要巩固目标词汇",
                "候选池中存在 NEW 或 WEAK 词汇",
                "针对性训练目标为词汇语境识别",
            ],
        },
        "difficulty_params": {
            "target_word_count": {"min": 2, "max": 10, "default": 5},
            "context_explicitness": {"levels": ["HIGH", "MEDIUM", "LOW"], "default": "MEDIUM"},
            "include_rare_meaning": {"type": "boolean", "default": False},
            "include_collocations": {"type": "boolean", "default": True},
            "hint_level": {"levels": ["HIGH", "MEDIUM", "LOW", "NONE"], "default": "MEDIUM"},
        },
        "generation_rules": [
            "词义判断必须依赖上下文线索，不能只考词典释义。",
            "目标词必须自然嵌入 CET-6 风格阅读材料中。",
            "干扰项可来自常见近义词、脱离语境释义或错误搭配。",
            "正确选项不应只是原文的简单复制。",
            "每道题目标能力标记为 VOCABULARY_CONTEXT。",
        ],
        "quality_requirements": [
            "目标词实际出现在材料中。",
            "目标词语境支持标准答案。",
            "客观题答案唯一。",
            "干扰项与错误类型对应。",
            "题目不依赖未提供背景知识。",
        ],
        "observable_evidence": [
            "用户能否根据上下文正确判断词义",
            "用户是否混淆近义词",
            "用户是否依赖提示",
            "用户是否能排除不符合语境的选项",
        ],
        "common_error_types": [
            "VOCABULARY_CONTEXT_ERROR",
            "IGNORING_CONTEXT_CLUES",
            "SURFACE_MEANING_ONLY",
            "NEAR_SYNONYM_CONFUSION",
            "COLLOCATION_MISMATCH",
        ],
        "source_provenance": "CET-6 style distilled rules",
        "status": "ACTIVE",
    }


def _sentence_logic_skill() -> dict[str, Any]:
    return {
        "skill_id": "sentence_logic",
        "version": MVP_SKILL_VERSION,
        "target_ability": "SENTENCE_LOGIC",
        "supported_task_types": [
            "LOW_PRESSURE_LEARNING", "SHORT_TRAINING",
        ],
        "applicable_conditions": {
            "profile_indicators": [
                "SENTENCE_LOGIC 能力评级为 beginner 或 intermediate",
                "用户能认识词但理解句意失败",
                "用户频繁使用句子提示或拆解",
                "用户在逻辑关系相关题目中出错",
            ],
            "task_scenarios": [
                "阅读材料中包含影响理解的复杂句",
                "针对性训练目标为长难句与逻辑关系",
            ],
        },
        "difficulty_params": {
            "sentence_length": {"min": 15, "max": 60, "default": 30},
            "clause_count": {"min": 1, "max": 4, "default": 2},
            "embedding_depth": {"min": 0, "max": 3, "default": 1},
            "anaphora_distance": {"min": 1, "max": 5, "default": 2},
            "connector_explicitness": {"levels": ["EXPLICIT", "IMPLICIT"], "default": "EXPLICIT"},
            "hint_level": {"levels": ["HIGH", "MEDIUM", "LOW", "NONE"], "default": "MEDIUM"},
        },
        "generation_rules": [
            "训练应围绕影响理解和答题的句法或逻辑关系。",
            "不做纯语法术语测试。",
            "题目应要求用户利用句间关系或句子主干判断含义。",
            "干扰项可利用转折前信息、因果倒置、指代误解或范围误判。",
            "每道题目标能力标记为 SENTENCE_LOGIC。",
        ],
        "quality_requirements": [
            "被训练句子确实包含目标结构或逻辑关系。",
            "讲解能区分主干与修饰。",
            "客观题答案唯一。",
            "答案依据可回指材料。",
            "干扰项与常见误解对应。",
        ],
        "observable_evidence": [
            "用户能否正确理解长句主干",
            "用户能否识别转折/因果/递进等逻辑关系",
            "用户能否正确解析指代关系",
            "用户是否被修饰信息误导",
        ],
        "common_error_types": [
            "SENTENCE_LOGIC_ERROR",
            "MISSING_MAIN_CLAUSE",
            "IGNORING_LOGICAL_CONNECTOR",
            "CAUSALITY_REVERSAL",
            "ANAPHORA_MISMATCH",
        ],
        "source_provenance": "CET-6 style distilled rules",
        "status": "ACTIVE",
    }


def _paraphrase_location_skill() -> dict[str, Any]:
    return {
        "skill_id": "paraphrase_location",
        "version": MVP_SKILL_VERSION,
        "target_ability": "PARAPHRASE_LOCATION",
        "supported_task_types": [
            "LOW_PRESSURE_LEARNING", "SHORT_TRAINING",
        ],
        "applicable_conditions": {
            "profile_indicators": [
                "PARAPHRASE_LOCATION 能力评级为 beginner 或 intermediate",
                "用户能看懂原文局部但找不到答案位置",
                "用户无法识别题干或选项的同义改写",
                "用户在细节题、推断题中失误",
            ],
            "task_scenarios": [
                "第二次自适应短训练需要强化真题风格迁移",
                "针对性训练目标为同义替换与定位",
            ],
        },
        "difficulty_params": {
            "locate_span": {"min": 1, "max": 5, "default": 2},
            "paraphrase_abstractness": {"levels": ["LOW", "MEDIUM", "HIGH"], "default": "MEDIUM"},
            "surface_overlap": {"levels": ["HIGH", "MEDIUM", "LOW"], "default": "LOW"},
            "distractor_plausibility": {"levels": ["LOW", "MEDIUM", "HIGH"], "default": "MEDIUM"},
            "hint_level": {"levels": ["HIGH", "MEDIUM", "LOW", "NONE"], "default": "MEDIUM"},
        },
        "generation_rules": [
            "正确选项不应只是复制原文，必须体现改写关系。",
            "题干和答案依据之间应存在可解释的改写关系。",
            "干扰项可使用原文词面、相邻信息或局部正确但整体错误的信息。",
            "定位线索必须客观存在于材料中。",
            "每道题目标能力标记为 PARAPHRASE_LOCATION。",
        ],
        "quality_requirements": [
            "题干存在可定位线索。",
            "正确答案与原文有可解释同义替换。",
            "干扰项不是无关乱造。",
            "答案唯一。",
            "答案依据可回指材料。",
        ],
        "observable_evidence": [
            "用户能否根据题干线索定位原文",
            "用户能否识别同义替换",
            "用户是否被原文词面重复的干扰项吸引",
            "用户是否能区分局部正确与整体正确",
        ],
        "common_error_types": [
            "PARAPHRASE_LOCATION_ERROR",
            "SURFACE_MATCH_DISTRACTOR",
            "ADJACENT_LOCATION_ERROR",
            "IGNORING_QUESTION_CONSTRAINT",
            "PARTIAL_MATCH_MISTAKE",
        ],
        "source_provenance": "CET-6 style distilled rules",
        "status": "ACTIVE",
    }


def _distractor_judgement_skill() -> dict[str, Any]:
    return {
        "skill_id": "distractor_judgement",
        "version": MVP_SKILL_VERSION,
        "target_ability": "DISTRACTOR_JUDGEMENT",
        "supported_task_types": [
            "LOW_PRESSURE_LEARNING", "SHORT_TRAINING",
        ],
        "applicable_conditions": {
            "profile_indicators": [
                "DISTRACTOR_JUDGEMENT 能力评级为 beginner 或 intermediate",
                "用户能定位原文但选错",
                "用户经常在两个选项间犹豫",
                "用户容易被看似相关的信息误导",
            ],
            "task_scenarios": [
                "训练目标从理解材料转向提高选项判断质量",
                "针对性训练目标为干扰项判断",
            ],
        },
        "difficulty_params": {
            "option_count": {"min": 3, "max": 5, "default": 4},
            "distractor_relevance": {"levels": ["LOW", "MEDIUM", "HIGH"], "default": "HIGH"},
            "pattern_complexity": {"levels": ["SINGLE", "MIXED"], "default": "SINGLE"},
            "option_variance": {"levels": ["LOW", "MEDIUM", "HIGH"], "default": "MEDIUM"},
            "hint_level": {"levels": ["HIGH", "MEDIUM", "LOW", "NONE"], "default": "LOW"},
        },
        "generation_rules": [
            "干扰项应来自真实阅读题常见错误模式。",
            "错误选项必须有迷惑性，但必须可被材料证据排除。",
            "不允许靠常识争议排除。",
            "不允许多个选项都可成立。",
            "每道题目标能力标记为 DISTRACTOR_JUDGEMENT，并辅以可标注的错误模式。",
        ],
        "quality_requirements": [
            "正确答案唯一。",
            "每个干扰项都有明确错误依据。",
            "干扰项属于可标注模式（过度推断/偷换概念/范围变化/无中生有/张冠李戴）。",
            "题目不依赖材料之外的主观判断。",
            "答案解释能说明为什么其他选项错。",
        ],
        "observable_evidence": [
            "用户能否识别错误选项的模式",
            "用户是否在两个选项间犹豫超过阈值",
            "用户是否列出排除理由",
            "用户是否能指出每个错误选项的具体问题",
        ],
        "common_error_types": [
            "DISTRACTOR_JUDGEMENT_ERROR",
            "OVER_INFERENCE",
            "CONCEPT_SWITCH",
            "SCOPE_EXPANSION",
            "SCOPE_REDUCTION",
            "FABRICATION",
            "MISATTRIBUTION",
        ],
        "source_provenance": "CET-6 style distilled rules",
        "status": "ACTIVE",
    }


# --------------- 种子 Skill 到数据库 ---------------

def seed_skill_versions(database_path: str | Path) -> dict[str, int]:
    """将 4 个 Skill 版本幂等写入 skill_versions 表。"""
    from app.repositories.vocabulary import create_skill_version, get_skill_version

    created = 0
    skipped = 0
    for skill in SKILL_CATALOG:
        skill_id = skill["skill_id"]
        version = skill["version"]
        existing = get_skill_version(database_path, skill_id, version)
        if existing is not None:
            skipped += 1
            continue
        full = get_skill_definition(skill_id, version)
        if full is None:
            continue
        create_skill_version(
            database_path,
            skill_id=full["skill_id"],
            version=full["version"],
            target_ability=full["target_ability"],
            applicable_conditions=full.get("applicable_conditions", {}),
            difficulty_params=full.get("difficulty_params", {}),
            generation_rules=full.get("generation_rules", []),
            quality_requirements=full.get("quality_requirements", []),
            observable_evidence=full.get("observable_evidence", []),
            common_error_types=full.get("common_error_types", []),
        )
        created += 1
    return {"created": created, "skipped": skipped}
