# LingoForge 后端业务接口契约冻结

本文冻结下一阶段可交给 DS/Claude Code 实现的后端业务契约。本文低于 `AGENTS.md`、`docs/SPEC.md` 和 `docs/AGENT_ARCHITECTURE.md`，高于 `tasks/ds_plan_03.md` 中的任务描述。若本文与既有架构文档冲突，以更高优先级文档为准。

本轮只冻结 MVP 后端薄业务层契约，不引入新数据库 Schema，不修改 Agent Runtime、ContextBuilder、ToolExecutor、Provider 公共契约、Prompt、Skill、Workflow 总编排、隔离测试防泄漏设计或 Vue 前端。

## 1. 通用边界

### 1.1 身份绑定

所有新增 API 必须沿用当前 Runtime/API 身份绑定方式：

- `X-LingoForge-User-Id`：必填，整数，由 API 层解析并绑定为当前用户。
- `X-LingoForge-Session-Id`：可选，整数，由 API 层解析并绑定为当前 session。
- 请求体不得包含 `user_id`、`session_id`、`permission_scope`、`current_user_id`、`current_session_id` 或等价身份字段。
- 若请求体出现身份字段，必须由 Pydantic 边界校验拒绝，通常为 HTTP 422。
- Service 和 Repository 只能使用 API 层注入的 `user_id/session_id`，不得信任客户端请求体中的身份。

### 1.2 错误响应

新增业务 API 的受控业务错误统一使用：

```json
{
  "detail": {
    "code": "STABLE_ERROR_CODE",
    "message": "中文稳定错误信息",
    "details": {}
  }
}
```

约定状态码：

- `400`：请求语义错误，例如训练任务题型不支持。
- `403`：资源存在但不属于当前用户。
- `404`：资源不存在。
- `409`：状态冲突，例如重复提交。
- `422`：Pydantic 请求结构校验失败。
- `500`：未预期服务错误，响应不得包含 traceback、数据库路径、SQL、密钥或内部异常正文。

FastAPI 默认 422 结构可以保留；业务主动抛出的错误使用上面的 `detail` 形状。

### 1.3 Repository 与 Service 职责

- Repository：只负责现有表的 CRUD、简单查询、JSON 字段序列化/反序列化、按 `user_id/session_id/task_id` 查询。不得写 Agent 策略，不得判分。
- Service：负责业务薄封装、字段校验、用户归属校验、调用评分器、组合写入 `generated_tasks`、`learning_evidence`、`profile_update_suggestions`。
- API：负责请求/响应模型、身份头解析、调用 Service、稳定错误映射。
- Agent Runtime：本阶段不修改。新增 API 不得绕过身份绑定去调用 Agent 内部工具。
- 确定性评分器：负责客观题评分、错误类型归类、学习证据 payload 生成所需的客观字段。

## 2. 英语分析结果契约

### 2.1 API

`POST /api/learning/analyze-text`

请求体：

```json
{
  "raw_text": "英文原文，1 到 5000 字符",
  "target_abilities": ["VOCABULARY_CONTEXT"],
  "max_keywords": 8,
  "generate_exercise": true
}
```

字段规则：

- `raw_text`：必填，字符串，去首尾空白后不得为空。
- `target_abilities`：可选，默认 `["VOCABULARY_CONTEXT"]`；值必须属于 `Ability` 常量。
- `max_keywords`：可选，默认 5，范围 1 到 12。
- `generate_exercise`：可选，默认 true。
- 请求体禁止身份字段。

响应体：

```json
{
  "analysis_id": "analysis_xxx",
  "raw_text": "原始英文文本",
  "keywords": [
    {
      "text": "adapt",
      "meaning_zh": "适应",
      "usage_note": "常与 to 搭配，表示适应环境或变化。",
      "ability": "VOCABULARY_CONTEXT",
      "selection_reason": "文本关键词，适合训练语境推断。"
    }
  ],
  "exercise": {
    "question_id": "q1",
    "question_type": "MULTIPLE_CHOICE",
    "prompt": "根据原文语境，adapt 最接近哪一项？",
    "options": [
      {"id": "A", "text": "adjust to"},
      {"id": "B", "text": "ignore"}
    ],
    "answer": "A",
    "explanation": "adapt 在此处表示适应或调整。",
    "target_ability": "VOCABULARY_CONTEXT"
  },
  "agent_feedback": "这段材料适合先抓关键词，再回到句子判断含义。",
  "source": "MOCK_DETERMINISTIC",
  "warnings": []
}
```

