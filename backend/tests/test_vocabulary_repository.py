"""词汇、Skill 元数据和候选词 Repository 测试。"""

from __future__ import annotations

import pytest

from app.database import init_database
from app.repositories.users import create_user
from app.repositories.vocabulary import (
    create_candidate_event,
    create_skill_version,
    create_vocabulary_item,
    get_recent_candidate_events,
    get_skill_version,
    get_vocabulary_item,
    list_vocabulary_by_source,
    list_vocabulary_by_tag,
)
from temp_paths import temp_db_path


@pytest.fixture
def db_path():
    path = temp_db_path("vocab_repo")
    init_database(path)
    return path


@pytest.fixture
def user_id(db_path):
    return create_user(db_path, "词汇测试用户")


class TestVocabularyItemRepository:
    """词汇项 Repository 测试。"""

    def test_create_and_get_item(self, db_path):
        vid = create_vocabulary_item(
            db_path, text="abandon", meaning_zh="放弃", tags=["CET-6", "高频"], source_type="CET6_VOCAB"
        )
        item = get_vocabulary_item(db_path, vid)
        assert item is not None
        assert item["text"] == "abandon"
        assert item["meaning_zh"] == "放弃"
        assert item["source_type"] == "CET6_VOCAB"

    def test_tags_are_objects(self, db_path):
        vid = create_vocabulary_item(db_path, text="departure", meaning_zh="出发", tags=["机场", "CET-6"])
        item = get_vocabulary_item(db_path, vid)
        assert item["tags"] == ["机场", "CET-6"]

    def test_get_nonexistent_item_returns_none(self, db_path):
        assert get_vocabulary_item(db_path, 999) is None

    def test_list_by_tag(self, db_path):
        create_vocabulary_item(db_path, text="a", tags=["CET-6", "动词"])
        create_vocabulary_item(db_path, text="b", tags=["CET-6", "名词"])
        create_vocabulary_item(db_path, text="c", tags=["雅思"])

        cet6_items = list_vocabulary_by_tag(db_path, "CET-6")
        assert len(cet6_items) == 2

        ielts_items = list_vocabulary_by_tag(db_path, "雅思")
        assert len(ielts_items) == 1

    def test_list_by_source_type(self, db_path):
        create_vocabulary_item(db_path, text="a", source_type="CET6_VOCAB")
        create_vocabulary_item(db_path, text="b", source_type="SIDEQUEST_ENV")
        create_vocabulary_item(db_path, text="c", source_type="CET6_VOCAB")

        cet6 = list_vocabulary_by_source(db_path, "CET6_VOCAB")
        assert len(cet6) == 2

        env = list_vocabulary_by_source(db_path, "SIDEQUEST_ENV")
        assert len(env) == 1

    def test_empty_query_returns_empty_list(self, db_path):
        assert list_vocabulary_by_tag(db_path, "nonexistent") == []
        assert list_vocabulary_by_source(db_path, "NONE") == []


