# LingoForge Claude Code 自动执行计划

## 使用范围

本文档列出当前规格与代码状态下，可以安全交给 Claude Code 自动完成的全部简单任务。它不是 Codex 核心实现计划，也不包含前端、Agent Runtime、ContextBuilder、记忆核心语义、Context Expansion、Prompt、教学 Skill、Workflow 总编排或公共接口设计。

Claude Code 执行本文档时必须遵守：

- 全部说明、汇报、测试报告和 Git 提交信息使用中文。
- 不修改 `AGENTS.md`、`docs/SPEC.md`、`docs/AGENT_ARCHITECTURE.md` 中定义的架构语义。
- 不修改前端目录。
- 不修改数据库 Schema。
- 不新增 Prompt，不修改 Skill 语义。
- 不实现 Agent Runtime、ContextBuilder、Context Expansion、DecisionValidator 或 Workflow 总编排。
- 每个任务按 TDD 执行，先写或补测试，再实现最小代码。
- 每个任务完成后运行任务指定测试，必要时运行 `python -m pytest backend\tests`。
- 每个任务应独立提交，提交信息使用本文建议的中文提交信息。

## 阶段一：后端基础工具

### 任务 1：新增 SQLite JSON 字段工具

**任务目标**

为后续 repository 和确定性服务提供最小 JSON 字段读写工具，避免各模块重复手写 `json.dumps` / `json.loads`。

**已确定的输入**

- Python 基础类型：`dict`、`list`、`str`、`int`、`float`、`bool`、`None`。
- SQLite TEXT 字段中的 JSON 字符串。
- 无效 JSON 字符串。

**已确定的输出**

- `to_json_text(value) -> str`：输出稳定 JSON 文本，中文不转义。
- `from_json_text(text, default)`：解析成功返回对象；空值或无效 JSON 返回 `default`。

**允许修改的文件范围**

- `backend/app/storage/json_fields.py`
- `backend/app/storage/__init__.py`
- `backend/tests/test_json_fields.py`

**禁止修改的范围**

- 不修改数据库 Schema。
- 不修改现有业务逻辑。
- 不新增第三方依赖。
- 不修改 LLM、Agent、Workflow、Prompt、Skill 或前端。

**验收标准**

- JSON 文本稳定可比较。
- 中文内容保持可读。
- 无效 JSON 不抛出未处理异常，而是返回默认值。
- 工具函数无数据库副作用。

**测试要求**

- 先新增 `backend/tests/test_json_fields.py`。
- 覆盖字典、列表、中文字符串、空值、无效 JSON。
- 运行：`python -m pytest backend\tests\test_json_fields.py`

**依赖关系**

- 无。

**建议的中文 Git 提交信息**

`新增 SQLite JSON 字段工具`

### 任务 2：新增后端枚举常量与基础校验

**任务目标**

集中定义当前 Schema 和规格已经明确的枚举常量，供 repository 和普通校验复用。

**已确定的输入**

- 当前文档已确定的能力维度、Workflow Stage、session 状态、调用类型、调用状态、画像建议状态、记忆状态。

**已确定的输出**

- 常量集合或轻量枚举。
- `is_valid_ability(value)`、`is_valid_workflow_stage(value)` 等简单校验函数。

**允许修改的文件范围**

- `backend/app/constants.py`
- `backend/tests/test_constants.py`

**禁止修改的范围**

- 不修改 DeepSeek 模型配置。
- 不修改数据库 Schema。
- 不设计公共 API。
- 不修改 Prompt、Skill 语义、Agent Runtime、ContextBuilder 或 Workflow 总编排。

**验收标准**

- 覆盖 4 类能力维度。
- 覆盖当前 Schema 已使用的主要状态值。
- `NEEDS_REVIEW` 仅作为合法记忆状态被包含。
- 画像建议状态只能采用当前 Schema 或规格已经明确的值，不得自行扩展。
- 非法值校验返回 false，不抛出未处理异常。

**测试要求**

- 先新增 `backend/tests/test_constants.py`。
- 覆盖合法与非法能力、阶段和状态。
- 运行：`python -m pytest backend\tests\test_constants.py`

