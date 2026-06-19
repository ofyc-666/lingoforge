"""副线运行和副线信号 Repository 测试。"""

from __future__ import annotations

import pytest

from app.database import init_database
from app.repositories.users import create_user
from app.repositories.vocabulary import create_vocabulary_item
from app.repositories.sidequest import (
    create_sidequest_run,
    create_sidequest_signal,
    get_pending_signals,
    get_signals_by_run,
)
from temp_paths import temp_db_path


@pytest.fixture
def db_path():
    path = temp_db_path("sidequest_repo")
    init_database(path)
    return path


@pytest.fixture
def user_id(db_path):
    return create_user(db_path, "副线测试用户")


@pytest.fixture
def run_id(db_path, user_id):
    return create_sidequest_run(
        db_path,
        user_id=user_id,
        task_name="AIRPORT_TICKET_PURCHASE",
        objective={"target": "purchase"},
        result={"status": "done"},
    )


@pytest.fixture
def vocab_id(db_path):
    return create_vocabulary_item(
        db_path, text="boarding_pass", meaning_zh="登机牌",
        tags=["机场"], source_type="SIDEQUEST_ENV",
    )


class TestSidequestRunRepository:
    """副线运行 Repository 测试。"""

    def test_create_run(self, db_path, user_id):
        rid = create_sidequest_run(
            db_path, user_id=user_id, task_name="AIRPORT_TICKET_PURCHASE",
            objective={"target": "buy"}, result={"outcome": "success"},
        )
        assert rid >= 1

    def test_run_with_default_json(self, db_path, user_id):
        rid = create_sidequest_run(db_path, user_id=user_id, task_name="TEST")
        from app.repositories.base import fetch_one
        run = fetch_one(db_path, "SELECT * FROM sidequest_runs WHERE id = ?", (rid,))
        from app.storage.json_fields import from_json_text
        assert from_json_text(run["objective_json"], None) == {}
        assert from_json_text(run["result_json"], None) == {}


class TestSidequestSignalRepository:
    """副线信号 Repository 测试。"""

    def test_create_signal(self, db_path, user_id, run_id, vocab_id):
        sid = create_sidequest_signal(
            db_path,
            user_id=user_id,
            sidequest_run_id=run_id,
            scene="AIRPORT_TICKET",
            vocabulary_item_id=vocab_id,
            expression_text="boarding pass",
            context_json={"npc": "counter"},
            signal_type="EXPOSURE",
        )
        assert sid >= 1

    def test_multiple_signals_per_run(self, db_path, user_id, run_id):
        s1 = create_sidequest_signal(
            db_path, user_id=user_id, sidequest_run_id=run_id,
            scene="AIRPORT_TICKET", signal_type="EXPOSURE",
        )
        s2 = create_sidequest_signal(
            db_path, user_id=user_id, sidequest_run_id=run_id,
            scene="AIRPORT_TICKET", signal_type="CLICKED_HINT",
        )
        assert s1 != s2

        signals = get_signals_by_run(db_path, run_id)
        assert len(signals) == 2

    def test_pending_signals_filter(self, db_path, user_id, run_id):
        # 创建两个信号，只有一个是 pending
        create_sidequest_signal(
            db_path, user_id=user_id, sidequest_run_id=run_id,
            scene="AIRPORT_TICKET", signal_type="EXPOSURE",
        )
        create_sidequest_signal(
            db_path, user_id=user_id, sidequest_run_id=run_id,
            scene="AIRPORT_TICKET", signal_type="TASK_SUCCESS",
        )

        # 直接修改第一条为非 pending
        from app.repositories.base import execute
        execute(db_path, "UPDATE sidequest_signals SET is_pending_verification = 0 WHERE id = 1")

        pending = get_pending_signals(db_path, user_id)
        assert len(pending) == 1

    def test_pending_signals_scoped_to_user(self, db_path, user_id, run_id):
        u2 = create_user(db_path, "另一个用户")
        r2 = create_sidequest_run(db_path, user_id=u2, task_name="TEST")
        create_sidequest_signal(db_path, user_id=user_id, sidequest_run_id=run_id,
                                scene="X", signal_type="EXPOSURE")
        create_sidequest_signal(db_path, user_id=u2, sidequest_run_id=r2,
                                scene="X", signal_type="EXPOSURE")

        assert len(get_pending_signals(db_path, user_id)) == 1
        assert len(get_pending_signals(db_path, u2)) == 1

    def test_signal_json_fields(self, db_path, user_id, run_id, vocab_id):
        ctx = {"npc": "check_in", "dialog": "Where to?"}
        create_sidequest_signal(
            db_path, user_id=user_id, sidequest_run_id=run_id,
            scene="AIRPORT_TICKET", vocabulary_item_id=vocab_id,
            expression_text="check-in counter", context_json=ctx,
            signal_type="MISRECOGNIZED",
        )
        pending = get_pending_signals(db_path, user_id)
        assert len(pending) == 1
        assert pending[0]["context_json"] == ctx
        assert pending[0]["vocabulary_item_id"] == vocab_id
        assert pending[0]["expression_text"] == "check-in counter"

    def test_empty_pending_for_new_user(self, db_path, user_id):
        assert get_pending_signals(db_path, user_id) == []

    def test_no_signals_for_run(self, db_path, run_id):
        assert get_signals_by_run(db_path, run_id) == []

    def test_signal_does_not_write_learning_evidence(self, db_path, user_id, run_id):
        # 副线信号不应写入学习证据表
        create_sidequest_signal(
            db_path, user_id=user_id, sidequest_run_id=run_id,
            scene="AIRPORT_TICKET", signal_type="EXPOSURE",
        )
        from app.repositories.training import get_learning_evidence_by_user
        assert get_learning_evidence_by_user(db_path, user_id) == []
