<script setup>
defineProps({
  message: { type: String, default: '发生错误，请稍后重试。' },
  code: { type: String, default: '' },
})

const emit = defineEmits(['retry'])
</script>

<template>
  <div class="error-state">
    <div class="error-icon">⚠️</div>
    <h3>出错了</h3>
    <p>{{ message }}</p>
    <p v-if="code" class="error-code">{{ code }}</p>
    <button class="retry-btn" @click="emit('retry')">重试</button>
  </div>
</template>

<style scoped>
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
  gap: 10px;
  text-align: center;
}

.error-icon {
  font-size: 2rem;
  margin-bottom: 4px;
}

.error-state h3 {
  color: var(--color-error);
  font-size: 1.1rem;
}

.error-state p {
  color: var(--color-text-secondary);
  max-width: 400px;
}

.error-code {
  font-family: var(--font-mono);
  font-size: 0.78rem !important;
  color: var(--color-text-muted) !important;
  background: var(--color-error-bg);
  padding: 2px 10px;
  border-radius: 4px;
}

.retry-btn {
  margin-top: 8px;
  padding: 8px 24px;
  background: var(--color-primary);
  color: #fff;
  border-radius: var(--radius-btn);
  font-weight: 500;
  transition: background 0.15s;
}

.retry-btn:hover {
  background: var(--color-primary-hover);
}
</style>