**依赖关系**

- 无。

**建议的中文 Git 提交信息**

`新增后端枚举常量和校验`

### 任务 3：新增 repository 基础数据库辅助

**任务目标**

为后续 repository 提供薄封装，减少重复 SQL 样板，但不改变数据库连接策略。

**已确定的输入**

- 当前 `backend/app/database.py` 的 `connect` 函数。
- SQLite row。
- SQL 参数。

**已确定的输出**

- `fetch_one`、`fetch_all`、`execute` 或等价小函数。
- row 转 dict 的辅助函数。
- 不持有全局连接，不引入 ORM。

**允许修改的文件范围**

- `backend/app/repositories/base.py`
- `backend/app/repositories/__init__.py`
- `backend/tests/test_repository_base.py`

**禁止修改的范围**

- 不修改 `backend/app/database.py` 的连接语义。
- 不引入 ORM。
- 不修改数据库 Schema。
- 不修改业务服务、Agent、Workflow 或前端。

**验收标准**

- 支持传入临时数据库路径。
- 查询不存在记录时返回 `None` 或空列表。
- 写入后提交生效。
- 外键约束仍由连接层启用。

**测试要求**

- 先新增 `backend/tests/test_repository_base.py`。
- 使用临时数据库路径，不污染开发数据库。
- 运行：`python -m pytest backend\tests\test_repository_base.py`

**依赖关系**

- 任务 1。

**建议的中文 Git 提交信息**

`新增 repository 基础数据库辅助`

## 阶段二：当前 Schema 的普通 Repository

### 任务 4：实现用户、目标和画像 Repository

**任务目标**

为 `users`、`user_goals`、`profile_snapshots`、`profile_update_suggestions` 提供普通 CRUD 和简单查询。

**已确定的输入**

- `display_name`
- 用户目标字段
- 画像 JSON
- 画像建议字段
- 临时数据库路径

**已确定的输出**

- 创建用户。
- 获取用户。
- 保存用户目标。
- 获取最新用户目标。
- 保存画像快照。
- 获取最新画像快照。
- 写入画像更新建议。
- 按用户读取画像建议列表。

**允许修改的文件范围**

- `backend/app/repositories/users.py`
- `backend/tests/test_user_repository.py`

**禁止修改的范围**

- 不修改 Schema。
- 不修改画像更新校验语义。
- 不实现 `submit_profile_update_suggestion` 工具。
- 不直接应用画像建议。
- 不修改 Agent Runtime、Memory Service、Workflow 或前端。

**验收标准**

- 所有写入均能回读。
- JSON 字段以对象形式传入和返回。
- 最新画像按 `created_at` 和自增 ID 稳定选择。
- 不存在用户时返回空结果，不伪造数据。

**测试要求**

- 先新增 `backend/tests/test_user_repository.py`。
- 使用临时数据库。
- 覆盖创建、读取、最新画像、画像建议写入。
- 运行：`python -m pytest backend\tests\test_user_repository.py`

**依赖关系**

- 任务 1。
- 任务 3。

**建议的中文 Git 提交信息**

`新增用户目标和画像 repository`

### 任务 5：实现词汇、Skill 元数据和候选词 Repository

**任务目标**

为 `vocabulary_items`、`skill_versions`、`candidate_vocabulary_events` 提供普通写入与查询。

**已确定的输入**

- 词汇文本、中文释义、标签、来源类型。
- Skill 元数据 JSON 字段。
- 候选词事件字段。

**已确定的输出**

- 创建词汇项。
- 按 ID 获取词汇项。
- 按标签或来源类型列出词汇项。
- 创建 Skill 版本元数据。
- 按 `skill_id` 和 `version` 获取 Skill 元数据。
- 写入候选词事件。
- 读取用户最近候选词事件。

**允许修改的文件范围**

- `backend/app/repositories/vocabulary.py`
- `backend/tests/test_vocabulary_repository.py`

**禁止修改的范围**

