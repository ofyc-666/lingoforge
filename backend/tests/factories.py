"""测试数据工厂。

为 API 和 Service 测试提供可复用的测试数据创建 helper。
只服务测试，不被生产代码导入。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.database import init_database
from app.repositories.training import create_generated_task, create_training_session, get_generated_task
from app.repositories.users import create_user


def create_user_with_session(
    db_path: str | Path,
    *,
    stage: str = "FIRST_MAIN",
    display_name: str = "测试用户",
) -> dict[str, Any]:
    """创建测试用户和训练会话。

    Returns:
        {"user_id": int, "session_id": int, "db_path": str}
    """
    user_id = create_user(db_path, display_name)
    session_id = create_training_session(db_path, user_id=user_id, stage=stage, status="IN_PROGRESS")
    return {"user_id": user_id, "session_id": session_id}


_MULTIPLE_CHOICE_CONTENT: dict[str, Any] = {
    "title": "词汇语境练习",
    "raw_text": "Climate change is a pressing challenge for ecosystems worldwide.",
    "instructions": "请选择最符合语境的答案。",
    "questions": [
        {
            "question_id": "q1",
            "question_type": "MULTIPLE_CHOICE",
            "prompt": "climate 最接近哪一项？",
            "options": [
                {"id": "A", "text": "气候"},
                {"id": "B", "text": "变化"},
                {"id": "C", "text": "挑战"},
                {"id": "D", "text": "适应"},
            ],
            "answer": "A",
            "explanation": "climate 意为气候。",
            "target_ability": "VOCABULARY_CONTEXT",
            "error_type_on_wrong": "VOCABULARY_CONTEXT_ERROR",
        },
        {
            "question_id": "q2",
            "question_type": "MULTIPLE_CHOICE",
            "prompt": "ecosystems 最接近哪一项？",
            "options": [
                {"id": "A", "text": "经济"},
                {"id": "B", "text": "生态系统"},
                {"id": "C", "text": "设备"},
                {"id": "D", "text": "展览"},
            ],
            "answer": "B",
            "explanation": "ecosystems 意为生态系统。",
            "target_ability": "VOCABULARY_CONTEXT",
            "error_type_on_wrong": "VOCABULARY_CONTEXT_ERROR",
        },
    ],
    "agent_feedback": "",
    "source": "TEST_FACTORY",
}


def create_multiple_choice_task(
    db_path: str | Path,
    *,
    user_id: int,
    session_id: int,
) -> int:
    """创建一个包含两道 MULTIPLE_CHOICE 题的训练任务，返回 task_id。"""
    return create_generated_task(
        db_path,
        session_id=session_id,
        user_id=user_id,
        task_type="LOW_PRESSURE_LEARNING",
        target_ability="VOCABULARY_CONTEXT",
        content_json=_MULTIPLE_CHOICE_CONTENT,
        quality_check_result={"status": "PASSED"},
    )
