<script setup>
import { computed, onMounted, ref } from 'vue'
import {
  addReaderVocabulary,
  downloadReaderVocabularyCsv,
  importReaderPdf,
  importReaderText,
  listReaderVocabulary,
} from '../api/index.js'
import StatusMessage from '../components/StatusMessage.vue'
import LoadingState from '../components/LoadingState.vue'

const DEMO_TEXT = `Climate change is a pressing challenge for governments, industry, and communities worldwide. Research shows that significant technology investment can transform energy systems, but people also need vocabulary and context to understand public debates.`

const rawText = ref(DEMO_TEXT)
const selectedFile = ref(null)
const importMode = ref('text')
const loading = ref(false)
const vocabLoading = ref(false)
const error = ref('')
const success = ref('')
const document = ref(null)
const vocabularyItems = ref([])
const addedWords = ref(new Set())

const keywords = computed(() => document.value?.keywords || [])

const highlightedSegments = computed(() => {
  const text = document.value?.raw_text || ''
  if (!text || keywords.value.length === 0) return [{ text, keyword: null }]

  const keywordMap = new Map(keywords.value.map((kw) => [kw.text.toLowerCase(), kw]))
  const escaped = keywords.value
    .map((kw) => kw.text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .sort((a, b) => b.length - a.length)
  const pattern = new RegExp(`\\b(${escaped.join('|')})\\b`, 'gi')
  const segments = []
  let lastIndex = 0
  for (const match of text.matchAll(pattern)) {
    if (match.index > lastIndex) {
      segments.push({ text: text.slice(lastIndex, match.index), keyword: null })
    }
    const word = match[0]
    segments.push({ text: word, keyword: keywordMap.get(word.toLowerCase()) || null })
    lastIndex = match.index + word.length
  }
  if (lastIndex < text.length) {
    segments.push({ text: text.slice(lastIndex), keyword: null })
  }
  return segments
})

function onFileChange(event) {
  selectedFile.value = event.target.files?.[0] || null
  if (selectedFile.value) {
    importMode.value = 'pdf'
  }
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const result = String(reader.result || '')
      resolve(result.includes(',') ? result.split(',')[1] : result)
    }
    reader.onerror = () => reject(new Error('PDF 文件读取失败'))
    reader.readAsDataURL(file)
  })
}

async function handleImport() {
  loading.value = true
  error.value = ''
  success.value = ''
  try {
    if (importMode.value === 'pdf') {
      if (!selectedFile.value) {
        throw new Error('请先选择英文 PDF 文件。')
      }
      const contentBase64 = await fileToBase64(selectedFile.value)
      document.value = await importReaderPdf({
        file_name: selectedFile.value.name,
        content_base64: contentBase64,
        max_keywords: 8,
      })
    } else {
      if (!rawText.value.trim()) {
        throw new Error('请粘贴一段英文文本。')
      }
      document.value = await importReaderText({
        raw_text: rawText.value.trim(),
        max_keywords: 8,
      })
    }
    success.value = '正文解析完成，已生成重点词汇和高亮。'
  } catch (e) {
    error.value = e.message || '导入失败'
  } finally {
    loading.value = false
  }
}

async function addKeyword(kw) {
  if (!document.value || addedWords.value.has(kw.text)) return
  error.value = ''
  success.value = ''
  try {
    await addReaderVocabulary({
      text: kw.text,
      meaning_zh: kw.meaning_zh,
      usage_note: kw.usage_note,
      ability: kw.ability,
      source_document_id: document.value.document_id,
      source_context: document.value.raw_text.slice(0, 240),
    })
    addedWords.value = new Set([...addedWords.value, kw.text])
    success.value = `已将 ${kw.text} 加入词汇本。`
    await loadVocabulary()
  } catch (e) {
    error.value = e.message || '加入词汇本失败'
  }
}

async function loadVocabulary() {
  vocabLoading.value = true
  try {
    const result = await listReaderVocabulary()
    vocabularyItems.value = result.items || []
    addedWords.value = new Set(vocabularyItems.value.map((item) => item.text))
  } catch (e) {
    error.value = e.message || '词汇本加载失败'
  } finally {
    vocabLoading.value = false
  }
}

