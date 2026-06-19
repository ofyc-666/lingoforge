# LingoForge MVP 总规格

## 1. 文档定位

本文档是 LingoForge 后续实现的正式总规格入口，面向 Codex、Claude Code、DeepSeek 和其他辅助执行者。后续自动构建、局部实现、审查和验收应先阅读本文，再按本文引用的文档进入细节。

本文档不包含实施任务列表，不替代后续按小型垂直切片生成的实时计划。

## 2. 文档优先级

当文档之间出现重复或冲突时，按以下优先级处理：

1. `AGENTS.md`
2. `docs/SPEC.md`
3. `docs/AGENT_ARCHITECTURE.md`
4. `docs/SPEC.md` 明确引用的其他文档

解释：

- `AGENTS.md` 是项目协作、范围纪律、执行者边界和安全约束的最高优先级规则。
- `docs/SPEC.md` 是 MVP 实现与验收的总入口。
- `docs/AGENT_ARCHITECTURE.md` 是 Agent 内部架构、Context、记忆、Function Calling 和审计的权威细节文档。
- 旧文档中的产品、流程、架构和数据模型仍然有效，但若与本文或 `docs/AGENT_ARCHITECTURE.md` 冲突，以优先级更高者为准。

### 2.1 被本文引用的规格文档

- `docs/MVP_SCOPE.md`：MVP 范围、做与不做。
- `docs/USER_FLOW.md`：完整用户闭环和阶段顺序。
- `docs/ACCEPTANCE_CRITERIA.md`：MVP 验收标准。
- `docs/AGENT_RESPONSIBILITIES.md`：Agent、Skill、Workflow、确定性程序职责边界。
- `docs/ARCHITECTURE.md`：Vue + FastAPI + SQLite + 单 Agent + 原生 Function Calling 的系统架构。
- `docs/DATA_MODEL.md`：SQLite 逻辑数据模型和数据边界。
- `docs/AGENT_ARCHITECTURE.md`：Agent Runtime、ContextBuilder、记忆系统、Context Expansion、时间序列分析工具、隔离防泄漏和审计链。
- `docs/AGENT_RUNTIME.md`：早期 Runtime 草案；若与 `docs/AGENT_ARCHITECTURE.md` 冲突，以 `docs/AGENT_ARCHITECTURE.md` 为准。
- `docs/IMPLEMENTATION_PLAN.md`、`docs/TASK_BREAKDOWN.md`：历史实施规划参考；后续 `/build auto` 不应机械照搬旧任务，应以本文和当前代码状态为准生成当次小范围实现计划。

## 3. MVP 目标

LingoForge 是面向 CET-6 词汇与阅读的自适应学习 Agent MVP。当前目标是证明一个最小、可运行、可审计的学习闭环：

**真题为源，Skill 为教学能力，Agent 负责调度，确定性程序负责判分，未见题负责验收。**

MVP 需要证明：

- 系统能收集用户目标并完成短诊断；
- 系统能形成基于 4 类能力维度的初始画像；
- Agent 能基于画像、证据、候选词和 Skill 调度第一次主线训练；
- 客观题判分由确定性程序完成；
- Agent 只能提出结构化画像更新建议，程序校验后才可应用；
- 机场副线只产生曝光和待验证信号，不直接更新正式画像；
- 第二次主线计划能基于更新画像和副线待验证信号发生有证据的自适应变化；
- 用户能完成至少一个体现变化的短训练任务；
- 用户能完成短隔离检测，隔离题与训练流程严格分离。

## 4. MVP 非目标

当前不实现：

- 听力；
- 口语；
- 完整写作教学；
- 雅思、托福等其他考试；
- 真正 3D 开放世界；
- 多个完整虚拟场景；
- 复杂角色养成与经济系统；
- 视频生成和自动字幕；
- 社交与排行榜；
- 支付与商业订阅；
- 多 Agent 协作；
- Agentic RL；
- 长期提分证明；
- 完整 CET-6 全题型覆盖；
- 生产级用户账号、权限和运维系统。

任何实现不得为了展示效果擅自扩大以上范围。

## 5. 当前已完成能力

截至本文档创建时，仓库已经具备：

