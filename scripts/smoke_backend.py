"""后端 Mock 模式 Smoke 测试脚本。

使用临时数据库和 LLM_MODE=mock，验证核心 API 端点可用。
不写入仓库内数据库，不调用真实 LLM API。
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# 将 backend 加入路径
_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent / "backend"
sys.path.insert(0, str(_BACKEND))

# 强制 Mock 模式
os.environ["LLM_MODE"] = "mock"
os.environ["DATABASE_PATH"] = os.path.join(tempfile.gettempdir(), "lingoforge_smoke_test.sqlite3")

from app.config import load_settings
from app.database import init_database
from app.main import create_app
from app.repositories.training import create_generated_task, create_training_session
from app.repositories.users import create_user

from fastapi.testclient import TestClient


def main() -> None:
    settings = load_settings()
    print(f"数据库路径: {settings.database_path}")
    print(f"LLM 模式:   {settings.llm_mode}")

    # 初始化
    init_database(settings.database_path)

    app = create_app(settings)
    client = TestClient(app)

    # 1. 健康检查
    print("\n--- Health Check ---")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health check 失败: {resp.text}"
    data = resp.json()
    assert data["status"] == "ok"
    print(f"  状态: {data['status']}")
    print(f"  LLM Provider: {data['llm_provider']}")

    # 2. 文本分析
    print("\n--- Text Analysis ---")
    resp = client.post(
        "/api/learning/analyze-text",
        json={
            "raw_text": "Climate change is a pressing challenge for ecosystems worldwide. "
                        "Scientists emphasize the need for sustainable solutions to protect biodiversity.",
            "target_abilities": ["VOCABULARY_CONTEXT"],
            "max_keywords": 5,
            "generate_exercise": True,
        },
        headers={"X-LingoForge-User-Id": "1"},
    )
    assert resp.status_code == 200, f"文本分析失败: {resp.text}"
    analysis = resp.json()
    print(f"  分析 ID: {analysis['analysis_id']}")
    print(f"  关键词数: {len(analysis['keywords'])}")
    exercise_ok = analysis["exercise"] is not None
    print(f"  练习题: {'有' if exercise_ok else '无'}")
    assert exercise_ok

    # 3. 创建训练任务
    print("\n--- 创建训练任务 ---")
    uid = create_user(settings.database_path, "Smoke 测试用户")
    sid = create_training_session(settings.database_path, user_id=uid, stage="FIRST_MAIN")
    content = {
        "title": "Smoke 测试任务",
        "raw_text": "The climate is changing.",
        "instructions": "请选择最符合语境的答案。",
        "questions": [
            {
                "question_id": "q1",
                "question_type": "MULTIPLE_CHOICE",
                "prompt": "climate 最接近？",
                "options": [
                    {"id": "A", "text": "气候"},
                    {"id": "B", "text": "变化"},
                ],
                "answer": "A",
                "explanation": "climate = 气候。",
                "target_ability": "VOCABULARY_CONTEXT",
                "error_type_on_wrong": "VOCABULARY_CONTEXT_ERROR",
            },
        ],
        "agent_feedback": "",
        "source": "SMOKE",
    }
    tid = create_generated_task(
        settings.database_path,
        session_id=sid,
        user_id=uid,
        task_type="LOW_PRESSURE_LEARNING",
        target_ability="VOCABULARY_CONTEXT",
        content_json=content,
        quality_check_result={"status": "PASSED"},
    )
    print(f"  user_id={uid}, session_id={sid}, task_id={tid}")

    # 4. 训练提交
    print("\n--- 训练提交 ---")
    resp = client.post(
        f"/api/training/tasks/{tid}/submit",
        json={
            "answers": [{"question_id": "q1", "answer": "A"}],
            "time_spent_seconds": 30,
        },
        headers={"X-LingoForge-User-Id": str(uid)},
    )
    assert resp.status_code == 200, f"训练提交失败: {resp.text}"
    submission = resp.json()
    print(f"  evidence_id: {submission['evidence_id']}")
    print(f"  评分: {submission['score']['correct']}/{submission['score']['total']}")
    assert submission["score"]["passed"] is True

    # 5. 训练结果查询
    print("\n--- 训练结果查询 ---")
    resp = client.get(
        f"/api/training/tasks/{tid}/result",
        headers={"X-LingoForge-User-Id": str(uid)},
    )
    assert resp.status_code == 200, f"结果查询失败: {resp.text}"
    result = resp.json()
    assert result["latest_submission"] is not None
    print(f"  最新提交 evidence_id: {result['latest_submission']['evidence_id']}")
    print(f"  画像建议 ID: {result['latest_submission']['profile_suggestion_id']}")

    print("\n===== Smoke 测试全部通过 =====")
    print(f"  health:             OK")
    print(f"  analyze-text:       OK ({analysis['analysis_id']})")
    print(f"  submit:             OK (evidence_id={submission['evidence_id']})")
    print(f"  result:             OK")


if __name__ == "__main__":
    main()