- 不编写或修改教学 Skill 语义。
- 不生成 Prompt。
- 不修改 Schema。
- 不实现 Skill Registry。
- 不修改 Agent Runtime、Workflow 或前端。

**验收标准**

- `skill_id + version` 唯一约束被测试覆盖。
- JSON 字段以对象形式传入和返回。
- 查询不存在记录时返回空结果。
- 候选词事件能保留副线 signal 引用字段，但不解释其业务含义。

**测试要求**

- 先新增 `backend/tests/test_vocabulary_repository.py`。
- 覆盖词汇、Skill 版本、候选词事件。
- 运行：`python -m pytest backend\tests\test_vocabulary_repository.py`

**依赖关系**

- 任务 1。
- 任务 3。

**建议的中文 Git 提交信息**

`新增词汇和 Skill 元数据 repository`

### 任务 6：实现训练会话、生成任务和学习证据 Repository

**任务目标**

为 `training_sessions`、`generated_tasks`、`generated_task_validations`、`learning_evidence` 提供普通 CRUD 和按用户/会话查询。

**已确定的输入**

- 用户 ID。
- Workflow Stage。
- session 状态。
- 生成任务字段。
- 校验记录字段。
- 学习证据字段。

**已确定的输出**

- 创建训练会话。
- 更新训练会话状态和完成时间。
- 创建生成任务。
- 获取生成任务。
- 写入生成任务校验记录。
- 写入学习证据。
- 按用户、session、task 查询学习证据。

**允许修改的文件范围**

- `backend/app/repositories/training.py`
- `backend/tests/test_training_repository.py`

**禁止修改的范围**

- 不实现判分。
- 不实现生成任务质量校验。
- 不修改 Schema。
- 不设计 Workflow 状态机。
- 不修改 Agent Runtime、ContextBuilder、Prompt、Skill 或前端。

**验收标准**

- 会话、任务、校验、证据均可写入并回读。
- 原始证据写入是追加式，不覆盖旧记录。
- JSON 字段正常序列化和反序列化。
- 外键错误由 SQLite 抛出或被测试明确覆盖。

**测试要求**

- 先新增 `backend/tests/test_training_repository.py`。
- 覆盖会话、任务、校验记录和多条证据追加。
- 运行：`python -m pytest backend\tests\test_training_repository.py`

**依赖关系**

- 任务 1。
- 任务 3。
- 任务 4。
- 任务 5。

**建议的中文 Git 提交信息**

`新增训练会话和学习证据 repository`

### 任务 7：实现副线运行和副线信号 Repository

**任务目标**

为 `sidequest_runs` 和 `sidequest_signals` 提供普通写入和查询能力。

**已确定的输入**

- 用户 ID。
- 副线任务名。
- objective JSON。
- result JSON。
- 副线 signal 字段。

**已确定的输出**

- 创建副线运行记录。
- 写入一条或多条副线信号。
- 按用户读取待验证副线信号。
- 按 run ID 读取信号。

**允许修改的文件范围**

- `backend/app/repositories/sidequest.py`
- `backend/tests/test_sidequest_repository.py`

**禁止修改的范围**

- 不让副线信号写入 `learning_evidence`。
- 不更新正式画像。
- 不实现机场副线业务流程。
- 不修改 Schema。
- 不修改 Agent Runtime、Workflow 或前端。

**验收标准**

- 副线运行和一对多信号关系可回读。
- 待验证信号查询只返回 `is_pending_verification = 1` 的记录。
- 副线 repository 不写入画像或正式证据表。

**测试要求**

- 先新增 `backend/tests/test_sidequest_repository.py`。
- 覆盖 run 创建、多 signal 写入、待验证查询。
- 运行：`python -m pytest backend\tests\test_sidequest_repository.py`

**依赖关系**

- 任务 1。
- 任务 3。
- 任务 4。
- 任务 5。

**建议的中文 Git 提交信息**

`新增副线运行和信号 repository`

### 任务 8：实现隔离检测题与尝试 Repository

**任务目标**

为 `isolated_test_items`、`isolated_test_attempts`、`isolated_attempt_items` 提供普通 CRUD 和连接关系查询。

