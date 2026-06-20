# LingoForge DS/Claude Code 执行计划 04：后端收口与前端接线准备

本计划是第三阶段之后的最后一批大范围 DS/Claude Code 委派任务。目标是让后端普通业务能力尽量接近 MVP 可接线状态，为 Codex 后续实现核心 Agent、Workflow 总编排和完整 Vue 前端留下清晰、稳定、可审查的接口。

本计划只允许 DS/Claude Code 实现已经冻结、机械、可测试的后端工作。不得把架构判断、Agent 核心循环、ContextBuilder、Memory 核心语义、Prompt/Skill、Workflow 总编排、隔离测试防泄漏设计或 Vue 前端交给 DS/Claude Code 自行发挥。

## 总规则

- 每个任务必须先写 RED 测试，再做 GREEN 实现。
- 每个任务尽量只修改 1 到 5 个文件；如确实超过，必须在提交说明中解释原因。
- 每个任务必须可独立提交、独立回滚。
- 每个任务完成后至少运行该任务指定测试；每 3 个任务后运行 `python -m pytest backend\tests`。
- 所有说明、测试名、提交信息使用中文。
- 不得修改数据库 Schema。
- 不得修改 Vue 前端。
- 不得修改 Agent Runtime 主循环、Runtime 身份权限模型、ToolExecutor 公共契约、Provider 公共契约、ContextBuilder 核心语义、Context Expansion、Memory 核心状态机、Workflow 总体编排、Prompt 或 Skill 语义。
- 不得引入 LangChain、多 Agent、向量数据库、消息队列、微服务或重型新依赖。
- 所有 API 身份只能来自请求头或 Runtime/API 边界绑定，不得从请求体读取或信任 `user_id/session_id/permission_scope`。
- 隔离测试接口必须严格执行防泄漏：开始和进行中不得返回答案、解析、评分依据、干扰项设计；提交后只返回受控结果包。

## 本轮冻结的新增接口契约

### 1. Profile API

`GET /api/profile/summary`

请求头：

```http
X-LingoForge-User-Id: int
```

响应：

```json
{
  "user": {"id": 1, "display_name": "Demo"},
  "latest_goal": {},
  "latest_profile": {},
  "pending_suggestions": []
}
```

`POST /api/profile/goal`

请求体：

```json
{
  "exam_type": "CET-6",
  "days_until_exam": 30,
  "target_score": 550,
  "daily_minutes": 30,
  "self_reported_weaknesses": ["vocabulary"],
  "interest_topics": ["technology"]
}
```

响应至少包含：

```json
{"goal_id": 1, "user_id": 1}
```

### 2. Training Session / Task API

`POST /api/training/sessions`

请求体：

```json
{"stage": "FIRST_MAIN"}
```

响应：

```json
{"session_id": 1, "user_id": 1, "stage": "FIRST_MAIN", "status": "IN_PROGRESS"}
```

`GET /api/training/sessions`

响应：

```json
{"sessions": []}
```

`GET /api/training/sessions/{session_id}/tasks`

响应：

```json
{"tasks": []}
```

`POST /api/learning/analyze-text/create-task`

请求头：

```http
X-LingoForge-User-Id: int
X-LingoForge-Session-Id: int
```

请求体复用 `TextAnalysisRequest`。响应：

```json
{
  "analysis": {},
  "task_id": 1
}
```

### 3. Learning History 分析服务契约

本轮只实现确定性 service，不接入 Agent Runtime / ToolExecutor。

```python
def analyze_learning_history(
    database_path,
    *,
    user_id: int,
    analysis_type: str,
    target: dict,
    current_goal: dict | None = None,
    time_window: dict | None = None,
    now: datetime | None = None,
) -> dict:
    ...
```

支持：

- `PROBLEM_TIMELINE`
- `REVIEW_PRIORITY`

