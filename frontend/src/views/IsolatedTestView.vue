<script setup>
import { ref } from 'vue'
import { startIsolatedTest, submitIsolatedTest } from '../api/index.js'
import { ABILITY_LABEL } from '../constants.js'
import QuestionCard from '../components/QuestionCard.vue'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import StatusMessage from '../components/StatusMessage.vue'

const step = ref('setup') // setup | testing | submitting | done
const loading = ref(false)
const error = ref('')
const errorCode = ref('')

// 设置
const targetAbility = ref('VOCABULARY_CONTEXT')
const questionLimit = ref(3)

// 测试数据
const attemptId = ref(null)
const testItems = ref([])
const answers = ref({})
const timeStart = ref(0)
const submitting = ref(false)

// 结果
const testResult = ref(null)

const abilityOptions = Object.entries(ABILITY_LABEL).map(([value, label]) => ({ value, label }))

async function handleStart() {
  loading.value = true
  error.value = ''
  try {
    const data = await startIsolatedTest({
      target_ability: targetAbility.value,
      limit: questionLimit.value,
    })
    attemptId.value = data.attempt_id
    // 将 sanitized items 转为题目格式
    testItems.value = (data.items || []).map((item) => ({
      question_id: `item_${item.item_id}`,
      item_id: item.item_id,
      prompt: item.prompt,
      options: (item.options || []).map((o) => ({
        id: o.id || o.label,
        text: o.text,
      })),
      target_ability: item.target_ability,
    }))
    answers.value = {}
    timeStart.value = Date.now()
    step.value = 'testing'
  } catch (e) {
    error.value = e.message || '启动检测失败'
    errorCode.value = e.code || ''
  } finally {
    loading.value = false
  }
}

function selectAnswer(questionId, optionId) {
  answers.value = { ...answers.value, [questionId]: optionId }
}

const allAnswered = () => {
  return testItems.value.every((item) => answers.value[item.question_id])
}

async function handleSubmit() {
  if (!allAnswered() || submitting.value) return
  submitting.value = true
  const timeSpent = Math.round((Date.now() - timeStart.value) / 1000)

  try {
    const answerList = testItems.value.map((item) => ({
      item_id: item.item_id,
      answer: answers.value[item.question_id],
    }))

    const result = await submitIsolatedTest(attemptId.value, {
      answers: answerList,
      time_spent_seconds: timeSpent,
    })

    testResult.value = result
    step.value = 'done'
  } catch (e) {
    error.value = e.message || '提交检测失败'
    errorCode.value = e.code || ''
  } finally {
    submitting.value = false
  }
}

function handleReset() {
  step.value = 'setup'
  error.value = ''
  errorCode.value = ''
  attemptId.value = null
  testItems.value = []
  answers.value = {}
  testResult.value = null
}

function formatPercent(val) {
  if (val == null) return '-'
  return `${Math.round(val * 100)}%`
}
</script>

