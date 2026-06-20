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
- 阅读导入 API（英文文本 / 可复制文本 PDF）；
- 阅读正文高亮、重点词汇释义、个人词汇本和 CSV 导出；
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

Agent Runtime、Context Expansion、Memory、Skill Registry 已具备课程作业版 MVP 的最小可运行实现，并由后端测试覆盖。

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

填好真实 Key 后，可以先单独验证 DeepSeek Provider：

```powershell
python scripts\verify_deepseek.py
```

该脚本会强制使用真实 DeepSeek Provider，通过项目内 Provider Adapter 发送一次极小请求，不会打印 API Key。若输出 `DeepSeek 验证通过。`，即可继续启动后端和前端演示。

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

### 阅读导入：英文文本

```powershell
curl -X POST http://localhost:8000/api/reader/import-text `
  -H "Content-Type: application/json" `
  -H "X-LingoForge-User-Id: 1" `
  -d '{"raw_text":"Climate change is a pressing challenge for communities worldwide.","max_keywords":8}'
```

返回 `raw_text`、`keywords` 和 `document_id`。前端会基于 `keywords` 在阅读页高亮正文。

### 阅读导入：英文 PDF

```powershell
curl -X POST http://localhost:8000/api/reader/import-pdf `
  -H "Content-Type: application/json" `
  -H "X-LingoForge-User-Id: 1" `
  -d '{"file_name":"sample.pdf","content_base64":"<PDF 文件 base64>","max_keywords":8}'
```

PDF 解析使用 `pypdf`，支持包含可复制文本的英文 PDF。纯扫描图片 PDF 需要先 OCR。

### 加入词汇本、查看和导出

```powershell
curl -X POST http://localhost:8000/api/reader/vocabulary `
  -H "Content-Type: application/json" `
  -H "X-LingoForge-User-Id: 1" `
  -d '{"text":"climate","meaning_zh":"气候","usage_note":"常与 change 搭配。","source_document_id":1}'

curl -X GET http://localhost:8000/api/reader/vocabulary `
  -H "X-LingoForge-User-Id: 1"

curl -X GET http://localhost:8000/api/reader/vocabulary/export.csv `
  -H "X-LingoForge-User-Id: 1" `
  -o lingoforge-vocabulary.csv
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

启动开发服务器（默认端口 5173）：

```powershell
npm run dev
```

构建：

```powershell
npm run build
```

前端默认调用 `http://localhost:8000` 的后端 API。如需修改，请设置环境变量 `VITE_API_BASE_URL`。

### 前端页面

| 页面 | 路由 | 说明 |
|------|------|------|
| 学习首页 | `/` | 默认首页：学习目标摘要、训练入口、机场任务、阶段检测、最近训练 |
| 阅读导入 | `/reader` | 导入英文 PDF 或文本，展示正文高亮、释义、词汇本和 CSV 导出 |
| 开始训练 | `/training` | 输入英文材料 → Agent 分析 → 答题 → 提交 |
| 训练结果 | `/training/:taskId/result` | 得分、正确率、每题正误与解析、Agent 反馈 |
| 学习记录 | `/history` | 历史训练会话列表，可展开查看任务 |
| 能力画像 | `/profile` | CET-6 目标设置、已确认画像、画像更新建议 |
| 扩展任务 | `/sidequest` | 机场购票副线：NPC 对话场景，选择英语表达 |
| 阶段检测 | `/isolated-test` | 隔离测试：启动、答题、受控结果包 |

### 演示流程

1. 确认后端已启动并已初始化 Demo 数据：
   ```powershell
   python scripts\seed_demo.py --database-path <路径>
   ```
2. 启动前端 `npm run dev`，访问 `http://localhost:5173`
3. 左侧导航进入「阅读导入」
4. 粘贴英文文本，或选择包含可复制英文正文的 PDF
5. 点击「解析并生成重点词汇」，确认正文显示且重点词被高亮
6. 在「重点词汇」区查看释义，点击「加入词汇本」
7. 在「我的词汇本」再次查看已加入词汇，点击「导出词汇表 CSV」
8. 左侧导航进入「开始训练」→ 使用内置 Demo 材料 → 「分析并生成训练」
9. 选择题答案 → 「提交答案」→ 查看训练结果
10. 左侧导航进入「扩展任务」→ 完成机场购票
11. 左侧导航进入「阶段检测」→ 启动检测 → 答题 → 提交
12. 左侧导航进入「学习记录」查看历史会话
13. 左侧导航进入「能力画像」设置目标

### 视觉风格

- Vue 3 + Vue Router 4 单页应用
- 浅色主题，紫色主色（#6C5CE7）
- 淡紫灰背景 + 白色卡片 + 深紫主按钮
- 10px 卡片圆角、8px 按钮圆角
- 参考 Inter / Noto Sans SC
- 组件化拆分：AppShell / SidebarNav / QuestionCard / OptionButton 等

### Demo 用户

默认使用 `user_id=1`（演示用户），配置集中在 `frontend/src/constants.js` 的 `DEMO_USER_ID`。

### 已实现功能

- LingoForge MVP 主线：英文材料驱动的 CET-6 自适应训练
- Agent 读取用户画像和学习历史，确定性服务完成质量校验、客观题判分、证据记录和画像建议
- 完整 Vue 应用壳与 8 个业务页面
- 英文 PDF / 文本导入、正文高亮、重点词汇释义、个人词汇本和 CSV 导出
- 用户目标保存与画像查看
- 英文材料输入 → Agent 分析 → 训练题生成
- 选择题答题与提交
- 训练结果展示（得分、正确率、每题正误、解析、Agent 反馈）
- 学习历史会话列表
- 机场购票副线任务
- 隔离测试启动、答题与受控结果

### 尚未实现功能

- 用户注册与登录系统
- 听力、口语、写作训练
- 完整背词流程（多阶段复习事件）
- 面向真实课堂展示的长周期第二次主线复训体验（当前已具备 API 层短训练、隔离检测与 smoke 串通）
- 副线信号到长期复习策略的复杂权重回流（当前已保存为待验证信号，不直接修改正式画像）
- 高亮 PDF 导出（当前支持词汇表 CSV 导出，尚未实现带高亮标注的 PDF 文件导出）
- 移动端适配（仅桌面端 1440×900+ 验证）

## 文档

- `docs/SPEC.md` — MVP 总规格入口
- `docs/ARCHITECTURE.md`
- `docs/DATA_MODEL.md`
- `docs/AGENT_ARCHITECTURE.md` — Agent 内部架构权威文档
- `docs/AGENT_RUNTIME.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TASK_BREAKDOWN.md`
- `docs/IMPLEMENTATION_CONTRACTS.md` — 业务接口契约冻结
