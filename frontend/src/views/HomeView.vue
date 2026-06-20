<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getProfileSummary,
  listTrainingSessions,
} from '../api/index.js'
import { STAGE_LABEL } from '../constants.js'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import EmptyState from '../components/EmptyState.vue'
import StatusMessage from '../components/StatusMessage.vue'

const router = useRouter()

const loading = ref(true)
const error = ref('')
const errorCode = ref('')

const profileSummary = ref(null)
const goal = ref(null)
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
      recentSessions.value = sessions.sessions.slice(0, 5).map((s) => ({
        ...s,
        stageLabel: STAGE_LABEL[s.stage] || s.stage,
      }))
    }
  } catch (e) {
    error.value = e.message || '加载失败'
    errorCode.value = e.code || ''
  } finally {
    loading.value = false
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

function goToHistory() {
  router.push('/history')
}

const hasGoal = () => {
  if (!goal.value) return false
  const g = goal.value
  return g.exam_type || g.target_score || g.daily_minutes
}

onMounted(loadData)
</script>

<template>
  <div class="home-page">
    <h1 class="page-title">LingoForge 学习首页</h1>

    <LoadingState v-if="loading" message="正在加载学习数据..." />

    <template v-else>
      <StatusMessage
        v-if="error"
        type="warning"
        :message="error"
        style="margin-bottom: 20px;"
      />

      <!-- CET-6 目标摘要 -->
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
          description="设置 CET-6 目标后，Agent 将根据你的画像定制训练。"
        />
        <div style="text-align: center; padding-bottom: 16px;">
          <button class="btn-primary" @click="goToProfile">设置目标</button>
        </div>
      </section>

      <!-- 推荐入口 -->
      <section class="card" style="margin-top: 20px;">
        <h2>📝 开始一次 Agent 训练</h2>
        <p class="section-desc">
          输入一段 CET-6 难度的英文材料，Agent 将读取你的学习画像和历史记录，
          生成针对性训练题目。确定性程序负责判分、记录证据和画像建议。
        </p>
        <button class="btn-primary" @click="goToTraining">开始训练</button>
      </section>

      <!-- 快捷入口 -->
      <div class="quick-actions" style="margin-top: 20px;">
        <section class="card quick-card" @click="goToSidequest" role="button" tabindex="0">
          <h3>✈️ 机场任务</h3>
          <p>在机场购票场景中练习英语表达，结果用于后续练习参考。</p>
        </section>

        <section class="card quick-card" @click="goToIsolatedTest" role="button" tabindex="0">
          <h3>🔒 阶段检测</h3>
          <p>在独立隔离环境中完成检测题，验证当前学习效果。</p>
        </section>

        <section class="card quick-card" @click="goToProfile" role="button" tabindex="0">
          <h3>👤 能力画像</h3>
          <p>查看已确认画像、待审核的画像更新建议，编辑学习目标。</p>
        </section>
      </div>

      <!-- 最近训练 -->
      <section class="card" style="margin-top: 20px;" v-if="recentSessions.length > 0">
        <div class="card-header">
          <h2>📊 最近训练</h2>
          <button class="link-btn" @click="goToHistory">查看全部</button>
        </div>
        <div class="session-list">
          <div
            v-for="s in recentSessions"
            :key="s.id"
            class="session-row"
          >
            <span class="session-stage">{{ s.stageLabel }}</span>
            <span class="session-status" :class="s.status === 'COMPLETED' ? 'done' : 'active'">
              {{ s.status === 'COMPLETED' ? '已完成' : '进行中' }}
            </span>
            <span class="session-date">{{ s.created_at?.slice(0, 10) || '-' }}</span>
          </div>
        </div>
      </section>

      <EmptyState
        v-else
        icon="📊"
        title="暂无训练记录"
        description="完成一次训练后，最近结果将在这里显示。"
      />
    </template>
  </div>
</template>

<style scoped>
.home-page {
  max-width: 960px;
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

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.section-desc {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  line-height: 1.7;
  margin: 8px 0 16px;
}

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

@media (max-width: 768px) {
  .goal-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .quick-actions {
    grid-template-columns: 1fr;
  }
}
</style>
