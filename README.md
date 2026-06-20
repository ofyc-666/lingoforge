# LingoForge

LingoForge 是一个课程作业版 MVP：面向 CET-6 词汇与阅读的自适应学习 Agent。当前实现阶段优先保证本地仓库可安装、可启动、可测试、可重置 Demo 数据。

## 当前可用能力

- FastAPI 后端骨架；
- Vue 前端骨架；
- 前端真实调用后端健康检查；
- SQLite 初始化与清空机制；
- 最小核心 Schema；
- `LLMProvider` 抽象和 `MockLLMProvider`；
- DeepSeek Provider（通过 Provider Adapter 隔离）；
- Agent API（Function Calling 闭环）；
- 用户画像摘要与目标保存 API；
- 文本分析 API（确定性 Mock 分析）；
- 文本分析并创建训练任务 API；
- 训练会话创建与列表 API；
- 训练任务列表与详情 API；
- 训练任务提交与评分 API；
- 训练结果查询 API；
- 训练任务质量校验服务；
- 学习历史分析服务（PROBLEM_TIMELINE + REVIEW_PRIORITY）；
- 隔离测试开始与提交 API（防泄漏 sanitizer）；
- 机场购票副线完成 API；
- 演示数据种子脚本（含隔离题和副线数据）；
- 完整后端 smoke 流程（10 个端点串通）；
- 后端健康检查、配置读取和数据库初始化测试。

完整 Agent Runtime、Context Expansion、Memory、Skill Registry 仍在后续任务中实现。

## 环境变量

复制 `.env.example` 为本地 `.env` 后再按需填写：

```powershell
Copy-Item .env.example .env
```

不要把 `.env` 或任何真实 API key 提交到仓库。

### Mock 模式（默认，本地开发）

```env
LLM_MODE=mock
LLM_PROVIDER=deepseek
DEEPSEEK_MODEL=deepseek-v4-flash
```

### DeepSeek 真实模式

```env
LLM_MODE=real
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_THINKING_ENABLED=false
```

`DATABASE_PATH` 留空时会使用操作系统临时目录下的 LingoForge Demo SQLite。若你的本地文件系统支持 SQLite 日志文件，也可以显式改成项目内路径，例如 `./data/lingoforge.sqlite3`。

## 后端

安装依赖：

```powershell
python -m pip install -r backend\requirements.txt
```

初始化或清空并重建 SQLite：

```powershell
python backend\scripts\reset_db.py
```

启动 FastAPI：

```powershell
python -m uvicorn app.main:app --app-dir backend --reload
```

### 演示数据

```powershell
python scripts\seed_demo.py --database-path <路径>
```

此脚本创建演示用户、目标、画像、词汇、训练会话和一个可提交训练任务。可重复运行，不写入真实密钥。

### Smoke 测试

```powershell
python scripts\smoke_backend.py
```

此脚本使用临时数据库和 Mock 模式，依次验证 10 个核心端点：

1. `GET /health`
2. `POST /api/profile/goal`
3. `GET /api/profile/summary`
4. `POST /api/training/sessions`
5. `POST /api/learning/analyze-text/create-task`
6. `POST /api/training/tasks/{task_id}/submit`
7. `GET /api/training/tasks/{task_id}/result`
8. `POST /api/sidequest/airport-ticket/complete`
9. `POST /api/isolated-tests/start`
10. `POST /api/isolated-tests/attempts/{attempt_id}/submit`

输出包含中文"通过"标记。所有身份通过请求头绑定，不放在请求体中。

运行后端测试：

```powershell
python -m pytest backend\tests
```

## API 示例

### 身份绑定

所有业务 API 使用请求头绑定当前用户，**不得将身份字段放在请求体**：

| 请求头 | 必须 | 说明 |
|--------|------|------|
| `X-LingoForge-User-Id` | 必填 | 当前用户 ID（整数） |
| `X-LingoForge-Session-Id` | 可选 | 当前训练会话 ID（整数） |

请求体中包含 `user_id`、`session_id`、`permission_scope` 等身份字段将被拒绝（HTTP 422）。

### 文本分析

