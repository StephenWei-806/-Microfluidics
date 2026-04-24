<template>
  <div :class="['message-bubble', { 'user-message': message.role === 'user', 'assistant-message': message.role === 'assistant' }]">
    <div v-if="message.role === 'assistant'" class="avatar">
      <el-icon :size="32"><ChatDotRound /></el-icon>
    </div>
    <div class="message-content">
      <!-- 思维链折叠面板 - 仅当有 reasoningContent 时显示 -->
      <div v-if="hasReasoningContent" class="reasoning-panel">
        <div class="reasoning-header" @click="reasoningExpanded = !reasoningExpanded">
          <span v-if="message.isStreaming && !message.content" class="reasoning-status">思考中...</span>
          <el-icon class="reasoning-arrow" :class="{ expanded: reasoningExpanded }">
            <ArrowRight />
          </el-icon>
        </div>
        <div v-show="reasoningExpanded" class="reasoning-body">
          <div class="reasoning-content" v-html="renderedReasoningContent"></div>
        </div>
      </div>
      <!-- 流式传输中：分段渲染，支持实时显示已完成的 mermaid 块 -->
      <div v-if="message.isStreaming" class="content-text streaming-mode">
        <template v-for="(seg, idx) in streamSegments" :key="idx">
          <div v-if="seg.type === 'text'" v-html="seg.rendered"></div>
          <div v-else-if="seg.type === 'mermaid' && seg.rendered && !seg.renderError" 
               class="mermaid-container" v-html="seg.rendered"></div>
          <div v-else-if="seg.type === 'mermaid' && seg.renderError"
               class="mermaid-container">
            <div class="mermaid-error-hint">⚠ 图表语法错误，已降级显示源码</div>
            <pre class="mermaid-fallback"><code class="hljs" v-html="seg.rendered || escapeHtml(seg.content)"></code></pre>
          </div>
          <div v-else-if="seg.type === 'mermaid'" class="mermaid-container mermaid-loading">
            <span>图表渲染中...</span>
          </div>
        </template>
        <!-- 未闭合的尾部文本 -->
        <span class="streaming-text">{{ trailingStreamText }}</span>
        <span class="typing-cursor"></span>
      </div>
      <!-- 流式完成后：分段渲染 Markdown 和 mermaid -->
      <div v-else class="content-text" ref="messageContentRef">
        <template v-for="(seg, idx) in finalSegments" :key="idx">
          <div v-if="seg.type === 'text'" v-html="seg.rendered"></div>
          <div v-else-if="seg.type === 'mermaid' && seg.rendered && !seg.renderError" 
               class="mermaid-container" v-html="seg.rendered"></div>
          <div v-else-if="seg.type === 'mermaid' && seg.renderError"
               class="mermaid-container">
            <div class="mermaid-error-hint">⚠ 图表语法错误，已降级显示源码</div>
            <pre class="mermaid-fallback"><code class="hljs" v-html="seg.rendered || escapeHtml(seg.content)"></code></pre>
          </div>
          <div v-else-if="seg.type === 'mermaid'"
               class="mermaid-container mermaid-loading">
            <span>图表渲染中...</span>
          </div>
        </template>
      </div>
      <div class="message-actions" v-if="!message.isStreaming">
        <el-button link type="primary" size="small" @click="copyMessage">
          <el-icon><DocumentCopy /></el-icon>
          复制
        </el-button>
      </div>
    </div>
  </div>

  <!-- 全屏模态框：放大查看图表 -->
  <Teleport to="body">
    <div v-if="showModal" class="mermaid-modal-overlay" @click="closeModal">
      <div class="mermaid-modal-container" @click.stop>
        <button class="mermaid-modal-close" @click="closeModal">
          <el-icon><Close /></el-icon>
        </button>
        <div class="mermaid-modal-content" v-html="modalSvgContent"></div>
      </div>
    </div>
  </Teleport>

  <!-- 右键上下文菜单 -->
  <Teleport to="body">
    <div
      v-if="showContextMenu"
      class="mermaid-context-menu"
      :style="{ left: `${contextMenuPosition.x}px`, top: `${contextMenuPosition.y}px` }"
    >
      <div class="mermaid-context-menu-item" @click="copyChart">
        <el-icon><DocumentCopy /></el-icon>
        <span>复制图表</span>
      </div>
      <div class="mermaid-context-menu-item" @click="downloadChart">
        <el-icon><Download /></el-icon>
        <span>下载图表</span>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { watch, nextTick, ref, onUnmounted, onMounted, computed } from 'vue'
