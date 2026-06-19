"""训练任务薄封装服务测试。"""

from __future__ import annotations

import pytest

from app.database import init_database
from app.repositories.training import get_generated_task
from app.repositories.users import create_user
from app.services.training_tasks import (
    TrainingTaskAccessError,
    TrainingTaskNotFoundError,
    create_task_from_analysis,
    get_user_training_task,
)
from factories import create_user_with_session
from temp_paths import temp_db_path


@pytest.fixture
def db_path():
    path = temp_db_path("training_task_svc")
    init_database(path)
    return path


@pytest.fixture
def ctx(db_path):
    return create_user_with_session(db_path)


@pytest.fixture
def user_id(ctx):
    return ctx["user_id"]


@pytest.fixture
def session_id(ctx):
    return ctx["session_id"]


@pytest.fixture
def other_user_id(db_path):
    return create_user(db_path, "其他用户")


def _sample_analysis() -> dict:
    return {
        "analysis_id": "analysis_test_01",
        "raw_text": "Climate change is a pressing challenge.",
        "keywords": [
            {
                "text": "climate",
                "meaning_zh": "气候",
                "usage_note": "常与 change、warming 搭配。",
                "ability": "VOCABULARY_CONTEXT",
                "selection_reason": "文本关键词。",
            },
            {
                "text": "change",
                "meaning_zh": "变化",
                "usage_note": "广泛使用。",
                "ability": "SENTENCE_LOGIC",
                "selection_reason": "文本关键词。",
            },
        ],
        "exercise": {
            "question_id": "q1",
            "question_type": "MULTIPLE_CHOICE",
            "prompt": "climate 最接近哪一项？",
            "options": [
                {"id": "A", "text": "气候"},
                {"id": "B", "text": "变化"},
            ],
            "answer": "A",
            "explanation": "climate = 气候。",
            "target_ability": "VOCABULARY_CONTEXT",
        },
        "agent_feedback": "Mock 反馈。",
        "source": "MOCK_DETERMINISTIC",
        "warnings": [],
    }


class TestCreateTaskFromAnalysis:
    """create_task_from_analysis 测试。"""

    def test_creates_task_and_reads_back(self, db_path, user_id, session_id):
        analysis = _sample_analysis()
        task_id = create_task_from_analysis(db_path, user_id=user_id, session_id=session_id, analysis=analysis)
        assert task_id >= 1

        task = get_generated_task(db_path, task_id)
        assert task is not None
        assert task["user_id"] == user_id
        assert task["session_id"] == session_id
        assert task["task_type"] == "LOW_PRESSURE_LEARNING"
        assert task["target_ability"] == "VOCABULARY_CONTEXT"
        # content_json 包含题目
        content = task["content_json"]
        assert len(content["questions"]) == 1
        assert content["title"]
        assert content["instructions"]
        # quality_check_result 标记 PASSED
        assert task["quality_check_result"]["status"] == "PASSED"

    def test_task_type_is_always_low_pressure_learning(self, db_path, user_id, session_id):
        task_id = create_task_from_analysis(db_path, user_id=user_id, session_id=session_id, analysis=_sample_analysis())
        task = get_generated_task(db_path, task_id)
        assert task["task_type"] == "LOW_PRESSURE_LEARNING"

    def test_target_ability_falls_back_when_no_keywords(self, db_path, user_id, session_id):
        analysis = _sample_analysis()
        analysis["keywords"] = []
        task_id = create_task_from_analysis(db_path, user_id=user_id, session_id=session_id, analysis=analysis)
        task = get_generated_task(db_path, task_id)
        assert task["target_ability"] == "VOCABULARY_CONTEXT"


class TestGetUserTrainingTask:
    """get_user_training_task 测试。"""

    def test_returns_task_for_owner(self, db_path, user_id, session_id):
        task_id = create_task_from_analysis(db_path, user_id=user_id, session_id=session_id, analysis=_sample_analysis())
        task = get_user_training_task(db_path, user_id=user_id, task_id=task_id)
        assert task is not None
        assert task["id"] == task_id

    def test_rejects_other_user(self, db_path, user_id, other_user_id, session_id):
        task_id = create_task_from_analysis(db_path, user_id=user_id, session_id=session_id, analysis=_sample_analysis())
        with pytest.raises(TrainingTaskAccessError) as exc:
            get_user_training_task(db_path, user_id=other_user_id, task_id=task_id)
        assert "无权访问" in str(exc.value)

    def test_raises_not_found_for_nonexistent_task(self, db_path, user_id):
        with pytest.raises(TrainingTaskNotFoundError) as exc:
            get_user_training_task(db_path, user_id=user_id, task_id=999)
        assert "不存在" in str(exc.value)
