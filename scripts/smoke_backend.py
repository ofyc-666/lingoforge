"""后端 Mock 模式 Smoke 测试脚本。

使用临时数据库和 LLM_MODE=mock，验证核心 API 端点可用。
覆盖 profile、training、learning、sidequest、isolated-tests 全部主线 API。
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

from app.config import Settings, load_settings  # noqa: E402
from app.database import init_database  # noqa: E402
from app.main import create_app  # noqa: E402
from app.repositories.isolated_tests import create_isolated_test_item  # noqa: E402
from app.repositories.training import create_generated_task, create_training_session  # noqa: E402
from app.repositories.users import create_user  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402


def main() -> None:
    settings = Settings(
        app_name="LingoForge Smoke",
        database_path=os.path.join(tempfile.gettempdir(), "lingoforge_smoke.sqlite3"),
        cors_origins=[],
        llm_mode="mock",
        llm_provider="deepseek",
    )
    print(f"数据库路径: {settings.database_path}")
    print(f"LLM 模式:   {settings.llm_mode}")

    init_database(settings.database_path)
    app = create_app(settings)
    client = TestClient(app)

    # 创建测试用户和基础数据
    uid = create_user(settings.database_path, "Smoke 测试用户")
    print(f"创建测试用户: user_id={uid}")

    # ---- 1. 健康检查 ----
    print("\n--- 1. Health Check ---")
    resp = client.get("/health")
    assert resp.status_code == 200, f"Health check 失败: {resp.text}"
    data = resp.json()
    assert data["status"] == "ok"
    print(f"    通过: status={data['status']}, provider={data['llm_provider']}")

    # ---- 2. POST /api/profile/goal ----
    print("\n--- 2. 保存用户目标 ---")
    resp = client.post(
        "/api/profile/goal",
        json={
            "exam_type": "CET-6",
            "days_until_exam": 30,
            "target_score": 550,
            "daily_minutes": 30,
            "self_reported_weaknesses": ["vocabulary"],
            "interest_topics": ["technology"],
        },
        headers={"X-LingoForge-User-Id": str(uid)},
    )
    assert resp.status_code == 200, f"保存目标失败: {resp.text}"
    goal_data = resp.json()
    assert goal_data["user_id"] == uid
    print(f"    通过: goal_id={goal_data['goal_id']}")

    # ---- 3. GET /api/profile/summary ----
    print("\n--- 3. 用户画像摘要 ---")
    resp = client.get(
        "/api/profile/summary",
        headers={"X-LingoForge-User-Id": str(uid)},
    )
    assert resp.status_code == 200, f"画像摘要失败: {resp.text}"
    summary = resp.json()
    assert summary["user"]["display_name"] == "Smoke 测试用户"
    assert summary["latest_goal"].get("exam_type") == "CET-6"
    print(f"    通过: user={summary['user']['display_name']}")

    # ---- 4. POST /api/training/sessions ----
    print("\n--- 4. 创建训练会话 ---")
    resp = client.post(
        "/api/training/sessions",
        json={"stage": "FIRST_MAIN"},
        headers={"X-LingoForge-User-Id": str(uid)},
    )
    assert resp.status_code == 200, f"创建会话失败: {resp.text}"
    session_data = resp.json()
    sid = session_data["session_id"]
    assert session_data["status"] == "IN_PROGRESS"
    print(f"    通过: session_id={sid}, stage={session_data['stage']}")

    # ---- 5. POST /api/learning/analyze-text/create-task ----
    print("\n--- 5. 文本分析并创建训练任务 ---")
    resp = client.post(
        "/api/learning/analyze-text/create-task",
        json={
            "raw_text": "Climate change is a pressing challenge for ecosystems worldwide. "
                        "Scientists emphasize the need for sustainable solutions to protect biodiversity.",
            "target_abilities": ["VOCABULARY_CONTEXT"],
            "max_keywords": 5,
            "generate_exercise": True,
        },
        headers={
            "X-LingoForge-User-Id": str(uid),
            "X-LingoForge-Session-Id": str(sid),
        },
    )
    assert resp.status_code == 200, f"创建任务失败: {resp.text}"
    analysis_data = resp.json()
    tid = analysis_data["task_id"]
    print(f"    通过: task_id={tid}, analysis_id={analysis_data['analysis']['analysis_id']}")

    # ---- 6. POST /api/training/tasks/{task_id}/submit ----
    print("\n--- 6. 提交训练答案 ---")
    resp = client.post(
        f"/api/training/tasks/{tid}/submit",
        json={
            "answers": [{"question_id": "q1", "answer": "A"}],
            "time_spent_seconds": 30,
        },
        headers={"X-LingoForge-User-Id": str(uid)},
    )
    assert resp.status_code == 200, f"提交训练失败: {resp.text}"
    submit_data = resp.json()
    assert submit_data["evidence_id"] >= 1
    score = submit_data["score"]
    print(f"    通过: evidence_id={submit_data['evidence_id']}, 评分={score['correct']}/{score['total']}")

    # ---- 7. GET /api/training/tasks/{task_id}/result ----
    print("\n--- 7. 查询训练结果 ---")
    resp = client.get(
        f"/api/training/tasks/{tid}/result",
        headers={"X-LingoForge-User-Id": str(uid)},
    )
    assert resp.status_code == 200, f"查询结果失败: {resp.text}"
    result_data = resp.json()
    assert result_data["latest_submission"] is not None
    print(f"    通过: latest_submission evidence_id={result_data['latest_submission']['evidence_id']}")

    # ---- 8. POST /api/sidequest/airport-ticket/complete ----
    print("\n--- 8. 机场购票副线完成 ---")
    resp = client.post(
        "/api/sidequest/airport-ticket/complete",
        json={
            "selected_expression": "I'd like to book a flight.",
            "scene": "AIRPORT_TICKET",
            "result": {"completed": True},
        },
        headers={"X-LingoForge-User-Id": str(uid)},
    )
    assert resp.status_code == 200, f"副线完成失败: {resp.text}"
    sq_data = resp.json()
    assert sq_data["is_pending_verification"] is True
    print(f"    通过: sidequest_run_id={sq_data['sidequest_run_id']}, signal_id={sq_data['signal_id']}")

    # ---- 9. POST /api/isolated-tests/start ----
    print("\n--- 9. 隔离测试开始 ---")
    # 先创建隔离题
    create_isolated_test_item(
        settings.database_path,
        target_ability="VOCABULARY_CONTEXT",
        item_version="v1",
        item_payload={
            "prompt": '"climate" 最接近哪一项？',
            "options": [{"id": "A", "text": "气候"}, {"id": "B", "text": "环境"}],
        },
        answer_key={"correct": "A"},
        answer_rationale={"A": "climate 意为气候"},
        distractor_rationale={"B": "环境是 environment"},
        is_active=True,
    )
    create_isolated_test_item(
        settings.database_path,
        target_ability="VOCABULARY_CONTEXT",
        item_version="v1",
        item_payload={
            "prompt": '"ecosystem" 最接近哪一项？',
            "options": [{"id": "A", "text": "经济"}, {"id": "B", "text": "生态系统"}],
        },
        answer_key={"correct": "B"},
        answer_rationale={"B": "ecosystem 意为生态系统"},
        distractor_rationale={"A": "经济是 economy"},
        is_active=True,
    )
    resp = client.post(
        "/api/isolated-tests/start",
        json={"target_ability": "VOCABULARY_CONTEXT", "limit": 2},
        headers={"X-LingoForge-User-Id": str(uid)},
    )
    assert resp.status_code == 200, f"隔离测试开始失败: {resp.text}"
    iso_start = resp.json()
    iso_attempt_id = iso_start["attempt_id"]
    assert len(iso_start["items"]) >= 1
    # 确认不含答案字段
    import json
    dumped = json.dumps(iso_start, ensure_ascii=False)
    assert "answer_key" not in dumped
    print(f"    通过: attempt_id={iso_attempt_id}, items={len(iso_start['items'])} (已 sanitize)")

    # ---- 10. POST /api/isolated-tests/attempts/{attempt_id}/submit ----
    print("\n--- 10. 隔离测试提交 ---")
    resp = client.post(
        f"/api/isolated-tests/attempts/{iso_attempt_id}/submit",
        json={
            "answers": [{"item_id": 1, "answer": "A"}],
            "time_spent_seconds": 45,
        },
        headers={"X-LingoForge-User-Id": str(uid)},
    )
    assert resp.status_code == 200, f"隔离测试提交失败: {resp.text}"
    iso_submit = resp.json()
    assert iso_submit["evidence_id"] >= 1
    iso_dumped = json.dumps(iso_submit, ensure_ascii=False)
    assert "answer_key" not in iso_dumped
    print(f"    通过: evidence_id={iso_submit['evidence_id']}, score={iso_submit['score']} (已 sanitize)")

    # ---- 总结 ----
    print()
    print("=" * 50)
    print("  Smoke 测试全部通过！")
    print("=" * 50)
    print(f"  1. health:                          OK")
    print(f"  2. profile/goal (POST):             OK (goal_id={goal_data['goal_id']})")
    print(f"  3. profile/summary (GET):           OK")
    print(f"  4. training/sessions (POST):        OK (session_id={sid})")
    print(f"  5. learning/create-task (POST):     OK (task_id={tid})")
    print(f"  6. training/submit (POST):          OK (evidence_id={submit_data['evidence_id']})")
    print(f"  7. training/result (GET):           OK")
    print(f"  8. sidequest/complete (POST):       OK (signal_id={sq_data['signal_id']})")
    print(f"  9. isolated-tests/start (POST):     OK (attempt_id={iso_attempt_id})")
    print(f"  10. isolated-tests/submit (POST):   OK (evidence_id={iso_submit['evidence_id']})")
    print("=" * 50)
    print()
    print("注意：身份验证通过请求头 X-LingoForge-User-Id 绑定，不放在请求体中。")


if __name__ == "__main__":
    main()