`user_id` 只能由调用方注入，模型或请求体不得提供。MVP 使用 `learning_evidence.payload_json`、`candidate_vocabulary_events`、`generated_tasks` 中已有客观数据；不得使用记忆创建时间冒充问题发生时间。

时间字段定义：

- `occurred_at`：学习事件真实发生时间；若 payload 无该字段，MVP 可降级为 evidence `created_at`，并在 `confidence` 中降低置信。
- `recorded_at`：数据库记录时间，即 evidence `created_at`。
- `memory_created_at`：派生记忆产生时间；本轮 service 不读 memory，返回 `null`。

`REVIEW_PRIORITY` 算法版本固定为 `review_priority_v1`。评分为 0 到 100 的透明确定性分数，不宣称精确模拟人脑遗忘曲线。

### 4. Isolated Test API

`POST /api/isolated-tests/start`

请求体：

```json
{
  "target_ability": "VOCABULARY_CONTEXT",
  "limit": 3
}
```

响应只允许：

```json
{
  "attempt_id": 1,
  "items": [
    {
      "item_id": 1,
      "item_order": 1,
      "target_ability": "VOCABULARY_CONTEXT",
      "item_version": "v1",
      "prompt": "题干",
      "options": [{"id": "A", "text": "选项"}]
    }
  ]
}
```

禁止返回：

- `answer_key`
- `answer_rationale`
- `distractor_rationale`
- 标准答案
- 详细解析
- 评分依据

`POST /api/isolated-tests/attempts/{attempt_id}/submit`

请求体：

```json
{
  "answers": [{"item_id": 1, "answer": "A"}],
  "time_spent_seconds": 60
}
```

响应为受控结果包：

```json
{
  "attempt_id": 1,
  "score": {"total": 1, "correct": 1, "accuracy": 1.0},
  "item_results": [
    {"item_id": 1, "target_ability": "VOCABULARY_CONTEXT", "is_correct": true}
  ],
  "evidence_id": 1,
  "safe_explanation": "受控中文摘要"
}
```

提交响应仍不得返回完整答案、详细解析、干扰项设计或隔离题全文。

### 5. Sidequest API

`POST /api/sidequest/airport-ticket/complete`

请求体：

```json
{
  "selected_expression": "I'd like to book a flight.",
  "scene": "AIRPORT_TICKET",
  "result": {"completed": true}
}
```

响应：

```json
{
  "sidequest_run_id": 1,
  "signal_id": 1,
  "is_pending_verification": true
}
```

该接口只写 `sidequest_runs` 和 `sidequest_signals`。不得写正式 `learning_evidence`，不得写 profile snapshot，不得直接修改正式画像。

---

## 阶段一：API 边界与前端接线基础

### 任务 1：新增稳定业务错误响应 helper

目标：提供普通 API 可复用的稳定错误响应构造，不改变 FastAPI 默认 422。

依赖：无。

允许修改的文件：

- `backend/app/api/errors.py`
- `backend/tests/test_api_errors.py`

允许新增的文件：

- `backend/app/api/errors.py`
- `backend/tests/test_api_errors.py`

禁止修改范围：

- Agent Runtime、ToolExecutor、Provider、ContextBuilder
- 数据库 Schema
- Vue 前端

已冻结的接口签名：

```python
def business_error(status_code: int, code: str, message: str, details: dict | None = None) -> HTTPException:
    ...
```

验收标准：

- 返回 `HTTPException`。
- `detail` 形状固定为 `{"code": str, "message": str, "details": dict}`。
- 不包含 traceback、数据库路径、SQL、API key 或内部异常正文。

RED 测试：

- 构造 400/403/404/409/500 错误并断言 detail 形状。
- details 为空时返回 `{}`。

GREEN 实现要求：

- 不修改既有 API 路由。
- 只提供 helper 和测试。

完整回归命令：

- `python -m pytest backend\tests\test_api_errors.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增稳定业务错误响应工具`

### 任务 2：新增用户画像摘要 API