async function exportVocabulary() {
  error.value = ''
  success.value = ''
  try {
    const blob = await downloadReaderVocabularyCsv()
    const url = URL.createObjectURL(blob)
    const link = window.document.createElement('a')
    link.href = url
    link.download = 'lingoforge-vocabulary.csv'
    link.click()
    URL.revokeObjectURL(url)
    success.value = '词汇表 CSV 已开始下载。'
  } catch (e) {
    error.value = e.message || '导出失败'
  }
}

onMounted(loadVocabulary)
</script>

<template>
  <div class="reader-page">
    <div class="page-heading">
      <div>
        <h1>阅读导入与词汇本</h1>
        <p>导入英文 PDF 或文本，解析正文，查看高亮释义，并沉淀到个人词汇本。</p>
      </div>
      <button class="btn-secondary" :disabled="vocabularyItems.length === 0" @click="exportVocabulary">
        导出词汇表 CSV
      </button>
    </div>

    <StatusMessage v-if="error" type="error" :message="error" class="status" />
    <StatusMessage v-if="success" type="success" :message="success" class="status" />

    <div class="reader-grid">
      <section class="panel import-panel">
        <h2>导入材料</h2>
        <div class="mode-tabs" role="group" aria-label="导入方式">
          <button
            type="button"
            class="mode-tab"
            :class="{ active: importMode === 'text' }"
            @click="importMode = 'text'"
          >
            英文文本
          </button>
          <button
            type="button"
            class="mode-tab"
            :class="{ active: importMode === 'pdf' }"
            @click="importMode = 'pdf'"
          >
            英文 PDF
          </button>
        </div>

        <textarea
          v-if="importMode === 'text'"
          v-model="rawText"
          class="text-input"
          rows="12"
          placeholder="粘贴英文正文..."
        />

        <label v-else class="file-drop">
          <input type="file" accept="application/pdf,.pdf" @change="onFileChange" />
          <span class="file-title">{{ selectedFile?.name || '选择英文 PDF 文件' }}</span>
          <span class="file-note">系统会提取可复制文本；扫描图片 PDF 需要先 OCR。</span>
        </label>

        <button class="btn-primary" :disabled="loading" @click="handleImport">
          {{ loading ? '解析中...' : '解析并生成重点词汇' }}
        </button>
      </section>

      <section class="panel reading-panel">
        <div class="panel-header">
          <h2>正文阅读</h2>
          <span v-if="document" class="meta-chip">
            {{ document.source_type === 'PDF' ? document.file_name : '文本导入' }}
          </span>
        </div>

        <LoadingState v-if="loading" message="正在解析正文..." />

        <div v-else-if="document" class="reader-body" aria-label="已解析正文">
          <template v-for="(segment, index) in highlightedSegments" :key="index">
            <mark
              v-if="segment.keyword"
              class="highlight"
              :title="segment.keyword.meaning_zh"
              tabindex="0"
            >
              {{ segment.text }}
              <span class="tooltip">
                <strong>{{ segment.keyword.text }}</strong>
                <span>{{ segment.keyword.meaning_zh }}</span>
                <small>{{ segment.keyword.usage_note }}</small>
              </span>
            </mark>
            <span v-else>{{ segment.text }}</span>
          </template>
        </div>

        <div v-else class="empty-reader">
          导入英文 PDF 或文本后，正文会显示在这里，重点词汇会被高亮。
        </div>
      </section>

      <aside class="side-column">
        <section class="panel">
          <h2>重点词汇</h2>
          <div v-if="keywords.length > 0" class="keyword-list">
            <article v-for="kw in keywords" :key="kw.text" class="keyword-card">
              <div>
                <strong>{{ kw.text }}</strong>
                <p>{{ kw.meaning_zh }}</p>
                <small>{{ kw.usage_note }}</small>
              </div>
              <button
                class="btn-small"
                :disabled="addedWords.has(kw.text)"
                @click="addKeyword(kw)"
              >
                {{ addedWords.has(kw.text) ? '已加入' : '加入词汇本' }}
              </button>
            </article>
          </div>
          <p v-else class="muted">解析后会在这里显示重点词汇和词组。</p>
        </section>

        <section class="panel vocabulary-panel">
          <div class="panel-header">
            <h2>我的词汇本</h2>
            <span class="meta-chip">{{ vocabularyItems.length }} 个</span>
          </div>
          <LoadingState v-if="vocabLoading" message="正在加载词汇本..." />
          <div v-else-if="vocabularyItems.length > 0" class="book-list">
            <article v-for="item in vocabularyItems" :key="item.id" class="book-item">
              <strong>{{ item.text }}</strong>
              <span>{{ item.meaning_zh }}</span>
              <small v-if="item.usage_note">{{ item.usage_note }}</small>
            </article>
          </div>
          <p v-else class="muted">还没有加入词汇。点击重点词汇旁的按钮即可保存。</p>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.reader-page {
  max-width: 1280px;
}

