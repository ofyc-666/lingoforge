# LingoForge Image 2 UI 生图提示词

本文档用于保留前端视觉方向和后续 Image 2 资产生成提示词。当前 MVP 的文字、按钮、表单、卡片、导航、正文高亮和交互必须由 Vue 代码实现，不允许用整页截图冒充前端。

## 统一视觉语言

- 产品类型：CET-6 词汇与阅读学习 MVP。
- 页面形态：桌面端 Web，优先适配 1440 x 900 及以上。
- 气质：清晰、克制、可信，有学习工作台感。
- 字体：参考 Inter / Noto Sans SC。
- 组件：侧边导航、顶部栏、内容面板、状态提示、词汇卡片、阅读正文区均应可拆成 Vue 组件。
- 边界：不要做手机 App、小程序、电商页、整页插画或不可拆的大图 UI。

## 阅读导入与词汇本页面

用于后续生成视觉参考图时的提示词：

```text
Create a desktop web UI design reference for LingoForge's reader import and vocabulary notebook page. Canvas 1440x900, light theme, professional CET-6 learning workspace, not a mobile app, not e-commerce.

Layout:
- Use the existing left sidebar and top navigation style.
- Main page title: "阅读导入与词汇本".
- Three-column workspace:
  1. Left import panel with tabs/buttons for "英文文本" and "英文 PDF", a text area, a PDF file picker, and a primary action "解析并生成重点词汇".
  2. Center reading panel showing parsed English body text. Important vocabulary should be highlighted inline. Hover/focus tooltip should show word, Chinese meaning and usage note.
  3. Right side column with "重点词汇" cards and "我的词汇本" list. Each keyword card has an "加入词汇本" action. The page header has "导出词汇表 CSV".

Visual details:
- Keep information dense but readable.
- Highlight color should be warm and accessible, not neon.
- Use compact white cards, subtle borders, and clear loading/error/success states.
- Do not show highlighter as a static screenshot; all text and highlights must be real DOM text.
- Do not claim highlighted PDF export exists. Only CSV vocabulary export is shown.
```

验收要点：

- 英文文本导入后正文能显示；
- 英文 PDF 导入后可复制正文能被解析并显示；
- 重点词汇在正文内高亮；
- 鼠标悬停或键盘聚焦高亮词时能看到释义；
- 词汇能加入个人词汇本并再次查看；
- 词汇表能导出 CSV；
- 不展示或暗示当前已支持“高亮 PDF 文件导出”。

## 主训练页面

用于后续生成视觉参考图时的提示词：

```text
Create a desktop web UI design reference for the LingoForge CET-6 training page. Canvas 1440x900, light theme, restrained English learning product.

Layout:
- Existing sidebar and top bar.
- Center training card with progress, target ability chip, question prompt and four options.
- Keyword analysis panel below or beside the question.
- Submit bar with disabled/loading states.

Visual details:
- Answer option states must be clear: default, selected, disabled, correct and incorrect after submit.
- Do not show answers before submit.
- Use compact spacing and readable typography.
```

## 画像、隔离测试和机场副线入口

用于后续生成视觉参考图时的提示词：

```text
Create a desktop web UI design reference for LingoForge's profile and mission hub. Canvas 1440x900, light theme, modern learning dashboard.

Layout:
- Existing sidebar and top bar.
- User goal card.
- Latest learner profile card.
- Profile suggestion list.
- Entry cards for isolated test and airport sidequest.

Visual details:
- Clearly separate confirmed profile from profile update suggestions.
- State that sidequest signals are pending verification and are not formal profile evidence.
- Do not show isolated test answers before submit.
```
