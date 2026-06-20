<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  createTrainingSession,
  analyzeTextAndCreateTask,
  runAgentWorkflow,
  submitTrainingTask,
  setSessionId,
  getSessionId,
} from '../api/index.js'
import { ABILITY_LABEL, TASK_TYPE_LABEL } from '../constants.js'
import QuestionCard from '../components/QuestionCard.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import StatusMessage from '../components/StatusMessage.vue'

const router = useRouter()

// 默认 CET-6 Demo 材料
const DEMO_TEXT = `Climate change is one of the most pressing challenges facing humanity today. Rising global temperatures have led to more frequent extreme weather events, including devastating floods, prolonged droughts, and intense hurricanes. Scientists have consistently warned that without immediate and substantial reductions in greenhouse gas emissions, the consequences will become increasingly severe. Many governments have pledged to achieve carbon neutrality by mid-century, but the transition to renewable energy sources requires substantial investment and international cooperation. Meanwhile, individual actions such as reducing energy consumption, adopting sustainable transportation, and supporting environmentally responsible businesses can collectively make a significant difference. The challenge is not merely technological or economic — it is fundamentally a test of human will and our capacity for global collaboration.`

// ---- 状态 ----
const step = ref('input') // input | answering | submitting | done
const loading = ref(false)
const error = ref('')
const errorCode = ref('')

// 输入
const rawText = ref(DEMO_TEXT)
const targetAbilities = ref(['VOCABULARY_CONTEXT'])
const useAgentWorkflow = ref(true)

// 会话与任务
const sessionId = ref(null)
const taskId = ref(null)
const taskContent = ref(null)
const analysis = ref(null)
const agentFeedback = ref('')

// 答题
const answers = ref({})
const timeStart = ref(0)
const submitting = ref(false)

// 结果
const submitResult = ref(null)

// ---- 计算属性 ----
const questions = computed(() => {
  if (!taskContent.value) return []
  const content = taskContent.value
  const qs = content.questions || content.exercise ? [content.exercise] : []
  return qs.filter(Boolean)
})

const hasSelection = computed(() => {
  return questions.value.every((q) => answers.value[q.question_id])
})

const abilityOptions = Object.entries(ABILITY_LABEL).map(([value, label]) => ({ value, label }))

// ---- 方法 ----
async function handleStartTraining() {
  if (!rawText.value.trim()) return

  loading.value = true
  error.value = ''
  step.value = 'input'

  try {
    // 创建训练会话
    const session = await createTrainingSession('FIRST_MAIN')
    sessionId.value = session.session_id
    setSessionId(session.session_id)

    let result
    if (useAgentWorkflow.value) {
      // 使用 Agent Workflow
      result = await runAgentWorkflow({
        raw_text: rawText.value.trim(),
        target_abilities: targetAbilities.value,
        max_keywords: 5,
        generate_exercise: true,
      })
      analysis.value = result.analysis || {}
      taskId.value = result.task_id
      taskContent.value = result.task || {}
      agentFeedback.value = result.agent_run?.final_answer || ''
    } else {
      // 使用简单分析 + 创建任务
      result = await analyzeTextAndCreateTask({
        raw_text: rawText.value.trim(),
        target_abilities: targetAbilities.value,
        max_keywords: 5,
        generate_exercise: true,
      })
      analysis.value = result.analysis || {}
      taskId.value = result.task_id
      // 拉取任务详情获取题目
      const { getTaskDetail } = await import('../api/index.js')
      const task = await getTaskDetail(result.task_id)
      taskContent.value = task.content || {}
    }

    // 初始化答题
    answers.value = {}
    timeStart.value = Date.now()

    if (questions.value.length > 0) {
      step.value = 'answering'
    } else if (taskId.value) {
      // 有关键词分析但无题目
      step.value = 'done'
    }
  } catch (e) {
    error.value = e.message || '训练创建失败'
    errorCode.value = e.code || ''
  } finally {
    loading.value = false
  }
}

