# LingoForge DS/Claude Code 执行计划 03

本计划扩大 DS/Claude Code 委派范围，包含可机械实现的后端业务代码。公共契约以 `docs/IMPLEMENTATION_CONTRACTS.md` 为准；若本计划与该契约冲突，以契约文档为准。

执行总规则：

- 每个任务必须先写 RED 测试，再做 GREEN 实现。
- 每个任务尽量只修改 1 到 5 个文件。
- 每个任务必须能独立提交、独立回滚。
- 不得修改数据库 Schema、Vue 前端、Agent Runtime 主循环、Runtime 身份权限模型、Provider 公共契约、ToolExecutor 公共契约、ContextBuilder 核心语义、Context Expansion、Memory 核心状态机、`analyze_learning_history` 算法设计、Workflow 总编排、Prompt / Skill 语义、隔离测试防泄漏设计。
- 不得引入 LangChain、多 Agent、向量数据库、消息队列、微服务或新的重型依赖。
- 所有说明、测试名、提交信息使用中文；代码标识符可用英文。

## 阶段一：冻结模型与确定性评分

### 任务 1：新增英语分析请求与响应模型

目标：新增文本分析 API 使用的 Pydantic 模型，字段与 `docs/IMPLEMENTATION_CONTRACTS.md` 第 2 节一致。

依赖：`docs/IMPLEMENTATION_CONTRACTS.md`。

允许修改的文件：

- `backend/tests/test_learning_models.py`

允许新增的文件：

- `backend/app/api/learning_models.py`

禁止修改范围：

- 数据库 Schema
- Agent Runtime、ToolExecutor、ContextBuilder、Provider 契约
- Prompt / Skill / Workflow
- Vue 前端

已冻结的接口签名：

```python
class TextAnalysisRequest(BaseModel): ...
class KeywordAnalysis(BaseModel): ...
class ExerciseOption(BaseModel): ...
class ExerciseQuestion(BaseModel): ...
class TextAnalysisResponse(BaseModel): ...
```

验收标准：

- `raw_text` 不能为空。
- `target_abilities` 只能使用 `Ability` 常量中的值。
- `max_keywords` 范围为 1 到 12。
- 请求体 extra 字段被拒绝，包括 `user_id/session_id/permission_scope`。

RED 测试：

- 非法 ability 返回模型校验失败。
- 空 `raw_text` 校验失败。
- 请求体包含 `user_id` 校验失败。

GREEN 实现要求：

- 使用 Pydantic v2 `ConfigDict(extra="forbid")`。
- 不写任何业务逻辑。

完整回归命令：

- `python -m pytest backend\tests\test_learning_models.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增英语分析接口模型`

### 任务 2：新增训练任务与提交模型

目标：新增训练任务、练习题、训练提交和训练结果响应模型，字段与契约第 3、4、5 节一致。

依赖：任务 1。

允许修改的文件：

- `backend/tests/test_training_models.py`

允许新增的文件：

- `backend/app/api/training_models.py`

禁止修改范围：

- 数据库 Schema
- Repository 实现
- Agent Runtime、ToolExecutor、ContextBuilder
- Prompt / Skill / Workflow
- Vue 前端

已冻结的接口签名：

```python
class TrainingOption(BaseModel): ...
class TrainingQuestion(BaseModel): ...
class TrainingTaskContent(BaseModel): ...
class TrainingAnswer(BaseModel): ...
class TrainingSubmitRequest(BaseModel): ...
class QuestionScoreResult(BaseModel): ...
class TrainingScore(BaseModel): ...
class TrainingSubmitResponse(BaseModel): ...
class TrainingTaskSummary(BaseModel): ...
class TrainingResultResponse(BaseModel): ...
```

验收标准：

- MVP 仅允许 `question_type="MULTIPLE_CHOICE"`。
- `answers` 至少 1 项。
- `time_spent_seconds` 非负。
- 请求体 extra 字段被拒绝，包括身份字段。

RED 测试：

