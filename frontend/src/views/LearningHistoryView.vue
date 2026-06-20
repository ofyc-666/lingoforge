<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listTrainingSessions, getSessionTasks } from '../api/index.js'
import { STAGE_LABEL } from '../constants.js'
import LoadingState from '../components/LoadingState.vue'
import ErrorState from '../components/ErrorState.vue'
import EmptyState from '../components/EmptyState.vue'

const router = useRouter()

const loading = ref(true)
const error = ref('')
const sessions = ref([])
const expandedSession = ref(null)
const sessionTasks = ref({})
const tasksLoading = ref(false)

onMounted(async () => {
  try {
    const data = await listTrainingSessions()
    sessions.value = data.sessions || []
  } catch (e) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
})

async function toggleSession(sessionId) {
  if (expandedSession.value === sessionId) {
    expandedSession.value = null
    return
  }
  expandedSession.value = sessionId
  if (!sessionTasks.value[sessionId]) {
    tasksLoading.value = true
    try {
      const data = await getSessionTasks(sessionId)
      sessionTasks.value = { ...sessionTasks.value, [sessionId]: data.tasks || [] }
    } catch (e) {
      sessionTasks.value = { ...sessionTasks.value, [sessionId]: [] }
    } finally {
      tasksLoading.value = false
    }
  }
}

function viewResult(taskId) {
  router.push({ name: 'training-result', params: { taskId } })
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  return dateStr.slice(0, 16).replace('T', ' ')
}
</script>

<template>
  <div class="history-page">
    <h1 class="page-title">学习记录</h1>

    <LoadingState v-if="loading" message="正在加载学习记录..." />

    <ErrorState
      v-else-if="error"
      :message="error"
      @retry="() => { loading = true; error = ''; onMounted() }"
    />

    <EmptyState
      v-else-if="sessions.length === 0"
      icon="📊"
      title="暂无学习记录"
      description="完成训练后，历史会话将在这里展示。"
    />

    <template v-else>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          class="session-card"
        >
          <div class="session-header" @click="toggleSession(s.id)">
            <div class="session-main">
              <span class="session-id">#{{ s.id }}</span>
              <span class="session-stage">{{ STAGE_LABEL[s.stage] || s.stage }}</span>
              <span class="session-status" :class="s.status === 'COMPLETED' ? 'done' : 'active'">
                {{ s.status === 'COMPLETED' ? '已完成' : '进行中' }}
              </span>
            </div>
            <div class="session-meta">
              <span class="session-date">{{ formatDate(s.created_at) }}</span>
              <span class="expand-icon">{{ expandedSession === s.id ? '▴' : '▾' }}</span>
            </div>
          </div>

          <!-- 展开的任务列表 -->
          <div v-if="expandedSession === s.id" class="session-tasks">
            <LoadingState v-if="tasksLoading" message="加载任务..." />
            <template v-else-if="sessionTasks[s.id]?.length > 0">
              <div
                v-for="t in sessionTasks[s.id]"
                :key="t.task_id"
                class="task-row"
                @click="viewResult(t.task_id)"
              >
                <span class="task-type">{{ t.task_type }}</span>
                <span class="task-ability">{{ t.target_ability }}</span>
                <span class="task-date">{{ formatDate(t.created_at) }}</span>
                <span class="task-action">查看结果 →</span>
              </div>
            </template>
            <p v-else class="no-tasks">该会话暂无任务记录。</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.history-page {
  max-width: 860px;
}

.page-title {
  margin-bottom: 24px;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.session-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.session-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  transition: background 0.15s;
}

.session-header:hover {
  background: var(--color-bg);
}

.session-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.session-id {
  font-weight: 700;
  color: var(--color-primary);
}

.session-stage {
  font-weight: 500;
  color: var(--color-text);
}

.session-status {
  font-size: 0.78rem;
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

.session-meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.session-date {
  font-size: 0.82rem;
  color: var(--color-text-muted);
}

.expand-icon {
  font-size: 0.7rem;
  color: var(--color-text-muted);
}

/* Tasks */
.session-tasks {
  border-top: 1px solid var(--color-border-light);
  padding: 12px 20px;
}

.task-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s;
}

.task-row:hover {
  background: var(--color-primary-bg);
}

.task-type {
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text);
  min-width: 120px;
}

.task-ability {
  font-size: 0.82rem;
  color: var(--color-text-secondary);
  flex: 1;
}

.task-date {
  font-size: 0.8rem;
  color: var(--color-text-muted);
}

.task-action {
  font-size: 0.85rem;
  color: var(--color-primary);
  font-weight: 500;
}

.no-tasks {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  text-align: center;
  padding: 12px;
}
</style>
