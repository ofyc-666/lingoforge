<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getProfileSummary,
  generateDailyPlan,
  getTodayPlan,
  listTrainingSessions,
  setSessionId,
} from '../api/index.js'
import { ABILITY_LABEL, PRACTICE_MODE_LABEL, PLAN_STATUS_LABEL, LEARNING_STATUS_LABEL } from '../constants.js'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import EmptyState from '../components/EmptyState.vue'
import StatusMessage from '../components/StatusMessage.vue'

const router = useRouter()

// 状态
const loading = ref(true)
const error = ref('')
const errorCode = ref('')

// 用户目标与画像
const profileSummary = ref(null)
const goal = ref(null)

// 今日计划
const todayPlan = ref(null)
const planLoading = ref(false)

// 最近训练会话
const recentSessions = ref([])

async function loadData() {
  loading.value = true
  error.value = ''
  try {
    const [summary, sessions] = await Promise.all([
      getProfileSummary().catch(() => null),
      listTrainingSessions().catch(() => ({ sessions: [] })),
    ])
    profileSummary.value = summary
    goal.value = summary?.latest_goal || null

    if (sessions?.sessions?.length > 0) {
      recentSessions.value = sessions.sessions.slice(0, 3).map((s) => ({
        ...s,
        stageLabel: s.stage || '',
      }))
    }

    // 尝试获取今日计划
    try {
      const plan = await getTodayPlan()
      todayPlan.value = plan
    } catch (_) {
      todayPlan.value = null
    }
  } catch (e) {
    error.value = e.message || '加载失败'
    errorCode.value = e.code || ''
  } finally {
    loading.value = false
  }
}

async function handleGeneratePlan() {
  planLoading.value = true
  try {
    await generateDailyPlan({ regenerate: false })
    const plan = await getTodayPlan()
    todayPlan.value = plan
  } catch (e) {
    error.value = e.message || '生成计划失败'
    errorCode.value = e.code || ''
  } finally {
    planLoading.value = false
  }
}

function goToTraining() {
  router.push('/training')
}

function goToSidequest() {
  router.push('/sidequest')
}

function goToIsolatedTest() {
  router.push('/isolated-test')
}

function goToProfile() {
  router.push('/profile')
}

const hasGoal = () => {
  if (!goal.value) return false
  const g = goal.value
  return g.exam_type || g.target_score || g.daily_minutes
}

onMounted(loadData)
</script>

<template>
  <div class="daily-page">
    <h1 class="page-title">今日学习</h1>

    <LoadingState v-if="loading" message="正在加载学习数据..." />

    <template v-else>
      <!-- 错误提示 -->
      <StatusMessage
        v-if="error"
        type="warning"
        :message="error"
        style="margin-bottom: 20px;"
      />

      <!-- 用户目标摘要卡片 -->
      <section class="goal-card card" v-if="hasGoal()">
        <div class="card-header">
          <h2>🎯 学习目标</h2>
          <button class="link-btn" @click="goToProfile">编辑</button>
        </div>
        <div class="goal-grid">
          <div class="goal-item">
            <span class="goal-label">考试</span>
            <span class="goal-value">{{ goal.exam_type || 'CET-6' }}</span>
          </div>
          <div class="goal-item">
            <span class="goal-label">目标分数</span>
            <span class="goal-value">{{ goal.target_score || '-' }} 分</span>
          </div>
          <div class="goal-item">
            <span class="goal-label">每日学习</span>
            <span class="goal-value">{{ goal.daily_minutes || '-' }} 分钟</span>
          </div>
          <div class="goal-item">
            <span class="goal-label">距考试</span>
            <span class="goal-value">{{ goal.days_until_exam ?? '-' }} 天</span>
          </div>
        </div>
      </section>

      <!-- 未设置目标 -->
      <section class="card" v-else>
        <div class="card-header">
          <h2>🎯 学习目标</h2>
        </div>
        <EmptyState
          icon="📋"
          title="尚未设置学习目标"
          description="设置目标后，Agent 将为你定制学习计划。"
        />
        <div style="text-align: center; padding-bottom: 16px;">
          <button class="btn-primary" @click="goToProfile">设置目标</button>
        </div>
      </section>

      <!-- 今日计划区域 -->
      <section class="card" style="margin-top: 20px;">
        <div class="card-header">
          <h2>📅 今日学习计划</h2>
          <button
            v-if="!todayPlan"
            class="btn-primary btn-sm"
            :disabled="planLoading"
            @click="handleGeneratePlan"
          >
            {{ planLoading ? '生成中...' : '生成今日计划' }}
          </button>
        </div>

        <template v-if="todayPlan">
          <div class="plan-summary">
            <div class="plan-stat">
              <span class="plan-stat-value">{{ PLAN_STATUS_LABEL[todayPlan.status] || todayPlan.status }}</span>
              <span class="plan-stat-label">状态</span>
            </div>
            <div class="plan-stat">
              <span class="plan-stat-value">{{ PRACTICE_MODE_LABEL[todayPlan.practice_mode] || todayPlan.practice_mode }}</span>
              <span class="plan-stat-label">练习模式</span>
            </div>
            <div class="plan-stat">
              <span class="plan-stat-value">{{ todayPlan.estimated_minutes || '-' }} 分钟</span>
              <span class="plan-stat-label">预计时长</span>
            </div>
            <div class="plan-stat">
              <span class="plan-stat-value">{{ todayPlan.vocabulary_items?.length || 0 }} 词</span>
              <span class="plan-stat-label">今日词汇</span>
            </div>
          </div>

          <div class="plan-rationale" v-if="todayPlan.rationale">
            <span class="rationale-label">推荐理由：</span>
            {{ todayPlan.rationale }}
          </div>

          <!-- 词汇列表 -->
          <div v-if="todayPlan.vocabulary_items?.length > 0" class="vocab-section">
            <h3>今日词汇</h3>
            <div class="vocab-grid">
              <div
                v-for="v in todayPlan.vocabulary_items"
                :key="v.id"
                class="vocab-chip"
                :class="`status-${v.learning_status || 'NEW'}`"
              >
                <span class="vocab-word">{{ v.word }}</span>
                <span class="vocab-meaning">{{ v.meaning_zh }}</span>
                <span class="vocab-tag">{{ LEARNING_STATUS_LABEL[v.learning_status] || v.learning_status }}</span>
              </div>
            </div>
          </div>

          <div class="plan-actions" style="margin-top: 20px;">
            <button class="btn-primary" @click="goToTraining">开始训练</button>
          </div>
        </template>

        <EmptyState
          v-else
          icon="📅"
          title="今日暂无学习计划"
          description="点击上方按钮生成今日计划，Agent 将根据你的画像和词汇数据定制学习内容。"
        />
      </section>

      <!-- 快捷入口卡片 -->
      <div class="quick-actions" style="margin-top: 20px;">
        <section class="card quick-card" @click="goToTraining" role="button" tabindex="0">
          <h3>📝 开始训练</h3>
          <p>创建训练会话，输入英文材料或使用推荐内容开始 CET-6 训练。</p>
        </section>

        <section class="card quick-card" @click="goToSidequest" role="button" tabindex="0">
          <h3>✈️ 机场任务</h3>
          <p>在机场购票场景中练习英语表达，结果用于后续练习参考。</p>
        </section>

        <section class="card quick-card" @click="goToIsolatedTest" role="button" tabindex="0">
          <h3>🔒 阶段检测</h3>
          <p>在独立隔离环境中完成检测题，验证当前学习效果。</p>
        </section>
      </div>

      <!-- 最近训练 -->
      <section class="card" style="margin-top: 20px;" v-if="recentSessions.length > 0">
        <div class="card-header">
          <h2>📊 最近训练</h2>
          <button class="link-btn" @click="router.push('/history')">查看全部</button>
        </div>
        <div class="session-list">
          <div
            v-for="s in recentSessions"
            :key="s.id"
            class="session-row"
          >
            <span class="session-stage">{{ s.stage || '-' }}</span>
            <span class="session-status" :class="s.status === 'COMPLETED' ? 'done' : 'active'">
              {{ s.status === 'COMPLETED' ? '已完成' : '进行中' }}
            </span>
            <span class="session-date">{{ s.created_at?.slice(0, 10) || '-' }}</span>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.daily-page {
  max-width: 960px;
}