目标：为前端提供当前用户目标、最新画像和待处理画像建议摘要。

依赖：任务 1。

允许修改的文件：

- `backend/app/api/profile.py`
- `backend/app/main.py`
- `backend/tests/test_profile_api.py`

允许新增的文件：

- `backend/app/api/profile.py`
- `backend/tests/test_profile_api.py`

禁止修改范围：

- 数据库 Schema
- Agent Runtime、Memory、Workflow、Prompt/Skill
- Vue 前端

已冻结的接口签名：

```http
GET /api/profile/summary
Headers:
  X-LingoForge-User-Id: int
```

验收标准：

- 只从请求头绑定 `user_id`。
- 返回当前用户、最新 goal、最新 profile snapshot、`validation_status="NEEDS_REVIEW"` 的建议列表。
- 用户不存在时返回稳定 404。
- 不返回其他用户数据。

RED 测试：

- 正常用户返回摘要。
- 缺少用户头返回 422。
- 不存在用户返回 404。
- 其他用户的 goal/profile/suggestion 不出现在响应中。

GREEN 实现要求：

- 复用现有 `users` repository。
- 如需要补 repository 查询 helper，只能新增简单读取函数，不改既有函数行为。

完整回归命令：

- `python -m pytest backend\tests\test_profile_api.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增用户画像摘要 API`

### 任务 3：新增用户目标保存 API

目标：为前端 onboarding 提供保存 CET-6 学习目标的后端接口。

依赖：任务 1、任务 2。

允许修改的文件：

- `backend/app/api/profile.py`
- `backend/tests/test_profile_api.py`

允许新增的文件：无。

禁止修改范围：

- 数据库 Schema
- Agent Runtime、Workflow、Memory
- Vue 前端

已冻结的接口签名：

```http
POST /api/profile/goal
Headers:
  X-LingoForge-User-Id: int
Body: ProfileGoalRequest
```

验收标准：

- 请求体禁止身份字段。
- `exam_type` 默认 `CET-6`。
- `days_until_exam/daily_minutes/target_score` 如提供必须为非负整数。
- 成功后写入 `user_goals`，返回 `goal_id/user_id`。
- 用户不存在返回 404。

RED 测试：

- 正常保存目标。
- 请求体含 `user_id` 返回 422。
- 负数时间或分数返回 422。
- 不存在用户返回 404。

GREEN 实现要求：

- 使用 Pydantic v2。
- 复用 `save_user_goal`。

完整回归命令：

- `python -m pytest backend\tests\test_profile_api.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增用户目标保存 API`

## 阶段二：训练任务接线与质量校验

### 任务 4：新增训练 session 创建与列表 API

目标：提供前端创建训练会话和读取训练会话列表的普通 API。

依赖：任务 1。

允许修改的文件：

- `backend/app/api/training.py`
- `backend/app/repositories/training.py`
- `backend/tests/test_training_session_api.py`

允许新增的文件：

- `backend/tests/test_training_session_api.py`

禁止修改范围：

- 数据库 Schema
- Workflow 总编排
- Agent Runtime / ContextBuilder
- Vue 前端

已冻结的接口签名：

```http
POST /api/training/sessions
GET /api/training/sessions
```

验收标准：

- `POST` 只允许 stage 使用现有 WorkflowStage 常量。
- 创建 session 状态为 `IN_PROGRESS`。
- `GET` 只返回当前用户 session，按 `id DESC` 排序，默认最多 20 条。
- 请求体禁止身份字段。

RED 测试：

- 正常创建 session。
- 非法 stage 返回 422 或稳定 400。
- 其他用户 session 不出现在列表中。
- 缺少用户头返回 422。

GREEN 实现要求：

- 可新增 `list_training_sessions_for_user` repository helper。
- 不实现 Workflow 阶段转换。

完整回归命令：

- `python -m pytest backend\tests\test_training_session_api.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增训练会话 API`