class TestSkillVersionRepository:
    """Skill 版本 Repository 测试。"""

    def test_create_and_get_skill_version(self, db_path):
        svid = create_skill_version(
            db_path,
            skill_id="vocab_context",
            version="1.0.0",
            target_ability="VOCABULARY_CONTEXT",
            applicable_conditions={"min_level": "beginner"},
            difficulty_params={"levels": [1, 2, 3]},
            generation_rules={"template": "context_cloze"},
            quality_requirements={"min_options": 4},
            observable_evidence={"track": ["accuracy", "time"]},
            common_error_types=["近义词混淆", "脱离上下文"],
        )
        sv = get_skill_version(db_path, "vocab_context", "1.0.0")
        assert sv is not None
        assert sv["id"] == svid
        assert sv["target_ability"] == "VOCABULARY_CONTEXT"
        assert sv["applicable_conditions"] == {"min_level": "beginner"}
        assert sv["difficulty_params"] == {"levels": [1, 2, 3]}
        assert sv["generation_rules"] == {"template": "context_cloze"}
        assert sv["quality_requirements"] == {"min_options": 4}
        assert sv["observable_evidence"] == {"track": ["accuracy", "time"]}
        assert sv["common_error_types"] == ["近义词混淆", "脱离上下文"]

    def test_skill_id_version_unique(self, db_path):
        create_skill_version(db_path, skill_id="vocab_context", version="1.0.0", target_ability="VOCABULARY_CONTEXT")
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            create_skill_version(db_path, skill_id="vocab_context", version="1.0.0", target_ability="VOCABULARY_CONTEXT")

    def test_get_nonexistent_skill_returns_none(self, db_path):
        assert get_skill_version(db_path, "nonexistent", "1.0.0") is None

    def test_multiple_skills(self, db_path):
        create_skill_version(db_path, skill_id="vocab_context", version="1.0.0", target_ability="VOCABULARY_CONTEXT")
        create_skill_version(db_path, skill_id="sentence_logic", version="1.0.0", target_ability="SENTENCE_LOGIC")
        create_skill_version(db_path, skill_id="vocab_context", version="2.0.0", target_ability="VOCABULARY_CONTEXT")

        v1 = get_skill_version(db_path, "vocab_context", "1.0.0")
        v2 = get_skill_version(db_path, "vocab_context", "2.0.0")
        assert v1 is not None
        assert v2 is not None
        assert v1["id"] != v2["id"]


class TestCandidateVocabularyEventRepository:
    """候选词事件 Repository 测试。"""

    def test_create_and_list_events(self, user_id, db_path):
        create_candidate_event(
            db_path,
            user_id=user_id,
            workflow_stage="FIRST_MAIN",
            ability="VOCABULARY_CONTEXT",
            candidate_items=[{"vocab_id": 1, "text": "abandon"}],
            included_sidequest_signal_ids=[],
            selection_reason="诊断结果显示词汇弱",
        )
        create_candidate_event(
            db_path,
            user_id=user_id,
            workflow_stage="SECOND_PLAN",
            ability="SENTENCE_LOGIC",
            candidate_items=[{"vocab_id": 2, "text": "however"}],
            included_sidequest_signal_ids=[5, 6],
            selection_reason="副线信号引入",
        )

        events = get_recent_candidate_events(db_path, user_id, limit=10)
        assert len(events) == 2
        # 按创建顺序排序
        assert events[0]["workflow_stage"] == "FIRST_MAIN"
        assert events[1]["workflow_stage"] == "SECOND_PLAN"

    def test_sidequest_signal_refs_preserved(self, user_id, db_path):
        create_candidate_event(
            db_path,
            user_id=user_id,
            workflow_stage="FIRST_MAIN",
            ability="VOCABULARY_CONTEXT",
            candidate_items=[{"vocab_id": 3}],
            included_sidequest_signal_ids=[10, 20],
        )
        events = get_recent_candidate_events(db_path, user_id)
        assert len(events) == 1
        assert events[0]["included_sidequest_signal_ids"] == [10, 20]

    def test_respects_limit(self, user_id, db_path):
        for i in range(5):
            create_candidate_event(
                db_path, user_id=user_id, workflow_stage="FIRST_MAIN",
                ability="VOCABULARY_CONTEXT", candidate_items=[{"i": i}],
            )
        events = get_recent_candidate_events(db_path, user_id, limit=3)
        assert len(events) == 3

    def test_no_events_returns_empty_list(self, user_id, db_path):
        assert get_recent_candidate_events(db_path, user_id) == []

    def test_candidate_items_are_objects(self, user_id, db_path):
        items = [{"vocab_id": 10, "text": "example"}]
        create_candidate_event(
            db_path, user_id=user_id, workflow_stage="FIRST_MAIN",
            ability="VOCABULARY_CONTEXT", candidate_items=items,
        )
        events = get_recent_candidate_events(db_path, user_id)
        assert events[0]["candidate_items"] == items
