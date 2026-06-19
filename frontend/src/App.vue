<script setup>
import { onMounted, ref } from 'vue'
import { API_BASE_URL, fetchHealth } from './api'

const health = ref(null)
const error = ref('')
const isLoading = ref(true)

async function loadHealth() {
  isLoading.value = true
  error.value = ''
  try {
    health.value = await fetchHealth()
  } catch (currentError) {
    error.value = currentError instanceof Error ? currentError.message : '健康检查失败'
  } finally {
    isLoading.value = false
  }
}

onMounted(loadHealth)
</script>

<template>
  <main class="app-shell">
    <section class="hero-panel" aria-labelledby="page-title">
      <p class="eyebrow">LingoForge MVP</p>
      <h1 id="page-title">CET-6 自适应学习 Agent</h1>
      <p class="summary">
        当前批次只验证前后端骨架、配置、SQLite 初始化和 Mock LLM Provider。完整主流程会在后续任务接入。
      </p>
    </section>

    <section class="status-grid" aria-label="系统状态">
      <article class="status-card">
        <span class="label">FastAPI</span>
        <strong>{{ isLoading ? '检查中' : error ? '不可用' : '已连接' }}</strong>
        <p>{{ API_BASE_URL }}</p>
      </article>

      <article class="status-card">
        <span class="label">SQLite</span>
        <strong>{{ health?.database_initialized ? '已初始化' : '等待检查' }}</strong>
        <p>核心 Schema 已由后端启动时初始化。</p>
      </article>

      <article class="status-card">
        <span class="label">LLM</span>
        <strong>{{ health?.llm_provider || 'mock' }}</strong>
        <p>默认 Mock 模式，真实 DeepSeek 后续接入。</p>
      </article>
    </section>

    <section class="health-panel" aria-live="polite">
      <div class="panel-header">
        <div>
          <h2>后端健康检查</h2>
          <p>Vue 页面会真实请求 FastAPI 的 <code>/health</code> 接口。</p>
        </div>
        <button type="button" @click="loadHealth">重新检查</button>
      </div>

      <p v-if="isLoading" class="state">正在读取后端状态...</p>
      <p v-else-if="error" class="state error">{{ error }}</p>
      <pre v-else>{{ JSON.stringify(health, null, 2) }}</pre>
    </section>
  </main>
</template>