**已确定的输入**

- 隔离题目标能力。
- item version。
- item payload。
- answer key 和 rationale JSON。
- 用户答案、分数 JSON、用时。

**已确定的输出**

- 创建隔离题。
- 按能力列出 active 隔离题。
- 创建隔离检测尝试。
- 关联 attempt 和 item。
- 读取 attempt 及其 item 列表。

**允许修改的文件范围**

- `backend/app/repositories/isolated_tests.py`
- `backend/tests/test_isolated_repository.py`

**禁止修改的范围**

- 不实现 `get_isolated_test_items` 服务。
- 不实现隔离题阶段权限。
- 不把隔离题暴露给 Agent。
- 不修改 Schema。
- 不修改 Agent Runtime、Workflow 或前端。

**验收标准**

- 连接表能保持题目顺序和版本。
- active 过滤可用。
- 重复关联同一 attempt 和 item 时遵守唯一约束。
- repository 只做数据访问，不做隔离权限裁决。

**测试要求**

- 先新增 `backend/tests/test_isolated_repository.py`。
- 覆盖题目创建、active 查询、attempt 创建、连接表关系。
- 运行：`python -m pytest backend\tests\test_isolated_repository.py`

**依赖关系**

- 任务 1。
- 任务 3。
- 任务 4。

**建议的中文 Git 提交信息**

`新增隔离检测 repository`

### 任务 9：实现工具调用和 Agent 决策日志 Repository

**任务目标**

为 `tool_call_logs` 和 `agent_decision_logs` 提供普通写入和查询能力。

**已确定的输入**

- 用户 ID，可为空。
- session ID，可为空。
- call name、call type、input JSON、output JSON、status、error_code。
- decision type、input summary JSON、decision JSON、evidence_refs。

**已确定的输出**

- 写入工具调用日志。
- 写入 Agent 决策日志。
- 按用户、session、call type 查询日志。
- 按 session 查询 Agent 决策。

**允许修改的文件范围**

- `backend/app/repositories/logs.py`
- `backend/tests/test_logs_repository.py`

**禁止修改的范围**

- 不实现 Function Calling Loop。
- 不实现 Agent Decision Schema 校验。
- 不实现 Context Manifest。
- 不修改 Schema。
- 不修改 Agent Runtime、Workflow 或前端。

**验收标准**

- 成功和失败日志均可记录。
- JSON 字段可回读为对象。
- 查询按创建顺序稳定返回。
- 不存在 session 时可返回空列表。

**测试要求**

- 先新增 `backend/tests/test_logs_repository.py`。
- 覆盖工具日志、服务日志、Agent 决策日志。
- 运行：`python -m pytest backend\tests\test_logs_repository.py`

**依赖关系**

- 任务 1。
- 任务 3。
- 任务 4。

**建议的中文 Git 提交信息**

`新增工具和决策日志 repository`

## 阶段三：当前基础能力的测试补强

### 任务 10：补充数据库 Schema 完整性测试

**任务目标**

在不修改 Schema 的前提下，补充当前核心表的默认值、唯一约束和关键外键测试。

**已确定的输入**

- 当前 `backend/app/schema.sql`。
- 临时 SQLite 数据库。

**已确定的输出**

- 更完整的数据库约束回归测试。

**允许修改的文件范围**

- `backend/tests/test_database.py`

**禁止修改的范围**

- 不修改 `backend/app/schema.sql`。
- 不修改 repository。
- 不修改业务代码。
- 不修改前端。

**验收标准**

- 测试覆盖 `skill_versions` 的唯一约束。
- 测试覆盖 JSON 默认值字段至少 3 个代表表。
- 测试覆盖 `sidequest_signals`、`generated_tasks`、`isolated_attempt_items` 的关键外键。
- 所有测试使用临时数据库。

**测试要求**

- 先补测试。
- 运行：`python -m pytest backend\tests\test_database.py`

**依赖关系**

- 无。

**建议的中文 Git 提交信息**

`补充数据库 Schema 完整性测试`

### 任务 11：补充配置解析测试

