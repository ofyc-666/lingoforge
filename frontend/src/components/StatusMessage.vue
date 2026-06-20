<script setup>
defineProps({
  type: {
    type: String,
    default: 'info',
    validator: (v) => ['info', 'success', 'warning', 'error'].includes(v),
  },
  message: { type: String, required: true },
})
</script>

<template>
  <div class="status-msg" :class="`type-${type}`">
    <span class="status-icon">
      <template v-if="type === 'success'">✓</template>
      <template v-else-if="type === 'error'">✗</template>
      <template v-else-if="type === 'warning'">!</template>
      <template v-else>ℹ</template>
    </span>
    <span>{{ message }}</span>
  </div>
</template>

<style scoped>
.status-msg {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  line-height: 1.5;
}

.type-info {
  background: var(--color-info-bg);
  color: #2B6CB0;
  border: 1px solid #BEE3F8;
}

.type-success {
  background: var(--color-success-bg);
  color: #1B7A5C;
  border: 1px solid #B2F0E2;
}

.type-warning {
  background: var(--color-warning-bg);
  color: #8B6914;
  border: 1px solid #FDE68A;
}

.type-error {
  background: var(--color-error-bg);
  color: #A13A3A;
  border: 1px solid #FECACA;
}

.status-icon {
  font-weight: 700;
  flex-shrink: 0;
  width: 20px;
  text-align: center;
}
</style>