function selectAnswer(questionId, optionId) {
  answers.value = { ...answers.value, [questionId]: optionId }
}

async function handleSubmit() {
  if (!hasSelection.value || submitting.value) return

  submitting.value = true
  const timeSpent = Math.round((Date.now() - timeStart.value) / 1000)

  try {
    const answerList = questions.value.map((q) => ({
      question_id: q.question_id,
      answer: answers.value[q.question_id],
    }))

    const result = await submitTrainingTask(taskId.value, {
      answers: answerList,
      time_spent_seconds: timeSpent,
    })

    submitResult.value = result
    step.value = 'done'

    // 跳转到结果页
    router.push({
      name: 'training-result',
      params: { taskId: taskId.value },
    })
  } catch (e) {
    error.value = e.message || '提交失败'
    errorCode.value = e.code || ''
  } finally {
    submitting.value = false
  }
}

function handleReset() {
  step.value = 'input'
  error.value = ''
  errorCode.value = ''
  taskId.value = null
  taskContent.value = null
  analysis.value = null
  submitResult.value = null
  answers.value = {}
  sessionId.value = null
  setSessionId(null)
}

function toggleAbility(ability) {
  const idx = targetAbilities.value.indexOf(ability)
  if (idx >= 0) {
    targetAbilities.value = targetAbilities.value.filter((a) => a !== ability)
  } else {
    targetAbilities.value = [...targetAbilities.value, ability]
  }
}
</script>

<template>
  <div class="training-page">
    <h1 class="page-title">开始训练</h1>

    <!-- 输入阶段 -->
    <template v-if="step === 'input'">
      <section class="card">
        <h2>📖 英文材料</h2>
        <p class="section-desc">
          输入一段 CET-6 难度的英文材料，Agent 将分析关键词并生成训练题目。
        </p>

        <textarea
          v-model="rawText"
          class="text-input"
          rows="10"
          placeholder="在此输入或粘贴英文材料..."
        ></textarea>

        <div class="options-row">
          <div class="ability-select">
            <span class="options-label">目标能力：</span>
            <button
              v-for="ab in abilityOptions"
              :key="ab.value"
              class="chip"
              :class="{ active: targetAbilities.includes(ab.value) }"
              @click="toggleAbility(ab.value)"
              type="button"
            >
              {{ ab.label }}
            </button>
          </div>

          <label class="toggle-label">
            <input type="checkbox" v-model="useAgentWorkflow" />
            <span>使用 Agent Workflow（含 Agent 决策与反馈）</span>
          </label>
        </div>

        <div class="input-actions">
          <button
            class="btn-primary"
            :disabled="!rawText.trim() || loading"
            @click="handleStartTraining"
          >
            {{ loading ? '分析中...' : '分析并生成训练' }}
          </button>
        </div>

        <StatusMessage
          v-if="error"
          type="error"
          :message="error"
          style="margin-top: 16px;"
        />
      </section>
    </template>

    <!-- 加载 -->
    <LoadingState v-if="loading && step !== 'input'" message="Agent 正在分析材料并生成训练任务..." />

    <!-- 答题阶段 -->
    <template v-if="step === 'answering' && questions.length > 0">
      <div class="answer-area">
        <div class="task-info">
          <span class="task-chip" v-if="taskContent.value?.task_type">
            {{ TASK_TYPE_LABEL[taskContent.value.task_type] || taskContent.value.task_type }}
          </span>
          <span class="task-chip" v-if="taskContent.value?.target_ability">
            {{ ABILITY_LABEL[taskContent.value.target_ability] || taskContent.value.target_ability }}
          </span>
        </div>

        <QuestionCard
          v-for="(q, idx) in questions"
          :key="q.question_id"
          :question="q"
          :selectedAnswer="answers[q.question_id] || ''"
          :disabled="submitting"
          :questionIndex="idx"
          :totalQuestions="questions.length"
          @select="(optId) => selectAnswer(q.question_id, optId)"
          style="margin-bottom: 20px;"
        />

        <!-- 关键词分析面板 -->
        <section class="card" v-if="analysis.value?.keywords?.length > 0" style="margin-bottom: 20px;">
          <h3>🔑 关键词分析</h3>
          <div class="keyword-list">
            <div v-for="kw in analysis.value.keywords" :key="kw.text" class="keyword-item">
              <span class="kw-word">{{ kw.text }}</span>
              <span class="kw-meaning">{{ kw.meaning_zh }}</span>
              <span class="kw-note" v-if="kw.usage_note">{{ kw.usage_note }}</span>
            </div>
          </div>
        </section>

        <div class="submit-bar">
          <div class="submit-info">
            <span v-if="!hasSelection">请完成所有题目后提交</span>
            <span v-else>已全部作答，可以提交</span>
          </div>
          <button
            class="btn-primary"
            :disabled="!hasSelection || submitting"
            @click="handleSubmit"
          >
            {{ submitting ? '提交中...' : '提交答案' }}
          </button>
        </div>
      </div>
    </template>

    <!-- Agent 反馈（仅有分析无题目时） -->
    <template v-if="step === 'done' && !submitResult && agentFeedback">
      <section class="card">
        <h3>🤖 Agent 反馈</h3>
        <p class="feedback-text">{{ agentFeedback }}</p>
        <div style="margin-top: 16px;">
          <button class="btn-primary" @click="handleReset">重新训练</button>
        </div>
      </section>
    </template>

    <!-- 错误 -->
    <ErrorState
      v-if="error && step !== 'input'"
      :message="error"
      :code="errorCode"
      @retry="handleReset"
    />
  </div>