- 非 MULTIPLE_CHOICE 题型校验失败。
- 空 answers 校验失败。
- `time_spent_seconds=-1` 校验失败。

GREEN 实现要求：

- 模型只做结构校验，不访问数据库。
- 保持 snake_case 字段风格。

完整回归命令：

- `python -m pytest backend\tests\test_training_models.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增训练任务与提交模型`

### 任务 3：实现确定性训练评分器

目标：实现不依赖 LLM 和数据库的客观题评分器。

依赖：任务 2。

允许修改的文件：

- `backend/tests/test_training_scorer.py`

允许新增的文件：

- `backend/app/services/training_scorer.py`

禁止修改范围：

- 数据库 Schema
- Repository
- API 路由
- Agent Runtime、ToolExecutor、ContextBuilder
- Prompt / Skill / Workflow

已冻结的接口签名：

```python
def score_training_submission(
    task_content: dict,
    answers: list[dict],
    *,
    used_hints: list[str] | None = None,
) -> dict:
    ...
```

验收标准：

- 按 `question_id` 匹配答案，不按数组顺序推断。
- 正确计算 `total/correct/accuracy/passed/question_results/error_types/used_hints`。
- 未答题记错，错误类型来自 `error_type_on_wrong` 或 `UNKNOWN_ERROR`。
- 多余答案不影响已有题目正确性，并在输出中可审计。

RED 测试：

- 全对、部分错误、未答题、多余答案、乱序答案各一例。

GREEN 实现要求：

- 纯函数实现。
- 不调用外部服务。
- 不记录日志。

完整回归命令：

- `python -m pytest backend\tests\test_training_scorer.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`实现确定性训练评分器`

## 阶段二：薄业务 Service

### 任务 4：实现文本分析确定性服务

目标：实现 `MOCK_DETERMINISTIC` 文本分析服务，用于 API 在没有完整 Agent 教学 Skill 前返回稳定结构化分析结果。

依赖：任务 1、任务 2。

允许修改的文件：

- `backend/tests/test_learning_analysis_service.py`

允许新增的文件：

- `backend/app/services/learning_analysis.py`

禁止修改范围：

- Agent Runtime、Prompt、Skill、Provider
- 数据库 Schema
- Vue 前端

已冻结的接口签名：

```python
def analyze_english_text(request: TextAnalysisRequest) -> TextAnalysisResponse:
    ...
```

验收标准：

- 返回原始英文文本。
- 返回不超过 `max_keywords` 个关键词。
- 每个关键词包含 `text/meaning_zh/usage_note/ability/selection_reason`。
- `generate_exercise=True` 时返回一题 MULTIPLE_CHOICE。
- `agent_feedback` 为稳定中文模板，不声称来自真实 Agent 思维。

RED 测试：

- 常规英文段落能返回关键词和练习题。
- `generate_exercise=False` 时 exercise 为 null。
- 文本过短时返回 warnings。

GREEN 实现要求：

- 使用确定性规则抽取英文 token，过滤过短 token 和重复 token。
- 中文释义可以使用小型内置词典加“待学习词汇”兜底。
- 不调用 LLM。

完整回归命令：

- `python -m pytest backend\tests\test_learning_analysis_service.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`实现确定性英语分析服务`

### 任务 5：实现训练任务薄封装服务

目标：基于现有 `generated_tasks` 表实现训练任务创建和归属校验薄封装。

依赖：任务 2、任务 4。

允许修改的文件：

- `backend/tests/test_training_task_service.py`

允许新增的文件：

- `backend/app/services/training_tasks.py`

禁止修改范围：

- 数据库 Schema
- Agent Runtime、ToolExecutor、ContextBuilder
- Prompt / Skill / Workflow
- Vue 前端

已冻结的接口签名：

```python
def create_task_from_analysis(
    database_path,
    *,
    user_id: int,
    session_id: int,
    analysis: dict,
) -> int:
    ...

def get_user_training_task(database_path, *, user_id: int, task_id: int) -> dict:
    ...
```

验收标准：