MVP 允许先实现 `MOCK_DETERMINISTIC` 分析：用确定性规则从文本中抽取英文词、生成中文释义占位、生成一题客观练习和模板化 `agent_feedback`。这不是最终教学 Skill，也不替代后续 Codex 实现 Agent 生成训练。

### 2.2 逻辑模型

建议新增 Pydantic 模型，但文件路径由任务约束限定：

- `TextAnalysisRequest`
- `KeywordAnalysis`
- `ExerciseQuestion`
- `ExerciseOption`
- `TextAnalysisResponse`

模型字段使用 snake_case，保持与当前后端 API 风格一致。

## 3. 训练任务与练习题契约

训练任务复用现有 `generated_tasks` 表，不新增表。任务正文写入 `generated_tasks.content_json`。

### 3.1 TrainingTaskContent

`content_json` 统一结构：

```json
{
  "title": "词汇语境练习",
  "raw_text": "英文材料或题干上下文",
  "instructions": "请选择最符合语境的答案。",
  "questions": [
    {
      "question_id": "q1",
      "question_type": "MULTIPLE_CHOICE",
      "prompt": "adapt 最接近哪一项？",
      "options": [
        {"id": "A", "text": "adjust to"},
        {"id": "B", "text": "remove"}
      ],
      "answer": "A",
      "explanation": "adapt 表示适应。",
      "target_ability": "VOCABULARY_CONTEXT",
      "error_type_on_wrong": "VOCABULARY_CONTEXT_ERROR"
    }
  ],
  "agent_feedback": "完成后重点检查是否能用上下文排除干扰项。",
  "source": "TEXT_ANALYSIS_MOCK"
}
```

`question_type` MVP 仅冻结 `MULTIPLE_CHOICE`。标准答案和解析可以存储在训练任务中，因为它不是隔离测试题库；隔离测试仍遵守 `docs/AGENT_ARCHITECTURE.md` 的防泄漏规则。

### 3.2 GeneratedTaskSummary

查询 API 返回训练任务时使用：

```json
{
  "task_id": 1,
  "session_id": 2,
  "task_type": "LOW_PRESSURE_LEARNING",
  "target_ability": "VOCABULARY_CONTEXT",
  "difficulty_params": {},
  "content": {},
  "quality_check_result": {},
  "created_at": "2026-06-20 12:00:00"
}
```

不得返回其他用户任务。

## 4. 训练提交与评分契约

### 4.1 API

`POST /api/training/tasks/{task_id}/submit`

请求体：

```json
{
  "answers": [
    {
      "question_id": "q1",
      "answer": "A"
    }
  ],
  "time_spent_seconds": 45,
  "used_hints": ["definition_hint"]
}
```

字段规则：

- `answers`：必填，至少 1 项。
- `question_id`：必填，必须匹配任务中的 question。
- `answer`：必填，MVP 为选项 ID 字符串。
- `time_spent_seconds`：可选，非负整数。
- `used_hints`：可选，字符串数组。
- 请求体禁止身份字段。

响应体：

```json
{
  "task_id": 1,
  "session_id": 2,
  "score": {
    "total": 1,
    "correct": 1,
    "accuracy": 1.0,
    "passed": true
  },
  "question_results": [
    {
      "question_id": "q1",
      "user_answer": "A",
      "standard_answer": "A",
      "is_correct": true,
      "error_type": null,
      "target_ability": "VOCABULARY_CONTEXT",
      "explanation": "adapt 表示适应。"
    }
  ],
  "evidence_id": 10,
  "profile_suggestion_id": 11,
  "agent_feedback": "本题正确，继续保持先看上下文再判断词义。"
}
```

### 4.2 确定性评分结果

评分器输入：

```python
score_training_submission(task_content: dict, answers: list[dict], *, used_hints: list[str] | None = None) -> dict
```

评分器输出：

```json
{
  "total": 1,
  "correct": 1,
  "accuracy": 1.0,
  "passed": true,
  "question_results": [],
  "error_types": [],
  "used_hints": []
}
```

