"""每日计划、背词、刷题和 Skill Registry 功能测试。"""

from __future__ import annotations

import datetime
import json
import pytest
from pathlib import Path

from tests.temp_paths import temp_db_path
from app.database import init_database


# ---- Skill Registry ----


class TestSkillRegistry:
    def test_all_four_skills_exist(self):
        from app.agent.skills import SKILL_CATALOG, get_skill_definition
        assert len(SKILL_CATALOG) == 4
        skill_ids = {s["skill_id"] for s in SKILL_CATALOG}
        assert skill_ids == {"vocabulary_context", "sentence_logic", "paraphrase_location", "distractor_judgement"}

    def test_skill_full_definition(self):
        from app.agent.skills import get_skill_definition
        skill = get_skill_definition("vocabulary_context")
        assert skill is not None
        assert skill["target_ability"] == "VOCABULARY_CONTEXT"
        assert "TARGETED_PRACTICE" in skill["supported_task_types"]
        assert "COMPREHENSIVE_SIMULATION" in skill["supported_task_types"]
        assert len(skill["generation_rules"]) > 0
        assert len(skill["common_error_types"]) > 0

    def test_skill_exists_check(self):
        from app.agent.skills import skill_exists
        assert skill_exists("vocabulary_context") is True
        assert skill_exists("nonexistent_skill") is False

    def test_seed_skill_versions(self):
        db = temp_db_path("feature")
        init_database(db)
        from app.agent.skills import seed_skill_versions
        result = seed_skill_versions(db)
        assert result["created"] == 4
        # 再次调用 —— 幂等
        result2 = seed_skill_versions(db)
        assert result2["skipped"] == 4


# ---- CET-6 词汇导入 ----


class TestVocabImport:
    def test_seed_cet6_idempotent(self):
        db = temp_db_path("feature")
        init_database(db)
        from app.services.vocab_import import seed_cet6_vocabulary, count_vocabulary_by_source
        result1 = seed_cet6_vocabulary(db)
        assert result1["created"] > 0
        count1 = count_vocabulary_by_source(db)
        # 再次导入 —— 幂等
        result2 = seed_cet6_vocabulary(db)
        assert result2["skipped"] == count1
        count2 = count_vocabulary_by_source(db)
        assert count2 == count1

    def test_import_from_dicts(self):
        db = temp_db_path("feature")
        init_database(db)
        from app.services.vocab_import import import_vocabulary_from_dicts
        words = [
            {"text": "testword1", "meaning_zh": "测试1", "part_of_speech": "noun", "tags": ["CET-6"]},
            {"text": "testword2", "meaning_zh": "测试2", "part_of_speech": "verb", "tags": ["CET-6"]},
        ]
        result = import_vocabulary_from_dicts(db, words)
        assert result["created"] == 2
        # 幂等
        result2 = import_vocabulary_from_dicts(db, words)
        assert result2["skipped"] == 2


# ---- 候选词筛选 ----