- 写入 `generated_tasks`，`task_type="LOW_PRESSURE_LEARNING"`。
- `content_json` 符合 `TrainingTaskContent`。
- `quality_check_result.status="PASSED"`。
- 读取任务时校验 `user_id`，其他用户访问抛出受控业务错误。

RED 测试：

- 创建任务后可通过 Repository 读回。
- 其他用户读取同一 task 被拒绝。
- 不存在 task 返回受控 not found。

GREEN 实现要求：

- 复用现有 `create_generated_task/get_generated_task`。
- 不新增表。

完整回归命令：

- `python -m pytest backend\tests\test_training_task_service.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`实现训练任务薄封装服务`

### 任务 6：实现学习证据写入服务

目标：为训练提交封装学习证据 payload 生成和 append-only 写入。

依赖：任务 3、任务 5。

允许修改的文件：

- `backend/tests/test_learning_evidence_service.py`

允许新增的文件：

- `backend/app/services/learning_evidence.py`

禁止修改范围：

- 数据库 Schema
- Agent Runtime、ContextBuilder、Memory
- Prompt / Skill / Workflow

已冻结的接口签名：

```python
def record_training_submission_evidence(
    database_path,
    *,
    user_id: int,
    session_id: int,
    task_id: int,
    answers: list[dict],
    score_result: dict,
    time_spent_seconds: int | None,
) -> int:
    ...
```

验收标准：

- 写入 `learning_evidence.evidence_type="TRAINING_ANSWER"`。
- payload 包含契约第 4.3 节所有字段。
- 多次调用追加多条证据，不覆盖旧证据。

RED 测试：

- 写入后按 task 查询能读回完整 payload。
- 两次写入生成两条不同 evidence。

GREEN 实现要求：

- 复用现有 `create_learning_evidence`。
- 不做画像建议写入。

完整回归命令：

- `python -m pytest backend\tests\test_learning_evidence_service.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`实现训练提交证据写入服务`

### 任务 7：实现画像更新建议薄服务

目标：基于确定性评分结果写入普通 `profile_update_suggestions`，不应用画像、不生成 profile snapshot。

依赖：任务 3、任务 6。

允许修改的文件：

- `backend/tests/test_profile_suggestion_service.py`

允许新增的文件：

- `backend/app/services/profile_suggestions.py`

禁止修改范围：

- 数据库 Schema
- Profile snapshot 写入逻辑
- Agent Runtime、Memory、Workflow
- Prompt / Skill

已冻结的接口签名：

```python
def propose_profile_update_from_score(
    database_path,
    *,
    user_id: int,
    evidence_id: int,
    score_result: dict,
) -> int:
    ...
```

验收标准：

- 写入 `profile_update_suggestions`。
- `direction` 只能是 `IMPROVE/DECLINE/UNCERTAIN/NO_CHANGE` 中的一个。
- `evidence_refs` 包含 evidence_id。
- `agent_payload.source="DETERMINISTIC_SCORER"`。
- 不修改 `profile_snapshots`。

RED 测试：

- 高正确率生成 IMPROVE 或 NO_CHANGE。
- 低正确率生成 DECLINE。
- 无能力信息生成 UNCERTAIN。

GREEN 实现要求：

- 复用 `create_profile_suggestion`。
- 不扩展画像建议状态枚举。

完整回归命令：

- `python -m pytest backend\tests\test_profile_suggestion_service.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`实现画像建议薄服务`

### 任务 8：实现训练提交编排服务

目标：组合任务归属校验、评分、证据写入和画像建议写入，形成训练提交业务闭环服务。

依赖：任务 3、5、6、7。

允许修改的文件：

- `backend/tests/test_training_submission_service.py`

允许新增的文件：

- `backend/app/services/training_submission.py`

禁止修改范围：

- 数据库 Schema
- API 路由
- Agent Runtime、ToolExecutor、ContextBuilder
- Prompt / Skill / Workflow

已冻结的接口签名：

```python
def submit_training_task(
    database_path,
    *,
    user_id: int,
    task_id: int,
    answers: list[dict],
    time_spent_seconds: int | None = None,
    used_hints: list[str] | None = None,
) -> dict:
    ...