- FastAPI 后端骨架；
- Vue 前端骨架；
- SQLite 初始化和核心 Schema；
- 数据库重置脚本；
- `.env.example`；
- 健康检查接口；
- 前端健康检查页面；
- LLMProvider 抽象；
- Mock LLM Provider；
- Provider 工厂；
- 基础后端测试；
- 产品范围、用户流程、验收、架构、数据模型、Agent 职责和 Agent 内部架构文档。

当前后端测试覆盖配置、健康检查、数据库初始化和 Mock Provider。完整业务闭环尚未实现。

## 6. 尚待实现能力

后续仍需实现：

- DeepSeek Provider；
- Function Calling 编排循环；
- Agent Runtime；
- ContextBuilder 和 Context Manifest；
- Context Expansion fast path / expansion path；
- 记忆系统和记忆 proposal 校验；
- `analyze_learning_history` 工具；
- 4 类 CET-6 阅读 Skill Registry；
- 核心 Prompt 与阶段 Prompt；
- LLM 可调用工具；
- Workflow 内部确定性服务；
- 生成任务质量校验、一次重试与种子兜底；
- Workflow 状态控制；
- 主线训练、画像建议和程序校验；
- 机场副线信号写入；
- 第二次自适应计划和短训练；
- 隔离检测读取、提交、判分和受控结果包；
- 完整 Vue 前端业务页面；
- 前后端端到端流程。

本节不是任务列表，只说明系统能力缺口。具体实现顺序应由后续小范围规划根据当前代码状态决定。

## 7. 完整用户闭环

MVP 用户闭环以 `docs/USER_FLOW.md` 为准，最小流程为：

1. 首次目标收集；
2. 短诊断；
3. 初始用户画像；
4. 第一次完整主线学习；
5. 第一次主线后的画像更新；
6. 机场购票副线任务；
7. 副线信号进入候选池或待验证标记；
8. 第二次自适应主线计划；
9. 至少一个体现自适应变化的短训练任务；
10. 短隔离检测；
11. 提交后展示受控结果解释和证据链。

第二次主线不要求再次完成完整学习闭环，但必须至少在 Skill 选择、目标能力、难度、题型或提示策略之一发生有证据的变化。仅改变文章主题不算自适应成立。

## 8. 系统架构

系统架构以 `docs/ARCHITECTURE.md` 和 `docs/AGENT_ARCHITECTURE.md` 为准。

当前架构方向：

- 前端：Vue；
- 后端：FastAPI；
- 数据：SQLite；
- Agent：单个学习 Agent；
- 工具连接：原生模型 Function Calling；
- 架构：前后端分离运行的模块化单体；
- 默认本地模式：Mock LLM；
- 首个真实 Provider：DeepSeek。

不得引入微服务、消息队列、多 Agent、复杂 RAG 平台、独立向量库或非必要基础设施。

## 9. 数据模型与数据边界

数据模型以 `docs/DATA_MODEL.md` 为准，并受 `docs/AGENT_ARCHITECTURE.md` 中记忆系统修订约束。

必须保持以下数据边界：

- 原始学习证据与派生画像分开保存；
- 原始客观证据只追加，不被画像或摘要覆盖；
- 画像更新建议与画像快照分开；
- 副线信号与正式学习证据分开；
- 隔离题集与训练生成流程隔离；
- 工具调用、内部服务调用、Agent 决策和质量校验结果可审计；
- 记忆系统优先承诺逻辑契约，不提前锁死复杂物理表拆分。

后续允许新增 `memory_items`，但暂不承诺独立 `memory_source_refs` 表。Context Manifest、AgentRun 和 Prompt 版本可根据现有日志表情况最小扩展，不默认新增多张表。

## 10. Agent、Skill、Workflow、确定性程序边界

边界以 `docs/AGENT_RESPONSIBILITIES.md` 和 `docs/AGENT_ARCHITECTURE.md` 为准。

### 10.1 Agent 可以自主决定

Agent 在程序约束内可以决定：

- 当前训练目标；
- 目标能力；
- 使用哪些 Skill；
- 难度；
- 题型；
- 新学与复习比例；
- 提示强度；
- 是否继续、降难、换策略或切换训练目标；
- 第二次计划与第一次计划之间的调整；
- 是否调用允许的 Function Calling 工具；
- 如何使用 `analyze_learning_history` 的分析结果调整教学策略；
- 是否提出画像更新建议或 memory proposal。

Agent 必须给出可追溯依据，不能只给泛化理由。