### 任务 5：新增训练任务列表与详情 API

目标：让前端能读取当前用户指定 session 下的训练任务。

依赖：任务 4。

允许修改的文件：

- `backend/app/api/training.py`
- `backend/app/repositories/training.py`
- `backend/tests/test_training_task_api.py`

允许新增的文件：

- `backend/tests/test_training_task_api.py`

禁止修改范围：

- 数据库 Schema
- Agent Runtime、Workflow、Prompt/Skill
- Vue 前端

已冻结的接口签名：

```http
GET /api/training/sessions/{session_id}/tasks
GET /api/training/tasks/{task_id}
```

验收标准：

- 只能读取当前用户自己的 session/task。
- task 响应使用已有 `TrainingTaskSummary` 语义。
- 不存在返回 404；存在但不属于当前用户返回 403。
- 不返回隔离测试题。

RED 测试：

- 正常列出 session 下任务。
- 正常读取单个 task。
- 其他用户 task 读取被拒绝。
- 其他用户 session 下任务列表被拒绝或为空；推荐 403。

GREEN 实现要求：

- 可新增 `list_generated_tasks_for_session_user` helper。
- 不改训练提交和结果查询既有行为。

完整回归命令：

- `python -m pytest backend\tests\test_training_task_api.py`
- `python -m pytest backend\tests\test_training_api.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增训练任务读取 API`

### 任务 6：新增生成训练任务质量校验服务

目标：为后续 Agent 生成训练任务提供确定性校验器和 validation 记录写入能力。

依赖：任务 5。

允许修改的文件：

- `backend/app/services/task_validation.py`
- `backend/tests/test_task_validation_service.py`

允许新增的文件：

- `backend/app/services/task_validation.py`
- `backend/tests/test_task_validation_service.py`

禁止修改范围：

- 数据库 Schema
- Agent Runtime、Prompt/Skill、Workflow
- Vue 前端

已冻结的接口签名：

```python
def validate_training_task_content(content: dict) -> dict:
    ...

def record_task_validation_result(database_path, *, task_id: int, validation_result: dict, attempt_number: int = 1) -> int:
    ...
```

验收标准：

- 校验 `TrainingTaskContent` 结构。
- 拒绝非 `MULTIPLE_CHOICE`。
- 拒绝重复 `question_id`。
- 拒绝标准答案不在 options 中。
- 拒绝非法 `target_ability`。
- validation_result 至少包含 `status/error_codes/error_details`。
- 写入 `generated_task_validations`。

RED 测试：

- 合法任务返回 `PASSED`。
- 上述每类非法任务返回 `FAILED` 和稳定 error_code。
- validation 记录可从 repository 读回。

GREEN 实现要求：

- 不调用 LLM。
- 不把模型自称“校验通过”当成真实校验。

完整回归命令：

- `python -m pytest backend\tests\test_task_validation_service.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增训练任务质量校验服务`

### 任务 7：新增文本分析并创建训练任务 API

目标：把已有确定性文本分析结果保存为训练任务，为前端提供一键生成训练的后端接口。

依赖：任务 4、任务 5、任务 6。

允许修改的文件：

- `backend/app/api/learning.py`
- `backend/tests/test_learning_api.py`

允许新增的文件：无。

禁止修改范围：

- 数据库 Schema
- Agent Runtime、Prompt/Skill、Workflow
- Vue 前端

已冻结的接口签名：

```http
POST /api/learning/analyze-text/create-task
Headers:
  X-LingoForge-User-Id: int
  X-LingoForge-Session-Id: int
Body: TextAnalysisRequest
```

验收标准：

- 先执行现有确定性文本分析。
- 再调用已有 `create_task_from_analysis` 写入 `generated_tasks`。
- 调用任务 6 的质量校验服务并写入 validation。
- session 必须属于当前用户，否则 403。
- 响应包含 `analysis` 和 `task_id`。

RED 测试：

