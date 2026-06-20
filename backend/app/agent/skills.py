"""MVP 教学 Skill 注册表。

当前只提供最小静态 Skill，用于 Agent 决策和 Context Manifest 引用。
Skill 不访问数据库、不判分、不写画像。
"""

from __future__ import annotations

from typing import Any


MVP_SKILL_VERSION = "1.0.0"


def list_skill_catalog() -> list[dict[str, Any]]:
    return [
        {
            "skill_id": "vocabulary_context",
            "version": MVP_SKILL_VERSION,
            "target_ability": "VOCABULARY_CONTEXT",
            "supported_task_types": ["LOW_PRESSURE_LEARNING", "SHORT_TRAINING"],
            "summary": "训练用户根据英文上下文判断词义，优先观察上下文线索和干扰项排除理由。",
            "estimated_tokens": 220,
            "status": "ACTIVE",
        }
    ]


def get_skill_definition(skill_id: str, version: str = MVP_SKILL_VERSION) -> dict[str, Any] | None:
    if skill_id != "vocabulary_context" or version != MVP_SKILL_VERSION:
        return None
    return {
        "skill_id": "vocabulary_context",
        "version": MVP_SKILL_VERSION,
        "target_ability": "VOCABULARY_CONTEXT",
        "input_contract": {
            "raw_text": "英文材料",
            "user_profile_slice": "可选的用户画像切片",
            "history_analysis": "可选的学习历史分析结果",
        },
        "output_contract": {
            "training_objective": "本轮训练目标",
            "exercise": "MULTIPLE_CHOICE 练习题",
            "expected_observations": "本题可观察的能力证据",
        },
        "generation_rules": [
            "题目必须能从原文上下文推出答案。",
            "干扰项应接近但可被上下文排除。",
            "反馈必须引用可观察表现，不伪造成绩趋势。",
        ],
        "common_error_types": ["VOCABULARY_CONTEXT_ERROR"],
        "quality_requirements": [
            "只使用 MULTIPLE_CHOICE。",
            "标准答案必须在 options 中。",
            "不得包含隔离测试题内容。",
        ],
    }
