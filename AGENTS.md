# LingoForge 项目协作规则

## 沟通语言

* 与用户交流时全部使用中文。
* 生成的产品、需求、架构和计划文档默认使用中文。
* 英文仅用于代码标识符、必要的技术术语和用户明确要求的内容。

## 当前项目阶段

当前处于课程作业版 MVP 的实现准备与代码实现阶段。

已通过人工审核的规格与架构文档是当前开发依据：

* `docs/MVP_SCOPE.md`
* `docs/USER_FLOW.md`
* `docs/AGENT_RESPONSIBILITIES.md`
* `docs/ACCEPTANCE_CRITERIA.md`
* `docs/ARCHITECTURE.md`
* `docs/DATA_MODEL.md`
* `docs/AGENT_RUNTIME.md`
* `docs/IMPLEMENTATION_PLAN.md`
* `docs/TASK_BREAKDOWN.md`

进入代码实现时仍必须遵守：

* 不擅自扩大 MVP 范围；
* 不引入微服务、消息队列、多 Agent 或复杂基础设施；
* 不绕过 Function Calling 工具和 Workflow 内部确定性服务边界；
* 不让 Agent 直接判分、直接写正式画像或访问隔离题正文；
* 不把副线信号直接作为正式能力画像证据；
* 不把模型自称“校验通过”当成真实质量校验结果。

当前最终核心交付物是 GitHub 仓库链接。仓库验收重点是能安装、能启动、能重置 Demo 数据、能运行测试、能走通完整主流程、核心 Prompt 和 Skill 可查看、架构与数据模型可查看、`.env.example` 完整、README 命令经过实际复跑，且不泄露 API 密钥。

首个真实模型 Provider 确认为 DeepSeek，模型为 `deepseek-v4-flash`，默认非思考模式；本地开发必须支持 `LLM_MODE=mock`。真实 DeepSeek 接入前必须通过 Provider Adapter 隔离供应商，并使用 `source-driven-development` 核对官方 API 文档。

## 开发智能体分工

Codex 是本项目的主开发者，负责完整项目的主要实现，而不是只负责架构或复杂后端。

Codex 负责：

* 总体架构与架构变更；
* 超详细实施规划与原子任务拆分；
* Agent Runtime；
* Function Calling 工具和编排循环；
* Workflow 状态控制；
* 数据模型、核心接口和复杂查询；
* 隔离题访问保护；
* 画像更新校验；
* 生成任务质量校验与兜底；
* 核心 Prompt 与教学 Skill；
* 所有复杂、高风险代码；
* 完整 Vue 前端的设计与实现；
* 前端 Image 2 视觉资产规划、生成、集成与验证；
* 前后端集成；
* 浏览器运行、测试和最终审查；
* 对 Claude Code、DeepSeek 或其他辅助执行结果进行审查和集成。

Claude Code + DeepSeek + agent-skills 只作为 Codex 规划下的辅助执行者。

它们只能完成边界明确、低风险、机械性的任务，例如：

* 简单 CRUD；
* SQLite 种子数据；
* 普通单元测试；
* README 和普通文档；
* 批量补类型、错误处理或注释；
* 简单 API 接线；
* Codex 已明确设计、接口和样式要求的局部小组件；
* 重复性代码和机械重构。

Claude Code、DeepSeek 或其他辅助执行者不得：

* 自行设计前端；
* 承担完整 Vue 页面；
* 自行调用 Image 2 决定视觉方向；
* 修改架构；
* 修改公共接口；
* 修改核心数据模型；
* 重写 Agent Runtime；
* 改变 Prompt 或 Skill 语义；
* 扩大 MVP 范围。

所有标记为 `CC_DS` 的任务必须由 Codex 预先明确文件范围、接口、输入输出、实现步骤、测试命令、验收标准和禁止修改范围。`CC_DS` 完成后，由 Codex 负责审查和集成。

## 前端与 Image 2 工作方式

前端由 Codex 完整负责。

Codex 在实现前端时，应按需自主调用 GPT Image 2，与代码实现配合完成 UI，而不是等待人工先生成设计稿，也不是把前端整体交给 Claude Code 或 DeepSeek。

前端工作流：

1. 阅读产品规格、用户流程和架构文档；
2. 确定页面信息架构和视觉方向；
3. 按需调用 GPT Image 2 生成页面视觉参考图、机场场景、虚拟角色、赛博背景、插画、纹理或其他复杂视觉资产；
4. 将生成资产保存到项目本地；
5. 将设计拆分为 Vue 组件和 CSS 布局；
6. 所有可读文字、按钮、表单、卡片、导航和交互必须使用 Vue 代码实现；
7. 不允许使用一张完整页面截图冒充前端；
8. 在浏览器中实际运行页面；
9. 对浏览器截图与参考设计进行对比；
10. 自主迭代布局、比例、间距、字体、资产裁切和响应式效果；
11. 完成 Vue 与 FastAPI 的真实接口接线。

如果当前 Codex 环境无法调用图像生成工具，必须明确报告，不得假装已调用或伪造资产；可以先输出待执行的图像生成任务，但不能宣称前端视觉已经完成。

项目专用 UI Skill：

* `.agents/skills/image2-ui-vue-web/SKILL.md`

实现 Vue Web 前端、GPT Image 2 辅助视觉、机场副线视觉资产、浏览器截图验证和多轮自主迭代时，应优先使用该 Skill。

## 工作原则

* 开始任务前先阅读本文件和相关项目文档。
* 按需使用 `.agents/skills` 中的Skill，不要机械调用全部Skill。
* 规格或架构变更优先使用 `spec-driven-development`、`documentation-and-adrs`、`api-and-interface-design` 和 `planning-and-task-breakdown`。
* 实现前端和视觉资产时按需使用 `image2-ui-vue-web`。
* 出现测试失败、浏览器问题或行为不符时按需使用 `debugging-and-error-recovery`、`test-driven-development`、`browser-testing-with-devtools`。
* 先分析已有需求，不要让用户从头重复介绍项目。
* 只有遇到会影响产品流程、Agent架构、数据模型或验收标准的关键歧义时，才向用户提问。
* 每次只问一个关键问题，并先给出推荐方案与理由。
* 不得擅自增加用户未要求的功能。
* 必须明确区分：

  * Agent自主决策；
  * Skill能力；
  * 固定Workflow；
  * 确定性程序。
* 重要结论必须写入项目文档，不能只保留在聊天记录中。
* 已通过人工审核的文档作为实现依据；当用户明确要求进入代码实现时，应按任务拆分继续完成实现、测试和汇报。

## MVP边界

当前MVP聚焦：

* CET-6词汇与阅读；
* 基于长期用户画像的自适应学习；
* 真题风格训练与确定性判分；
* 主线训练后的画像更新；
* 2D或2.5D赛博小镇副线；
* 一个机场购票任务。

当前暂不实现：

* 听力；
* 口语；
* 完整写作教学；
* 雅思、托福等其他考试；
* 真正3D开放世界；
* 多个完整虚拟场景；
* 复杂角色养成与经济系统；
* 视频生成和自动字幕；
* 社交与排行榜；
* 支付与商业订阅；
* 多Agent协作；
* Agentic RL。

详细产品需求以 `docs/PRODUCT_BRIEF.md` 及后续审核通过的规格文档为准。
