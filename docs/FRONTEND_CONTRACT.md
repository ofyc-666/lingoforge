# LingoForge Vue Web 前端集成契约

本文档冻结后续 Vue Web 前端实现需要遵守的后端集成边界。它只描述页面、API、字段和状态，不规定具体组件文件结构。

## 1. 文档优先级

前端实现遇到重复或冲突时，按以下顺序判断：

1. `AGENTS.md`
2. `docs/SPEC.md`
3. `docs/AGENT_ARCHITECTURE.md`
4. 本文档
5. 本文档引用的其他接口、数据和验收文档

本文档不覆盖 Agent、Workflow、Memory、Prompt、Skill 的架构语义；这些仍以 `docs/AGENT_ARCHITECTURE.md` 为准。

## 2. 前端总流程

MVP 桌面端 Vue Web 使用一个主学习工作台承载核心流程：

1. 用户创建或选择训练 Session。
2. 用户输入英文材料。
3. 前端调用 Agent Workflow API，后端完成 Agent 决策、确定性文本分析、训练任务生成和质量校验。
4. 前端展示原文、关键词、中文释义、用法、练习题和 Agent 反馈。
5. 用户提交训练答案。
6. 前端展示确定性评分、错因、解析、学习证据和画像更新建议。
7. 用户查看学习历史、用户画像、隔离测试入口和机场副线入口。

前端不得自行判分、生成正式画像、推断学习历史趋势、访问隔离测试答案或复用隔离测试题内容。

## 3. 身份与模式

### 3.1 身份绑定

所有需要用户身份的 API 均由后端通过请求头绑定：

```http
X-LingoForge-User-Id: <int>
X-LingoForge-Session-Id: <int>
```

前端请求体不得包含 `user_id`、`session_id`、`permission_scope` 或等价身份字段。后端会拒绝正文身份覆盖。

### 3.2 Mock 与 DeepSeek 模式

前端不直接选择 Provider。运行模式由后端环境变量控制：

- `LLM_MODE=mock`：本地开发和演示默认模式。
- `LLM_MODE=deepseek`：真实 DeepSeek Provider，模型固定为项目约定的 `deepseek-v4-flash`。

前端只展示后端返回的稳定状态和错误信息，不显示 API Key、Provider 内部错误、traceback 或数据库路径。

## 4. 页面清单

### 4.1 主学习工作台

用途：英文输入、Agent 分析、关键词高亮、训练任务生成。

主要 API：

- `POST /api/training/sessions`
- `POST /api/agent/workflow/text-training`
- `GET /api/training/tasks/{task_id}`

页面状态：

- `loading`：创建 session、Agent Workflow 运行或任务加载中。
- `empty`：尚未输入英文材料。
- `success`：显示分析结果、关键词和训练任务。
- `error`：显示后端稳定错误码和用户可理解提示。

关键词高亮数据来自 `analysis.keywords`：

- `text`：英文关键词。
- `meaning_zh`：中文释义。
- `usage_note`：简短用法。
- `ability`：能力维度。
- `selection_reason`：选择原因。

训练任务数据来自 `task.content_json.questions`。前端可隐藏标准答案，直到用户提交后通过结果 API 或提交响应展示解析。

### 4.2 训练答题页面

用途：展示题目、选项、进度和提交。

主要 API：

- `GET /api/training/tasks/{task_id}`
- `POST /api/training/tasks/{task_id}/submit`
- `GET /api/training/tasks/{task_id}/result`

提交请求：

```json
{
  "answers": [
    {"question_id": "q1", "answer": "A"}
  ],
  "time_spent_seconds": 30,
  "used_hints": ["optional-hint-id"]
}
```

提交响应重点字段：

- `score.total`
- `score.correct`
- `score.accuracy`
- `score.passed`
- `question_results[].is_correct`
- `question_results[].error_type`
- `question_results[].explanation`
- `evidence_id`
- `profile_suggestion_id`
- `agent_feedback`

前端不得在提交前展示 `answer` 或 `explanation`，除非当前页面明确是结果页。

### 4.3 训练结果与学习历史页面

用途：展示本次结果、历史趋势、复习优先级和客观证据引用。

主要 API：

- `GET /api/training/tasks/{task_id}/result`
- `GET /api/learning/history/problem-timeline`
- `GET /api/learning/history/review-priority`

展示映射：

- 问题首次出现、最近出现、出现次数、跨 Session 次数来自后端学习历史 API。
- 复习优先级、复习窗口和风险等级来自确定性 `REVIEW_PRIORITY` 结果。
- `evidence_refs` 只作为引用和跳转线索，不让前端重新解释为画像结论。

页面状态：

- `empty`：暂无提交或历史证据。
- `success`：展示后端返回的趋势和复习建议。
- `error`：展示稳定错误信息。

### 4.4 用户画像与学习目标页面

用途：展示用户目标、最新画像、画像更新建议。

主要 API：

- `GET /api/profile/goal`
- `POST /api/profile/goal`
- `GET /api/profile/latest`
- `GET /api/profile/suggestions`

展示要求：

- 最新画像与画像建议必须区分展示。
- 前端不得把 `profile_update_suggestions` 直接当作已确认画像。
- 用户纠正入口 MVP 可暂不制作；后端保留数据能力。

### 4.5 隔离测试页面

用途：启动隔离测试、答题、提交、结果解释。

主要 API：

- `POST /api/isolated-tests/start`
- `GET /api/isolated-tests/{attempt_id}`
- `POST /api/isolated-tests/{attempt_id}/submit`
- `GET /api/isolated-tests/{attempt_id}/result`

硬约束：

- 测试前和测试中不得展示答案、解析、评分依据。
- 前端不得缓存或复用隔离测试题用于普通训练。
- 提交后只展示后端受控结果包。
- 隔离测试内容不得进入普通 Agent Context。

### 4.6 机场副线入口与结果页面

用途：展示机场购票副线入口、任务结果和非正式学习信号。

主要 API：

- `POST /api/sidequest/airport-ticket/complete`
- `GET /api/sidequest/history`

展示要求：

- 副线结果可作为体验反馈展示。
- 副线信号不得被前端显示为正式能力画像证据。
- 不得把副线结果直接写成画像更新建议。

## 5. 稳定错误响应

后端错误统一展示：

```json
{
  "detail": {
    "code": "STABLE_ERROR_CODE",
    "message": "用户可理解提示",
    "details": {}
  }
}
```

前端只显示 `message` 和必要的 `code`，不得显示 traceback、内部 SQL、数据库路径、Provider 密钥或原始异常。

## 6. 前端不得自行推断的业务逻辑

前端不得自行完成以下逻辑：

- 判分和错因分类。
- 画像更新建议生成或确认。
- 学习历史趋势判断。
- 复习优先级计算。
- Agent Skill 选择。
- Context Expansion。
- Memory 写入、压缩、争议或替代关系。
- 隔离测试答案、解析和评分依据管理。
- 副线信号转正式证据。

前端可以做：

- 表单校验、空状态提示、加载状态、错误展示。
- 基于后端字段的关键词高亮、卡片布局、进度显示。
- 调用后端 API 并展示返回结果。

## 7. 前端首轮实现建议

首轮 Vue 实现可优先完成以下页面：

1. 主学习工作台。
2. 训练答题与结果页。
3. 学习历史与画像侧栏。
4. 隔离测试和机场副线入口卡片。

视觉方向与生图提示词见 `docs/IMAGE2_UI_PROMPTS.md`。