</template>

<style scoped>
.training-page {
  max-width: 860px;
}

.page-title {
  margin-bottom: 24px;
}

.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.section-desc {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  margin: 8px 0 16px;
}

.text-input {
  width: 100%;
  padding: 16px;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  font-family: var(--font-sans);
  font-size: 0.93rem;
  line-height: 1.7;
  resize: vertical;
  background: var(--color-bg);
  color: var(--color-text);
  transition: border-color 0.15s;
}

.text-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.options-row {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.options-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-right: 8px;
}

.ability-select {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  padding: 5px 14px;
  border-radius: 20px;
  font-size: 0.82rem;
  font-weight: 500;
  background: var(--color-bg);
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
  transition: all 0.15s;
}

.chip:hover {
  border-color: var(--color-primary-light);
}

.chip.active {
  background: var(--color-primary-bg);
  color: var(--color-primary);
  border-color: var(--color-primary);
  font-weight: 600;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  cursor: pointer;
}

.input-actions {
  margin-top: 20px;
}

/* Answer area */
.answer-area {
  /* full width within training-page */
}

.task-info {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.task-chip {
  font-size: 0.82rem;
  font-weight: 600;
  padding: 4px 14px;
  border-radius: 20px;
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

/* Keywords */
.keyword-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.keyword-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: var(--color-bg);
  border-radius: var(--radius-sm);
}

.kw-word {
  font-weight: 700;
  color: var(--color-primary);
  min-width: 100px;
}

.kw-meaning {
  color: var(--color-text);
  font-weight: 500;
}

.kw-note {
  font-size: 0.82rem;
  color: var(--color-text-muted);
}

/* Submit bar */
.submit-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.submit-info {
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

/* Buttons */
.btn-primary {
  padding: 10px 28px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-btn);
  font-weight: 600;
  font-size: 0.93rem;
  transition: background 0.15s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.feedback-text {
  font-size: 0.93rem;
  line-height: 1.8;
  color: var(--color-text-secondary);
  padding: 14px;
  background: var(--color-bg);
  border-radius: var(--radius-md);
}
</style>