- 正常分析并创建 task。
- 请求体含身份字段返回 422。
- 使用其他用户 session 返回 403。
- 质量校验失败时返回稳定 400，不写入可用 task 或写入 task 后 validation 为 FAILED；二选一，但测试必须固定实际行为。

GREEN 实现要求：

- 不调用 Agent 或 DeepSeek。
- 不改变现有 `/api/learning/analyze-text` 行为。

完整回归命令：

- `python -m pytest backend\tests\test_learning_api.py`
- `python -m pytest backend\tests\test_task_validation_service.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增文本分析创建训练任务 API`

## 阶段三：学习历史分析确定性服务

### 任务 8：新增 Learning History 模型与 PROBLEM_TIMELINE 服务

目标：实现不接入 Runtime 的确定性历史分析 service，先支持 `PROBLEM_TIMELINE`。

依赖：任务 1。

允许修改的文件：

- `backend/app/services/learning_history.py`
- `backend/tests/test_learning_history_service.py`

允许新增的文件：

- `backend/app/services/learning_history.py`
- `backend/tests/test_learning_history_service.py`

禁止修改范围：

- Agent Runtime、ToolExecutor、ContextBuilder、Context Expansion
- Memory 核心状态机
- 数据库 Schema
- Vue 前端

已冻结的接口签名：

```python
def analyze_learning_history(
    database_path,
    *,
    user_id: int,
    analysis_type: str,
    target: dict,
    current_goal: dict | None = None,
    time_window: dict | None = None,
    now: datetime | None = None,
) -> dict:
    ...
```

验收标准：

- `analysis_type="PROBLEM_TIMELINE"` 返回 `first_observed_at/last_observed_at/occurrence_count/session_count/last_success_at/recent_trend/evidence_refs/confidence`。
- 支持按 `ability`、`error_type`、`vocabulary_text` 过滤。
- 只分析当前 `user_id` 的 `learning_evidence`。
- 区分 `occurred_at/recorded_at/memory_created_at`；无 occurred_at 时可用 evidence `created_at` 降级，并降低 confidence。
- 不使用 memory 创建时间冒充问题发现时间。

RED 测试：

- 同一错误跨多个 session 的 first/last/count/session_count 正确。
- 其他用户 evidence 不参与分析。
- 有成功记录时 `last_success_at` 正确。
- 无证据时返回 `INSUFFICIENT_EVIDENCE` 或等价稳定状态。

GREEN 实现要求：

- 使用现有 `learning_evidence` 表。
- 不引入向量数据库或复杂 RAG。
- 不接入 Function Calling。

完整回归命令：

- `python -m pytest backend\tests\test_learning_history_service.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`实现学习历史问题时间线分析`

### 任务 9：实现 REVIEW_PRIORITY 确定性评分

目标：在 learning history service 中补充透明、可测试、可版本化的复习优先级评分。

依赖：任务 8。

允许修改的文件：

- `backend/app/services/learning_history.py`
- `backend/tests/test_learning_history_service.py`

允许新增的文件：无。

禁止修改范围：

- Agent Runtime、ToolExecutor、ContextBuilder
- 数据库 Schema
- Prompt/Skill
- Vue 前端

已冻结的算法：

- `algorithm_version="review_priority_v1"`。
- 输出 `review_priority` 为 0 到 100。
- 基础因素：
  - 距离上次练习越久，分数越高，最高 +25。
  - 距离上次成功越久或从未成功，最高 +20。
  - 历史正确率越低，最高 +20。
  - 提示依赖越高，最高 +10。
  - 连续错误最高 +10；连续成功可降低最多 10。
  - 当前目标相关性最高 +10。
  - 反复出现问题最高 +10。
  - 内容难度可作为 +0 到 +5 的轻权重因素。
- 最终裁剪到 0 到 100。
- `review_status`：
  - `DUE_NOW`: >= 70
  - `SOON`: 40 到 69
  - `STABLE`: < 40
  - `INSUFFICIENT_EVIDENCE`: 无足够证据

验收标准：

- 返回 `review_priority/review_status/recommended_window/estimated_decay/factors/evidence_refs/algorithm_version`。
- `now` 可注入，测试不依赖真实当前时间。
- 不宣称精确模拟人脑遗忘曲线。

RED 测试：

- 长时间未练且低正确率得到高优先级。
- 最近连续成功得到低优先级。
- 当前目标相关性会提高因素分。
- 无证据返回 `INSUFFICIENT_EVIDENCE`。

GREEN 实现要求：

- 纯确定性计算。
- 所有 factors 保留原始客观依据摘要。

完整回归命令：

- `python -m pytest backend\tests\test_learning_history_service.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`实现确定性复习优先级评分`

