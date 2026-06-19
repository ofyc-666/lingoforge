# LingoForge DS/Claude Code 简单任务计划 02

本文件只包含核心接口已经确定后，可以交给 DS/Claude Code 自动执行的机械任务。不得修改 Provider 公共契约、Agent Runtime、ToolExecutor、ContextBuilder、身份边界、Prompt、Skill、Workflow、数据库 Schema 或前端。

## 阶段一：DeepSeek 配置与错误路径测试补强

### 任务 1：补充 DeepSeek Base URL 与模型配置解析测试

任务目标：验证 `DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`、`DEEPSEEK_API_KEY` 从环境变量读取，并确认 `public_summary()` 不泄露密钥。

已确定输入：环境变量 `DEEPSEEK_BASE_URL`、`DEEPSEEK_MODEL`、`DEEPSEEK_API_KEY`。

已确定输出：`Settings` 中对应字段正确，`public_summary()` 不包含 API Key 名称和值。

允许修改的文件范围：

* `backend/tests/test_config.py`

禁止修改的范围：

* `backend/app/config.py`
* `backend/app/llm/`
* 数据库 Schema
* Agent Runtime、ToolExecutor、ContextBuilder

验收标准：

* 新测试覆盖默认值和环境变量覆盖。
* 测试不得打印或断言真实密钥。

测试要求：

* `python -m pytest backend\tests\test_config.py`

依赖关系：无。

建议的中文 Git 提交信息：`补充 DeepSeek 配置解析测试`

### 任务 2：补充 DeepSeek HTTP 非 401/429 错误映射测试

任务目标：验证 DeepSeek Provider 对普通 4xx/5xx 返回稳定 `DeepSeekHTTPError`，不泄露响应正文中的内部细节。

已确定输入：HTTP mock 返回 400、500。

已确定输出：抛出 `DeepSeekHTTPError`，错误类型稳定。

允许修改的文件范围：

* `backend/tests/test_deepseek_provider.py`

禁止修改的范围：

* `backend/app/llm/deepseek_provider.py`
* Provider 公共契约
* Agent Runtime、ToolExecutor、ContextBuilder

验收标准：

* 400 和 500 至少各有一个测试断言。
* 测试不得访问真实 DeepSeek API。

测试要求：

* `python -m pytest backend\tests\test_deepseek_provider.py`

依赖关系：依赖本轮 DeepSeek Provider 已实现。

建议的中文 Git 提交信息：`补充 DeepSeek HTTP 错误映射测试`

### 任务 3：补充 DeepSeek 返回格式错误测试

任务目标：验证 choices 缺失、message 缺失、tool_calls 非数组、工具参数非对象时均被拒绝为稳定坏响应错误。

已确定输入：HTTP mock 返回格式异常的 JSON。

已确定输出：抛出 `DeepSeekBadResponseError`。

允许修改的文件范围：

* `backend/tests/test_deepseek_provider.py`

禁止修改的范围：

* `backend/app/llm/deepseek_provider.py`
* Provider 公共契约
* Agent Runtime、ToolExecutor、ContextBuilder

验收标准：

* 覆盖至少三类格式错误。
* 不为了适配测试修改 Provider 行为。

测试要求：

* `python -m pytest backend\tests\test_deepseek_provider.py`

依赖关系：依赖本轮 DeepSeek Provider 已实现。

建议的中文 Git 提交信息：`补充 DeepSeek 坏响应测试`

## 阶段二：Agent API 参数与身份边界反例测试

### 任务 4：补充 Agent API 请求体参数校验测试

任务目标：验证 `/api/agent/run` 对空 `user_input`、缺失 `user_input`、额外字段均返回 422。

已确定输入：非法 JSON 请求体。

已确定输出：HTTP 422，Provider 不被调用。

允许修改的文件范围：

* `backend/tests/test_agent_api.py`

禁止修改的范围：

* `backend/app/api/agent.py`
* Agent Runtime、ToolExecutor、ContextBuilder
* 数据库 Schema

验收标准：

* 至少覆盖空字符串、缺失字段、额外字段三类请求。
* 测试明确断言 Provider 调用次数为 0。

测试要求：

* `python -m pytest backend\tests\test_agent_api.py`

依赖关系：依赖本轮最小 Agent API 已实现。

建议的中文 Git 提交信息：`补充 Agent API 请求参数反例测试`

### 任务 5：补充 Agent API 认证头反例测试

任务目标：验证缺失 `X-LingoForge-User-Id`、非法用户 ID、非法 session ID 时 API 不进入 Runtime。

