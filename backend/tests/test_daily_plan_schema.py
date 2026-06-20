"""新表与约束测试。"""

from __future__ import annotations

import pytest

from app.database import init_database
from tests.temp_paths import temp_db_path


class TestNewTablesExist:
    def test_user_vocabulary_states_table(self):
        db = temp_db_path("test")
        init_database(db)
        from app.repositories.base import fetch_all
        rows = fetch_all(db, "SELECT name FROM sqlite_master WHERE type='table' AND name='user_vocabulary_states'")
        assert len(rows) == 1

    def test_vocabulary_review_events_table(self):
        db = temp_db_path("test")
        init_database(db)
        from app.repositories.base import fetch_all
        rows = fetch_all(db, "SELECT name FROM sqlite_master WHERE type='table' AND name='vocabulary_review_events'")
        assert len(rows) == 1

    def test_daily_learning_plans_table(self):
        db = temp_db_path("test")
        init_database(db)
        from app.repositories.base import fetch_all
        rows = fetch_all(db, "SELECT name FROM sqlite_master WHERE type='table' AND name='daily_learning_plans'")
        assert len(rows) == 1

    def test_daily_plan_vocabulary_items_table(self):
        db = temp_db_path("test")
        init_database(db)
        from app.repositories.base import fetch_all
        rows = fetch_all(db, "SELECT name FROM sqlite_master WHERE type='table' AND name='daily_plan_vocabulary_items'")
        assert len(rows) == 1

    def test_vocabulary_text_unique_index(self):
        db = temp_db_path("test")
        init_database(db)
        from app.repositories.base import fetch_all
        rows = fetch_all(db, "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_vocabulary_items_text'")
        assert len(rows) == 1


class TestVocabularyStateConstraints:
    def test_user_vocabulary_unique_constraint(self):
        db = temp_db_path("test")
        init_database(db)
        from app.repositories.daily_plan import upsert_user_vocabulary_state
        from app.repositories.users import create_user
        from app.repositories.vocabulary import create_vocabulary_item

        uid = create_user(db, "测试用户")
        vid = create_vocabulary_item(db, "test_word", source_type="CET6_VOCAB")

        # 第一次 upsert
        sid1 = upsert_user_vocabulary_state(db, user_id=uid, vocabulary_item_id=vid)
        # 第二次 upsert —— 应更新同一行，不创建新行
        sid2 = upsert_user_vocabulary_state(db, user_id=uid, vocabulary_item_id=vid)
        assert sid1 == sid2

    def test_counts_non_negative(self):
        db = temp_db_path("test")
        init_database(db)
        from app.repositories.daily_plan import upsert_user_vocabulary_state
        from app.repositories.users import create_user
        from app.repositories.vocabulary import create_vocabulary_item

        uid = create_user(db, "测试用户")
        vid = create_vocabulary_item(db, "word", source_type="CET6_VOCAB")
        sid = upsert_user_vocabulary_state(
            db, user_id=uid, vocabulary_item_id=vid,
            correct_count=5, wrong_count=3, context_error_count=2,
            consecutive_correct=2, consecutive_wrong=1,
        )
        from app.repositories.daily_plan import get_user_vocabulary_state
        state = get_user_vocabulary_state(db, uid, vid)
        assert state is not None
        assert state["correct_count"] == 5
        assert state["wrong_count"] == 3
        assert state["consecutive_correct"] == 2


class TestDailyPlanVocabularyItemsUnique:
    def test_plan_vocab_unique(self):
        db = temp_db_path("test")
        init_database(db)
        from app.repositories.users import create_user
        from app.repositories.vocabulary import create_vocabulary_item
        from app.repositories.daily_plan import (
            create_daily_plan, add_plan_vocabulary_item,
        )
        import datetime
        uid = create_user(db, "测试")
        vid = create_vocabulary_item(db, "word1", source_type="CET6_VOCAB")
        plan_id = create_daily_plan(db, user_id=uid, session_id=None,
                                     plan_date=datetime.date.today().isoformat())
        add_plan_vocabulary_item(db, plan_id=plan_id, vocabulary_item_id=vid, word_role="NEW")
        # 第二次插入应失败（UNIQUE constraint）
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            add_plan_vocabulary_item(db, plan_id=plan_id, vocabulary_item_id=vid, word_role="NEW")


class TestDatabaseDoubleInit:
    def test_init_database_idempotent(self):
        db = temp_db_path("test")
        init_database(db)
        init_database(db)  # 不应报错
        from app.repositories.base import fetch_all
        rows = fetch_all(db, "SELECT COUNT(*) as cnt FROM sqlite_master WHERE type='table'")
        assert rows[0]["cnt"] > 10