## 阶段四：隔离测试受控后端闭环

### 任务 10：新增隔离测试模型与安全 sanitizer

目标：定义隔离测试开始、提交和结果响应模型，并实现不泄漏答案的 item sanitizer。

依赖：任务 1。

允许修改的文件：

- `backend/app/api/isolated_models.py`
- `backend/app/services/isolated_tests.py`
- `backend/tests/test_isolated_service.py`

允许新增的文件：

- `backend/app/api/isolated_models.py`
- `backend/app/services/isolated_tests.py`
- `backend/tests/test_isolated_service.py`

禁止修改范围：

- 数据库 Schema
- Agent Runtime、ContextBuilder、Memory、Workflow
- Vue 前端

已冻结的接口签名：

```python
def sanitize_isolated_item(item: dict) -> dict:
    ...
```

验收标准：

- sanitized item 只包含 `item_id/item_order/target_ability/item_version/prompt/options`。
- 输出不得包含 `answer_key/answer_rationale/distractor_rationale/explanation/standard_answer`。
- 请求体禁止身份字段。

RED 测试：

- 输入完整 isolated item，输出不含任何禁止字段。
- 请求模型中带 `user_id/session_id/permission_scope` 被 Pydantic 拒绝。

GREEN 实现要求：

- 不实现 API 路由。
- 不调用 Agent。

完整回归命令：

- `python -m pytest backend\tests\test_isolated_service.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增隔离测试安全模型`

### 任务 11：新增隔离测试开始 API

目标：从 active 隔离题中创建一次 attempt，并只返回 sanitized items。

依赖：任务 10。

允许修改的文件：

- `backend/app/api/isolated.py`
- `backend/app/main.py`
- `backend/app/services/isolated_tests.py`
- `backend/tests/test_isolated_api.py`

允许新增的文件：

- `backend/app/api/isolated.py`
- `backend/tests/test_isolated_api.py`

禁止修改范围：

- 数据库 Schema
- Agent Runtime、ContextBuilder、Memory、Workflow
- Vue 前端

已冻结的接口签名：

```http
POST /api/isolated-tests/start
```

验收标准：

- 只从请求头绑定 `user_id`，可选绑定 `X-LingoForge-Session-Id`。
- 按 `target_ability` 读取 active items，按 id ASC 取前 `limit` 条。
- 创建 `isolated_test_attempts` 和 `isolated_attempt_items`。
- 返回 sanitized items。
- 不返回答案、解析或评分依据。
- 无可用题目返回稳定 404 或 400，测试固定一种。

RED 测试：

- 正常开始 attempt。
- 响应 JSON 字符串中不出现禁止字段名。
- 缺少用户头返回 422。
- 无题目时返回稳定错误。

GREEN 实现要求：

- 不接入 Agent。
- 不实现随机抽题；MVP 使用确定性 id ASC。

完整回归命令：

- `python -m pytest backend\tests\test_isolated_api.py`
- `python -m pytest backend\tests\test_isolated_service.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增隔离测试开始 API`

### 任务 12：新增隔离测试提交评分与受控结果包

目标：实现隔离测试提交、确定性评分、受控结果包和学习证据写入。