已确定输入：缺失或格式非法的请求头。

已确定输出：HTTP 422，Provider 不被调用。

允许修改的文件范围：

* `backend/tests/test_agent_api.py`

禁止修改的范围：

* `backend/app/api/agent.py`
* 身份绑定方式
* Agent Runtime、ToolExecutor、ContextBuilder

验收标准：

* 测试覆盖缺失用户头、非整数用户头、非整数 session 头。
* Provider 调用次数为 0。

测试要求：

* `python -m pytest backend\tests\test_agent_api.py`

依赖关系：依赖本轮最小 Agent API 已实现。

建议的中文 Git 提交信息：`补充 Agent API 身份头反例测试`

### 任务 6：补充 Agent API 未知工具摘要测试

任务目标：验证模型请求未知工具时，API 返回受控工具调用摘要，不暴露内部异常。

已确定输入：Fake Provider 首次返回未知工具调用，第二次返回最终文本。

已确定输出：HTTP 200，状态为 `COMPLETED_WITH_TOOL_ERRORS`，工具摘要包含 `TOOL_NOT_FOUND`。

允许修改的文件范围：

* `backend/tests/test_agent_api.py`

禁止修改的范围：

* `backend/app/api/agent.py`
* ToolExecutor
* Agent Runtime

验收标准：

* 断言响应体不包含 traceback、数据库路径或测试中的内部异常字符串。
* 断言 tool call log 写入失败状态。

测试要求：

* `python -m pytest backend\tests\test_agent_api.py`

依赖关系：依赖本轮最小 Agent API 已实现。

建议的中文 Git 提交信息：`补充 Agent API 未知工具摘要测试`

## 阶段三：测试夹具与本地脚本

### 任务 7：提取 Agent API 测试数据工厂

任务目标：把 `test_agent_api.py` 中重复创建用户、目标、画像、session 的代码提取为测试内局部 helper，降低后续 API 反例测试重复。

已确定输入：现有 `test_agent_api.py` 中的测试数据创建逻辑。

已确定输出：同文件内清晰的 helper，行为不变。

允许修改的文件范围：

* `backend/tests/test_agent_api.py`

禁止修改的范围：

* 生产代码
* 数据库 Schema
* Agent Runtime、ToolExecutor、ContextBuilder

验收标准：

* 只做测试代码去重，不改变测试语义。
* 相关测试全部通过。

测试要求：

* `python -m pytest backend\tests\test_agent_api.py`

依赖关系：建议在任务 4、5、6 之后执行。

建议的中文 Git 提交信息：`整理 Agent API 测试数据工厂`

### 任务 8：新增后端本地 smoke test 脚本

任务目标：新增一个只使用 Mock Provider 的后端 smoke test 脚本，用于初始化临时数据库并调用 `/health` 与 `/api/agent/run`。

已确定输入：本地 Python 环境、Mock LLM 模式、临时 SQLite 数据库。

已确定输出：脚本退出码 0 表示 smoke test 通过；失败时输出中文错误。

允许修改的文件范围：

* `scripts/smoke_backend.py`

禁止修改的范围：

* `backend/app/`
* 数据库 Schema
* 前端
* README

验收标准：

* 脚本不需要真实 DeepSeek API Key。
* 脚本不写入仓库内数据库文件。
* 脚本能够独立运行并调用两个接口。

测试要求：

* `python scripts\smoke_backend.py`

依赖关系：依赖本轮最小 Agent API 已实现。

建议的中文 Git 提交信息：`新增后端 Mock smoke test 脚本`

## 阶段四：机械文档同步

### 任务 9：补充 README 后端启动与 Agent API 调用说明

任务目标：在 README 中补充 Mock 模式启动、DeepSeek 环境变量、最小 Agent API curl 示例。

已确定输入：现有 README、已实现的 `/api/agent/run` 接口、环境变量名称。

已确定输出：中文 README 小节，说明不包含真实 API Key。

允许修改的文件范围：

* `README.md`

禁止修改的范围：

* 业务代码
* 数据库 Schema
* 架构规格
* 前端

验收标准：

* 示例默认使用 `LLM_MODE=mock`。
* DeepSeek 说明只列环境变量，不出现真实密钥。
* curl 示例通过请求头传递 `X-LingoForge-User-Id` 和可选 session。

测试要求：

* 人工检查 README 示例。
* 若已有 smoke 脚本，可运行 `python scripts\smoke_backend.py`。

依赖关系：依赖任务 8 或本轮最小 Agent API 已实现。

建议的中文 Git 提交信息：`补充后端启动与 Agent API 说明`
