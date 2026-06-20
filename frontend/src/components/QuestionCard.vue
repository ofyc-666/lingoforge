<script setup>
import { computed } from 'vue'
import OptionButton from './OptionButton.vue'
import { ABILITY_LABEL } from '../constants.js'

const props = defineProps({
  question: { type: Object, required: true },
  selectedAnswer: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  showResult: { type: Boolean, default: false },
  questionIndex: { type: Number, default: 0 },
  totalQuestions: { type: Number, default: 0 },
})

const emit = defineEmits(['select'])

const abilityLabel = computed(() => {
  const ab = props.question.target_ability || ''
  return ABILITY_LABEL[ab] || ab
})

const optionState = (optionId) => {
  if (!props.showResult) {
    return props.selectedAnswer === optionId ? 'selected' : 'default'
  }
  const isCorrect = optionId === props.question.answer
  const isSelected = props.selectedAnswer === optionId
  if (isCorrect) return 'correct'
  if (isSelected && !isCorrect) return 'incorrect'
  return 'dimmed'
}
</script>

<template>
  <div class="question-card">
    <div class="question-header">
      <span class="question-num" v-if="totalQuestions > 0">
        第 {{ questionIndex + 1 }} / {{ totalQuestions }} 题
      </span>
      <span class="ability-chip">{{ abilityLabel }}</span>
    </div>

    <div class="question-prompt">{{ question.prompt }}</div>

    <div class="options-list">
      <OptionButton
        v-for="opt in question.options"
        :key="opt.id"
        :id="opt.id"
        :text="opt.text"
        :state="optionState(opt.id)"
        :disabled="disabled"
        @select="emit('select', opt.id)"
      />
    </div>

    <div v-if="showResult && question.explanation" class="explanation">
      <span class="explanation-label">解析：</span>
      {{ question.explanation }}
    </div>
  </div>
</template>

<style scoped>
.question-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 28px;
}

.question-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.question-num {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.ability-chip {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--color-primary);
  background: var(--color-primary-bg);
  padding: 3px 10px;
  border-radius: 20px;
}

.question-prompt {
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--color-text);
  margin-bottom: 24px;
  padding: 16px;
  background: var(--color-bg);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-primary-light);
}

.options-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.explanation {
  margin-top: 20px;
  padding: 14px 16px;
  background: var(--color-info-bg);
  border-radius: var(--radius-md);
  font-size: 0.9rem;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

.explanation-label {
  font-weight: 600;
  color: var(--color-text);
}
</style>
