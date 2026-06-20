<script setup>
defineProps({
  id: { type: String, required: true },
  text: { type: String, required: true },
  state: {
    type: String,
    default: 'default',
    validator: (v) => ['default', 'selected', 'correct', 'incorrect', 'dimmed'].includes(v),
  },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['select'])
</script>

<template>
  <button
    class="option-btn"
    :class="[`state-${state}`, { disabled }]"
    :disabled="disabled"
    @click="emit('select', id)"
    type="button"
  >
    <span class="option-id">{{ id }}</span>
    <span class="option-text">{{ text }}</span>
    <span v-if="state === 'correct'" class="option-mark">✓</span>
    <span v-if="state === 'incorrect'" class="option-mark">✗</span>
  </button>
</template>

<style scoped>
.option-btn {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 14px 18px;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text);
  text-align: left;
  font-size: 0.95rem;
  line-height: 1.5;
  transition: all 0.15s ease;
  cursor: pointer;
}

.option-btn:not(.disabled):hover {
  border-color: var(--color-primary-light);
  background: var(--color-primary-bg);
}

.option-btn.state-selected {
  border-color: var(--color-primary);
  background: var(--color-primary-bg);
  box-shadow: 0 0 0 1px var(--color-primary);
}

.option-btn.state-correct {
  border-color: var(--color-success);
  background: var(--color-success-bg);
  cursor: default;
}

.option-btn.state-incorrect {
  border-color: var(--color-error);
  background: var(--color-error-bg);
  cursor: default;
}

.option-btn.state-dimmed {
  opacity: 0.45;
  cursor: default;
}

.option-btn.disabled {
  pointer-events: none;
}

.option-id {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--color-bg);
  font-weight: 700;
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.state-selected .option-id {
  background: var(--color-primary);
  color: #fff;
}

.state-correct .option-id {
  background: var(--color-success);
  color: #fff;
}

.state-incorrect .option-id {
  background: var(--color-error);
  color: #fff;
}

.option-text {
  flex: 1;
}

.option-mark {
  font-size: 1.1rem;
  font-weight: 700;
  flex-shrink: 0;
}

.state-correct .option-mark { color: var(--color-success); }
.state-incorrect .option-mark { color: var(--color-error); }
</style>