依赖：任务 11。

允许修改的文件：

- `backend/app/api/isolated.py`
- `backend/app/services/isolated_tests.py`
- `backend/tests/test_isolated_api.py`
- `backend/tests/test_isolated_service.py`

允许新增的文件：无。

禁止修改范围：

- 数据库 Schema
- Agent Runtime、ContextBuilder、Memory、Workflow
- Vue 前端

已冻结的接口签名：

```http
POST /api/isolated-tests/attempts/{attempt_id}/submit
```

验收标准：

- attempt 必须属于当前用户。
- 按 `answer_key` 确定性评分。
- 更新 attempt 的 `user_answers/score_json/time_spent_seconds`。
- 写入一条 `learning_evidence.evidence_type="ISOLATED_TEST_RESULT"`。
- 返回受控结果包，不返回完整答案、详细解析、干扰项设计或隔离题全文。
- 重复提交返回 409。

RED 测试：

- 正常提交得到分数和 evidence_id。
- 其他用户提交 attempt 被拒绝。
- 重复提交返回 409。
- 响应 JSON 字符串中不出现 `answer_key/answer_rationale/distractor_rationale`。

GREEN 实现要求：

- 不把隔离测试内容写入普通训练任务。
- 不生成 profile snapshot。

完整回归命令：

- `python -m pytest backend\tests\test_isolated_api.py backend\tests\test_isolated_service.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`实现隔离测试提交与受控结果包`

## 阶段五：机场副线后端记录

### 任务 13：新增机场购票副线完成 API

目标：记录机场购票副线完成结果和待验证副线信号，为第二次计划提供候选信号数据。

依赖：任务 1。

允许修改的文件：

- `backend/app/api/sidequest.py`
- `backend/app/main.py`
- `backend/tests/test_sidequest_api.py`

允许新增的文件：

- `backend/app/api/sidequest.py`
- `backend/tests/test_sidequest_api.py`

禁止修改范围：

- 数据库 Schema
- Agent Runtime、Workflow、Memory、Prompt/Skill
- Vue 前端

已冻结的接口签名：

```http
POST /api/sidequest/airport-ticket/complete
```

验收标准：

- 只从请求头绑定 `user_id`。
- 写入 `sidequest_runs`。
- 写入一条 `sidequest_signals.is_pending_verification=1`。
- 响应包含 `sidequest_run_id/signal_id/is_pending_verification`。
- 不写 `learning_evidence`。
- 不写 `profile_snapshots`。
- 请求体禁止身份字段。

RED 测试：

- 正常完成副线，run 和 signal 均可读回。
- 请求体含 `user_id` 返回 422。
- 断言 learning_evidence 和 profile_snapshots 没有新增记录。

GREEN 实现要求：

- 复用现有 sidequest repository。
- 不实现前端场景逻辑。

完整回归命令：

- `python -m pytest backend\tests\test_sidequest_api.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增机场副线完成 API`

## 阶段六：演示数据与端到端 smoke 收口

### 任务 14：扩充 demo seed 数据

目标：让 demo seed 覆盖前端接线和 smoke 所需的目标、画像、训练任务、隔离题和副线基础数据。

依赖：任务 11、任务 13。

允许修改的文件：

- `scripts/seed_demo.py`
- `backend/tests/test_demo_seed_script.py`

允许新增的文件：无。

禁止修改范围：

- 数据库 Schema
- 后端业务模块
- Vue 前端
- Agent Runtime、Prompt/Skill

已冻结的命令：

```powershell
python scripts\seed_demo.py --database-path <path>
```

验收标准：

- 重复运行不崩溃。
- 至少创建或确保存在：
  - demo user
  - user_goal
  - profile_snapshot
  - vocabulary_items
  - training_session
  - generated_task
  - isolated_test_items
  - sidequest seed 数据或可用于副线 API 的 vocabulary
- 输出中文摘要，包含 user_id/session_id/task_id。
- 不写真实 API key。

RED 测试：

- 临时库运行 seed 后核心数据存在。
- 连续运行两次仍通过。
- active isolated items 至少 2 条。

GREEN 实现要求：

- 优先复用 repository。
- 不因幂等需求修改 Schema；可接受重复 demo 数据，只要不崩溃且摘要清晰。

完整回归命令：

- `python -m pytest backend\tests\test_demo_seed_script.py`
- `python scripts\seed_demo.py --database-path %TEMP%\lingoforge_demo.sqlite3`
- `python -m pytest backend\tests`

推荐中文提交信息：`扩充演示数据种子脚本`

### 任务 15：扩展 Mock 后端完整 smoke 脚本与 README

目标：把目前 smoke 扩展为可证明后端主干 API 能串起来的最小演示闭环。

依赖：任务 2 到任务 14。

允许修改的文件：

- `scripts/smoke_backend.py`
- `backend/tests/test_smoke_backend_script.py`
- `README.md`

允许新增的文件：无。

禁止修改范围：

- `backend/app/`
- 数据库 Schema
- Vue 前端
- Agent Runtime、Prompt/Skill

已冻结的命令：

```powershell
python scripts\smoke_backend.py
```

验收标准：

- smoke 使用临时数据库和 `LLM_MODE=mock`。
- 至少依次验证：
  - `/health`
  - `POST /api/profile/goal`
  - `GET /api/profile/summary`
  - `POST /api/training/sessions`
  - `POST /api/learning/analyze-text/create-task`
  - `POST /api/training/tasks/{task_id}/submit`
  - `GET /api/training/tasks/{task_id}/result`
  - `POST /api/sidequest/airport-ticket/complete`
  - `POST /api/isolated-tests/start`
  - `POST /api/isolated-tests/attempts/{attempt_id}/submit`
- README 同步这些命令和接口示例。
- README 不包含真实密钥。
- README 明确身份通过请求头绑定，不能放请求体。

RED 测试：

- smoke 脚本测试断言输出包含“通过”或等价中文成功标记。
- README 测试只检查关键命令和安全提示，不做纯关键词堆砌；必须与实际 smoke 命令对应。

GREEN 实现要求：

- 不修改后端业务代码。
- 不访问真实 DeepSeek API。

完整回归命令：

- `python scripts\smoke_backend.py`
- `python -m pytest backend\tests\test_smoke_backend_script.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`扩展后端完整 smoke 流程`