<template>
  <div class="isolated-page">
    <h1 class="page-title">🔒 阶段检测</h1>

    <StatusMessage
      type="info"
      message="阶段检测使用预先保留的隔离题目，独立于日常训练。检测期间不提供提示和解析。结果经程序校验后作为独立评估依据。"
      style="margin-bottom: 20px;"
    />

    <!-- 设置阶段 -->
    <template v-if="step === 'setup'">
      <section class="card">
        <h2>检测设置</h2>
        <div class="setup-form">
          <label class="form-label">
            目标能力
            <select v-model="targetAbility" class="form-input">
              <option v-for="ab in abilityOptions" :key="ab.value" :value="ab.value">
                {{ ab.label }}
              </option>
            </select>
          </label>
          <label class="form-label">
            题目数量
            <select v-model.number="questionLimit" class="form-input">
              <option :value="1">1 题</option>
              <option :value="2">2 题</option>
              <option :value="3">3 题</option>
              <option :value="5">5 题</option>
            </select>
          </label>
          <button
            class="btn-primary"
            :disabled="loading"
            @click="handleStart"
          >
            {{ loading ? '加载题目...' : '开始检测' }}
          </button>
        </div>
      </section>
    </template>

    <!-- 加载 -->
    <LoadingState v-if="loading" message="正在加载隔离测试题..." />

    <!-- 答题阶段 -->
    <template v-if="step === 'testing'">
      <div class="test-header">
        <span class="test-badge">🔒 隔离检测进行中</span>
        <span class="test-info">{{ testItems.length }} 道题 · {{ ABILITY_LABEL[targetAbility] }}</span>
      </div>

      <QuestionCard
        v-for="(item, idx) in testItems"
        :key="item.question_id"
        :question="item"
        :selectedAnswer="answers[item.question_id] || ''"
        :disabled="submitting"
        :questionIndex="idx"
        :totalQuestions="testItems.length"
        @select="(optId) => selectAnswer(item.question_id, optId)"
        style="margin-bottom: 20px;"
      />

      <div class="submit-bar">
        <span v-if="!allAnswered()" class="hint">请完成所有题目后提交</span>
        <span v-else class="hint ready">已全部作答，可以提交</span>
        <button
          class="btn-primary"
          :disabled="!allAnswered() || submitting"
          @click="handleSubmit"
        >
          {{ submitting ? '提交中...' : '提交检测' }}
        </button>
      </div>
    </template>

    <!-- 结果阶段 -->
    <template v-if="step === 'done' && testResult">
      <section class="card result-card">
        <h2>📊 检测结果</h2>

        <div class="score-summary">
          <div class="score-item">
            <span class="score-num">{{ testResult.score?.correct || 0 }} / {{ testResult.score?.total || 0 }}</span>
            <span class="score-label">正确题数</span>
          </div>
          <div class="score-item">
            <span class="score-num">{{ formatPercent(testResult.score?.accuracy) }}</span>
            <span class="score-label">正确率</span>
          </div>
        </div>

        <div class="item-results">
          <div
            v-for="ir in (testResult.item_results || [])"
            :key="ir.item_id"
            class="item-result-row"
            :class="ir.is_correct ? 'correct' : 'incorrect'"
          >
            <span class="ir-id">题 #{{ ir.item_id }}</span>
            <span class="ir-ability">{{ ABILITY_LABEL[ir.target_ability] || ir.target_ability }}</span>
            <span class="ir-status">{{ ir.is_correct ? '✓ 正确' : '✗ 错误' }}</span>
          </div>
        </div>

        <div v-if="testResult.safe_explanation" class="safe-explanation">
          <h3>结果说明</h3>
          <p>{{ testResult.safe_explanation }}</p>
        </div>

        <StatusMessage
          type="info"
          message="此为受控结果包。隔离检测的具体答案和详细解析不会进入日常训练的 Agent Context。"
          style="margin-top: 16px;"
        />

        <div style="margin-top: 20px;">
          <button class="btn-secondary" @click="handleReset">再次检测</button>
        </div>
      </section>
    </template>

    <ErrorState
      v-if="error"
      :message="error"
      :code="errorCode"
      @retry="handleReset"
    />
  </div>
</template>

<style scoped>
.isolated-page {
  max-width: 860px;
}

.page-title {
  margin-bottom: 24px;
}

.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 28px;
}

.setup-form {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 12px;
}

.form-label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.form-input {
  padding: 8px 12px;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 0.93rem;
  font-family: inherit;
  background: var(--color-bg);
  color: var(--color-text);
  min-width: 160px;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

/* Test header */
.test-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding: 12px 18px;
  background: var(--color-warning-bg);
  border: 1px solid #FDE68A;
  border-radius: var(--radius-md);
}

.test-badge {
  font-weight: 600;
  font-size: 0.9rem;
}

.test-info {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
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

.hint {
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

.hint.ready {
  color: var(--color-success);
}

/* Result */
.result-card {
  margin-top: 20px;
}

.score-summary {
  display: flex;
  gap: 24px;
  margin: 16px 0;
}

.score-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.score-num {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text);
}

.score-label {
  font-size: 0.82rem;
  color: var(--color-text-muted);
}

.item-results {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 16px 0;
}

.item-result-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
}

.item-result-row.correct {
  background: var(--color-success-bg);
}

.item-result-row.incorrect {
  background: var(--color-error-bg);
}

.ir-id {
  font-weight: 600;
}

.ir-ability {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  flex: 1;
}

.ir-status {
  font-weight: 600;
  font-size: 0.9rem;
}

.correct .ir-status { color: #1B7A5C; }
.incorrect .ir-status { color: #A13A3A; }

.safe-explanation {
  margin-top: 16px;
  padding: 14px;
  background: var(--color-bg);
  border-radius: var(--radius-md);
}

.safe-explanation h3 {
  font-size: 0.95rem;
  margin-bottom: 8px;
}

.safe-explanation p {
  font-size: 0.9rem;
  line-height: 1.7;
  color: var(--color-text-secondary);
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

.btn-secondary {
  padding: 10px 28px;
  background: var(--color-bg);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-btn);
  font-weight: 500;
  font-size: 0.93rem;
  transition: all 0.15s;
}

.btn-secondary:hover {
  border-color: var(--color-primary-light);
  background: var(--color-primary-bg);
}
</style>