**任务目标**

补充当前配置读取的边界测试，确保环境变量解析稳定且不泄露密钥。

**已确定的输入**

- 当前 `backend/app/config.py`。
- 环境变量：`CORS_ORIGINS`、`DEEPSEEK_THINKING_ENABLED`、`DATABASE_PATH`。

**已确定的输出**

- 配置解析回归测试。
- 如发现现有解析对大小写、空格或 false 值处理不稳定，可做最小修复。

**允许修改的文件范围**

- `backend/app/config.py`
- `backend/tests/test_config.py`

**禁止修改的范围**

- 不修改 DeepSeek 默认模型、base URL 或 thinking 默认值。
- 不新增配置项。
- 不打印或读取真实 API key。
- 不修改前端。

**验收标准**

- CORS 逗号分隔和空格裁剪行为有测试。
- bool true/false 常见写法有测试。
- `public_summary()` 不包含 `DEEPSEEK_API_KEY`。
- 默认配置保持不变。

**测试要求**

- 先补测试，再按需最小修复。
- 运行：`python -m pytest backend\tests\test_config.py`

**依赖关系**

- 无。

**建议的中文 Git 提交信息**

`补充配置解析边界测试`

### 任务 12：补充 Mock LLM Provider 测试

**任务目标**

补充 Mock Provider 对预设响应队列、工具名透传和 timeout 参数记录的测试，保证后续 Agent Runtime 测试可复用。

**已确定的输入**

- 当前 `MockLLMProvider`。
- `LLMMessage`、`LLMResponse`、`LLMToolCall`、`LLMToolSpec`。

**已确定的输出**

- Mock Provider 行为回归测试。
- 如发现现有 Mock 对测试注入不稳定，可做最小修复。

**允许修改的文件范围**

- `backend/app/llm/mock_provider.py`
- `backend/tests/test_llm_provider.py`

**禁止修改的范围**

- 不实现 DeepSeek Provider。
- 不改变 `LLMProvider.generate` 抽象接口。
- 不实现 Function Calling Loop。
- 不访问网络。
- 不修改前端。

**验收标准**

- 预设响应按顺序返回。
- 队列耗尽后回到默认 mock 响应。
- 默认响应记录传入工具名。
- 默认响应记录 timeout。

**测试要求**

- 先补测试，再按需最小修复。
- 运行：`python -m pytest backend\tests\test_llm_provider.py`

**依赖关系**

- 无。

**建议的中文 Git 提交信息**

`补充 Mock LLM Provider 行为测试`

### 任务 13：补充数据库重置脚本测试

**任务目标**

为 `backend/scripts/reset_db.py` 增加测试，确认脚本尊重 `DATABASE_PATH` 并可重复执行。

**已确定的输入**

- 临时数据库路径。
- `DATABASE_PATH` 环境变量。
- 当前 reset 脚本。

**已确定的输出**

- 脚本级回归测试。

**允许修改的文件范围**

- `backend/tests/test_reset_db_script.py`
- `backend/scripts/reset_db.py`

**禁止修改的范围**

- 不修改 Schema。
- 不修改数据库连接策略。
- 不填充种子数据。
- 不修改前端。

**验收标准**

- 测试能在临时路径执行 reset。
- reset 后核心表存在。
- 重复执行不失败。
- 输出不包含任何密钥。

**测试要求**

- 先新增 `backend/tests/test_reset_db_script.py`。
- 可使用 subprocess 或直接调用 `main()`，但必须隔离环境变量。
- 运行：`python -m pytest backend\tests\test_reset_db_script.py`

**依赖关系**

- 无。

**建议的中文 Git 提交信息**

`补充数据库重置脚本测试`

## 总体验证检查点

Claude Code 完成全部任务后，必须执行：

```powershell
python -m pytest backend\tests
git status --short
```

验收要求：

- 后端测试全部通过。
- 未修改前端目录。
- 未修改数据库 Schema。
- 未新增 Prompt 或 Skill 语义文件。
- 未提交真实 API key。
- 每个任务都有独立中文提交信息。
