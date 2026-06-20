<script setup>
import { ref, onMounted } from 'vue'
import {
  getProfileSummary,
  saveProfileGoal,
} from '../api/index.js'
import { ABILITY_LABEL } from '../constants.js'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import EmptyState from '../components/EmptyState.vue'
import StatusMessage from '../components/StatusMessage.vue'

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const successMsg = ref('')

const profileData = ref(null)
const goal = ref({
  exam_type: 'CET-6',
  days_until_exam: 30,
  target_score: 550,
  daily_minutes: 30,
  self_reported_weaknesses: [],
  interest_topics: [],
})

const weaknessOptions = ['vocabulary', 'reading', 'grammar', 'writing', 'listening']
const interestOptions = ['technology', 'science', 'environment', 'culture', 'education', 'health']

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const data = await getProfileSummary()
    profileData.value = data
    if (data.latest_goal && Object.keys(data.latest_goal).length > 0) {
      const g = data.latest_goal
      goal.value = {
        exam_type: g.exam_type || 'CET-6',
        days_until_exam: g.days_until_exam ?? 30,
        target_score: g.target_score ?? 550,
        daily_minutes: g.daily_minutes ?? 30,
        self_reported_weaknesses: g.self_reported_weaknesses || [],
        interest_topics: g.interest_topics || [],
      }
    }
  } catch (e) {
    error.value = e.message || '加载画像失败'
  } finally {
    loading.value = false
  }
}

async function handleSaveGoal() {
  saving.value = true
  successMsg.value = ''
  error.value = ''
  try {
    await saveProfileGoal({
      exam_type: goal.value.exam_type,
      days_until_exam: goal.value.days_until_exam,
      target_score: goal.value.target_score,
      daily_minutes: goal.value.daily_minutes,
      self_reported_weaknesses: goal.value.self_reported_weaknesses,
      interest_topics: goal.value.interest_topics,
    })
    successMsg.value = '学习目标已保存'
    await loadData()
  } catch (e) {
    error.value = e.message || '保存失败'
  } finally {
    saving.value = false
  }
}

function toggleWeakness(w) {
  const idx = goal.value.self_reported_weaknesses.indexOf(w)
  if (idx >= 0) {
    goal.value.self_reported_weaknesses = goal.value.self_reported_weaknesses.filter((x) => x !== w)
  } else {
    goal.value.self_reported_weaknesses = [...goal.value.self_reported_weaknesses, w]
  }
}

function toggleInterest(t) {
  const idx = goal.value.interest_topics.indexOf(t)
  if (idx >= 0) {
    goal.value.interest_topics = goal.value.interest_topics.filter((x) => x !== t)
  } else {
    goal.value.interest_topics = [...goal.value.interest_topics, t]
  }
}

onMounted(loadData)
</script>