```

验收标准：

- 当前用户只能提交自己的任务。
- 返回契约第 4.1 节响应所需字段。
- 成功提交写入 learning evidence 和 profile suggestion。
- 不存在任务、其他用户任务、非法任务内容均返回受控业务错误。

RED 测试：

- 正常提交完整闭环。
- 其他用户提交被拒绝。
- 不存在任务返回 not found。
- 非 MULTIPLE_CHOICE 内容返回受控错误。

GREEN 实现要求：

- 不调用 Agent 或 LLM。
- 不新增表。
- 错误类型用本服务内稳定异常类或稳定错误 dict。

完整回归命令：

- `python -m pytest backend\tests\test_training_submission_service.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`实现训练提交编排服务`

## 阶段三：业务 API 路由

### 任务 9：实现文本分析 API 路由

目标：新增 `/api/learning/analyze-text`，将 API 身份绑定和文本分析服务接起来。

依赖：任务 1、4。

允许修改的文件：

- `backend/app/main.py`
- `backend/tests/test_learning_api.py`

允许新增的文件：

- `backend/app/api/learning.py`

禁止修改范围：

- Agent Runtime、ToolExecutor、ContextBuilder
- Provider 公共契约
- 数据库 Schema
- Vue 前端

已冻结的接口签名：

```http
POST /api/learning/analyze-text
Headers:
  X-LingoForge-User-Id: int
  X-LingoForge-Session-Id: int optional
Body: TextAnalysisRequest
Response: TextAnalysisResponse
```

验收标准：

- 请求体不能包含身份字段。
- 缺失或非法用户头返回 422。
- 正常请求返回关键词、练习题和 `agent_feedback`。

RED 测试：

- 正常分析成功。
- 请求体带 `user_id` 被拒绝。
- 缺失用户头不调用服务。

GREEN 实现要求：

- 使用 `APIRouter(prefix="/api/learning")`。
- 路由注册进 `create_app`。
- 不写数据库。

完整回归命令：

- `python -m pytest backend\tests\test_learning_api.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增文本分析 API`

### 任务 10：实现训练提交 API 路由

目标：新增 `/api/training/tasks/{task_id}/submit`，绑定当前用户并调用训练提交服务。

依赖：任务 2、8。

允许修改的文件：

- `backend/app/main.py`
- `backend/tests/test_training_api.py`

允许新增的文件：

- `backend/app/api/training.py`

禁止修改范围：

- 数据库 Schema
- Agent Runtime、ToolExecutor、ContextBuilder
- Prompt / Skill / Workflow
- Vue 前端

已冻结的接口签名：

```http
POST /api/training/tasks/{task_id}/submit
Headers:
  X-LingoForge-User-Id: int
Body: TrainingSubmitRequest
Response: TrainingSubmitResponse
```

验收标准：

- API 层使用请求头绑定 `user_id`。
- 请求体包含身份字段时返回 422。
- 其他用户任务返回 403。
- 成功提交返回 score、question_results、evidence_id、profile_suggestion_id。

RED 测试：

- 正常提交成功。
- 身份覆盖字段被拒绝。
- 其他用户任务被拒绝。
- 非法 answers 被拒绝。

GREEN 实现要求：

- 业务错误映射为稳定 `detail.code`。
- 不调用 Agent 或 LLM。

完整回归命令：

- `python -m pytest backend\tests\test_training_api.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增训练提交 API`

### 任务 11：实现训练结果查询 API 路由

目标：新增 `/api/training/tasks/{task_id}/result`，返回任务摘要和最新提交结果。

依赖：任务 5、6、10。

允许修改的文件：

- `backend/app/api/training.py`
- `backend/tests/test_training_api.py`

允许新增的文件：

- 若确有需要，可新增 `backend/app/services/training_results.py`

禁止修改范围：

- 数据库 Schema
- Agent Runtime、ContextBuilder、ToolExecutor
- Prompt / Skill / Workflow
- Vue 前端

已冻结的接口签名：

