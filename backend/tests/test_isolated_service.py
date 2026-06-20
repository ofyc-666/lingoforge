"""隔离测试服务与模型测试。

测试 sanitize_isolated_item 和隔离测试请求/响应 Pydantic 模型。
"""

from __future__ import annotations

import json

import pytest

from app.api.isolated_models import (
    IsolatedTestStartRequest,
    IsolatedTestSubmitRequest,
    IsolatedTestSubmitResponse,
)
from app.services.isolated_tests import sanitize_isolated_item


# --------------- sanitize_isolated_item ---------------


class TestSanitizeIsolatedItem:
    """测试 sanitize_isolated_item 安全性。"""

    _FULL_ITEM: dict = {
        "item_id": 1,
        "item_order": 1,
        "target_ability": "VOCABULARY_CONTEXT",
        "item_version": "v1",
        "prompt": "climate 最接近哪一项？",
        "options": [{"id": "A", "text": "气候"}, {"id": "B", "text": "环境"}],
        "answer_key": {"correct": "A"},
        "answer_rationale": {"reason": "climate 意为气候"},
        "distractor_rationale": {"B": "环境不是 climate"},
        "explanation": "详细解释",
        "standard_answer": "A",
        "internal_notes": "内部备注",
    }

    def test_输出只包含允许字段(self) -> None:
        result = sanitize_isolated_item(self._FULL_ITEM)
        allowed_keys = {"item_id", "item_order", "target_ability", "item_version", "prompt", "options"}
        assert set(result.keys()) == allowed_keys
        assert result["item_id"] == 1
        assert result["target_ability"] == "VOCABULARY_CONTEXT"

    def test_输出不包含_answer_key(self) -> None:
        result = sanitize_isolated_item(self._FULL_ITEM)
        dumped = json.dumps(result, ensure_ascii=False)
        assert "answer_key" not in result
        assert "answer_key" not in dumped

    def test_输出不包含_answer_rationale(self) -> None:
        result = sanitize_isolated_item(self._FULL_ITEM)
        assert "answer_rationale" not in result

    def test_输出不包含_distractor_rationale(self) -> None:
        result = sanitize_isolated_item(self._FULL_ITEM)
        assert "distractor_rationale" not in result

    def test_输出不包含_explanation(self) -> None:
        result = sanitize_isolated_item(self._FULL_ITEM)
        assert "explanation" not in result

    def test_输出不包含_standard_answer(self) -> None:
        result = sanitize_isolated_item(self._FULL_ITEM)
        assert "standard_answer" not in result


# --------------- 请求模型禁止身份字段 ---------------


class TestIsolatedTestStartRequest:
    """验证 start 请求模型禁止身份字段。"""

    def test_含_user_id_被拒绝(self) -> None:
        with pytest.raises(Exception):
            IsolatedTestStartRequest(
                target_ability="VOCABULARY_CONTEXT",
                limit=3,
                user_id=1,  # type: ignore[call-arg]
            )

    def test_含_session_id_被拒绝(self) -> None:
        with pytest.raises(Exception):
            IsolatedTestStartRequest(
                target_ability="VOCABULARY_CONTEXT",
                limit=3,
                session_id=1,  # type: ignore[call-arg]
            )

    def test_含_permission_scope_被拒绝(self) -> None:
        with pytest.raises(Exception):
            IsolatedTestStartRequest(
                target_ability="VOCABULARY_CONTEXT",
                limit=3,
                permission_scope="admin",  # type: ignore[call-arg]
            )

    def test_合法参数创建成功(self) -> None:
        req = IsolatedTestStartRequest(
            target_ability="VOCABULARY_CONTEXT",
            limit=3,
        )
        assert req.target_ability == "VOCABULARY_CONTEXT"
        assert req.limit == 3


class TestIsolatedTestSubmitRequest:
    """验证 submit 请求模型禁止身份字段。"""

    def test_含_user_id_被拒绝(self) -> None:
        with pytest.raises(Exception):
            IsolatedTestSubmitRequest(
                answers=[{"item_id": 1, "answer": "A"}],
                time_spent_seconds=60,
                user_id=1,  # type: ignore[call-arg]
            )

    def test_合法参数创建成功(self) -> None:
        req = IsolatedTestSubmitRequest(
            answers=[{"item_id": 1, "answer": "A"}],
            time_spent_seconds=60,
        )
        assert len(req.answers) == 1
        assert req.time_spent_seconds == 60
