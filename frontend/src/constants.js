/**
 * 前端常量与后端枚举的中文映射。
 * 禁止在用户界面展示原始后端枚举值。
 */

// ---- 用户默认值 ----
export const DEMO_USER_ID = 1

// ---- 能力维度映射 ----
export const ABILITY_LABEL = {
  VOCABULARY_CONTEXT: '词汇语境',
  SENTENCE_LOGIC: '长难句逻辑',
  PARAPHRASE_LOCATION: '同义替换与定位',
  DISTRACTOR_JUDGEMENT: '干扰项判断',
}

export const ABILITY_LIST = Object.keys(ABILITY_LABEL)

// ---- 错误类型映射 ----
export const ERROR_TYPE_LABEL = {
  VOCABULARY_MISMATCH: '词义理解偏差',
  LOGIC_MISREAD: '逻辑关系误判',
  PARAPHRASE_MISS: '未识别同义替换',
  DISTRACTOR_FALL: '受干扰项误导',
  UNKNOWN: '其他错误',
}

// ---- 训练任务类型映射 ----
export const TASK_TYPE_LABEL = {
  LOW_PRESSURE_LEARNING: '低压力阅读',
  TRANSFER_PRACTICE: '真题风格训练',
  REMEDIATION: '补救练习',
  SHORT_TRAINING: '短训练',
  VOCABULARY_LEARNING: '词汇学习',
  VOCABULARY_REVIEW: '词汇复习',
}

// ---- Workflow 阶段映射 ----
export const STAGE_LABEL = {
  DIAGNOSTIC: '诊断',
  FIRST_MAIN: '第一次主线',
  SIDEQUEST: '副线任务',
  SECOND_PLAN: '第二次计划',
  SHORT_TRAINING: '短训练',
  ISOLATED_TEST: '阶段检测',
}
