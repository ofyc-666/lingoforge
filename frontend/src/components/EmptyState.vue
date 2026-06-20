<script setup>
defineProps({
  icon: { type: String, default: '📭' },
  title: { type: String, default: '暂无内容' },
  description: { type: String, default: '' },
})
</script>

<template>
  <div class="empty-state">
    <span class="empty-icon">{{ icon }}</span>
    <h3>{{ title }}</h3>
    <p v-if="description">{{ description }}</p>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 48px 20px;
  gap: 8px;
  text-align: center;
  color: var(--color-text-secondary);
}

.empty-icon {
  font-size: 2.5rem;
  margin-bottom: 4px;
  opacity: 0.7;
}

.empty-state h3 {
  font-size: 1.05rem;
  color: var(--color-text-secondary);
}

.empty-state p {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  max-width: 360px;
}
</style>