评分器要求：

- 只支持 `MULTIPLE_CHOICE`。
- 标准答案来自 `task_content.questions[].answer`。
- 用户答案按 `question_id` 匹配，不按数组顺序推断。
- 未答题记为错误，`error_type` 使用题目 `error_type_on_wrong`，没有则使用 `UNKNOWN_ERROR`。
- 多余答案记入 `extra_answers` 或受控错误，不得影响已有题目的正确性。
- 不调用 LLM，不读取数据库，不写日志。

### 4.3 学习证据字段

提交成功后写入一条 `learning_evidence`：

- `evidence_type`: `TRAINING_ANSWER`
- `user_id`: API 绑定用户
- `session_id`: 任务所属 session
- `task_id`: 训练任务 ID
- `payload_json`:

```json
{
  "event": "TRAINING_SUBMISSION_SCORED",
  "task_id": 1,
  "session_id": 2,
  "answers": [],
  "score": {},
  "question_results": [],
  "target_abilities": ["VOCABULARY_CONTEXT"],
  "error_types": [],
  "used_hints": [],
  "time_spent_seconds": 45
}
```

原始学习证据只追加，不覆盖旧记录。

### 4.4 画像更新建议字段

提交成功后可写入一条普通画像更新建议：

- `ability`: 若只有一个能力，使用该能力；多个能力时使用第一题能力或 `VOCABULARY_CONTEXT` 兜底。
- `direction`: `IMPROVE`、`DECLINE` 或 `UNCERTAIN`。
- `reason`: 中文短句，基于本次确定性评分，例如“本次训练正确率 100%”。
- `evidence_refs`: 包含本次 `learning_evidence.id`。
- `agent_payload`:

```json
{
  "source": "DETERMINISTIC_SCORER",
  "score": {},
  "error_types": [],
  "requires_agent_review": true
}
```

MVP 不自动应用画像建议，不写 profile snapshot。

## 5. 训练结果查询契约

`GET /api/training/tasks/{task_id}/result`

响应体：

```json
{
  "task": {
    "task_id": 1,
    "session_id": 2,
    "task_type": "LOW_PRESSURE_LEARNING",
    "target_ability": "VOCABULARY_CONTEXT",
    "content": {}
  },
  "latest_submission": {
    "evidence_id": 10,
    "score": {},
    "question_results": [],
    "profile_suggestion_id": 11,
    "created_at": "2026-06-20 12:00:00"
  }
}
```

查询规则：

- `task_id` 必须存在。
- 任务 `user_id` 必须等于 API 绑定用户，否则 403。
- 若尚无提交，`latest_submission` 为 null。
- 不读取隔离测试题库，不返回隔离题内容。

## 6. 文本分析到训练任务的薄封装

`POST /api/learning/analyze-text` 默认只返回分析结果，不强制写数据库。允许请求模型后续扩展 `create_training_task=true`，但本轮冻结为不支持，DS 不得擅自扩展。

若需要把分析结果保存为训练任务，使用单独 Service 函数：

```python
create_task_from_analysis(database_path, *, user_id: int, session_id: int, analysis: dict) -> int
```

该函数写入 `generated_tasks`：

- `task_type`: `LOW_PRESSURE_LEARNING`
- `target_ability`: 第一条 keyword ability，缺省 `VOCABULARY_CONTEXT`
- `content_json`: 符合 `TrainingTaskContent`
- `quality_check_result`: `{"status": "PASSED", "source": "CONTRACT_MVP"}`

本函数不调用 Agent，不调用 DeepSeek。

## 7. 本阶段禁止事项

DS/Claude Code 实现本文契约时仍禁止：

- 修改数据库 Schema。
- 修改 Runtime 身份与权限模型。
- 修改 Agent Runtime 主循环。
- 修改 Provider 公共契约。
- 修改 ToolExecutor 公共契约。
- 修改 ContextBuilder 核心语义。
- 实现 Context Expansion。
- 实现 Memory 核心状态机。
- 设计或实现 `analyze_learning_history` 算法。
- 修改 Workflow 总体编排。
- 修改 Prompt / Skill 语义。
- 修改隔离测试防泄漏设计。
- 修改 Vue 前端。
- 引入多 Agent、LangChain、向量数据库、消息队列或微服务。