<template>
  <div class="profile-page">
    <h1 class="page-title">能力画像</h1>

    <LoadingState v-if="loading" message="正在加载画像数据..." />

    <ErrorState
      v-else-if="error && !profileData"
      :message="error"
      @retry="loadData"
    />

    <template v-else>
      <!-- 用户信息 -->
      <section class="card" style="margin-bottom: 20px;">
        <h2>👤 用户信息</h2>
        <div class="user-info">
          <span class="user-name">{{ profileData?.user?.display_name || 'Demo 用户' }}</span>
          <span class="user-id">ID: {{ profileData?.user?.id || '-' }}</span>
        </div>
      </section>

      <!-- 学习目标 -->
      <section class="card" style="margin-bottom: 20px;">
        <h2>🎯 学习目标</h2>

        <StatusMessage v-if="successMsg" type="success" :message="successMsg" style="margin-bottom: 16px;" />
        <StatusMessage v-if="error" type="error" :message="error" style="margin-bottom: 16px;" />

        <div class="goal-form">
          <div class="form-row">
            <label class="form-label">
              考试类型
              <select v-model="goal.exam_type" class="form-input">
                <option value="CET-6">CET-6</option>
                <option value="CET-4">CET-4</option>
              </select>
            </label>
            <label class="form-label">
              距离考试（天）
              <input v-model.number="goal.days_until_exam" type="number" min="0" class="form-input" />
            </label>
          </div>
          <div class="form-row">
            <label class="form-label">
              目标分数
              <input v-model.number="goal.target_score" type="number" min="0" max="710" class="form-input" />
            </label>
            <label class="form-label">
              每日学习（分钟）
              <input v-model.number="goal.daily_minutes" type="number" min="0" max="480" class="form-input" />
            </label>
          </div>

          <div class="form-group">
            <span class="form-label-text">自评薄弱项</span>
            <div class="chip-group">
              <button
                v-for="w in weaknessOptions"
                :key="w"
                class="chip"
                :class="{ active: goal.self_reported_weaknesses.includes(w) }"
                @click="toggleWeakness(w)"
                type="button"
              >
                {{ w }}
              </button>
            </div>
          </div>

          <div class="form-group">
            <span class="form-label-text">感兴趣的主题</span>
            <div class="chip-group">
              <button
                v-for="t in interestOptions"
                :key="t"
                class="chip"
                :class="{ active: goal.interest_topics.includes(t) }"
                @click="toggleInterest(t)"
                type="button"
              >
                {{ t }}
              </button>
            </div>
          </div>

          <div class="form-actions">
            <button class="btn-primary" :disabled="saving" @click="handleSaveGoal">
              {{ saving ? '保存中...' : '保存目标' }}
            </button>
          </div>
        </div>
      </section>

      <!-- 已确认画像 -->
      <section class="card" style="margin-bottom: 20px;">
        <h2>📊 已确认画像</h2>
        <div v-if="profileData?.latest_profile && Object.keys(profileData.latest_profile).length > 0" class="profile-display">
          <div class="profile-meta">
            <span class="meta-item">
              来源：{{ profileData.latest_profile.source || '-' }}
            </span>
          </div>
          <div class="ability-bars">
            <div
              v-for="(value, key) in ABILITY_LABEL"
              :key="key"
              class="ability-bar"
            >
              <div class="bar-header">
                <span class="bar-label">{{ value }}</span>
              </div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: '60%' }"></div>
              </div>
            </div>
          </div>
        </div>
        <EmptyState
          v-else
          icon="📊"
          title="暂无画像数据"
          description="完成诊断或训练后，系统将根据学习证据生成能力画像。"
        />
      </section>

      <!-- 画像更新建议 -->
      <section class="card">
        <h2>💡 画像更新建议</h2>
        <div v-if="profileData?.pending_suggestions?.length > 0" class="suggestion-list">
          <div
            v-for="s in profileData.pending_suggestions"
            :key="s.id"
            class="suggestion-item"
          >
            <div class="suggestion-header">
              <span class="suggestion-id">建议 #{{ s.id }}</span>
              <span class="suggestion-status needs-review">待审核</span>
            </div>
            <div class="suggestion-detail">
              <span>能力维度：{{ ABILITY_LABEL[s.ability] || s.ability || '-' }}</span>
              <span>方向：{{ s.direction || '-' }}</span>
              <span>置信度：{{ s.confidence || '-' }}</span>
            </div>
            <div v-if="s.reason" class="suggestion-reason">{{ s.reason }}</div>
          </div>
        </div>
        <EmptyState
          v-else
          icon="💡"
          title="暂无待处理的画像更新建议"
          description="训练后 Agent 会分析你的表现并给出画像更新建议，经过程序校验后会在这里展示。"
        />
        <p class="suggestion-note">
          画像更新建议由 Agent 提出，经程序校验后才会应用到正式画像。
        </p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.profile-page {
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

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-name {
  font-size: 1.1rem;
  font-weight: 600;
}

.user-id {
  font-size: 0.82rem;
  color: var(--color-text-muted);
}

/* Goal form */
.goal-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
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
  transition: border-color 0.15s;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label-text {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.chip-group {
  display: flex;
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

.form-actions {
  padding-top: 8px;
}

/* Profile display */
.profile-display {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.profile-meta {
  display: flex;
  gap: 16px;
}

.meta-item {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.ability-bars {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.ability-bar {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bar-header {
  display: flex;
  justify-content: space-between;
}

.bar-label {
  font-size: 0.88rem;
  font-weight: 500;
}

.bar-track {
  height: 8px;
  background: var(--color-border-light);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary-light), var(--color-primary));
  border-radius: 4px;
  transition: width 0.3s;
}

/* Suggestions */
.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.suggestion-item {
  padding: 14px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.suggestion-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.suggestion-id {
  font-weight: 600;
}

.suggestion-status {
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.suggestion-status.needs-review {
  background: var(--color-warning-bg);
  color: #8B6914;
}

.suggestion-detail {
  display: flex;
  gap: 16px;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.suggestion-reason {
  margin-top: 8px;
  font-size: 0.85rem;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.suggestion-note {
  margin-top: 12px;
  font-size: 0.78rem;
  color: var(--color-text-muted);
  font-style: italic;
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

@media (max-width: 600px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