.page-title {
  margin-bottom: 24px;
}

/* Card base */
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 24px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

/* Goal grid */
.goal-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.goal-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.goal-label {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  font-weight: 500;
}

.goal-value {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--color-text);
}

/* Plan summary */
.plan-summary {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}

.plan-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.plan-stat-value {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-primary);
}

.plan-stat-label {
  font-size: 0.78rem;
  color: var(--color-text-muted);
}

.plan-rationale {
  padding: 12px 16px;
  background: var(--color-bg);
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
  margin-bottom: 16px;
}

.rationale-label {
  font-weight: 600;
  color: var(--color-text);
}

/* Vocab section */
.vocab-section h3 {
  font-size: 0.95rem;
  margin-bottom: 12px;
}

.vocab-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.vocab-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: border-color 0.15s;
}

.vocab-chip:hover {
  border-color: var(--color-primary-light);
}

.vocab-word {
  font-weight: 700;
  color: var(--color-text);
}

.vocab-meaning {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.vocab-tag {
  font-size: 0.7rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

/* Quick actions */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.quick-card {
  cursor: pointer;
  transition: all 0.15s ease;
}

.quick-card:hover {
  border-color: var(--color-primary-light);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.quick-card h3 {
  font-size: 1.05rem;
  margin-bottom: 8px;
}

.quick-card p {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* Session list */
.session-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 14px;
  background: var(--color-bg);
  border-radius: var(--radius-sm);
}

.session-stage {
  flex: 1;
  font-weight: 500;
}

.session-status {
  font-size: 0.8rem;
  padding: 3px 10px;
  border-radius: 10px;
  font-weight: 500;
}

.session-status.done {
  background: var(--color-success-bg);
  color: #1B7A5C;
}

.session-status.active {
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

.session-date {
  font-size: 0.82rem;
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

.btn-primary:hover {
  background: var(--color-primary-hover);
}

.btn-sm {
  padding: 6px 16px;
  font-size: 0.85rem;
}

.link-btn {
  background: none;
  color: var(--color-primary);
  font-size: 0.85rem;
  font-weight: 500;
  padding: 2px 4px;
}

.link-btn:hover {
  text-decoration: underline;
}

/* Responsive */
@media (max-width: 768px) {
  .goal-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .quick-actions {
    grid-template-columns: 1fr;
  }
  .plan-summary {
    flex-wrap: wrap;
    gap: 12px;
  }
}
</style>