## 本计划完成后的交接要求

DS/Claude Code 完成后必须汇报：

- 每个任务对应提交哈希。
- 每个任务运行的测试命令和结果。
- 是否有任何偏离本计划或 `docs/IMPLEMENTATION_CONTRACTS.md`。
- 是否修改了禁止范围。
- 当前完整后端测试结果。
- 是否存在它认为需要 Codex 审查的风险点。

Codex 随后负责：

- 完整审查 DS 产物。
- 修复 P1/P2 问题。
- 接入或调整核心 Agent / Workflow。
- 实现 Vue 前端和前后端最终集成。
- 做最终验收、浏览器验证、README 命令复跑和收尾。

## 预计完成度判断

如果本计划 15 项质量良好地完成，后端普通业务与演示闭环会接近收口；剩余主要集中在 Codex 必须负责的高风险核心：

- Agent Runtime 深化与 Workflow 编排。
- ContextBuilder / Context Expansion / Memory 核心语义。
- Prompt 与教学 Skill。
- `analyze_learning_history` 接入 Function Calling 和审计链。
- 隔离测试与普通训练在 Agent Context 层面的最终防泄漏审查。
- 完整 Vue 前端、视觉资产和端到端集成。

因此，本计划之后通常还需要 Codex 做一轮较重的最终冲刺；如果 DS 交付质量高，理论上可以进入“Codex 审查修复 + 核心接入 + 前端完成”的最后阶段。