```http
GET /api/training/tasks/{task_id}/result
Headers:
  X-LingoForge-User-Id: int
Response: TrainingResultResponse
```

验收标准：

- 当前用户只能查询自己的任务。
- 无提交时 `latest_submission=null`。
- 有多次提交时返回最新 evidence。
- 响应不包含其他用户数据。

RED 测试：

- 无提交查询。
- 一次提交后查询。
- 两次提交后返回最新。
- 其他用户查询被拒绝。

GREEN 实现要求：

- 可通过现有 `get_learning_evidence_by_task` 查询，并在服务/API 层过滤 task 归属。
- 不新增表。

完整回归命令：

- `python -m pytest backend\tests\test_training_api.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增训练结果查询 API`

## 阶段四：Repository 查询补强与测试基础设施

### 任务 12：补充训练 Repository 归属查询 helper

目标：在不改 Schema 的前提下，为 Service 提供明确的按用户读取任务、读取最新提交证据 helper。

依赖：任务 5、6、11。

允许修改的文件：

- `backend/app/repositories/training.py`
- `backend/tests/test_training_repository.py`

允许新增的文件：无。

禁止修改范围：

- 数据库 Schema
- API 路由
- Agent Runtime、ToolExecutor、ContextBuilder
- Prompt / Skill / Workflow

已冻结的接口签名：

```python
def get_generated_task_for_user(database_path, *, user_id: int, task_id: int) -> dict | None:
    ...

def get_latest_training_submission_evidence(database_path, *, task_id: int) -> dict | None:
    ...
```

验收标准：

- `get_generated_task_for_user` 只返回属于该用户的任务。
- 最新提交证据按 `created_at DESC, id DESC` 截取最新一条。
- JSON 字段反序列化行为与现有 Repository 一致。

RED 测试：

- 其他用户任务返回 None。
- 多条 evidence 返回最新一条。

GREEN 实现要求：

- 只做查询 helper，不改变现有函数行为。

完整回归命令：

- `python -m pytest backend\tests\test_training_repository.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`补充训练任务归属查询`

### 任务 13：整理后端测试数据工厂

目标：新增测试工厂 helper，减少 API 和 Service 测试重复建用户、session、任务、题目。

依赖：任务 2、5。

允许修改的文件：

- `backend/tests/test_training_api.py`
- `backend/tests/test_training_submission_service.py`
- `backend/tests/test_training_task_service.py`

允许新增的文件：

- `backend/tests/factories.py`

禁止修改范围：

- 生产代码
- 数据库 Schema
- Agent Runtime、ToolExecutor、ContextBuilder
- Prompt / Skill

已冻结的接口签名：

```python
def create_user_with_session(db_path, *, stage: str = "FIRST_MAIN") -> dict:
    ...

def create_multiple_choice_task(db_path, *, user_id: int, session_id: int) -> int:
    ...
```

验收标准：

- 工厂只服务测试，不被生产代码导入。
- 使用现有 Repository 创建数据。
- 被整理的测试行为不变。

RED 测试：

- 工厂创建的任务可被 `get_generated_task` 读回。

GREEN 实现要求：

- 避免把业务判断写进工厂。

完整回归命令：

- `python -m pytest backend\tests`

推荐中文提交信息：`整理后端测试数据工厂`

### 任务 14：补充 Agent API 与 DeepSeek Provider 反例测试

目标：合并完成上一轮计划中尚未执行的 API 身份反例、未知工具摘要、DeepSeek HTTP 错误和坏响应测试补强。

依赖：当前 `0f17ee6` 之后代码。

允许修改的文件：

- `backend/tests/test_agent_api.py`
- `backend/tests/test_deepseek_provider.py`
- `backend/tests/test_config.py`

允许新增的文件：无。

禁止修改范围：

- `backend/app/agent/`
- `backend/app/llm/deepseek_provider.py`
- `backend/app/api/agent.py`
- Provider 公共契约
- ToolExecutor 公共契约

已冻结的接口签名：

```python
DeepSeekHTTPError
DeepSeekBadResponseError
POST /api/agent/run
```

验收标准：

- 400/500 映射为 `DeepSeekHTTPError`。
- choices/message/tool_calls/arguments 格式错误映射为 `DeepSeekBadResponseError`。
- Agent API 缺失身份头、非法身份头、未知工具均有反例测试。
- 不访问真实 DeepSeek API。

RED 测试：

- 每个错误路径先失败再实现测试所需 fixture 调整。

GREEN 实现要求：

- 原则上只补测试；只有发现阻塞性真实 bug 才可做最小修复，并在提交说明中写清。

完整回归命令：

- `python -m pytest backend\tests\test_agent_api.py backend\tests\test_deepseek_provider.py backend\tests\test_config.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`补强 Agent 与 DeepSeek 反例测试`

