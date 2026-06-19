"""画像更新建议薄服务测试。"""

from __future__ import annotations

import pytest

from app.database import init_database
from app.repositories.training import create_training_session
from app.repositories.users import create_user, get_user_profile_suggestions
from app.services.profile_suggestions import propose_profile_update_from_score
from temp_paths import temp_db_path


@pytest.fixture
def db_path():
    path = temp_db_path("profile_svc")
    init_database(path)
    return path


@pytest.fixture
def user_id(db_path):
    return create_user(db_path, "画像服务测试用户")


@pytest.fixture
def session_id(db_path, user_id):
    return create_training_session(db_path, user_id=user_id, stage="FIRST_MAIN")


def _score(total: int, correct: int) -> dict:
    """构造评分结果。"""
    accuracy = correct / total if total > 0 else 0.0
    question_results = []
    for i in range(total):
        is_correct = i < correct
        question_results.append({
            "question_id": f"q{i + 1}",
            "user_answer": "A" if is_correct else "B",
            "standard_answer": "A",
            "is_correct": is_correct,
            "error_type": None if is_correct else "VOCABULARY_CONTEXT_ERROR",
            "target_ability": "VOCABULARY_CONTEXT",
            "explanation": "",
        })
    return {
        "total": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "passed": accuracy >= 0.6,
        "question_results": question_results,
        "error_types": ["VOCABULARY_CONTEXT_ERROR"] if correct < total else [],
        "used_hints": [],
    }


class TestProposeProfileUpdate:
    """propose_profile_update_from_score 测试。"""

    def test_high_accuracy_generates_improve(self, db_path, user_id):
        score = _score(5, 5)
        suggestion_id = propose_profile_update_from_score(
            db_path, user_id=user_id, evidence_id=100, score_result=score,
        )
        assert suggestion_id >= 1

        suggestions = get_user_profile_suggestions(db_path, user_id)
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["direction"] in ("IMPROVE", "NO_CHANGE")
        assert s["ability"] == "VOCABULARY_CONTEXT"
        assert 100 in s["evidence_refs"]
        assert s["agent_payload"]["source"] == "DETERMINISTIC_SCORER"

    def test_low_accuracy_generates_decline(self, db_path, user_id):
        score = _score(5, 1)
        suggestion_id = propose_profile_update_from_score(
            db_path, user_id=user_id, evidence_id=101, score_result=score,
        )
        suggestions = get_user_profile_suggestions(db_path, user_id)
        assert suggestions[0]["direction"] == "DECLINE"

    def test_no_ability_info_generates_uncertain(self, db_path, user_id):
        """无能力信息（空题目）时生成 UNCERTAIN。"""
        score = {
            "total": 0,
            "correct": 0,
            "accuracy": 0.0,
            "passed": False,
            "question_results": [],
            "error_types": [],
            "used_hints": [],
        }
        suggestion_id = propose_profile_update_from_score(
            db_path, user_id=user_id, evidence_id=102, score_result=score,
        )
        suggestions = get_user_profile_suggestions(db_path, user_id)
        assert suggestions[0]["direction"] == "UNCERTAIN"

    def test_does_not_write_profile_snapshot(self, db_path, user_id):
        score = _score(3, 2)
        propose_profile_update_from_score(
            db_path, user_id=user_id, evidence_id=103, score_result=score,
        )
        # 验证 profile_snapshots 表无新记录
        from app.repositories.base import fetch_all
        snapshots = fetch_all(db_path, "SELECT * FROM profile_snapshots WHERE user_id = ?", (user_id,))
        assert len(snapshots) == 0
