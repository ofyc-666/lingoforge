"""演示数据种子脚本。

可重复运行，创建演示用户、目标、画像、词汇、会话和可提交训练任务。
不调用 Agent 或 DeepSeek，不写入真实 API Key。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 将 backend 加入路径
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent / "backend"
sys.path.insert(0, str(_BACKEND))

from app.database import init_database
from app.repositories.training import create_generated_task, create_training_session
from app.repositories.users import create_profile_snapshot, create_user, save_user_goal
from app.repositories.vocabulary import create_vocabulary_item


def seed(database_path: str) -> None:
    init_database(database_path)

    # 1. 创建演示用户
    user_id = create_user(database_path, "演示用户")
    print(f"用户: user_id={user_id}")

    # 2. 创建用户目标
    goal_id = save_user_goal(
        database_path,
        user_id=user_id,
        exam_type="CET-6",
        days_until_exam=90,
        target_score=550,
        daily_minutes=30,
        self_reported_weaknesses=["VOCABULARY_CONTEXT", "SENTENCE_LOGIC"],
        interest_topics=["科技", "环境"],
    )
    print(f"用户目标: goal_id={goal_id}")

    # 3. 创建初始画像快照
    profile = {
        "VOCABULARY_CONTEXT": {"level": "intermediate", "confidence": "MEDIUM"},
        "SENTENCE_LOGIC": {"level": "beginner", "confidence": "LOW"},
        "PARAPHRASE_LOCATION": {"level": "intermediate", "confidence": "MEDIUM"},
        "DISTRACTOR_JUDGEMENT": {"level": "beginner", "confidence": "LOW"},
    }
    snapshot_id = create_profile_snapshot(
        database_path,
        user_id=user_id,
        source="DIAGNOSTIC",
        profile=profile,
        evidence_refs=[],
    )
    print(f"画像快照: snapshot_id={snapshot_id}")

    # 4. 创建词汇
    vocab_items = [
        ("climate", "气候", "CET6_VOCAB"),
        ("ecosystem", "生态系统", "CET6_VOCAB"),
        ("biodiversity", "生物多样性", "CET6_VOCAB"),
        ("sustainable", "可持续的", "CET6_VOCAB"),
        ("adapt", "适应", "CET6_VOCAB"),
        ("transform", "转变", "CET6_VOCAB"),
        ("significant", "显著的", "CET6_VOCAB"),
        ("correlation", "相关性", "CET6_VOCAB"),
    ]
    vocab_ids = []
    for text, meaning, source_type in vocab_items:
        vid = create_vocabulary_item(
            database_path,
            text=text,
            meaning_zh=meaning,
            source_type=source_type,
            tags=["CET-6", "demo"],
        )
        vocab_ids.append(vid)
    print(f"词汇: 已创建 {len(vocab_ids)} 条词汇")

    # 5. 创建训练会话
    session_id = create_training_session(
        database_path,
        user_id=user_id,
        stage="FIRST_MAIN",
        status="IN_PROGRESS",
    )
    print(f"训练会话: session_id={session_id}")

    # 6. 创建可提交训练任务
    content = {
        "title": "词汇语境练习 - 环境主题",
        "raw_text": "Climate change is one of the most pressing challenges of our time. "
                     "Rising temperatures affect ecosystems and biodiversity around the globe. "
                     "Scientists emphasize the need for sustainable solutions.",
        "instructions": "请根据原文语境选择最符合词义的答案。",
        "questions": [
            {
                "question_id": "q1",
                "question_type": "MULTIPLE_CHOICE",
                "prompt": '"climate" 在文中最接近哪一项？',
                "options": [
                    {"id": "A", "text": "气候"},
                    {"id": "B", "text": "环境"},
                    {"id": "C", "text": "天气"},
                    {"id": "D", "text": "温度"},
                ],
                "answer": "A",
                "explanation": "climate 在语境中指长期的气候状况。",
                "target_ability": "VOCABULARY_CONTEXT",
                "error_type_on_wrong": "VOCABULARY_CONTEXT_ERROR",
            },
            {
                "question_id": "q2",
                "question_type": "MULTIPLE_CHOICE",
                "prompt": '"ecosystems" 在文中最接近哪一项？',
                "options": [
                    {"id": "A", "text": "经济系统"},
                    {"id": "B", "text": "生态系统"},
                    {"id": "C", "text": "操作系统"},
                    {"id": "D", "text": "社会制度"},
                ],
                "answer": "B",
                "explanation": "ecosystems 指生物群落及其环境的整体系统。",
                "target_ability": "VOCABULARY_CONTEXT",
                "error_type_on_wrong": "VOCABULARY_CONTEXT_ERROR",
            },
            {
                "question_id": "q3",
                "question_type": "MULTIPLE_CHOICE",
                "prompt": '"sustainable" 在文中最接近哪一项？',
                "options": [
                    {"id": "A", "text": "快速的"},
                    {"id": "B", "text": "复杂的"},
                    {"id": "C", "text": "可持续的"},
                    {"id": "D", "text": "临时的"},
                ],
                "answer": "C",
                "explanation": "sustainable 指可长期维持的，不损害后代需求。",
                "target_ability": "VOCABULARY_CONTEXT",
                "error_type_on_wrong": "VOCABULARY_CONTEXT_ERROR",
            },
        ],
        "agent_feedback": "Demo 训练任务，非 Agent 生成。",
        "source": "DEMO_SEED",
    }
    task_id = create_generated_task(
        database_path,
        session_id=session_id,
        user_id=user_id,
        task_type="LOW_PRESSURE_LEARNING",
        target_ability="VOCABULARY_CONTEXT",
        content_json=content,
        quality_check_result={"status": "PASSED", "source": "DEMO_SEED"},
    )
    print(f"训练任务: task_id={task_id}")

    print()
    print("===== Demo 数据摘要 =====")
    print(f"  user_id:    {user_id}")
    print(f"  session_id: {session_id}")
    print(f"  task_id:    {task_id}")
    print(f"  词汇数:     {len(vocab_ids)}")
    print("=========================")
    print("Demo 数据创建完成，可用于本地开发和测试。")


def main() -> None:
    parser = argparse.ArgumentParser(description="LingoForge Demo 数据种子脚本")
    parser.add_argument(
        "--database-path",
        required=True,
        help="SQLite 数据库文件路径",
    )
    args = parser.parse_args()
    seed(args.database_path)


if __name__ == "__main__":
    main()