## 阶段五：Demo 数据、Smoke 与文档

### 任务 15：新增 Demo seed 脚本

目标：新增可重复运行的 demo 数据脚本，创建演示用户、目标、画像、词汇、session 和一个可提交训练任务。

依赖：任务 5。

允许修改的文件：

- `backend/tests/test_demo_seed_script.py`

允许新增的文件：

- `scripts/seed_demo.py`

禁止修改范围：

- 数据库 Schema
- 后端业务模块
- Vue 前端
- Agent Runtime、Prompt、Skill

已冻结的接口签名：

```bash
python scripts\seed_demo.py --database-path <path>
```

验收标准：

- 脚本可重复运行，不因已有数据崩溃。
- 不写入真实 API Key。
- 至少创建一个用户、一个 user_goal、一个 profile_snapshot、若干 vocabulary_items、一个 training_session、一个 generated_task。
- 输出中文摘要，包含 user_id/session_id/task_id。

RED 测试：

- 在临时数据库运行脚本后断言核心数据存在。
- 连续运行两次仍通过。

GREEN 实现要求：

- 使用现有 Repository。
- 不调用 Agent 或 DeepSeek。

完整回归命令：

- `python -m pytest backend\tests\test_demo_seed_script.py`
- `python scripts\seed_demo.py --database-path %TEMP%\lingoforge_demo.sqlite3`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增演示数据种子脚本`

### 任务 16：新增 Mock 模式后端 smoke test 与 README 说明

目标：新增 Mock 模式 smoke test 脚本，并补充 README 后端启动、DeepSeek 环境变量、文本分析和训练提交 API 示例。

依赖：任务 9、10、11、15。

允许修改的文件：

- `README.md`
- `backend/tests/test_smoke_backend_script.py`

允许新增的文件：

- `scripts/smoke_backend.py`

禁止修改范围：

- `backend/app/`
- 数据库 Schema
- Vue 前端
- Agent Runtime、Prompt、Skill

已冻结的接口签名：

```bash
python scripts\smoke_backend.py
```

验收标准：

- smoke 脚本使用临时数据库和 `LLM_MODE=mock`。
- 脚本调用 `/health`、`/api/learning/analyze-text`、`/api/training/tasks/{task_id}/submit`、`/api/training/tasks/{task_id}/result`。
- README 示例不包含真实密钥。
- README 说明身份通过请求头绑定，不能放在请求体。

RED 测试：

- 脚本运行失败时测试失败。

GREEN 实现要求：

- 脚本不写仓库内数据库。
- README 只做文档同步，不改架构规格。

完整回归命令：

- `python scripts\smoke_backend.py`
- `python -m pytest backend\tests\test_smoke_backend_script.py`
- `python -m pytest backend\tests`

推荐中文提交信息：`新增后端 smoke 测试与启动说明`

## 本计划完成后的交接要求

DS/Claude Code 完成后必须汇报：

- 每个任务对应提交哈希。
- 每个任务运行的测试命令和结果。
- 是否有任何偏离 `docs/IMPLEMENTATION_CONTRACTS.md` 的地方。
- 是否修改了禁止范围。
- 当前完整后端测试结果。

Codex 随后负责审查、修复高风险问题，并继续实现剩余核心模块。