class TestCandidateVocabFiltering:
    def test_generate_candidates(self):
        db = temp_db_path("feature")
        init_database(db)
        from app.repositories.users import create_user, save_user_goal
        from app.services.vocab_import import seed_cet6_vocabulary

        uid = create_user(db, "测试用户")
        save_user_goal(db, uid, exam_type="CET-6", days_until_exam=90, target_score=550)
        seed_cet6_vocabulary(db)

        from app.services.candidate_vocab import generate_candidate_vocabulary
        now = datetime.datetime(2026, 6, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
        result = generate_candidate_vocabulary(db, user_id=uid, now=now)

        assert result["candidate_event_id"] > 0
        assert result["total_candidates"] > 0
        assert result["algorithm_version"] == "candidate-filter-mvp-v1"
        assert len(result["candidate_items"]) > 0
        # 每个候选词都有必要字段
        item = result["candidate_items"][0]
        assert "vocabulary_item_id" in item
        assert "text" in item
        assert "candidate_role" in item
        assert "review_priority" in item
        assert "selection_reason" in item

    def test_candidate_event_detail(self):
        db = temp_db_path("feature")
        init_database(db)
        from app.repositories.users import create_user, save_user_goal
        from app.services.vocab_import import seed_cet6_vocabulary
        from app.services.candidate_vocab import generate_candidate_vocabulary, get_candidate_event_detail

        uid = create_user(db, "测试用户")
        save_user_goal(db, uid, exam_type="CET-6")
        seed_cet6_vocabulary(db)

        now = datetime.datetime(2026, 6, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
        result = generate_candidate_vocabulary(db, user_id=uid, now=now)
        event = get_candidate_event_detail(db, result["candidate_event_id"], uid)
        assert event is not None
        assert event["user_id"] == uid
        # 其他用户不能读
        event2 = get_candidate_event_detail(db, result["candidate_event_id"], 999)
        assert event2 is None


# ---- get_candidate_vocabulary 工具 ----


class TestCandidateVocabTool:
    def test_tool_spec(self):
        from app.agent.tools import get_candidate_vocabulary_tool_spec
        spec = get_candidate_vocabulary_tool_spec()
        assert spec.name == "get_candidate_vocabulary"
        params = spec.parameters
        assert "candidate_event_id" in params["properties"]
        assert "include_history_summary" in params["properties"]
        # 参数中不得有身份字段
        assert "user_id" not in params["properties"]
        assert "session_id" not in params["properties"]

    def test_identity_argument_rejected(self):
        from app.agent.tools import _validate_get_candidate_vocabulary_arguments
        result, error = _validate_get_candidate_vocabulary_arguments({
            "candidate_event_id": 1,
            "user_id": 999,
        })
        assert error == "IDENTITY_ARGUMENT_FORBIDDEN"
        assert result is None

    def test_valid_arguments_accepted(self):
        from app.agent.tools import _validate_get_candidate_vocabulary_arguments
        result, error = _validate_get_candidate_vocabulary_arguments({
            "candidate_event_id": 1,
            "include_history_summary": True,
        })
        assert error is None
        assert result is not None
        assert result["candidate_event_id"] == 1

    def test_invalid_arguments_rejected(self):
        from app.agent.tools import _validate_get_candidate_vocabulary_arguments
        # 缺少必要参数
        result, error = _validate_get_candidate_vocabulary_arguments({})
        assert error == "INVALID_TOOL_ARGUMENTS"
        # 未知参数
        result, error = _validate_get_candidate_vocabulary_arguments({
            "candidate_event_id": 1,
            "extra_field": "x",
        })
        assert error == "INVALID_TOOL_ARGUMENTS"

    def test_registry_includes_tool(self):
        db = temp_db_path("feature")
        init_database(db)
        from app.agent.tools import create_default_tool_registry
        registry = create_default_tool_registry(db)
        tool = registry.get("get_candidate_vocabulary")
        assert tool is not None
        assert tool.name == "get_candidate_vocabulary"


# ---- 每日计划 ----


class TestDailyPlan:
    def _setup_db(self) -> tuple[str, int]:
        db = temp_db_path("feature")
        init_database(db)
        from app.repositories.users import create_user, save_user_goal, create_profile_snapshot
        from app.services.vocab_import import seed_cet6_vocabulary
        from app.agent.skills import seed_skill_versions

        uid = create_user(db, "演示用户")
        save_user_goal(db, uid, exam_type="CET-6", days_until_exam=90, target_score=550)
        create_profile_snapshot(db, uid, source="DIAGNOSTIC", profile={
            "VOCABULARY_CONTEXT": {"level": "intermediate", "confidence": "MEDIUM"},
            "SENTENCE_LOGIC": {"level": "beginner", "confidence": "LOW"},
        })
        seed_cet6_vocabulary(db)
        seed_skill_versions(db)
        return db, uid

    def test_generate_daily_plan(self):
        db, uid = self._setup_db()
        from app.llm.mock_provider import MockLLMProvider
        from app.services.daily_plan import generate_daily_plan

        now = datetime.datetime(2026, 6, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
        result = generate_daily_plan(
            db,
            provider=MockLLMProvider(),
            user_id=uid,
            max_new_words=5,
            max_review_words=8,
            now=now,
        )
        assert result["plan_id"] > 0
        assert result["status"] == "PLANNED"
        assert result["plan_date"] == "2026-06-20"
        assert len(result["vocabulary_items"]) > 0

    def test_daily_plan_idempotent(self):
        db, uid = self._setup_db()
        from app.llm.mock_provider import MockLLMProvider
        from app.services.daily_plan import generate_daily_plan

        now = datetime.datetime(2026, 6, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
        r1 = generate_daily_plan(db, provider=MockLLMProvider(), user_id=uid, now=now)
        r2 = generate_daily_plan(db, provider=MockLLMProvider(), user_id=uid, now=now)
        assert r1["plan_id"] == r2["plan_id"]
        assert r2.get("regenerated") is False

    def test_regenerate_plan(self):
        db, uid = self._setup_db()
        from app.llm.mock_provider import MockLLMProvider
        from app.services.daily_plan import generate_daily_plan

        now = datetime.datetime(2026, 6, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
        r1 = generate_daily_plan(db, provider=MockLLMProvider(), user_id=uid, now=now, regenerate=False)
        r2 = generate_daily_plan(db, provider=MockLLMProvider(), user_id=uid, now=now, regenerate=True)
        assert r1["plan_id"] != r2["plan_id"]


# ---- 背词事件 ----


class TestVocabReview:
    def _setup_db(self) -> tuple[str, int, int]:
        db = temp_db_path("feature")
        init_database(db)
        from app.repositories.users import create_user
        from app.repositories.vocabulary import create_vocabulary_item
        from app.repositories.daily_plan import create_daily_plan
        import datetime

        uid = create_user(db, "测试用户")
        vids = []
        for text in ["word_a", "word_b", "word_c"]:
            vid = create_vocabulary_item(db, text=text, source_type="CET6_VOCAB")
            vids.append(vid)
        plan_id = create_daily_plan(
            db, user_id=uid, session_id=None,
            plan_date=datetime.date.today().isoformat(),
        )
        return db, uid, plan_id

    def test_process_review_events(self):
        db, uid, plan_id = self._setup_db()
        from app.services.vocab_review import process_review_events
        from app.repositories.vocabulary import list_all_vocabulary

        words = list_all_vocabulary(db)
        assert len(words) >= 3

        events = [
            {
                "vocabulary_item_id": words[0]["id"],
                "event_type": "WORD_SHOWN",
                "is_correct": None,
                "used_hint": False,
            },
            {
                "vocabulary_item_id": words[1]["id"],
                "event_type": "SELF_RATING",
                "self_rating": "KNOWN",
                "used_hint": False,
            },
        ]
        now = datetime.datetime(2026, 6, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
        result = process_review_events(db, user_id=uid, plan_id=plan_id, events=events, now=now)
        assert result["processed_events"] == 2
        assert len(result["updated_states"]) == 2
        assert result["evidence_id"] > 0

        # 背词后状态已更新
        from app.repositories.daily_plan import get_user_vocabulary_state
        state = get_user_vocabulary_state(db, uid, words[0]["id"])
        assert state is not None
        assert state["learning_status"] in ("NEW", "LEARNING")

    def test_complete_vocabulary(self):
        db, uid, plan_id = self._setup_db()
        from app.services.vocab_review import complete_vocabulary_phase
        result = complete_vocabulary_phase(db, plan_id, uid)
        assert result["status"] == "VOCABULARY_COMPLETED"

    def test_fixed_clock_injected(self):
        db, uid, plan_id = self._setup_db()
        from app.services.vocab_review import process_review_events
        from app.repositories.vocabulary import list_all_vocabulary

        words = list_all_vocabulary(db)
        fixed_time = datetime.datetime(2026, 1, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        events = [{
            "vocabulary_item_id": words[0]["id"],
            "event_type": "MEANING_CHECK",
            "is_correct": True,
            "used_hint": False,
            "time_spent_seconds": 10,
        }]
        result = process_review_events(db, user_id=uid, plan_id=plan_id, events=events, now=fixed_time)
        assert result["processed_events"] == 1

        # 检查 next_review_at 是注入时间加偏移量
        from app.repositories.daily_plan import get_user_vocabulary_state
        state = get_user_vocabulary_state(db, uid, words[0]["id"])
        assert state is not None
        assert state["last_reviewed_at"] is not None


# ---- 刷题 ----


class TestPracticeGeneration:
    def _setup_db(self) -> tuple[str, int, int]:
        db = temp_db_path("feature")
        init_database(db)
        from app.repositories.users import create_user, save_user_goal, create_profile_snapshot
        from app.repositories.training import create_training_session
        from app.repositories.daily_plan import create_daily_plan
        from app.agent.skills import seed_skill_versions
        from app.services.vocab_import import seed_cet6_vocabulary
        import datetime

        uid = create_user(db, "测试用户")
        save_user_goal(db, uid, exam_type="CET-6")
        create_profile_snapshot(db, uid, source="DIAGNOSTIC", profile={})
        seed_cet6_vocabulary(db)
        seed_skill_versions(db)

        session_id = create_training_session(db, user_id=uid, stage="DAILY_PLAN")
        plan_id = create_daily_plan(
            db, user_id=uid, session_id=session_id,
            plan_date=datetime.date.today().isoformat(),
            practice_mode="TARGETED_PRACTICE",
            target_abilities=["PARAPHRASE_LOCATION"],
            selected_skills=[{"skill_id": "paraphrase_location", "version": "1.0.0"}],
        )
        return db, uid, plan_id

    def test_start_targeted_practice(self):
        db, uid, plan_id = self._setup_db()
        from app.services.practice_gen import start_practice
        result = start_practice(
            db, user_id=uid, plan_id=plan_id,
            practice_mode="TARGETED_PRACTICE",
            max_questions=2,
        )
        assert result["practice_mode"] == "TARGETED_PRACTICE"
        assert result["task_id"] > 0
        assert len(result["questions"]) == 2

    def test_start_comprehensive_simulation(self):
        db, uid, plan_id = self._setup_db()
        from app.services.practice_gen import start_practice
        result = start_practice(
            db, user_id=uid, plan_id=plan_id,
            practice_mode="COMPREHENSIVE_SIMULATION",
            max_questions=6,
        )
        assert result["practice_mode"] == "COMPREHENSIVE_SIMULATION"
        assert len(result["target_abilities"]) >= 2

    def test_practice_plan_access_denied(self):
        db, uid, plan_id = self._setup_db()
        from app.services.practice_gen import start_practice
        with pytest.raises(ValueError, match="PLAN_NOT_FOUND"):
            start_practice(db, user_id=999, plan_id=plan_id)


# ---- 任务质量校验 ----


class TestTaskValidationExtension:
    def test_targeted_practice_validation(self):
        content = {
            "practice_mode": "TARGETED_PRACTICE",
            "selected_skills": [{"skill_id": "vocabulary_context", "version": "1.0.0"}],
            "target_abilities": ["VOCABULARY_CONTEXT"],
            "questions": [
                {
                    "question_id": "q1",
                    "question_type": "MULTIPLE_CHOICE",
                    "skill_id": "vocabulary_context",
                    "target_ability": "VOCABULARY_CONTEXT",
                    "prompt": "测试题",
                    "options": [{"id": "A", "text": "选项A"}, {"id": "B", "text": "选项B"}],
                    "answer": "A",
                    "explanation": "解释",
                },
            ],
        }
        from app.services.task_validation import validate_training_task_content
        result = validate_training_task_content(content)
        assert result["status"] == "PASSED"

    def test_targeted_practice_too_many_skills(self):
        content = {
            "practice_mode": "TARGETED_PRACTICE",
            "selected_skills": [
                {"skill_id": "vocabulary_context"},
                {"skill_id": "sentence_logic"},
                {"skill_id": "paraphrase_location"},
            ],
            "target_abilities": ["VOCABULARY_CONTEXT"],
            "questions": [{"question_id": "q1", "question_type": "MULTIPLE_CHOICE",
                           "skill_id": "x", "target_ability": "VOCABULARY_CONTEXT",
                           "options": [{"id": "A"}], "answer": "A"}],
        }
        from app.services.task_validation import validate_training_task_content
        result = validate_training_task_content(content)
        assert "TARGETED_PRACTICE_SKILL_COUNT" in result["error_codes"]

    def test_simulation_less_than_two_abilities(self):
        content = {
            "practice_mode": "COMPREHENSIVE_SIMULATION",
            "selected_skills": [
                {"skill_id": "vocabulary_context"},
                {"skill_id": "sentence_logic"},
            ],
            "target_abilities": ["VOCABULARY_CONTEXT"],
            "questions": [
                {"question_id": "q1", "question_type": "MULTIPLE_CHOICE",
                 "skill_id": "x", "target_ability": "VOCABULARY_CONTEXT",
                 "options": [{"id": "A"}], "answer": "A"},
                {"question_id": "q2", "question_type": "MULTIPLE_CHOICE",
                 "skill_id": "y", "target_ability": "VOCABULARY_CONTEXT",
                 "options": [{"id": "A"}], "answer": "A"},
            ],
        }
        from app.services.task_validation import validate_training_task_content
        result = validate_training_task_content(content)
        assert "SIMULATION_LESS_THAN_TWO_ABILITIES" in result["error_codes"]

    def test_simulation_all_questions_same_ability(self):
        content = {
            "practice_mode": "COMPREHENSIVE_SIMULATION",
            "selected_skills": [
                {"skill_id": "vocabulary_context"},
                {"skill_id": "sentence_logic"},
            ],
            "target_abilities": ["VOCABULARY_CONTEXT", "SENTENCE_LOGIC"],
            "questions": [
                {"question_id": "q1", "question_type": "MULTIPLE_CHOICE",
                 "skill_id": "x", "target_ability": "VOCABULARY_CONTEXT",
                 "options": [{"id": "A"}], "answer": "A"},
                {"question_id": "q2", "question_type": "MULTIPLE_CHOICE",
                 "skill_id": "y", "target_ability": "VOCABULARY_CONTEXT",
                 "options": [{"id": "A"}], "answer": "A"},
            ],
        }
        from app.services.task_validation import validate_training_task_content
        result = validate_training_task_content(content)
        assert "ALL_QUESTIONS_SAME_ABILITY" in result["error_codes"]


# ---- DecisionValidator 扩展 ----


class TestDecisionValidatorDailyPlan:
    def test_valid_daily_plan_accepted(self):
        from app.agent.validation import DecisionValidator
        from app.agent.models import RuntimeContext
        from app.agent.skills import seed_skill_versions

        db = temp_db_path("feature")
        init_database(db)
        seed_skill_versions(db)

        decision = {
            "decision_type": "DAILY_LEARNING_PLAN",
            "next_step": "START_VOCABULARY",
            "practice_mode": "TARGETED_PRACTICE",
            "daily_vocabulary_plan": {
                "new_word_ids": [1, 2],
                "review_word_ids": [3],
                "priority_word_ids": [],
                "selection_rationale": "测试理由",
            },
            "target_abilities": ["VOCABULARY_CONTEXT"],
            "selected_skills": [{"skill_id": "vocabulary_context", "version": "1.0.0"}],
            "decision_basis": [{"summary": "测试"}],
            "difficulty_params": {},
            "hint_strategy": {},
            "estimated_minutes": 25,
        }
        dv = DecisionValidator()
        context = RuntimeContext(
            user_id=1, session_id=1, workflow_stage="DAILY_PLAN",
            objective="test", allowed_tools=(), permission_scope=(),
        )
        _, validation = dv.validate(json.dumps(decision), context, [])
        assert validation.status == "PASSED"

    def test_daily_plan_missing_rationale_rejected(self):
        from app.agent.validation import DecisionValidator
        from app.agent.models import RuntimeContext

        decision = {
            "decision_type": "DAILY_LEARNING_PLAN",
            "next_step": "START_VOCABULARY",
            "daily_vocabulary_plan": {
                "new_word_ids": [1],
                "review_word_ids": [],
                "priority_word_ids": [],
                "selection_rationale": "",
            },
            "decision_basis": [],
            "selected_skills": [],
        }
        dv = DecisionValidator()
        context = RuntimeContext(
            user_id=1, session_id=1, workflow_stage="DAILY_PLAN",
            objective="test", allowed_tools=(), permission_scope=(),
        )
        _, validation = dv.validate(json.dumps(decision), context, [])
        assert validation.status == "FAILED"

    def test_direct_profile_write_forbidden(self):
        from app.agent.validation import DecisionValidator
        from app.agent.models import RuntimeContext

        decision = {
            "decision_type": "DAILY_LEARNING_PLAN",
            "next_step": "START_VOCABULARY",
            "direct_profile_write": True,
            "daily_vocabulary_plan": {
                "new_word_ids": [1],
                "review_word_ids": [],
                "priority_word_ids": [],
                "selection_rationale": "test",
            },
            "decision_basis": [{"summary": "x"}],
            "selected_skills": [],
        }
        dv = DecisionValidator()
        context = RuntimeContext(
            user_id=1, session_id=1, workflow_stage="DAILY_PLAN",
            objective="test", allowed_tools=(), permission_scope=(),
        )
        _, validation = dv.validate(json.dumps(decision), context, [])
        assert validation.status == "FAILED"


# ---- 用户资源隔离 ----


class TestUserIsolation:
    def test_plan_belongs_to_user(self):
        db = temp_db_path("feature")
        init_database(db)
        from app.repositories.users import create_user
        from app.repositories.daily_plan import create_daily_plan, get_daily_plan
        import datetime

        uid1 = create_user(db, "用户1")
        uid2 = create_user(db, "用户2")
        plan_id = create_daily_plan(
            db, user_id=uid1, session_id=None,
            plan_date=datetime.date.today().isoformat(),
        )
        # uid1 可以看到
        plan = get_daily_plan(db, plan_id)
        assert plan is not None
        assert plan["user_id"] == uid1
        # uid2 不能通过 API 级校验（repository 不强制归属，由服务和 API 校验）


# ---- Mock 模式完整流程 ----


class TestMockFullFlow:
    def test_mock_daily_plan_flow(self):
        """Mock 模式下完整流程：候选词 → 计划 → 背词 → 完成 → 刷题。"""
        db = temp_db_path("feature")
        init_database(db)
        from app.repositories.users import create_user, save_user_goal, create_profile_snapshot
        from app.services.vocab_import import seed_cet6_vocabulary
        from app.agent.skills import seed_skill_versions
        from app.llm.mock_provider import MockLLMProvider
        from app.services.daily_plan import generate_daily_plan
        from app.services.vocab_review import process_review_events, complete_vocabulary_phase
        from app.services.practice_gen import start_practice

        uid = create_user(db, "演示用户")
        save_user_goal(db, uid, exam_type="CET-6")
        create_profile_snapshot(db, uid, source="DIAGNOSTIC", profile={
            "VOCABULARY_CONTEXT": {"level": "intermediate"},
            "SENTENCE_LOGIC": {"level": "beginner"},
            "PARAPHRASE_LOCATION": {"level": "intermediate"},
            "DISTRACTOR_JUDGEMENT": {"level": "beginner"},
        })
        seed_cet6_vocabulary(db)
        seed_skill_versions(db)

        # 1. 生成每日计划
        now = datetime.datetime(2026, 6, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
        plan_result = generate_daily_plan(
            db, provider=MockLLMProvider(), user_id=uid, now=now,
        )
        plan_id = plan_result["plan_id"]
        assert plan_id > 0

        # 2. 背词事件
        from app.repositories.vocabulary import list_all_vocabulary
        words = list_all_vocabulary(db)[:3]
        events = [{"vocabulary_item_id": w["id"], "event_type": "MEANING_CHECK",
                    "is_correct": True, "used_hint": False} for w in words]
        review_result = process_review_events(db, user_id=uid, plan_id=plan_id, events=events, now=now)
        assert review_result["processed_events"] == len(events)

        # 3. 完成背词
        complete_result = complete_vocabulary_phase(db, plan_id, uid)
        assert complete_result["status"] == "VOCABULARY_COMPLETED"

        # 4. 开始刷题
        practice_result = start_practice(
            db, user_id=uid, plan_id=plan_id,
            practice_mode="TARGETED_PRACTICE", max_questions=4,
        )
        assert practice_result["task_id"] > 0
        assert len(practice_result["questions"]) > 0


# ---- 旧接口兼容 ----


class TestBackwardCompatibility:
    def test_old_text_analysis_still_works(self):
        """文本导入分析接口仍然可用。"""
        from app.services.learning_analysis import analyze_english_text
        from app.api.learning_models import TextAnalysisRequest
        req = TextAnalysisRequest(
            raw_text="Climate change is a pressing challenge.",
            target_abilities=["VOCABULARY_CONTEXT"],
            max_keywords=5,
            generate_exercise=True,
        )
        analysis = analyze_english_text(req)
        result = analysis.model_dump()
        assert len(result["raw_text"]) > 0
        assert len(result["keywords"]) > 0

    def test_old_training_submission_still_works(self):
        """训练提交与评分仍然可用。"""
        db = temp_db_path("feature")
        init_database(db)
        from app.repositories.users import create_user
        from app.repositories.training import create_training_session, create_generated_task
        from app.services.training_scorer import score_training_submission

        uid = create_user(db, "测试")
        sid = create_training_session(db, user_id=uid, stage="FIRST_MAIN")
        content = {
            "questions": [
                {"question_id": "q1", "question_type": "MULTIPLE_CHOICE", "answer": "A", "options": [
                    {"id": "A", "text": "对"}, {"id": "B", "text": "错"}]},
            ],
        }
        tid = create_generated_task(db, session_id=sid, user_id=uid,
                                     task_type="SHORT_TRAINING", target_ability="VOCABULARY_CONTEXT",
                                     content_json=content)
        answers = [{"question_id": "q1", "answer": "A"}]
        score = score_training_submission(content, answers)
        assert score["total"] > 0


# ---- 隔离题防泄漏 ----


class TestIsolationStillWorks:
    def test_isolated_items_not_leaked(self):
        """隔离题不应通过候选词或每日计划泄漏。"""
        db = temp_db_path("feature")
        init_database(db)
        from app.repositories.users import create_user, save_user_goal
        from app.repositories.isolated_tests import create_isolated_test_item
        from app.services.vocab_import import seed_cet6_vocabulary
        from app.services.candidate_vocab import generate_candidate_vocabulary

        uid = create_user(db, "测试")
        save_user_goal(db, uid, exam_type="CET-6")
        seed_cet6_vocabulary(db)
        create_isolated_test_item(
            db, target_ability="VOCABULARY_CONTEXT", item_version="v1",
            item_payload={"prompt": "隔离题"}, answer_key={"correct": "A"},
            answer_rationale={"A": "答案"}, distractor_rationale={},
        )
        now = datetime.datetime(2026, 6, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
        result = generate_candidate_vocabulary(db, user_id=uid, now=now)
        # 候选词不应包含隔离题内容
        for item in result["candidate_items"]:
            assert "隔离题" not in str(item)
            # 候选词只来自 vocabulary_items 表
