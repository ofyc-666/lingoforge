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
  TARGETED_PRACTICE: '针对性训练',
  COMPREHENSIVE_SIMULATION: '综合模拟',
}

// ---- Workflow 阶段映射 ----
export const STAGE_LABEL = {
  DIAGNOSTIC: '诊断',
  FIRST_MAIN: '第一次主线',
  SIDEQUEST: '副线任务',
  SECOND_PLAN: '第二次计划',
  SHORT_TRAINING: '短训练',
  ISOLATED_TEST: '阶段检测',
  DAILY_PLAN: '每日计划',
}

// ---- 练习模式映射 ----
export const PRACTICE_MODE_LABEL = {
  TARGETED_PRACTICE: '针对性训练',
  COMPREHENSIVE_SIMULATION: '综合模拟',
}

// ---- 计划状态映射 ----
export const PLAN_STATUS_LABEL = {
  PLANNED: '已规划',
  VOCABULARY_IN_PROGRESS: '背词中',
  VOCABULARY_COMPLETED: '背词完成',
  PRACTICE_IN_PROGRESS: '刷题中',
  COMPLETED: '已完成',
}

// ---- 词汇学习状态 ----
export const LEARNING_STATUS_LABEL = {
  NEW: '新词',
  LEARNING: '学习中',
  REVIEWING: '复习中',
  MASTERED: '已掌握',
  WEAK: '薄弱',
}

// ---- 自评结果 ----
export const SELF_RATING_LABEL = {
  KNOWN: '认识',
  FUZZY: '模糊',
  UNKNOWN: '不认识',
}