.page-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 20px;
}

.page-heading p,
.muted {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.status {
  margin-bottom: 14px;
}

.reader-grid {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr) 340px;
  gap: 18px;
  align-items: start;
}

.panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.import-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.mode-tabs {
  display: flex;
  padding: 4px;
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.mode-tab {
  flex: 1;
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  font-weight: 600;
}

.mode-tab.active {
  background: var(--color-surface);
  color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}

.text-input {
  width: 100%;
  min-height: 260px;
  padding: 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text);
  font: inherit;
  line-height: 1.7;
  resize: vertical;
}

.text-input:focus {
  border-color: var(--color-primary);
  outline: none;
}

.file-drop {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  min-height: 180px;
  padding: 20px;
  border: 1.5px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg);
  cursor: pointer;
}

.file-drop input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.file-drop:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-bg);
}

.file-title {
  font-weight: 700;
  color: var(--color-text);
}

.file-note {
  color: var(--color-text-muted);
  font-size: 0.84rem;
}

.reading-panel {
  min-height: 620px;
}

.reader-body {
  min-height: 540px;
  max-height: 720px;
  overflow: auto;
  white-space: pre-wrap;
  padding: 22px;
  border-radius: var(--radius-md);
  background: #fff;
  border: 1px solid var(--color-border-light);
  color: var(--color-text);
  font-size: 1rem;
  line-height: 1.9;
}

.highlight {
  position: relative;
  padding: 1px 4px;
  border-radius: 5px;
  background: #fff1a8;
  color: #3d3411;
  cursor: help;
}

.highlight:focus .tooltip,
.highlight:focus-within .tooltip,
.highlight:hover .tooltip {
  display: grid;
}

.tooltip {
  position: absolute;
  z-index: 20;
  left: 0;
  bottom: calc(100% + 8px);
  display: none;
  width: 260px;
  gap: 4px;
  padding: 10px 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  box-shadow: var(--shadow-lg);
  color: var(--color-text);
  white-space: normal;
}

.tooltip small {
  color: var(--color-text-secondary);
}

.empty-reader {
  display: grid;
  place-items: center;
  min-height: 540px;
  padding: 24px;
  border-radius: var(--radius-md);
  background: var(--color-bg);
  color: var(--color-text-muted);
  text-align: center;
}

.keyword-list,
.book-list,
.side-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.keyword-card,
.book-item {
  padding: 12px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  background: var(--color-bg);
}

.keyword-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 10px;
}

.keyword-card p,
.book-item span {
  display: block;
  color: var(--color-text);
  font-weight: 600;
}

.keyword-card small,
.book-item small {
  display: block;
  color: var(--color-text-muted);
  font-size: 0.8rem;
  line-height: 1.5;
}

.meta-chip {
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--color-primary-bg);
  color: var(--color-primary);
  font-size: 0.8rem;
  font-weight: 700;
}

.btn-primary,
.btn-secondary,
.btn-small {
  border-radius: var(--radius-btn);
  font-weight: 700;
}

.btn-primary {
  padding: 10px 18px;
  background: var(--color-primary);
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}

.btn-secondary {
  padding: 9px 15px;
  background: var(--color-surface);
  color: var(--color-primary);
  border: 1px solid var(--color-primary-light);
}

.btn-small {
  padding: 7px 10px;
  background: var(--color-primary-bg);
  color: var(--color-primary);
}

.btn-small:hover:not(:disabled) {
  background: var(--color-primary-bg-hover);
}

@media (max-width: 1180px) {
  .reader-grid {
    grid-template-columns: 1fr;
  }

  .reading-panel {
    min-height: auto;
  }
}

@media (max-width: 720px) {
  .page-heading {
    flex-direction: column;
  }
}
</style>