### 10.2 Skill 负责

Skill 负责：

- 教学方法；
- 错误分类框架；
- 内容生成原则；
- 策略建议；
- 输出约束；
- 示例和反例；
- 可观察证据要求；
- 质量校验要求。

Skill 不是独立 Agent，不访问数据库，不判分，不伪造历史分析结果。

### 10.3 Workflow 负责

Workflow 负责：

- 阶段顺序；
- 阶段转换条件；
- 数据权限边界；
- 业务硬约束；
- 固定内部确定性服务调用时机；
- 隔离检测阶段控制；
- Function Calling 工具 allowlist。

Workflow 不写死具体教学策略，例如“连续错两次必须降难”。

### 10.4 确定性程序负责

确定性程序负责：

- 数据库；
- 客观题判分；
- 输入校验；
- 工具执行；
- 原始证据记录；
- 权限；
- 数据隔离；
- 结果验证；
- 防伪造；
- Context 预算和截断；
- 画像更新建议校验；
- memory proposal 校验、去重和拒绝；
- 时间序列聚合和复习评分；
- 隔离题访问保护。

## 11. Agent 内部架构要求

Agent 内部架构以 `docs/AGENT_ARCHITECTURE.md` 为权威文档。

后续实现必须遵守：

- Runtime 支持 fast path，简单调用不能强制产生两次模型调用；
- Context Expansion 同时支持请求记忆、Skill 详情和历史分析；
- 模型不能自由指定用户身份或权限范围；
- Runtime 根据认证上下文向用户数据工具注入当前 `user_id`、session 和权限范围；
- `analyze_learning_history` 等用户数据工具必须强制绑定当前用户，并校验 Workflow Stage 和数据权限；
- 一次 AgentRun 内历史分析结果按规范化参数、用户、算法版本缓存和去重；
- Context Expansion 已预取的相同历史分析，后续 Function Calling 必须复用同一结果；
- Context Manifest 和审计记录引用同一个 analysis_result_id；
- Agent 不能直接覆盖或删除记忆；
- 解释性长期记忆由 Agent 提议、程序验证后写入；
- 原始证据由确定性程序直接记录；
- 默认不长期保存完整 Context 正文，只保存 Manifest、引用、版本和 hash。

## 12. Mock 与 DeepSeek 模式

### 12.1 Mock 模式

本地开发和测试默认使用：

```env
LLM_MODE=mock
LLM_PROVIDER=deepseek
```

Mock 模式必须：

- 不依赖真实 API；
- 可稳定复跑后端测试；
- 支持模拟普通模型响应；
- 支持模拟工具调用响应；
- 不访问真实网络；
- 不需要 API key。

### 12.2 DeepSeek 模式

首个真实模型 Provider 为：

- Provider：DeepSeek；
- 模型：`deepseek-v4-flash`；
- 默认非思考模式；
- 通过 Provider Adapter 隔离供应商差异。

推荐环境变量以 `.env.example` 为准：

```env
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_THINKING_ENABLED=false
```

真实 DeepSeek 接入前必须使用 `source-driven-development` 核对官方 API 文档。测试不得依赖真实 API，不得提交或打印真实 API key。

## 13. 隔离测试硬约束

隔离测试以 `docs/USER_FLOW.md`、`docs/ACCEPTANCE_CRITERIA.md` 和 `docs/AGENT_ARCHITECTURE.md` 为准。

硬约束：

- 隔离题来自预先保留的未见题集或合法样题风格保留题；
- 不能由 Agent 根据本轮用户表现临时生成后自证；
- 隔离题读取服务不是 LLM Function Calling 工具；
- 训练生成、补救练习、第二次计划阶段不能访问隔离题内容；
- 测试前和测试中，题目答案、解析、评分依据不得进入 Agent Context；
- 隔离测试进行中禁用 Context Expansion；
- 隔离测试进行中禁用记忆扩展；
- 隔离测试进行中禁用 `analyze_learning_history`；
- 测试期间不提供提示、分层讲解、答案反馈或动态降难度；
- 提交后只允许 Agent 使用受控结果包；
- 隔离题正文、标准答案和详细解析不得写入普通训练可复用记忆；
- 隔离检测结果可以作为较高置信度证据，但仍需程序校验后才能影响正式画像。

## 14. 前端与视觉边界

