"""刷题生成服务。

支持 TARGETED_PRACTICE（针对性训练）和 COMPREHENSIVE_SIMULATION（综合模拟）。
不调用 LLM 判分；生成内容经 task_validation 校验。
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any

from app.agent.skills import (
    get_skill_definition,
    get_skills_by_ability,
    get_skills_by_task_mode,
)
from app.constants import (
    Ability,
    PlanStatus,
    PracticeMode,
    TaskType,
)
from app.repositories.base import fetch_one
from app.repositories.daily_plan import (
    get_daily_plan,
    get_plan_vocabulary_items,
    update_plan_status,
)
from app.repositories.training import create_generated_task
from app.services.task_validation import validate_training_task_content


def start_practice(
    database_path: str | Path,
    *,
    user_id: int,
    plan_id: int,
    practice_mode: str = PracticeMode.TARGETED_PRACTICE,
    target_abilities: list[str] | None = None,
    max_questions: int = 5,
) -> dict[str, Any]:
    """根据计划生成刷题任务。

    返回包含题目列表的结构化结果。
    """
    # 校验计划归属
    plan = get_daily_plan(database_path, plan_id)
    if plan is None or plan["user_id"] != user_id:
        raise ValueError("PLAN_NOT_FOUND_OR_ACCESS_DENIED")

    # 获取计划词汇
    plan_vocab = get_plan_vocabulary_items(database_path, plan_id)

    # 获取计划选择的 Skill
    selected_skills = plan.get("selected_skills", [])
    if not selected_skills:
        # 回退：按实践模式加载
        selected_skills = get_skills_by_task_mode(practice_mode)

    # 按目标能力筛选 Skill
    if target_abilities:
        filtered_skills = []
        for skill in selected_skills:
            full = get_skill_definition(skill.get("skill_id", "")) if isinstance(skill, dict) else None
            if full and full.get("target_ability") in target_abilities:
                filtered_skills.append(skill)
        if filtered_skills:
            selected_skills = filtered_skills

    # TARGETED_PRACTICE: 1-2 Skill
    if practice_mode == PracticeMode.TARGETED_PRACTICE:
        selected_skills = selected_skills[:2]
    # COMPREHENSIVE_SIMULATION: 至少 2 个 Skill
    elif practice_mode == PracticeMode.COMPREHENSIVE_SIMULATION:
        if len(selected_skills) < 2:
            # 补充 Skill 到至少 2 个
            all_mode_skills = get_skills_by_task_mode(practice_mode)
            existing_ids = {s.get("skill_id", "") for s in selected_skills if isinstance(s, dict)}
            for s in all_mode_skills:
                if s["skill_id"] not in existing_ids:
                    selected_skills.append({"skill_id": s["skill_id"], "version": s["version"]})
                    existing_ids.add(s["skill_id"])
                if len(selected_skills) >= 4:
                    break
        selected_skills = selected_skills[:4]

    # 生成题目规格
    abilities = []
    for skill in selected_skills:
        sid = skill.get("skill_id", "") if isinstance(skill, dict) else ""
        full = get_skill_definition(sid)
        if full:
            abilities.append(full.get("target_ability", ""))

    if practice_mode == PracticeMode.TARGETED_PRACTICE:
        task_type = TaskType.TARGETED_PRACTICE
        instructions = "请针对薄弱能力进行专项训练。每小题标注 Skill、目标能力、错误类型和解释。"
    else:
        task_type = TaskType.COMPREHENSIVE_SIMULATION
        instructions = "一篇 CET-6 风格阅读材料，组合多个 Skill 考查点。每小题标注所属 Skill 和能力。"

    # 构建练习内容
    vocab_texts = [v.get("vocabulary_item_id") for v in plan_vocab]
    content = {
        "practice_mode": practice_mode,
        "instructions": instructions,
        "selected_skills": selected_skills,
        "target_abilities": abilities,
        "plan_vocabulary_ids": vocab_texts,
        "max_questions": max_questions,
        "questions": _generate_mock_questions(
            practice_mode, selected_skills, abilities, max_questions
        ),
    }

    # 质量校验
    validation = validate_training_task_content(content)

    # 创建生成任务
    task_id = create_generated_task(
        database_path,
        session_id=plan.get("session_id"),
        user_id=user_id,
        task_type=task_type,
        target_ability=",".join(abilities),
        content_json=content,
        quality_requirements={
            "practice_mode": practice_mode,
            "skill_count": len(selected_skills),
            "ability_count": len(set(abilities)),
        },
        quality_check_result=validation,
    )

    # 更新计划状态
    update_plan_status(database_path, plan_id, PlanStatus.PRACTICE_IN_PROGRESS)

    return {
        "plan_id": plan_id,
        "practice_mode": practice_mode,
        "task_id": task_id,
        "session_id": plan.get("session_id"),
        "target_abilities": list(set(abilities)),
        "selected_skills": selected_skills,
        "questions": content["questions"],
        "validation": validation,
        "message": f"已生成 {practice_mode} 练习，共 {len(content['questions'])} 题",
    }


def _generate_mock_questions(
    practice_mode: str,
    selected_skills: list[dict[str, Any]],
    abilities: list[str],
    max_questions: int,
) -> list[dict[str, Any]]:
    """生成 Mock 练习题（非 LLM 生成，供测试和演示）。

    在实际环境中，这部分由 Agent 根据 Skill 约束生成。
    """
    questions = []
    reading_passage = (
        "The rapid advancement of artificial intelligence has transformed numerous industries, "
        "from healthcare to finance. While some experts argue that automation will inevitably "
        "lead to job displacement, others contend that new opportunities will emerge in "
        "compensation. The debate largely hinges on whether societies can adapt their "
        "educational systems to prepare workers for an AI-driven economy."
    )

    for i in range(min(max_questions, len(selected_skills) * 2)):
        skill_idx = i % len(selected_skills)
        skill = selected_skills[skill_idx] if isinstance(selected_skills[skill_idx], dict) else {}
        skill_id = skill.get("skill_id", "unknown")
        ability = abilities[skill_idx] if skill_idx < len(abilities) else "VOCABULARY_CONTEXT"

        question_templates = {
            "vocabulary_context": {
                "prompt": f'根据上下文，"advancement" 在文中最接近哪一项？',
                "options": [
                    {"id": "A", "text": "进步；发展"},
                    {"id": "B", "text": "广告；宣传"},
                    {"id": "C", "text": "建议；忠告"},
                    {"id": "D", "text": "优势；利益"},
                ],
                "answer": "A",
                "explanation": "advancement 在此语境中指技术进步。",
            },
            "sentence_logic": {
                "prompt": "文中 While 引导的从句与主句之间是什么逻辑关系？",
                "options": [
                    {"id": "A", "text": "转折/让步"},
                    {"id": "B", "text": "因果"},
                    {"id": "C", "text": "递进"},
                    {"id": "D", "text": "并列"},
                ],
                "answer": "A",
                "explanation": "While 在此表示\"虽然...但是\"的让步转折关系。",
            },
            "paraphrase_location": {
                "prompt": "下列哪一项最能体现文中 \"lead to\" 的同义替换？",
                "options": [
                    {"id": "A", "text": "result in"},
                    {"id": "B", "text": "follow after"},
                    {"id": "C", "text": "guide toward"},
                    {"id": "D", "text": "walk into"},
                ],
                "answer": "A",
                "explanation": "lead to = result in，表示\"导致\"。",
            },
            "distractor_judgement": {
                "prompt": "关于 AI 对就业的影响，下列哪一项在文中被提及？",
                "options": [
                    {"id": "A", "text": "自动化将不可避免地导致就业替代"},
                    {"id": "B", "text": "某些专家认为新机会会出现以补偿损失"},
                    {"id": "C", "text": "AI 将在所有行业完全取代人类工人"},
                    {"id": "D", "text": "政府已经制定了完整的应对政策"},
                ],
                "answer": "B",
                "explanation": "B 对应原文 \"others contend that new opportunities will emerge in compensation\"。A 过度推断，C 范围扩大，D 无中生有。",
            },
        }

        template = question_templates.get(skill_id, question_templates["vocabulary_context"])
        questions.append({
            "question_id": f"pq{i + 1}",
            "skill_id": skill_id,
            "skill_version": skill.get("version", "1.0.0"),
            "target_ability": ability,
            "question_type": "MULTIPLE_CHOICE",
            "prompt": template["prompt"],
            "options": template["options"],
            "answer": template["answer"],
            "explanation": template["explanation"],
            "error_type_on_wrong": f"{ability}_ERROR",
            "source_passage": reading_passage if practice_mode == PracticeMode.COMPREHENSIVE_SIMULATION else "",
        })

    return questions
