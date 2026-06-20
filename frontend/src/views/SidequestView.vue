<script setup>
import { ref } from 'vue'
import { completeAirportTicket } from '../api/index.js'
import LoadingState from '../components/LoadingState.vue'
import StatusMessage from '../components/StatusMessage.vue'

const loading = ref(false)
const submitted = ref(false)
const result = ref(null)
const error = ref('')

const selectedExpression = ref('')
const expressions = [
  {
    id: 'A',
    text: 'I\'d like to book a flight to London.',
    label: '预订航班',
  },
  {
    id: 'B',
    text: 'Can I have a window seat, please?',
    label: '选座请求',
  },
  {
    id: 'C',
    text: 'What time does the flight depart?',
    label: '询问时间',
  },
]

// 机场场景信息
const sceneInfo = {
  scene: 'AIRPORT_TICKET',
  npc: 'Ticket Agent',
  location: '北京首都国际机场 · 国际出发',
  taskDescription: '你正在机场柜台办理国际航班购票。请选择合适的英语表达来完成对话。',
  npcQuestion: 'Good afternoon! How can I help you today?',
}

async function handleSubmit() {
  if (!selectedExpression.value || loading.value) return

  loading.value = true
  error.value = ''
  try {
    const data = await completeAirportTicket({
      selected_expression: selectedExpression.value,
      scene: sceneInfo.scene,
      result: { completed: true },
    })
    result.value = data
    submitted.value = true
  } catch (e) {
    error.value = e.message || '提交失败'
  } finally {
    loading.value = false
  }
}

function handleReset() {
  submitted.value = false
  result.value = null
  selectedExpression.value = ''
  error.value = ''
}
</script>

<template>
  <div class="sidequest-page">
    <h1 class="page-title">✈️ 机场购票任务</h1>

    <!-- 任务说明 -->
    <section class="card scene-card">
      <div class="scene-header">
        <div class="scene-icon">🛫</div>
        <div>
          <h2>机场副线任务</h2>
          <p class="scene-location">{{ sceneInfo.location }}</p>
        </div>
      </div>

      <p class="scene-desc">{{ sceneInfo.taskDescription }}</p>

      <!-- NPC 对话区域 -->
      <div class="npc-bubble">
        <div class="npc-avatar">🧑‍✈️</div>
        <div class="npc-info">
          <span class="npc-name">{{ sceneInfo.npc }}</span>
          <p class="npc-question">{{ sceneInfo.npcQuestion }}</p>
        </div>
      </div>

      <!-- 选项 -->
      <div v-if="!submitted" class="expression-options">
        <h3>选择你的回答：</h3>
        <button
          v-for="expr in expressions"
          :key="expr.id"
          class="expr-option"
          :class="{ selected: selectedExpression === expr.text }"
          :disabled="loading"
          @click="selectedExpression = expr.text"
          type="button"
        >
          <span class="expr-id">{{ expr.id }}</span>
          <div class="expr-content">
            <span class="expr-text">{{ expr.text }}</span>
            <span class="expr-label">{{ expr.label }}</span>
          </div>
        </button>
      </div>

      <!-- 操作 -->
      <div v-if="!submitted" class="sidequest-actions">
        <button
          class="btn-primary"
          :disabled="!selectedExpression || loading"
          @click="handleSubmit"
        >
          {{ loading ? '提交中...' : '确认回答' }}
        </button>
      </div>
    </section>

    <!-- 完成反馈 -->
    <section v-if="submitted && result" class="card result-card">
      <div class="result-header">
        <span class="result-icon">✅</span>
        <div>
          <h2>任务完成</h2>
          <p>你的回答已记录。</p>
        </div>
      </div>

      <div class="result-detail">
        <div class="result-row">
          <span class="result-label">你选择的表达：</span>
          <span class="result-value">{{ selectedExpression }}</span>
        </div>
        <div class="result-row">
          <span class="result-label">记录 ID：</span>
          <span class="result-value">#{{ result.sidequest_run_id }}</span>
        </div>
      </div>

      <StatusMessage
        type="info"
        message="该结果只用于后续练习参考，不直接改变正式画像。副线信号需经主线正式验证后才可影响能力评估。"
        style="margin-top: 16px;"
      />

      <div style="margin-top: 20px;">
        <button class="btn-secondary" @click="handleReset">再次尝试</button>
      </div>
    </section>

    <StatusMessage
      v-if="error"
      type="error"
      :message="error"
      style="margin-top: 16px;"
    />
  </div>
</template>

<style scoped>
.sidequest-page {
  max-width: 720px;
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

/* Scene card */
.scene-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
}

.scene-icon {
  font-size: 2rem;
}

.scene-location {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  margin-top: 2px;
}

.scene-desc {
  font-size: 0.93rem;
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: 24px;
  padding: 14px;
  background: var(--color-bg);
  border-radius: var(--radius-md);
}

/* NPC bubble */
.npc-bubble {
  display: flex;
  gap: 14px;
  padding: 18px;
  background: linear-gradient(135deg, #EDE9FE, #F5F3FF);
  border: 1.5px solid var(--color-primary-light);
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
}

.npc-avatar {
  font-size: 2rem;
  flex-shrink: 0;
}

.npc-name {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--color-primary);
}

.npc-question {
  font-size: 1.05rem;
  font-weight: 500;
  color: var(--color-text);
  margin-top: 4px;
  line-height: 1.5;
}

/* Options */
.expression-options h3 {
  font-size: 0.95rem;
  margin-bottom: 12px;
}

.expr-option {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 14px 18px;
  margin-bottom: 10px;
  background: var(--color-bg);
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  text-align: left;
  transition: all 0.15s;
}

.expr-option:hover:not(:disabled) {
  border-color: var(--color-primary-light);
  background: var(--color-primary-bg);
}

.expr-option.selected {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.expr-id {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--color-surface);
  font-weight: 700;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.selected .expr-id {
  background: var(--color-primary);
  color: #fff;
}

.expr-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.expr-text {
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--color-text);
}

.expr-label {
  font-size: 0.78rem;
  color: var(--color-text-muted);
}

.sidequest-actions {
  margin-top: 20px;
}

/* Result */
.result-card {
  margin-top: 20px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 16px;
}

.result-icon {
  font-size: 2rem;
}

.result-detail {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-row {
  display: flex;
  gap: 8px;
  font-size: 0.9rem;
}

.result-label {
  color: var(--color-text-muted);
}

.result-value {
  font-weight: 600;
  color: var(--color-text);
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