import { ChatDotRound, DocumentCopy, Close, Download, ArrowRight } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import type { Message } from '@/types'
import 'highlight.js/styles/github.css'

import { parseContent, escapeHtml, hashContent } from './message/ContentParser'
import { renderAllMermaidSegments, addMermaidEventListeners } from './message/MermaidRenderer'
import { copyChart as copyChartImpl, downloadChart as downloadChartImpl } from './message/SvgExporter'
import type { ContentSegment } from './message/types'

// 消息内容容器的 ref
const messageContentRef = ref<HTMLElement>()

interface Props {
  message: Message
}

const props = defineProps<Props>()

// 折叠面板状态
const reasoningExpanded = ref(false)

// 是否有思维链内容
const hasReasoningContent = computed(() => {
  return !!props.message.reasoningContent && props.message.reasoningContent.trim().length > 0
})

// 渲染后的思维链内容（Markdown → HTML）
const renderedReasoningContent = computed(() => {
  if (!props.message.reasoningContent) return ''
  return marked(props.message.reasoningContent) as string
})

// 模态框状态
const showModal = ref(false)
const modalSvgContent = ref('')

// 右键菜单状态
const showContextMenu = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const currentSvgElement = ref<HTMLElement | null>(null)

// 存储事件监听器的清理函数
const cleanupFunctions: (() => void)[] = []

// document click 监听器清理函数（单独管理，避免被 addMermaidEventListeners 清理）
let documentClickCleanup: (() => void) | null = null

// 流式传输中的分段内容
const streamSegments = ref<ContentSegment[]>([])
// 流式传输中的尾部未闭合文本
const trailingStreamText = ref('')
// 流式完成后的最终分段内容
const finalSegments = ref<ContentSegment[]>([])
// 已渲染的 mermaid 块 content hash 集合，避免重复渲染
const renderedMermaidHashes = ref<Set<string>>(new Set())

// 流式更新互斥锁，防止并发渲染问题
let streamingUpdateLock = false
let pendingStreamingUpdate = false

// 流式更新防抖定时器
let streamingDebounceTimer: ReturnType<typeof setTimeout> | null = null

// 关闭模态框
function closeModal() {
  showModal.value = false
  modalSvgContent.value = ''
}

// 打开模态框
function openModal(svgHtml: string) {
  modalSvgContent.value = svgHtml
  showModal.value = true
}

// 显示右键菜单
function showContextMenuAt(event: MouseEvent, svgElement: HTMLElement) {
  event.preventDefault()
  currentSvgElement.value = svgElement
  contextMenuPosition.value = { x: event.clientX, y: event.clientY }
  showContextMenu.value = true
}

// 关闭右键菜单
function closeContextMenu() {
  showContextMenu.value = false
}

// 监听文档点击以关闭右键菜单
function handleDocumentClick() {
  closeContextMenu()
}

// 初始化文档点击监听（单独管理，不放入 cleanupFunctions）
document.addEventListener('click', handleDocumentClick)
documentClickCleanup = () => {
  document.removeEventListener('click', handleDocumentClick)
}

// 更新流式传输中的内容
async function updateStreamingContent() {
  // 互斥锁检查：如果已有更新在执行，标记待处理并返回
  if (streamingUpdateLock) {
    pendingStreamingUpdate = true
    return
  }
  streamingUpdateLock = true

  try {
    const { segments, hasUnclosedMermaid, trailingText } = parseContent(props.message.content)

    // 保留已处理的 mermaid 段落的渲染结果（包括成功渲染和降级显示的）
    const existingRendered = new Map<string, ContentSegment>()
    streamSegments.value.forEach(seg => {
      if (seg.type === 'mermaid' && (seg.rendered || seg.renderError)) {
        existingRendered.set(hashContent(seg.content), seg)
      }
    })

    // 合并新的段落和已渲染的结果
    streamSegments.value = segments.map(seg => {
      if (seg.type === 'mermaid') {
        const hash = hashContent(seg.content)
        const existing = existingRendered.get(hash)
        if (existing) {
          return { ...existing }
        }
      }
      return seg
    })

    trailingStreamText.value = hasUnclosedMermaid ? trailingText : ''

    // 渲染新出现的 mermaid 段落
    await nextTick()
    await renderAllMermaidSegments(streamSegments.value, renderedMermaidHashes.value)
    // 强制触发 Vue 响应式更新（渲染会修改 segment 内部属性，Vue 无法自动检测）
    streamSegments.value = [...streamSegments.value]
  } finally {
    streamingUpdateLock = false
    // 如果有待处理的更新，使用 nextTick 确保不会同步重入
    if (pendingStreamingUpdate) {
      pendingStreamingUpdate = false
      await nextTick()
      updateStreamingContent()
    }
  }
}