前端由 Codex 完整负责，后续实现 Vue Web 前端和视觉资产时应遵守 `AGENTS.md` 与项目专用 UI Skill。

MVP 前端应服务完整学习闭环和证据链展示：

- 目标与诊断；
- 初始画像；
- 主线训练；
- Agent 观察；
- 机场副线；
- 第二次计划；
- 短训练；
- 隔离检测；
- 总结和审计信息。

前端不负责判分、画像更新、隔离题访问控制、Agent 决策或工具执行。

不允许用一张整页截图冒充前端。所有可读文字、按钮、表单、卡片、导航和交互必须由 Vue 代码实现。

## 15. 系统级验收标准

最终仓库验收必须满足：

- 能安装；
- 能启动；
- 能重置 Demo 数据；
- 能运行测试；
- 能走通完整主流程；
- 核心 Prompt 和 Skill 可查看；
- 架构与数据模型可查看；
- `.env.example` 完整；
- README 命令经过实际复跑；
- 不泄露 API 密钥；
- 默认 Mock 模式可复跑；
- DeepSeek Provider 被 Provider Adapter 隔离；
- Agent 真实调用允许的 Function Calling 工具；
- 工具调用、内部服务调用和 Agent 决策可审计；
- 原始证据、派生画像、副线信号、记忆和隔离结果边界清晰；
- 画像更新由 Agent 提议、程序校验后应用；
- 生成任务质量校验不依赖模型自称；
- 第二次计划存在有证据的自适应变化；
- 隔离题不泄漏到训练 Context 或普通记忆；
- `analyze_learning_history` 返回可审计的算法版本、证据引用和确定性分析结果。

验收不通过示例：

- Agent 既生成题又自行判分；
- 副线信号直接修改正式画像；
- 第二次计划只换文章主题；
- 隔离题由 Agent 临时生成；
- 训练 Context 包含隔离题答案或解析；
- 没有保存原始证据；
- 记忆摘要不能追溯到原始证据；
- 工具或历史分析结果无法审计；
- 测试依赖真实 API；
- 提交真实 API key。

## 16. 命令与运行入口

当前 README 中的本地命令是实现和验收的起点，后续如命令变化必须更新 README 并实际复跑。

后端：

```powershell
python -m pip install -r backend\requirements.txt
python backend\scripts\reset_db.py
python -m uvicorn app.main:app --app-dir backend --reload
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

测试：

```powershell
python -m pytest backend\tests
```

前端构建命令：

```powershell
cd frontend
npm run build
```

## 17. 旧文档冲突处理

若旧文档之间出现重复或冲突，按以下规则处理：

- MVP 范围以 `docs/SPEC.md` 和 `docs/MVP_SCOPE.md` 为准；若冲突，以 `docs/SPEC.md` 为准。
- 用户流程以 `docs/USER_FLOW.md` 为准；若与旧实施计划冲突，以 `docs/USER_FLOW.md` 和本文为准。
- Agent 内部 Runtime、Context、记忆、历史分析和审计以 `docs/AGENT_ARCHITECTURE.md` 为准。
- 系统架构以 `docs/ARCHITECTURE.md` 为基础，但 Agent 内部细节以 `docs/AGENT_ARCHITECTURE.md` 为准。
- 数据模型以 `docs/DATA_MODEL.md` 为基础，但记忆系统物理实现不提前锁死，按 `docs/AGENT_ARCHITECTURE.md` 的逻辑契约处理。
- `docs/IMPLEMENTATION_PLAN.md` 和 `docs/TASK_BREAKDOWN.md` 是历史规划参考，不是后续自动构建必须照搬的任务清单。
- 若后续实现发现文档与代码现实冲突，应先更新规格或记录明确决策，再实现。

## 18. 后续执行规则

后续进入实现时：

- 不得跳过本文档和被引用文档；
- 不得扩大 MVP 范围；
- 不得引入本文明确排除的基础设施；
- 不得绕过 Function Calling 工具和 Workflow 内部确定性服务边界；
- 不得让 Agent 直接判分、直接写正式画像或访问隔离题正文；
- 不得把模型自称“校验通过”当成真实校验结果；
- 不得让辅助执行者修改架构、公共接口、核心数据模型、Prompt 或 Skill 语义；
- 每次实现应围绕小型垂直切片即时规划、实现、测试和审查。
