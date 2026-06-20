<script setup>
import { DEMO_USER_ID } from '../constants.js'
</script>

<template>
  <header class="topbar">
    <div class="topbar-left">
      <span class="topbar-title">CET-6 自适应学习</span>
    </div>
    <div class="topbar-right">
      <span class="user-badge">Demo 用户 #{{ DEMO_USER_ID }}</span>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--topbar-height);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  z-index: 200;
}

.topbar-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.user-badge {
  font-size: 0.82rem;
  color: var(--color-text-muted);
  background: var(--color-primary-bg);
  padding: 4px 12px;
  border-radius: 20px;
  font-weight: 500;
}
</style>