// 更新流式完成后的最终内容
async function updateFinalContent() {
  const { segments } = parseContent(props.message.content)
  
  // 保留已渲染的 mermaid 段落的渲染结果（同时从流式段落和最终段落中继承）
  const existingRendered = new Map<string, ContentSegment>()
  // 优先从流式阶段的段落中继承渲染结果（流式→最终的过渡场景）
  streamSegments.value.forEach(seg => {
    if (seg.type === 'mermaid' && (seg.rendered || seg.renderError)) {
      existingRendered.set(hashContent(seg.content), seg)
    }
  })
  // 再从已有的最终段落中查找（页面刷新后重新渲染的场景）
  finalSegments.value.forEach(seg => {
    if (seg.type === 'mermaid' && (seg.rendered || seg.renderError)) {
      existingRendered.set(hashContent(seg.content), seg)
    }
  })
  
  // 合并新的段落和已渲染的结果
  finalSegments.value = segments.map(seg => {
    if (seg.type === 'mermaid') {
      const hash = hashContent(seg.content)
      const existing = existingRendered.get(hash)
      if (existing) {
        return { ...existing }
      }
    }
    return seg
  })
  
  // 渲染所有 mermaid 段落
  await nextTick()
  await renderAllMermaidSegments(finalSegments.value, renderedMermaidHashes.value)
  // 强制触发 Vue 响应式更新
  finalSegments.value = [...finalSegments.value]

  // 添加事件监听
  await nextTick()
  addMermaidEventListeners(
    messageContentRef.value,
    {
      onClick: openModal,
      onContextMenu: showContextMenuAt
    },
    cleanupFunctions
  )
}

// 监听内容变化（流式传输中）
watch(
  () => props.message.content,
  () => {
    if (props.message.isStreaming) {
      // 防抖处理：仅在流式传输时添加 80ms 延迟，平衡实时性和性能
      if (streamingDebounceTimer) clearTimeout(streamingDebounceTimer)
      streamingDebounceTimer = setTimeout(() => {
        updateStreamingContent()
      }, 80)
    }
  },
  { immediate: true }
)

// 监听流式状态变化
watch(
  () => props.message.isStreaming,
  async (isStreaming, oldIsStreaming) => {
    if (oldIsStreaming === true && isStreaming === false) {
      // 流式结束，切换到最终渲染模式
      // 注意：先调用 updateFinalContent，再清空流式段落，
      // 以便 updateFinalContent 能继承流式阶段已渲染的 mermaid 结果
      await updateFinalContent()
      streamSegments.value = []
      trailingStreamText.value = ''
    }
  }
)

// 组件挂载时，如果消息已完成（从 localStorage 加载的情况），立即渲染
onMounted(async () => {
  if (!props.message.isStreaming) {
    await updateFinalContent()
  }
})

function copyMessage() {
  navigator.clipboard.writeText(props.message.content)
  ElMessage.success('已复制到剪贴板')
}

// 复制图表（包装函数，提供当前 SVG 元素和完成回调）
async function copyChart() {
  await copyChartImpl(currentSvgElement.value, closeContextMenu)
}

// 下载图表（包装函数，提供当前 SVG 元素和完成回调）
async function downloadChart() {
  await downloadChartImpl(currentSvgElement.value, closeContextMenu)
}

// 组件卸载时清理所有事件监听器
onUnmounted(() => {
  cleanupFunctions.forEach(fn => fn())
  cleanupFunctions.length = 0
  // 清理 document click 监听器
  if (documentClickCleanup) {
    documentClickCleanup()
    documentClickCleanup = null
  }
  // 清理防抖定时器
  if (streamingDebounceTimer) {
    clearTimeout(streamingDebounceTimer)
    streamingDebounceTimer = null
  }
})
</script>

<style scoped lang="scss">
.message-bubble {
  display: flex;
  margin-bottom: 20px;
  max-width: 85%;

  &.user-message {
    margin-left: auto;
    flex-direction: row-reverse;
  }

  &.assistant-message {
    margin-right: auto;
  }
}

.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  flex-shrink: 0;
  margin: 0 12px;
}

.message-content {
  background: white;
  border-radius: 12px;
  padding: 16px 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  position: relative;

  .user-message & {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
  }
}