```powershell
curl -X POST http://localhost:8000/api/learning/analyze-text `
  -H "Content-Type: application/json" `
  -H "X-LingoForge-User-Id: 1" `
  -d '{"raw_text":"Climate change is a pressing challenge.","target_abilities":["VOCABULARY_CONTEXT"],"max_keywords":5,"generate_exercise":true}'
```

### 训练提交

```powershell
curl -X POST http://localhost:8000/api/training/tasks/1/submit `
  -H "Content-Type: application/json" `
  -H "X-LingoForge-User-Id: 1" `
  -d '{"answers":[{"question_id":"q1","answer":"A"}],"time_spent_seconds":30}'
```

### 用户画像摘要

```powershell
curl -X GET http://localhost:8000/api/profile/summary `
  -H "X-LingoForge-User-Id: 1"
```

### 保存用户目标

```powershell
curl -X POST http://localhost:8000/api/profile/goal `
  -H "Content-Type: application/json" `
  -H "X-LingoForge-User-Id: 1" `
  -d '{"exam_type":"CET-6","days_until_exam":30,"target_score":550,"daily_minutes":30,"self_reported_weaknesses":["vocabulary"],"interest_topics":["technology"]}'
```

### 创建训练会话

```powershell
curl -X POST http://localhost:8000/api/training/sessions `
  -H "Content-Type: application/json" `
  -H "X-LingoForge-User-Id: 1" `
  -d '{"stage":"FIRST_MAIN"}'
```

### 文本分析并创建训练任务

```powershell
curl -X POST http://localhost:8000/api/learning/analyze-text/create-task `
  -H "Content-Type: application/json" `
  -H "X-LingoForge-User-Id: 1" `
  -H "X-LingoForge-Session-Id: 1" `
  -d '{"raw_text":"Climate change is a pressing challenge.","target_abilities":["VOCABULARY_CONTEXT"],"max_keywords":3,"generate_exercise":true}'
```

### 训练结果查询

```powershell
curl -X GET http://localhost:8000/api/training/tasks/1/result `
  -H "X-LingoForge-User-Id: 1"
```

### 机场购票副线完成

```powershell
curl -X POST http://localhost:8000/api/sidequest/airport-ticket/complete `
  -H "Content-Type: application/json" `
  -H "X-LingoForge-User-Id: 1" `
  -d '{"selected_expression":"I'\''d like to book a flight.","scene":"AIRPORT_TICKET","result":{"completed":true}}'
```

### 隔离测试开始

```powershell
curl -X POST http://localhost:8000/api/isolated-tests/start `
  -H "Content-Type: application/json" `
  -H "X-LingoForge-User-Id: 1" `
  -d '{"target_ability":"VOCABULARY_CONTEXT","limit":3}'
```

> 响应只包含 sanitized 题项（prompt + options），不含答案、解析或评分依据。

### 隔离测试提交

```powershell
curl -X POST http://localhost:8000/api/isolated-tests/attempts/1/submit `
  -H "Content-Type: application/json" `
  -H "X-LingoForge-User-Id: 1" `
  -d '{"answers":[{"item_id":1,"answer":"A"}],"time_spent_seconds":60}'
```

> 返回受控结果包，不含完整答案或详细解析。

### 身份安全提醒

- **所有 API 身份只能来自请求头**（`X-LingoForge-User-Id`、`X-LingoForge-Session-Id`）。
- **不得将 `user_id`、`session_id`、`permission_scope` 放入请求体**。请求体包含这些字段将被拒绝（HTTP 422）。
- **隔离测试开始和提交响应不返回 `answer_key`、`answer_rationale`、`distractor_rationale`**。
- README 和代码中不包含真实 API key。

## 前端

安装依赖：

```powershell
cd frontend
npm install
```

启动开发服务器：

```powershell
npm run dev
```

构建：

```powershell
npm run build
```

前端默认调用 `http://localhost:8000/health`。如需修改，请设置 `VITE_API_BASE_URL`。

## 文档

- `docs/SPEC.md` — MVP 总规格入口
- `docs/ARCHITECTURE.md`
- `docs/DATA_MODEL.md`
- `docs/AGENT_ARCHITECTURE.md` — Agent 内部架构权威文档
- `docs/AGENT_RUNTIME.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TASK_BREAKDOWN.md`
- `docs/IMPLEMENTATION_CONTRACTS.md` — 业务接口契约冻结
