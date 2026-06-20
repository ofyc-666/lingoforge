"""演示数据种子脚本。

可重复运行（幂等），创建演示用户、目标、画像、词汇、会话和可提交训练任务。
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
from app.repositories.base import fetch_one
from app.repositories.isolated_tests import create_isolated_test_item
from app.repositories.sidequest import create_sidequest_run, create_sidequest_signal
from app.repositories.training import create_generated_task, create_training_session
from app.repositories.users import create_profile_snapshot, create_user, save_user_goal
from app.repositories.vocabulary import create_vocabulary_item, get_vocabulary_by_text
from app.services.vocab_import import seed_cet6_vocabulary


def seed(database_path: str) -> None:
    init_database(database_path)

    # ===== 幂等：检查是否已有演示用户 =====
    existing_user = fetch_one(database_path, "SELECT id FROM users WHERE display_name = ?", ("演示用户",))
    if existing_user is not None:
        user_id = existing_user["id"]
        print(f"用户已存在: user_id={user_id}（跳过创建）")
    else:
        user_id = create_user(database_path, "演示用户")
        print(f"用户: user_id={user_id}")

    # 2. 创建用户目标（幂等：检查是否已存在）
    existing_goal = fetch_one(
        database_path,
        "SELECT id FROM user_goals WHERE user_id = ? AND exam_type = 'CET-6' ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    if existing_goal is not None:
        goal_id = existing_goal["id"]
        print(f"用户目标已存在: goal_id={goal_id}（跳过创建）")
    else:
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

    # 3. 创建初始画像快照（幂等：检查是否已存在 DIAGNOSTIC 快照）
    existing_snapshot = fetch_one(
        database_path,
        "SELECT id FROM profile_snapshots WHERE user_id = ? AND source = 'DIAGNOSTIC' ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    if existing_snapshot is not None:
        snapshot_id = existing_snapshot["id"]
        print(f"画像快照已存在: snapshot_id={snapshot_id}（跳过创建）")
    else:
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

    # 4. CET-6 词表演示子集（幂等导入）
    cet6_result = seed_cet6_vocabulary(database_path)
    print(f"CET-6 词汇导入: 新增 {cet6_result['created']}, 跳过 {cet6_result['skipped']}")

    # 5. 演示基础词汇（与旧 seed 兼容，幂等）
    demo_vocab_items = [
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
    for text, meaning, source_type in demo_vocab_items:
        existing = get_vocabulary_by_text(database_path, text)
        if existing is not None:
            vocab_ids.append(existing["id"])
        else:
            vid = create_vocabulary_item(
                database_path,
                text=text,
                meaning_zh=meaning,
                source_type=source_type,
                tags=["CET-6", "demo"],
            )
            vocab_ids.append(vid)
    print(f"词汇: 已有 {len(set(vocab_ids))} 条演示词汇（幂等）")

    # 6. 创建训练会话（幂等：仅在没有 FIRST_MAIN session 时创建）
    existing_session = fetch_one(
        database_path,
        "SELECT id FROM training_sessions WHERE user_id = ? AND stage = 'FIRST_MAIN' ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    if existing_session is not None:
        session_id = existing_session["id"]
        print(f"训练会话已存在: session_id={session_id}（跳过创建）")
    else:
        session_id = create_training_session(
            database_path,
            user_id=user_id,
            stage="FIRST_MAIN",
            status="IN_PROGRESS",
        )
        print(f"训练会话: session_id={session_id}")

    # 7. 创建可提交训练任务（幂等：检查同 session 是否已有 LOW_PRESSURE_LEARNING 任务）
    existing_task = fetch_one(
        database_path,
        "SELECT id FROM generated_tasks WHERE session_id = ? AND task_type = 'LOW_PRESSURE_LEARNING' LIMIT 1",
        (session_id,),
    )
    if existing_task is not None:
        task_id = existing_task["id"]
        print(f"训练任务已存在: task_id={task_id}（跳过创建）")
    else:
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

    # 8. 创建隔离测试题（幂等：仅在没有 active 题时创建）
    existing_isolated = fetch_one(
        database_path,
        "SELECT COUNT(*) as cnt FROM isolated_test_items WHERE is_active = 1",
    )
    if existing_isolated and existing_isolated["cnt"] > 0:
        print(f"隔离测试题已有 {existing_isolated['cnt']} 道 active 题（跳过创建）")
    else:
        isolated_items = [
            {
                "target_ability": "VOCABULARY_CONTEXT",
                "item_payload": {
                    "prompt": '"climate" 在原文中最接近哪一项？',
                    "options": [
                        {"id": "A", "text": "气候"},
                        {"id": "B", "text": "环境"},
                        {"id": "C", "text": "变化"},
                        {"id": "D", "text": "温度"},
                    ],
                },
                "answer_key": {"correct": "A"},
                "answer_rationale": {"A": "climate 意为气候"},
                "distractor_rationale": {"B": "环境更接近 environment", "C": "变化是 change", "D": "温度是 temperature"},
            },
            {
                "target_ability": "VOCABULARY_CONTEXT",
                "item_payload": {
                    "prompt": '"ecosystems" 在原文中最接近哪一项？',
                    "options": [
                        {"id": "A", "text": "经济系统"},
                        {"id": "B", "text": "生态系统"},
                        {"id": "C", "text": "操作系统"},
                        {"id": "D", "text": "社会制度"},
                    ],
                },
                "answer_key": {"correct": "B"},
                "answer_rationale": {"B": "ecosystems 意为生态系统"},
                "distractor_rationale": {"A": "经济是 economy", "C": "操作系统是 operating system", "D": "社会制度是 social system"},
            },
            {
                "target_ability": "VOCABULARY_CONTEXT",
                "item_payload": {
                    "prompt": '"sustainable" 在原文中最接近哪一项？',
                    "options": [
                        {"id": "A", "text": "快速的"},
                        {"id": "B", "text": "复杂的"},
                        {"id": "C", "text": "可持续的"},
                        {"id": "D", "text": "临时的"},
                    ],
                },
                "answer_key": {"correct": "C"},
                "answer_rationale": {"C": "sustainable 意为可持续的"},
                "distractor_rationale": {"A": "快速的是 fast", "B": "复杂的是 complex", "D": "临时的是 temporary"},
            },
        ]
        for i, item_data in enumerate(isolated_items):
            iid = create_isolated_test_item(
                database_path,
                target_ability=item_data["target_ability"],
                item_version="v1",
                item_payload=item_data["item_payload"],
                answer_key=item_data["answer_key"],
                answer_rationale=item_data["answer_rationale"],
                distractor_rationale=item_data["distractor_rationale"],
                is_active=True,
            )
            print(f"隔离题 {i + 1}: item_id={iid}")
        print(f"隔离测试题: 已创建 {len(isolated_items)} 道 active 题")

    # 9. 创建副线 seed 数据（幂等：检查是否已有 AIRPORT_TICKET_PURCHASE run）
    existing_sq_run = fetch_one(
        database_path,
        "SELECT id FROM sidequest_runs WHERE user_id = ? AND task_name = 'AIRPORT_TICKET_PURCHASE' LIMIT 1",
        (user_id,),
    )
    if existing_sq_run is not None:
        sq_run_id = existing_sq_run["id"]
        print(f"副线运行已存在: sidequest_run_id={sq_run_id}（跳过创建）")
    else:
        sq_run_id = create_sidequest_run(
            database_path,
            user_id=user_id,
            task_name="AIRPORT_TICKET_PURCHASE",
            objective={"scene": "AIRPORT_TICKET", "expression": "I'd like to book a flight."},
            result={"completed": True},
        )
        print(f"副线运行: sidequest_run_id={sq_run_id}")

    existing_sq_signal = fetch_one(
        database_path,
        "SELECT id FROM sidequest_signals WHERE user_id = ? AND scene = 'AIRPORT_TICKET' LIMIT 1",
        (user_id,),
    )
    if existing_sq_signal is not None:
        sq_signal_id = existing_sq_signal["id"]
        print(f"副线信号已存在: signal_id={sq_signal_id}（跳过创建）")
    else:
        sq_signal_id = create_sidequest_signal(
            database_path,
            user_id=user_id,
            sidequest_run_id=sq_run_id if existing_sq_run is None else existing_sq_run["id"],
            scene="AIRPORT_TICKET",
            signal_type="TASK_SUCCESS",
            expression_text="I'd like to book a flight.",
            context_json={"scene": "AIRPORT_TICKET"},
        )
        print(f"副线信号: signal_id={sq_signal_id}")

    print()
    print("===== Demo 数据摘要 =====")
    print(f"  user_id:    {user_id}")
    print(f"  session_id: {session_id}")
    cet6_count = len([v for v in demo_vocab_items]) + cet6_result['created']
    print(f"  词汇数:     ~{cet6_count}")
    print(f"  CET-6 导入: 新增 {cet6_result['created']}, 跳过 {cet6_result['skipped']}")
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
