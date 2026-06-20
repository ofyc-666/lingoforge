<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const navItems = [
  { path: '/', label: '今日学习', icon: '📅' },
  { path: '/reader', label: '阅读导入', icon: '📄' },
  { path: '/training', label: '开始训练', icon: '📝' },
  { path: '/history', label: '学习记录', icon: '📊' },
  { path: '/profile', label: '能力画像', icon: '👤' },
  { path: '/sidequest', label: '扩展任务', icon: '✈️' },
]

const isActive = (path) => {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}
</script>

<template>
  <nav class="sidebar" aria-label="主导航">
    <div class="sidebar-brand">
      <span class="brand-icon">🔮</span>
      <span class="brand-text">LingoForge</span>
    </div>
    <ul class="nav-list">
      <li v-for="item in navItems" :key="item.path">
        <router-link
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </li>
    </ul>
    <div class="sidebar-footer">
      <span class="version-tag">MVP v0.1</span>
    </div>
  </nav>
</template>

<style scoped>
.sidebar {
  position: fixed;
  top: var(--topbar-height);
  left: 0;
  bottom: 0;
  width: var(--sidebar-width);
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  z-index: 100;
  overflow-y: auto;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 20px 12px;
}

.brand-icon {
  font-size: 1.4rem;
}

.brand-text {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: -0.01em;
}

.nav-list {
  list-style: none;
  margin: 0;
  padding: 8px 12px;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: 0.93rem;
  font-weight: 500;
  transition: all 0.15s ease;
  margin-bottom: 2px;
}

.nav-item:hover {
  background: var(--color-primary-bg);
  color: var(--color-primary);
  text-decoration: none;
}

.nav-item.active {
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-weight: 600;
}

.nav-icon {
  font-size: 1.15rem;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.nav-label {
  white-space: nowrap;
}

.sidebar-footer {
  padding: 16px 20px;
  border-top: 1px solid var(--color-border-light);
}

.version-tag {
  font-size: 0.75rem;
  color: var(--color-text-muted);
  font-weight: 500;
}

@media (max-width: 900px) {
  .sidebar {
    display: none;
  }
}
</style>
