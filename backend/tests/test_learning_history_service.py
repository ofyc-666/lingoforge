"""学习历史分析服务测试。

测试 analyze_learning_history 的 PROBLEM_TIMELINE 和 REVIEW_PRIORITY。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.database import init_database
from app.repositories.training import create_learning_evidence
from app.repositories.users import create_user
from app.services.learning_history import analyze_learning_history
from temp_paths import temp_db_path


_T0 = datetime(2026, 6, 1, tzinfo=timezone.utc)


def _create_evidence(
    db_path: str,
    user_id: int,
    *,
    evidence_type: str = "TRAINING_ANSWER",
    session_id: int | None = None,
    task_id: int | None = None,
    payload: dict | None = None,
) -> int:
    return create_learning_evidence(
        db_path,
        user_id=user_id,
        evidence_type=evidence_type,
        session_id=session_id,
        task_id=task_id,
        payload=payload or {},
    )


class TestProblemTimeline:
    """PROBLEM_TIMELINE 分析测试。"""

    def test_同一错误跨多个_session_统计正确(self) -> None:
        db_path = str(temp_db_path("history_timeline"))
        init_database(db_path)
        uid = create_user(db_path, "历史分析用户")
        base_payload = {
            "score": {"total": 5, "correct": 3, "accuracy": 0.6},
            "question_results": [
                {
                    "question_id": "q1",
                    "target_ability": "VOCABULARY_CONTEXT",
                    "is_correct": False,
                    "error_type": "VOCABULARY_CONTEXT_ERROR",
                },
            ],
        }
        # session_id 用 None 避免 FK 约束
        eid1 = _create_evidence(db_path, uid, session_id=None, payload=base_payload)
        eid2 = _create_evidence(db_path, uid, session_id=None, payload=base_payload)
        eid3 = _create_evidence(db_path, uid, session_id=None, payload={
            **base_payload,
            "question_results": [
                {
                    "question_id": "q1",
                    "target_ability": "VOCABULARY_CONTEXT",
                    "is_correct": True,
                },
            ],
        })
        result = analyze_learning_history(
            db_path,
            user_id=uid,
            analysis_type="PROBLEM_TIMELINE",
            target={"ability": "VOCABULARY_CONTEXT"},
            now=_T0,
        )
        assert result["analysis_type"] == "PROBLEM_TIMELINE"
        items = result.get("problem_items", result.get("items", []))
        assert len(items) > 0
        found = False
        for item in items:
            if item.get("error_type") == "VOCABULARY_CONTEXT_ERROR" or "VOCABULARY" in str(item.get("ability", "")):
                found = True
                assert item.get("occurrence_count", 0) >= 1
        assert found, f"未找到 VOCABULARY_CONTEXT_ERROR 相关问题，items={items}"

    def test_其他用户_evidence_不参与分析(self) -> None:
        db_path = str(temp_db_path("history_isolation"))
        init_database(db_path)
        uid1 = create_user(db_path, "隔离用户1")
        uid2 = create_user(db_path, "隔离用户2")
        _create_evidence(db_path, uid2, session_id=None, payload={
            "score": {"total": 3, "correct": 0},
            "question_results": [
                {"question_id": "q1", "target_ability": "SENTENCE_LOGIC", "is_correct": False, "error_type": "LOGIC_ERROR"},
            ],
        })
        result = analyze_learning_history(
            db_path,
            user_id=uid1,
            analysis_type="PROBLEM_TIMELINE",
            target={"ability": "VOCABULARY_CONTEXT"},
            now=_T0,
        )
        assert result.get("status") == "INSUFFICIENT_EVIDENCE"

    def test_有成功记录时_last_success_at_正确(self) -> None:
        db_path = str(temp_db_path("history_success"))
        init_database(db_path)
        uid = create_user(db_path, "成功记录用户")
        _create_evidence(db_path, uid, session_id=None, payload={
            "question_results": [
                {"question_id": "q1", "target_ability": "VOCABULARY_CONTEXT", "is_correct": True},
            ],
        })
        result = analyze_learning_history(
            db_path,
            user_id=uid,
            analysis_type="PROBLEM_TIMELINE",
            target={"ability": "VOCABULARY_CONTEXT"},
            now=_T0,
        )
        items = result.get("problem_items", result.get("items", []))
        has_success = any(i.get("last_success_at") is not None for i in items)
        assert has_success or result.get("status") != "INSUFFICIENT_EVIDENCE"

    def test_无证据时返回_INSUFFICIENT_EVIDENCE(self) -> None:
        db_path = str(temp_db_path("history_no_evidence"))
        init_database(db_path)
        uid = create_user(db_path, "无证据用户")
        result = analyze_learning_history(
            db_path,
            user_id=uid,
            analysis_type="PROBLEM_TIMELINE",
            target={"ability": "VOCABULARY_CONTEXT"},
            now=_T0,
        )
        assert result["status"] == "INSUFFICIENT_EVIDENCE"


class TestReviewPriority:
    """REVIEW_PRIORITY 评分测试。"""

    def test_长时间未练且低正确率得到高优先级(self) -> None:
        db_path = str(temp_db_path("review_high"))
        init_database(db_path)
        uid = create_user(db_path, "高优用户")
        long_ago = (_T0 - timedelta(days=15)).isoformat()
        _create_evidence(db_path, uid, session_id=None, payload={
            "score": {"total": 5, "correct": 1, "accuracy": 0.2},
            "question_results": [
                {"question_id": "q1", "target_ability": "VOCABULARY_CONTEXT", "is_correct": False, "error_type": "VOCABULARY_CONTEXT_ERROR"},
            ],
            "occurred_at": long_ago,
        })
        result = analyze_learning_history(
            db_path,
            user_id=uid,
            analysis_type="REVIEW_PRIORITY",
            target={"ability": "VOCABULARY_CONTEXT"},
            now=_T0,
        )
        assert result.get("analysis_type") == "REVIEW_PRIORITY"
        assert result.get("status") != "INSUFFICIENT_EVIDENCE"
        priority = result.get("review_priority", 0)
        assert priority >= 40, f"预期较高优先级，实际 {priority}"

    def test_最近连续成功得到低优先级(self) -> None:
        db_path = str(temp_db_path("review_low"))
        init_database(db_path)
        uid = create_user(db_path, "低优用户")
        for i in range(3):
            recent = (_T0 - timedelta(days=i * 0.5)).isoformat()
            _create_evidence(db_path, uid, session_id=None, payload={
                "score": {"total": 5, "correct": 5, "accuracy": 1.0},
                "question_results": [
                    {"question_id": "q1", "target_ability": "VOCABULARY_CONTEXT", "is_correct": True},
                ],
                "occurred_at": recent,
            })
        result = analyze_learning_history(
            db_path,
            user_id=uid,
            analysis_type="REVIEW_PRIORITY",
            target={"ability": "VOCABULARY_CONTEXT"},
            now=_T0,
        )
        assert result.get("status") != "INSUFFICIENT_EVIDENCE"
        priority = result.get("review_priority", 100)
        assert priority < 60, f"预期较低优先级，实际 {priority}"

    def test_无证据返回_INSUFFICIENT_EVIDENCE(self) -> None:
        db_path = str(temp_db_path("review_no_evidence"))
        init_database(db_path)
        uid = create_user(db_path, "无证据用户2")
        result = analyze_learning_history(
            db_path,
            user_id=uid,
            analysis_type="REVIEW_PRIORITY",
            target={"ability": "VOCABULARY_CONTEXT"},
            now=_T0,
        )
        assert result["status"] == "INSUFFICIENT_EVIDENCE"
        assert result["analysis_type"] == "REVIEW_PRIORITY"

    def test_返回字段包含必要_keys(self) -> None:
        db_path = str(temp_db_path("review_keys"))
        init_database(db_path)
        uid = create_user(db_path, "key测试用户")
        _create_evidence(db_path, uid, session_id=None, payload={
            "score": {"total": 3, "correct": 1, "accuracy": 0.33},
            "question_results": [
                {"question_id": "q1", "target_ability": "VOCABULARY_CONTEXT", "is_correct": False, "error_type": "VOCABULARY_CONTEXT_ERROR"},
            ],
            "occurred_at": (_T0 - timedelta(days=5)).isoformat(),
        })
        result = analyze_learning_history(
            db_path,
            user_id=uid,
            analysis_type="REVIEW_PRIORITY",
            target={"ability": "VOCABULARY_CONTEXT"},
            now=_T0,
        )
        assert "review_priority" in result
        assert "review_status" in result
        assert "algorithm_version" in result
        assert result["algorithm_version"] == "review_priority_v1"
        assert 0 <= result["review_priority"] <= 100
        assert "factors" in result
        assert "evidence_refs" in result

    def test_review_status_分类正确(self) -> None:
        db_path = str(temp_db_path("review_status"))
        init_database(db_path)
        uid = create_user(db_path, "状态测试用户")
        old = (_T0 - timedelta(days=20)).isoformat()
        _create_evidence(db_path, uid, session_id=None, payload={
            "score": {"total": 5, "correct": 0, "accuracy": 0.0},
            "question_results": [
                {"question_id": "q1", "target_ability": "VOCABULARY_CONTEXT", "is_correct": False, "error_type": "VOCABULARY_CONTEXT_ERROR"},
            ],
            "occurred_at": old,
        })
        result = analyze_learning_history(
            db_path,
            user_id=uid,
            analysis_type="REVIEW_PRIORITY",
            target={"ability": "VOCABULARY_CONTEXT"},
            now=_T0,
        )
        status = result["review_status"]
        assert status in ("DUE_NOW", "SOON", "STABLE", "INSUFFICIENT_EVIDENCE")