.content-text {
  line-height: 1.6;
  word-wrap: break-word;

  :deep(code) {
    background: #f5f5f5;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
  }

  :deep(pre) {
    background: #f8f8f8;
    padding: 12px;
    border-radius: 8px;
    overflow-x: auto;

    code {
      background: none;
      padding: 0;
    }
  }

  .user-message & {
    :deep(code), :deep(pre) {
      background: rgba(255, 255, 255, 0.2);
    }
  }
}

.streaming-mode {
  white-space: pre-wrap;
}

.streaming-text {
  white-space: pre-wrap;
}

.typing-cursor {
  display: inline-block;
  width: 2px;
  height: 1em;
  background-color: currentColor;
  margin-left: 2px;
  vertical-align: text-bottom;
  animation: blink 1s step-end infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

// 思维链折叠面板样式
.reasoning-panel {
  margin-bottom: 12px;
  border: 1px solid #e8e8f0;
  border-radius: 8px;
  background: #f8f8fc;
  overflow: hidden;
  font-size: 14px;
}

.reasoning-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;

  &:hover {
    background: #ededf5;
  }
}

.reasoning-icon {
  font-size: 16px;
  line-height: 1;
}

.reasoning-title {
  font-weight: 500;
  color: #555;
  flex: 1;
}

.reasoning-status {
  color: #909399;
  font-size: 12px;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.reasoning-arrow {
  transition: transform 0.2s ease;
  color: #909399;
  font-size: 14px;

  &.expanded {
    transform: rotate(90deg);
  }
}

.reasoning-body {
  padding: 0 14px 12px;
  border-top: 1px solid #e8e8f0;
}

.reasoning-content {
  line-height: 1.6;
  color: #666;
  font-size: 13px;
  max-height: 400px;
  overflow-y: auto;
  padding-top: 10px;

  :deep(p) {
    margin: 0 0 8px;
  }

  :deep(code) {
    background: #eef;
    padding: 2px 5px;
    border-radius: 3px;
    font-size: 0.85em;
  }

  :deep(pre) {
    background: #f0f0f8;
    padding: 10px;
    border-radius: 6px;
    overflow-x: auto;

    code {
      background: none;
      padding: 0;
    }
  }

  :deep(ul), :deep(ol) {
    padding-left: 20px;
    margin: 4px 0;
  }

  :deep(blockquote) {
    margin: 4px 0;
    padding-left: 10px;
    border-left: 3px solid #d0d0e0;
    color: #888;
  }
}

.message-actions {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  opacity: 0;
  transition: opacity 0.2s;

  .message-bubble:hover & {
    opacity: 1;
  }
}

// Mermaid 图表容器样式
:deep(.mermaid-container) {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  margin: 10px 0;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow-x: auto;
  transition: box-shadow 0.2s ease;

  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  }

  .mermaid {
    display: flex;
    justify-content: center;

    svg {
      max-width: 100%;
      height: auto;
    }
  }

  // 用户消息（紫色背景）中的 mermaid 容器
  .user-message & {
    background: rgba(255, 255, 255, 0.15);
    border-color: rgba(255, 255, 255, 0.3);
  }
}

// mermaid 渲染失败降级样式
:deep(.mermaid-fallback) {
  background: #f8f8f8;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0;

  code {
    background: none;
    padding: 0;
    font-size: 0.85em;
  }
}

// mermaid 渲染错误提示样式
:deep(.mermaid-error-hint) {
  color: #e6a23c;
  font-size: 12px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}

// 全屏模态框样式
.mermaid-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 20px;
}

.mermaid-modal-container {
  background: white;
  border-radius: 12px;
  padding: 24px;
  max-width: 90vw;
  max-height: 90vh;
  overflow: auto;
  position: relative;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.mermaid-modal-close {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 36px;
  height: 36px;
  border: none;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s ease;
  color: #666;
  font-size: 18px;

  &:hover {
    background: rgba(0, 0, 0, 0.1);
    color: #333;
  }
}

.mermaid-modal-content {
  display: flex;
  justify-content: center;
  align-items: center;
  min-width: 200px;
  min-height: 100px;

  :deep(svg) {
    max-width: 100%;
    max-height: calc(90vh - 80px);
    height: auto;
  }
}

// 右键上下文菜单样式
.mermaid-context-menu {
  position: fixed;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  padding: 6px 0;
  z-index: 3000;
  min-width: 140px;
  border: 1px solid #e8e8e8;
}

.mermaid-context-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.15s ease;
  font-size: 14px;
  color: #333;

  &:hover {
    background: #f5f5f5;
  }

  .el-icon {
    font-size: 16px;
    color: #666;
  }
}
</style>
