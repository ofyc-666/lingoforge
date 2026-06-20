<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTaskResult } from '../api/index.js'
import { ABILITY_LABEL, ERROR_TYPE_LABEL, TASK_TYPE_LABEL } from '../constants.js'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import EmptyState from '../components/EmptyState.vue'

const props = defineProps({
  taskId: { type: [String, Number], required: true },
})

const router = useRouter()

const loading = ref(true)
const error = ref('')
const result = ref(null)

onMounted(async () => {
  try {
    result.value = await getTaskResult(props.taskId)
  } catch (e) {
    error.value = e.message || '加载结果失败'
  } finally {
    loading.value = false
  }
})

function formatPercent(val) {
  if (val == null) return '-'
  return `${Math.round(val * 100)}%`
}

function goHome() {
  router.push('/')
}

function goTrainAgain() {
  router.push('/training')
}
</script>

<template>
  <div class="result-page">
    <h1 class="page-title">训练结果</h1>

    <LoadingState v-if="loading" message="正在加载训练结果..." />

    <ErrorState
      v-else-if="error"
      :message="error"
      @retry="() => { loading = true; error = ''; onMounted() }"
    />

    <template v-else-if="result">
      <!-- 得分概览 -->
      <section class="score-cards">
        <div class="score-card">
          <span class="score-value">{{ result.latest_submission?.score?.correct || 0 }} / {{ result.latest_submission?.score?.total || 0 }}</span>
          <span class="score-label">正确题数</span>
        </div>
        <div class="score-card">
          <span class="score-value">{{ formatPercent(result.latest_submission?.score?.accuracy) }}</span>
          <span class="score-label">正确率</span>
        </div>
        <div class="score-card" :class="result.latest_submission?.score?.passed ? 'passed' : 'failed'">
          <span class="score-value">{{ result.latest_submission?.score?.passed ? '通过 ✓' : '未通过' }}</span>
          <span class="score-label">结果</span>
        </div>
        <div class="score-card">
          <span class="score-value">{{ ABILITY_LABEL[result.task?.target_ability] || result.task?.target_ability || '-' }}</span>
          <span class="score-label">目标能力</span>
        </div>
      </section>

      <!-- 错题详情 -->
      <section class="card" style="margin-top: 20px;">
        <h2>📋 题目详情</h2>
        <div
          v-for="(qr, idx) in (result.latest_submission?.question_results || [])"
          :key="qr.question_id"
          class="question-result"
          :class="qr.is_correct ? 'correct' : 'incorrect'"
        >
          <div class="qr-header">
            <span class="qr-num">第 {{ idx + 1 }} 题</span>
            <span class="qr-status" :class="qr.is_correct ? 'ok' : 'fail'">
              {{ qr.is_correct ? '✓ 正确' : '✗ 错误' }}
            </span>
            <span class="qr-ability">
              {{ ABILITY_LABEL[qr.target_ability] || qr.target_ability }}
            </span>
          </div>
          <div class="qr-detail">
            <div class="qr-answer-row">
              <span class="qr-label">你的答案：</span>
              <span class="qr-answer" :class="qr.is_correct ? 'ok' : 'fail'">{{ qr.user_answer || '-' }}</span>
            </div>
            <div class="qr-answer-row">
              <span class="qr-label">正确答案：</span>
              <span class="qr-answer ok">{{ qr.standard_answer }}</span>
            </div>
            <div v-if="qr.error_type" class="qr-error-type">
              错误类型：{{ ERROR_TYPE_LABEL[qr.error_type] || qr.error_type }}
            </div>
          </div>
          <div v-if="qr.explanation" class="qr-explanation">
            <span class="explanation-label">解析：</span>{{ qr.explanation }}
          </div>
        </div>
      </section>

      <!-- Agent 反馈 -->
      <section class="card agent-feedback" style="margin-top: 20px;" v-if="result.task?.content?.agent_feedback">
        <h2>🤖 Agent 反馈</h2>
        <p>{{ result.task.content.agent_feedback }}</p>
      </section>

      <!-- 操作 -->
      <div class="result-actions">
        <button class="btn-secondary" @click="goHome">返回首页</button>
        <button class="btn-primary" @click="goTrainAgain">再练一次</button>
      </div>
    </template>

    <EmptyState
      v-else
      icon="📭"
      title="暂无训练结果"
      description="完成一次训练并提交后，结果将在这里显示。"
    />
  </div>
</template>

<style scoped>
.result-page {
  max-width: 860px;
}

.page-title {
  margin-bottom: 24px;
}

/* Score cards */
.score-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.score-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.score-card.passed {
  border-color: var(--color-success);
  background: var(--color-success-bg);
}

.score-card.failed {
  border-color: var(--color-error);
  background: var(--color-error-bg);
}

.score-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--color-text);
}

.score-label {
  font-size: 0.82rem;
  color: var(--color-text-muted);
}

/* Card */
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
}

/* Question result */
.question-result {
  padding: 16px;
  border-radius: var(--radius-md);
  margin-bottom: 12px;
}

.question-result.correct {
  background: var(--color-success-bg);
  border: 1px solid #B2F0E2;
}

.question-result.incorrect {
  background: var(--color-error-bg);
  border: 1px solid #FECACA;
}

.qr-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.qr-num {
  font-weight: 600;
}

.qr-status {
  font-size: 0.85rem;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 10px;
}

.qr-status.ok {
  background: #B2F0E2;
  color: #1B7A5C;
}

.qr-status.fail {
  background: #FECACA;
  color: #A13A3A;
}

.qr-ability {
  font-size: 0.78rem;
  color: var(--color-text-muted);
}

.qr-detail {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 0.9rem;
}

.qr-answer-row {
  display: flex;
  gap: 8px;
}

.qr-label {
  color: var(--color-text-muted);
}

.qr-answer {
  font-weight: 700;
}

.qr-answer.ok { color: #1B7A5C; }
.qr-answer.fail { color: #A13A3A; }

.qr-error-type {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.qr-explanation {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--color-border);
  font-size: 0.88rem;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.explanation-label {
  font-weight: 600;
  color: var(--color-text);
}

/* Agent feedback */
.agent-feedback p {
  font-size: 0.93rem;
  line-height: 1.8;
  color: var(--color-text-secondary);
  padding: 14px;
  background: var(--color-bg);
  border-radius: var(--radius-md);
}

/* Actions */
.result-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
  justify-content: center;
}

.btn-primary {
  padding: 10px 28px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-btn);
  font-weight: 600;
  font-size: 0.93rem;
  transition: background 0.15s;
}

.btn-primary:hover {
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

@media (max-width: 768px) {
  .score-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
