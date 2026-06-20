"""训练任务质量校验服务测试。

测试 validate_training_task_content 和 record_task_validation_result。
"""

from __future__ import annotations

import pytest

from app.database import init_database
from app.repositories.training import create_generated_task, create_task_validation
from app.services.task_validation import (
    record_task_validation_result,
    validate_training_task_content,
)
from factories import create_user_with_session
from temp_paths import temp_db_path


# --------------- 测试数据 ---------------

_VALID_CONTENT: dict = {
    "title": "词汇测试",
    "raw_text": "Climate change affects ecosystems.",
    "instructions": "请选择正确答案。",
    "questions": [
        {
            "question_id": "q1",
            "question_type": "MULTIPLE_CHOICE",
            "prompt": "climate 最接近？",
            "options": [
                {"id": "A", "text": "气候"},
                {"id": "B", "text": "环境"},
                {"id": "C", "text": "变化"},
                {"id": "D", "text": "温度"},
            ],
            "answer": "A",
            "explanation": "climate 指气候。",
            "target_ability": "VOCABULARY_CONTEXT",
        },
    ],
    "agent_feedback": "",
    "source": "TEST",
}


class TestValidateTrainingTaskContent:
    """测试 validate_training_task_content 函数。"""

    def test_合法任务返回_PASSED(self) -> None:
        result = validate_training_task_content(_VALID_CONTENT)
        assert result["status"] == "PASSED"
        assert result["error_codes"] == []
        assert result["error_details"] == {}

    def test_非_MULTIPLE_CHOICE_返回_FAILED(self) -> None:
        content = {**_VALID_CONTENT, "questions": [
            {**_VALID_CONTENT["questions"][0], "question_type": "FILL_IN_BLANK"},
        ]}
        result = validate_training_task_content(content)
        assert result["status"] == "FAILED"
        assert "UNSUPPORTED_QUESTION_TYPE" in result["error_codes"]

    def test_重复_question_id_返回_FAILED(self) -> None:
        q = _VALID_CONTENT["questions"][0]
        content = {**_VALID_CONTENT, "questions": [q, q]}
        result = validate_training_task_content(content)
        assert result["status"] == "FAILED"
        assert "DUPLICATE_QUESTION_ID" in result["error_codes"]

    def test_标准答案不在_options_中返回_FAILED(self) -> None:
        q = {**_VALID_CONTENT["questions"][0], "answer": "E"}
        content = {**_VALID_CONTENT, "questions": [q]}
        result = validate_training_task_content(content)
        assert result["status"] == "FAILED"
        assert "ANSWER_NOT_IN_OPTIONS" in result["error_codes"]

    def test_非法_target_ability_返回_FAILED(self) -> None:
        q = {**_VALID_CONTENT["questions"][0], "target_ability": "INVALID_ABILITY"}
        content = {**_VALID_CONTENT, "questions": [q]}
        result = validate_training_task_content(content)
        assert result["status"] == "FAILED"
        assert "INVALID_TARGET_ABILITY" in result["error_codes"]

    def test_缺少_title_返回_FAILED(self) -> None:
        content = {k: v for k, v in _VALID_CONTENT.items() if k != "title"}
        result = validate_training_task_content(content)
        assert result["status"] == "FAILED"

    def test_缺少_instructions_返回_FAILED(self) -> None:
        content = {k: v for k, v in _VALID_CONTENT.items() if k != "instructions"}
        result = validate_training_task_content(content)
        assert result["status"] == "FAILED"

    def test_无_questions_返回_FAILED(self) -> None:
        content = {**_VALID_CONTENT, "questions": []}
        result = validate_training_task_content(content)
        assert result["status"] == "FAILED"


class TestRecordTaskValidationResult:
    """测试 record_task_validation_result 函数。"""

    def test_validation_记录可读回(self) -> None:
        db_path = str(temp_db_path("task_validation"))
        init_database(db_path)
        ctx = create_user_with_session(db_path)
        tid = create_generated_task(
            db_path,
            session_id=ctx["session_id"],
            user_id=ctx["user_id"],
            task_type="LOW_PRESSURE_LEARNING",
            target_ability="VOCABULARY_CONTEXT",
            content_json=_VALID_CONTENT,
        )
        validation_result = {
            "status": "PASSED",
            "error_codes": [],
            "error_details": {},
        }
        vid = record_task_validation_result(
            db_path,
            task_id=tid,
            validation_result=validation_result,
            attempt_number=1,
        )
        assert vid >= 1

    def test_FAILED_校验包含稳定_error_code(self) -> None:
        result = validate_training_task_content({})
        assert result["status"] == "FAILED"
        assert len(result["error_codes"]) > 0
        for code in result["error_codes"]:
            assert isinstance(code, str)
            assert len(code) > 0
