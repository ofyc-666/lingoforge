# LingoForge

LingoForge 是一个课程作业版 MVP：面向 CET-6 词汇与阅读的自适应学习 Agent。当前实现阶段优先保证本地仓库可安装、可启动、可测试、可重置 Demo 数据。

## 当前可用能力

- FastAPI 后端骨架；
- Vue 前端骨架；
- 前端真实调用后端健康检查；
- SQLite 初始化与清空机制；
- 最小核心 Schema；
- `LLMProvider` 抽象和 `MockLLMProvider`；
- 后端健康检查、配置读取和数据库初始化测试。

完整 Agent Runtime、真实 DeepSeek 调用、Function Calling 工具、业务主流程和 Image 2 视觉资产仍在后续任务中实现。

## 环境变量

复制 `.env.example` 为本地 `.env` 后再按需填写：

```powershell
Copy-Item .env.example .env
```

不要把 `.env` 或任何真实 API key 提交到仓库。

`DATABASE_PATH` 留空时会使用操作系统临时目录下的 LingoForge Demo SQLite。若你的本地文件系统支持 SQLite 日志文件，也可以显式改成项目内路径，例如 `./data/lingoforge.sqlite3`。

默认本地模式为：

```env
LLM_MODE=mock
LLM_PROVIDER=deepseek
DEEPSEEK_MODEL=deepseek-v4-flash
```

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

运行后端测试：

```powershell
python -m pytest backend\tests
```

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

- `docs/ARCHITECTURE.md`
- `docs/DATA_MODEL.md`
- `docs/AGENT_RUNTIME.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/TASK_BREAKDOWN.md`
