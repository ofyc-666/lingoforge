"""隔离检测题与尝试 Repository 测试。"""

from __future__ import annotations

import pytest

from app.database import init_database
from app.repositories.users import create_user
from app.repositories.isolated_tests import (
    add_item_to_attempt,
    create_isolated_test_attempt,
    create_isolated_test_item,
    get_attempt_with_items,
    get_items_for_attempt,
    list_active_items_by_ability,
)
from temp_paths import temp_db_path


@pytest.fixture
def db_path():
    path = temp_db_path("isolated_repo")
    init_database(path)
    return path


@pytest.fixture
def user_id(db_path):
    return create_user(db_path, "隔离测试用户")


@pytest.fixture
def item_a(db_path):
    return create_isolated_test_item(
        db_path,
        target_ability="VOCABULARY_CONTEXT",
        item_version="1.0",
        item_payload={"question": "Q1", "options": ["A", "B", "C", "D"]},
        answer_key={"correct": "B"},
        answer_rationale={"B": "上下文线索..."},
        distractor_rationale={"A": "干扰原因"},
    )


@pytest.fixture
def item_b(db_path):
    return create_isolated_test_item(
        db_path,
        target_ability="SENTENCE_LOGIC",
        item_version="1.0",
        item_payload={"question": "Q2"},
        answer_key={"correct": "A"},
    )


class TestIsolatedTestItemRepository:
    """隔离题 Repository 测试。"""

    def test_create_item(self, db_path):
        iid = create_isolated_test_item(
            db_path, target_ability="VOCABULARY_CONTEXT", item_version="1.0",
            item_payload={"q": "test"}, answer_key={"k": "v"},
        )
        assert iid >= 1

    def test_default_is_active(self, db_path, item_a):
        from app.repositories.base import fetch_one
        item = fetch_one(db_path, "SELECT * FROM isolated_test_items WHERE id = ?", (item_a,))
        assert item["is_active"] == 1

    def test_create_inactive_item(self, db_path):
        iid = create_isolated_test_item(
            db_path, target_ability="VOCABULARY_CONTEXT", item_version="1.0",
            item_payload={}, answer_key={}, is_active=False,
        )
        from app.repositories.base import fetch_one
        item = fetch_one(db_path, "SELECT * FROM isolated_test_items WHERE id = ?", (iid,))
        assert item["is_active"] == 0

    def test_list_active_by_ability(self, db_path, item_a, item_b):
        active_vocab = list_active_items_by_ability(db_path, "VOCABULARY_CONTEXT")
        assert len(active_vocab) == 1
        assert active_vocab[0]["id"] == item_a

        active_logic = list_active_items_by_ability(db_path, "SENTENCE_LOGIC")
        assert len(active_logic) == 1
        assert active_logic[0]["id"] == item_b

    def test_inactive_items_excluded(self, db_path):
        create_isolated_test_item(
            db_path, target_ability="VOCABULARY_CONTEXT", item_version="1.0",
            item_payload={}, answer_key={}, is_active=False,
        )
        assert list_active_items_by_ability(db_path, "VOCABULARY_CONTEXT") == []

    def test_json_fields_preserved(self, db_path, item_a):
        from app.repositories.base import fetch_one
        item = fetch_one(db_path, "SELECT * FROM isolated_test_items WHERE id = ?", (item_a,))
        from app.storage.json_fields import from_json_text
        payload = from_json_text(item["item_payload"], {})
        assert payload["question"] == "Q1"
        answer_key = from_json_text(item["answer_key"], {})
        assert answer_key["correct"] == "B"

    def test_no_active_items_returns_empty(self, db_path):
        assert list_active_items_by_ability(db_path, "NONEXISTENT") == []


class TestIsolatedAttemptRepository:
    """隔离检测尝试 Repository 测试。"""

    def test_create_attempt(self, db_path, user_id):
        aid = create_isolated_test_attempt(
            db_path, user_id=user_id,
            user_answers={"1": "B"}, score_json={"total": 1, "correct": 1},
            time_spent_seconds=120,
        )
        assert aid >= 1

    def test_attempt_with_session(self, db_path, user_id):
        from app.repositories.training import create_training_session
        sid = create_training_session(db_path, user_id=user_id, stage="ISOLATED_TEST")
        aid = create_isolated_test_attempt(
            db_path, user_id=user_id, session_id=sid,
            user_answers={}, score_json={},
        )
        assert aid >= 1

    def test_add_items_to_attempt(self, db_path, user_id, item_a, item_b):
        aid = create_isolated_test_attempt(db_path, user_id=user_id, user_answers={}, score_json={})
        add_item_to_attempt(db_path, attempt_id=aid, item_id=item_a, item_order=1, item_version="1.0")
        add_item_to_attempt(db_path, attempt_id=aid, item_id=item_b, item_order=2, item_version="1.0")

        items = get_items_for_attempt(db_path, aid)
        assert len(items) == 2
        assert items[0]["item_order"] == 1
        assert items[1]["item_order"] == 2

    def test_duplicate_item_prevented(self, db_path, user_id, item_a):
        import sqlite3
        aid = create_isolated_test_attempt(db_path, user_id=user_id, user_answers={}, score_json={})
        add_item_to_attempt(db_path, attempt_id=aid, item_id=item_a, item_order=1, item_version="1.0")
        with pytest.raises(sqlite3.IntegrityError):
            add_item_to_attempt(db_path, attempt_id=aid, item_id=item_a, item_order=2, item_version="1.0")

    def test_get_attempt_with_items(self, db_path, user_id, item_a, item_b):
        aid = create_isolated_test_attempt(
            db_path, user_id=user_id,
            user_answers={"1": "B", "2": "A"},
            score_json={"total": 2, "correct": 2},
            time_spent_seconds=180,
        )
        add_item_to_attempt(db_path, attempt_id=aid, item_id=item_a, item_order=1, item_version="1.0")
        add_item_to_attempt(db_path, attempt_id=aid, item_id=item_b, item_order=2, item_version="1.0")

        result = get_attempt_with_items(db_path, aid)
        assert result is not None
        assert result["attempt"]["id"] == aid
        assert result["attempt"]["user_answers"] == {"1": "B", "2": "A"}
        assert result["attempt"]["score_json"] == {"total": 2, "correct": 2}
        assert result["attempt"]["time_spent_seconds"] == 180
        assert len(result["items"]) == 2

    def test_get_nonexistent_attempt(self, db_path):
        assert get_attempt_with_items(db_path, 999) is None
        assert get_items_for_attempt(db_path, 999) == []
