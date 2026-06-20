# LingoForge Image 2 UI 生图提示词

本文档为后续 GPT Image 2 生成 Vue Web 视觉参考图准备。所有提示词面向桌面端网页，不生成手机 App、小程序、电商风格或整页不可拆图片。生成图只作为视觉参考，最终文字、按钮、表单、卡片、交互和数据展示必须由 Vue 组件实现。

统一视觉语言：

- 产品类型：CET-6 英语学习 Agent MVP。
- 气质：现代、克制、清晰、可信，有英语学习产品感。
- 画布：桌面端 1440 x 1024。
- 字体：偏无衬线，中文与英文都清晰可读；参考 Inter、Noto Sans SC 的中性观感。
- 配色：浅色主界面，白色与冷灰为底，低饱和蓝绿作为主色，少量荧光青作为状态强调；避免紫色渐变、厚重深蓝、棕橙和电商促销感。
- 圆角：卡片 8px 左右，按钮 6px 左右。
- 间距：信息密度中等偏高，适合学习工作台；不要做夸张大字营销页。
- 组件拆分：所有区域都要方便拆成 Vue 组件，避免复杂不可分割装饰。

## 图 1：主学习工作台

直接用于 Image 2 的提示词：

```text
Create a desktop web UI design reference for "LingoForge", a modern CET-6 English learning agent workspace. Canvas 1440x1024, light theme, restrained professional learning product, not a mobile app, not a mini-program, not e-commerce.

Layout:
- Left vertical navigation rail, 72px wide, with simple icon slots for Workspace, Training, History, Profile, Sidequest.
- Top bar with product name "LingoForge", current mode "Mock / DeepSeek", session status, and a compact user badge.
- Main area split into two columns.
- Left column: large English text input panel with title "英文材料", a multiline editor, a primary button "分析并生成训练", and subtle loading / error / empty states.
- Right column: analysis result panel with original text preview and keyword highlights. Highlighted words should appear as pill markers inside the paragraph. Include hover popover mockups for Chinese meaning, short usage note, ability dimension, and selection reason.
- Bottom band: generated training task preview card with one multiple choice question, four options, progress indicator, and "开始训练" button.

Visual details:
- White and cool gray background, low saturation teal/blue accents, thin dividers, 8px card radius, compact readable typography.
- Use real UI components rather than decorative illustration.
- Include component boundaries that are easy to translate into Vue components.
- Text hierarchy should be clear: page title, section title, body, captions, status chips.
- Show states for loading, empty, success and error as small inline examples, not as separate screens.
```

设计拆分建议：

- `AppShell`
- `LearningWorkspace`
- `TextInputPanel`
- `KeywordHighlightText`
- `KeywordPopover`
- `TrainingPreviewCard`

## 图 2：训练答题页面

直接用于 Image 2 的提示词：

```text
Create a desktop web UI design reference for the LingoForge training page. Canvas 1440x1024, light theme, modern restrained English learning product. Do not create a phone app, mini-program, or e-commerce page.

Layout:
- Same left navigation rail and top bar as the main workspace.
- Center content: one focused training card, max width about 860px, with section title "词汇语境训练".
- Top of card: progress bar "1 / 5", target ability chip "VOCABULARY_CONTEXT", difficulty chip, and session status.
- Question area: English prompt with the target word visually emphasized, brief instruction text, and four multiple choice options A-D.
- Right side narrow panel: "本题观察点", showing expected observations, allowed hints, and a timer / elapsed time block.
- Bottom actions: secondary "保存进度" and primary "提交答案"; disabled, loading and error states should be visually represented.

Visual details:
- Clear answer option states: default, hover, selected, disabled, correct after submit, incorrect after submit.
- Use precise spacing and compact typography suitable for study.
- Avoid showing answer explanation before submit; use a locked explanation placeholder.
- Background should be calm white / gray, with teal-blue accent for selected state and green/red only for post-submit result.
- Components should be easy to recreate in Vue: nav, progress, question, option buttons, side info panel, footer actions.
```

设计拆分建议：

- `TrainingPage`
- `QuestionCard`
- `OptionButton`
- `TrainingProgress`
- `ObservationPanel`
- `SubmitBar`

## 图 3：训练结果与学习历史页面

直接用于 Image 2 的提示词：

```text
Create a desktop web UI design reference for LingoForge training result and learning history. Canvas 1440x1024, light theme, modern restrained data-rich learning dashboard, not e-commerce, not a mobile app.

Layout:
- Same left navigation rail and top bar.
- Main header: "训练结果与学习历史", with session selector and date range filter.
- Upper row: score summary cards for accuracy, correct count, evidence id, profile suggestion status. Cards should be compact, not oversized.
- Middle left: question result list showing each question, user's answer, standard answer after submit, correct/incorrect state, error type, and explanation.
- Middle right: learning history analysis panel with problem timeline fields: first observed, last observed, occurrence count, session count, last success, recent trend, confidence.
- Bottom: review priority panel showing priority score, review status, recommended window, estimated decay/risk level, and transparent factor breakdown.

Visual details:
- Use tables, chips, and compact cards; avoid nested card clutter.
- Evidence refs and algorithm version should appear as small audit metadata.
- Green/red result colors should be restrained and accessible.
- Include empty state "暂无提交记录" and error state examples.
- Make it easy to split into Vue components: score summary, result list, timeline panel, review priority panel.
```

设计拆分建议：

- `ResultHistoryPage`
- `ScoreSummary`
- `QuestionResultList`
- `ProblemTimelinePanel`
- `ReviewPriorityPanel`
- `EvidenceRefList`

## 图 4：画像、隔离测试和机场副线入口

直接用于 Image 2 的提示词：

```text
Create a desktop web UI design reference for the LingoForge profile and mission hub page. Canvas 1440x1024, light theme, modern restrained English learning product with a subtle cyber airport sidequest flavor. Not a mobile app, not a mini-program, not e-commerce.

Layout:
- Same left navigation rail and top bar.
- Left main column: user goal card showing target CET-6 score, daily minutes, weaknesses, interest topics, and editable goal controls.
- Center column: latest learner profile card with ability slices, confidence, profile source, and evidence references. Clearly separate "已确认画像" from "画像更新建议".
- Right column: two entry cards:
  1. "隔离测试" card with strict privacy/leakage note, start button, status chip, and result-only-after-submit hint.
  2. "机场副线" card with a restrained 2.5D cyber airport ticket counter thumbnail area, task status, and note that sidequest signals are not formal profile evidence.
- Bottom area: profile suggestion list with accept/review status placeholders, audit metadata, and empty state.

Visual details:
- Professional UI with small cyber accents only in the sidequest thumbnail; do not make the whole app a dark sci-fi game.
- Keep cards flat, 8px radius, clear spacing, readable Chinese labels.
- Use icon slots and status chips; avoid decorative blobs or purple gradients.
- Include loading, empty, success and error states as small inline variants.
- All elements must be easy to recreate as Vue components.
```

设计拆分建议：

- `ProfileMissionHub`
- `UserGoalCard`
- `LearnerProfileCard`
- `ProfileSuggestionList`
- `IsolatedTestEntryCard`
- `AirportSidequestEntryCard`

## 生成后验收要求

每张图生成后需要人工或 Codex 检查：

- 是否为 1440 x 1024 桌面网页。
- 是否保留统一导航和视觉语言。
- 是否能拆成 Vue 组件，而不是不可维护的整页插画。
- 是否避免手机、小程序、电商和营销页风格。
- 是否没有在隔离测试图中提前展示答案或解析。
- 是否没有把机场副线结果展示成正式画像证据。
