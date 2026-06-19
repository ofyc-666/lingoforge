"""用户、目标和画像 Repository 测试。"""

from __future__ import annotations

import pytest

from app.database import init_database
from app.repositories.users import (
    create_user,
    create_profile_snapshot,
    create_profile_suggestion,
    get_latest_profile,
    get_latest_user_goal,
    get_user,
    get_user_profile_suggestions,
    save_user_goal,
)
from temp_paths import temp_db_path


@pytest.fixture
def db_path():
    """创建带完整 Schema 的临时数据库。"""
    path = temp_db_path("user_repo")
    init_database(path)
    return path


class TestUserRepository:
    """用户 CRUD 测试。"""

    def test_create_and_get_user(self, db_path):
        user_id = create_user(db_path, "测试用户")
        user = get_user(db_path, user_id)
        assert user is not None
        assert user["display_name"] == "测试用户"
        assert user["id"] == user_id

    def test_get_nonexistent_user_returns_none(self, db_path):
        assert get_user(db_path, 999) is None

    def test_create_multiple_users(self, db_path):
        a = create_user(db_path, "用户A")
        b = create_user(db_path, "用户B")
        assert a != b
        assert get_user(db_path, a)["display_name"] == "用户A"
        assert get_user(db_path, b)["display_name"] == "用户B"


class TestUserGoalRepository:
    """用户目标 Repository 测试。"""

    def test_save_and_get_latest_goal(self, db_path):
        user_id = create_user(db_path, "目标测试用户")
        save_user_goal(
            db_path,
            user_id=user_id,
            days_until_exam=90,
            target_score=550,
            daily_minutes=60,
            self_reported_weaknesses=["阅读", "词汇"],
            interest_topics=["科技", "教育"],
        )
        goal = get_latest_user_goal(db_path, user_id)
        assert goal is not None
        assert goal["user_id"] == user_id
        assert goal["days_until_exam"] == 90
        assert goal["target_score"] == 550
        assert goal["daily_minutes"] == 60

    def test_goal_json_fields_are_objects(self, db_path):
        user_id = create_user(db_path, "JSON测试")
        save_user_goal(db_path, user_id=user_id, self_reported_weaknesses=["阅读"], interest_topics=["科技"])
        goal = get_latest_user_goal(db_path, user_id)
        assert goal["self_reported_weaknesses"] == ["阅读"]
        assert goal["interest_topics"] == ["科技"]

    def test_latest_goal_is_newest(self, db_path):
        user_id = create_user(db_path, "多目标用户")
        save_user_goal(db_path, user_id=user_id, target_score=500)
        save_user_goal(db_path, user_id=user_id, target_score=600)
        goal = get_latest_user_goal(db_path, user_id)
        assert goal["target_score"] == 600

    def test_no_goal_returns_none(self, db_path):
        user_id = create_user(db_path, "无目标用户")
        assert get_latest_user_goal(db_path, user_id) is None

    def test_default_values_preserved(self, db_path):
        user_id = create_user(db_path, "默认值用户")
        save_user_goal(db_path, user_id=user_id)
        goal = get_latest_user_goal(db_path, user_id)
        assert goal["exam_type"] == "CET-6"


class TestProfileSnapshotRepository:
    """画像快照 Repository 测试。"""

    def test_save_and_get_latest_snapshot(self, db_path):
        user_id = create_user(db_path, "画像用户")
        profile = {"vocabulary_context": {"status": "weak"}}
        evidence = [1, 2]
        snapshot_id = create_profile_snapshot(
            db_path, user_id=user_id, source="DIAGNOSTIC", profile=profile, evidence_refs=evidence
        )
        assert snapshot_id is not None

        latest = get_latest_profile(db_path, user_id)
        assert latest is not None
        assert latest["source"] == "DIAGNOSTIC"
        assert latest["profile_json"] == profile
        assert latest["evidence_refs"] == evidence

    def test_latest_snapshot_is_newest(self, db_path):
        user_id = create_user(db_path, "多快照用户")
        create_profile_snapshot(db_path, user_id=user_id, source="DIAGNOSTIC", profile={"v": 1})
        create_profile_snapshot(db_path, user_id=user_id, source="MAIN_TRAINING", profile={"v": 2})

        latest = get_latest_profile(db_path, user_id)
        assert latest["source"] == "MAIN_TRAINING"
        assert latest["profile_json"] == {"v": 2}

    def test_no_snapshot_returns_none(self, db_path):
        user_id = create_user(db_path, "无画像用户")
        assert get_latest_profile(db_path, user_id) is None

    def test_evidence_refs_default(self, db_path):
        user_id = create_user(db_path, "默认引用用户")
        create_profile_snapshot(db_path, user_id=user_id, source="DIAGNOSTIC", profile={})
        latest = get_latest_profile(db_path, user_id)
        assert latest["evidence_refs"] == []


class TestProfileSuggestionRepository:
    """画像建议 Repository 测试。"""

    def test_write_and_list_suggestions(self, db_path):
        user_id = create_user(db_path, "建议用户")
        create_profile_suggestion(
            db_path,
            user_id=user_id,
            ability="VOCABULARY_CONTEXT",
            direction="IMPROVE",
            reason="连续三次正确率 > 80%",
            evidence_refs=[10, 11],
            agent_payload={"confidence": "HIGH"},
        )
        create_profile_suggestion(
            db_path,
            user_id=user_id,
            ability="SENTENCE_LOGIC",
            direction="DECLINE",
            reason="长难句错误增多",
        )

        suggestions = get_user_profile_suggestions(db_path, user_id)
        assert len(suggestions) == 2
        assert suggestions[0]["ability"] == "VOCABULARY_CONTEXT"
        assert suggestions[1]["ability"] == "SENTENCE_LOGIC"

    def test_suggestions_preserve_fields(self, db_path):
        user_id = create_user(db_path, "字段测试用户")
        create_profile_suggestion(
            db_path,
            user_id=user_id,
            ability="DISTRACTOR_JUDGEMENT",
            direction="UNCERTAIN",
            reason="证据不足",
            evidence_refs=[5],
            agent_payload={"note": "需更多数据"},
        )
        suggestions = get_user_profile_suggestions(db_path, user_id)
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["direction"] == "UNCERTAIN"
        assert s["evidence_refs"] == [5]
        assert s["agent_payload"] == {"note": "需更多数据"}
        assert s["validation_status"] == "NEEDS_REVIEW"

    def test_no_suggestions_returns_empty_list(self, db_path):
        user_id = create_user(db_path, "无建议用户")
        assert get_user_profile_suggestions(db_path, user_id) == []

    def test_suggestions_isolated_by_user(self, db_path):
        u1 = create_user(db_path, "用户1")
        u2 = create_user(db_path, "用户2")
        create_profile_suggestion(db_path, user_id=u1, ability="VOCABULARY_CONTEXT", direction="IMPROVE", reason="r1")
        create_profile_suggestion(db_path, user_id=u2, ability="SENTENCE_LOGIC", direction="DECLINE", reason="r2")

        assert len(get_user_profile_suggestions(db_path, u1)) == 1
        assert len(get_user_profile_suggestions(db_path, u2)) == 1
        assert get_user_profile_suggestions(db_path, u1)[0]["reason"] == "r1"
