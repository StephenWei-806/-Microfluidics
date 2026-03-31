<template>
  <div :class="['message-bubble', { 'user-message': message.role === 'user', 'assistant-message': message.role === 'assistant' }]">
    <div v-if="message.role === 'assistant'" class="avatar">
      <el-icon :size="32"><ChatDotRound /></el-icon>
    </div>
    <div class="message-content">
      <!-- 流式传输中：显示纯文本 + 打字机光标 -->
      <div v-if="message.isStreaming" class="content-text streaming-mode">
        <span class="streaming-text">{{ message.content }}</span>
        <span class="typing-cursor"></span>
      </div>
      <!-- 流式完成后：渲染 Markdown -->
      <div v-else class="content-text" v-html="renderedContent" ref="messageContentRef"></div>
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
import { computed, watch, nextTick, ref, onUnmounted, onMounted } from 'vue'
import { ChatDotRound, DocumentCopy, Close, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { Message } from '@/types'
import { marked, type RendererObject } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import mermaid from 'mermaid'

// 初始化 mermaid
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
})

// 配置 marked 使用自定义 renderer（兼容 marked v12 API）
marked.use({
  renderer: {
    code(code: string, infostring: string | undefined, _escaped: boolean): string {
      const lang = (infostring ?? '').split(/\s+/)[0]
      if (lang === 'mermaid') {
        // mermaid 代码块输出特殊容器，源码 HTML 转义后放入
        const escaped = code
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
        return `<div class="mermaid-container"><pre class="mermaid">${escaped}</pre></div>`
      }
      // 其他语言使用 highlight.js 高亮
      const language = hljs.getLanguage(lang) ? lang : 'plaintext'
      const highlighted = hljs.highlight(code, { language }).value
      return `<pre><code class="hljs language-${language}">${highlighted}</code></pre>`
    }
  } as RendererObject
})

// 消息内容容器的 ref
const messageContentRef = ref<HTMLElement>()

interface Props {
  message: Message
}

const props = defineProps<Props>()

// 模态框状态
const showModal = ref(false)
const modalSvgContent = ref('')

// 右键菜单状态
const showContextMenu = ref(false)
const contextMenuPosition = ref({ x: 0, y: 0 })
const currentSvgElement = ref<HTMLElement | null>(null)

// 存储事件监听器的清理函数
const cleanupFunctions: (() => void)[] = []

const renderedContent = computed(() => {
  if (props.message.isStreaming) {
    return ''
  }
  return marked(props.message.content) as string
})

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

// 将SVG转换为Canvas
async function svgToCanvas(svgElement: HTMLElement): Promise<HTMLCanvasElement> {
  // 克隆 SVG 以避免修改原始 DOM
  const clonedSvg = svgElement.cloneNode(true) as SVGSVGElement

  // 确保有 xmlns 属性
  if (!clonedSvg.getAttribute('xmlns')) {
    clonedSvg.setAttribute('xmlns', 'http://www.w3.org/2000/svg')
  }
  // 确保 xlink namespace
  if (!clonedSvg.getAttribute('xmlns:xlink')) {
    clonedSvg.setAttribute('xmlns:xlink', 'http://www.w3.org/1999/xlink')
  }

  // 获取实际尺寸
  const svgRect = svgElement.getBoundingClientRect()
  const width = svgRect.width || parseInt(clonedSvg.getAttribute('width') || '800')
  const height = svgRect.height || parseInt(clonedSvg.getAttribute('height') || '600')

  // 设置显式宽高
  clonedSvg.setAttribute('width', String(width))
  clonedSvg.setAttribute('height', String(height))

  // 收集并内联计算样式（将所有相关 CSS 嵌入 SVG）
  const styleElement = document.createElement('style')
  const cssRules: string[] = []
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules) {
        cssRules.push(rule.cssText)
      }
    } catch {
      // 跨域样式表会抛出错误，忽略即可
    }
  }
  styleElement.textContent = cssRules.join('\n')
  clonedSvg.insertBefore(styleElement, clonedSvg.firstChild)

  // 使用 data URL 方式，比 Blob URL 更可靠
  const svgData = new XMLSerializer().serializeToString(clonedSvg)
  const svgDataUrl = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgData)

  // 计算满足最小分辨率要求的缩放因子
  const MIN_LONG_SIDE = 1920
  const MIN_SHORT_SIDE = 720

  let targetWidth: number
  let targetHeight: number

  if (width >= height) {
    // 横向图表
    targetWidth = Math.max(MIN_LONG_SIDE, width)
    targetHeight = targetWidth * (height / width)
    if (targetHeight < MIN_SHORT_SIDE) {
      targetHeight = MIN_SHORT_SIDE
      targetWidth = targetHeight * (width / height)
    }
  } else {
    // 纵向图表
    targetHeight = Math.max(MIN_LONG_SIDE, height)
    targetWidth = targetHeight * (width / height)
    if (targetWidth < MIN_SHORT_SIDE) {
      targetWidth = MIN_SHORT_SIDE
      targetHeight = targetWidth * (height / width)
    }
  }

  const scale = Math.max(2, targetWidth / width, targetHeight / height)

  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => {
      const canvas = document.createElement('canvas')
      canvas.width = Math.round(width * scale)
      canvas.height = Math.round(height * scale)

      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('无法获取 canvas 上下文'))
        return
      }

      // 填充白色背景
      ctx.fillStyle = 'white'
      ctx.fillRect(0, 0, canvas.width, canvas.height)
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      resolve(canvas)
    }
    img.onerror = (e) => {
      console.error('SVG 图片加载失败:', e)
      reject(new Error('SVG 图片加载失败'))
    }
    img.src = svgDataUrl
  })
}

// 复制图表到剪贴板
async function copyChart() {
  if (!currentSvgElement.value) return

  try {
    const canvas = await svgToCanvas(currentSvgElement.value)
    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((b) => {
        if (b) {
          resolve(b)
        } else {
          reject(new Error('Canvas toBlob 返回空'))
        }
      }, 'image/png')
    })

    // 检查是否支持 ClipboardItem API
    if (typeof ClipboardItem !== 'undefined') {
      await navigator.clipboard.write([
        new ClipboardItem({ 'image/png': blob })
      ])
      ElMessage.success('图表已复制到剪贴板')
    } else {
      ElMessage.warning('当前浏览器不支持复制图片，请使用下载功能')
    }
  } catch (err) {
    console.error('复制图表失败:', err)
    ElMessage.error('复制失败，请使用下载功能')
  } finally {
    closeContextMenu()
  }
}

// 下载图表为PNG
async function downloadChart() {
  if (!currentSvgElement.value) return

  try {
    const canvas = await svgToCanvas(currentSvgElement.value)
    const dataUrl = canvas.toDataURL('image/png')

    const link = document.createElement('a')
    link.href = dataUrl
    link.download = 'mermaid-chart.png'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('图表已下载')
  } catch (err) {
    console.error('下载图表失败:', err)
    ElMessage.error('下载失败')
  } finally {
    closeContextMenu()
  }
}

// 为mermaid容器添加事件监听（限定在当前组件范围内）
function addMermaidEventListeners() {
  // 先清理旧的事件监听器
  cleanupFunctions.forEach(fn => fn())
  cleanupFunctions.length = 0

  // 限定在当前消息内容容器内查找
  const containers = messageContentRef.value?.querySelectorAll<HTMLElement>('.mermaid-container') ?? []
  containers.forEach((container) => {
    const svg = container.querySelector('svg')
    if (!svg) return

    // 添加点击事件
    const handleClick = () => {
      openModal(svg.outerHTML)
    }
    container.addEventListener('click', handleClick)
    container.style.cursor = 'pointer'

    // 添加右键事件
    const handleContextMenu = (e: MouseEvent) => {
      showContextMenuAt(e, svg as unknown as HTMLElement)
    }
    container.addEventListener('contextmenu', handleContextMenu)

    // 存储清理函数
    cleanupFunctions.push(() => {
      container.removeEventListener('click', handleClick)
      container.removeEventListener('contextmenu', handleContextMenu)
      container.style.cursor = ''
    })
  })
}

// 监听文档点击以关闭右键菜单
function handleDocumentClick() {
  closeContextMenu()
}

document.addEventListener('click', handleDocumentClick)
cleanupFunctions.push(() => {
  document.removeEventListener('click', handleDocumentClick)
})

// 渲染 mermaid 图表的核心逻辑（限定在当前组件范围内）
async function renderMermaidCharts() {
  if (!messageContentRef.value) return

  await nextTick()
  try {
    // 只渲染当前消息内容容器内的 mermaid 元素
    const nodes = messageContentRef.value.querySelectorAll('.mermaid')
    if (nodes.length > 0) {
      await mermaid.run({
        nodes: Array.from(nodes) as HTMLElement[]
      })
    }
    // 渲染成功后，为当前消息的 mermaid 容器添加交互事件
    addMermaidEventListeners()
  } catch (err) {
    console.error('Mermaid 渲染失败:', err)
    // 渲染失败时降级：将 .mermaid 元素内容替换为高亮源码显示
    const containers = messageContentRef.value?.querySelectorAll<HTMLElement>('.mermaid-container') ?? []
    containers.forEach((container) => {
      const pre = container.querySelector('.mermaid')
      if (pre && !pre.querySelector('svg')) {
        const rawCode = pre.textContent ?? ''
        const highlighted = hljs.highlight(rawCode, { language: 'plaintext' }).value
        container.innerHTML = `<pre class="mermaid-fallback"><code class="hljs">${highlighted}</code></pre>`
      }
    })
  }
}

// 当流式传输完成后，渲染 mermaid 图表
watch(
  () => props.message.isStreaming,
  async (isStreaming) => {
    if (!isStreaming) {
      await renderMermaidCharts()
    }
  }
)

// 组件挂载时，如果消息已完成（从 localStorage 加载的情况），立即渲染 mermaid
onMounted(async () => {
  if (!props.message.isStreaming) {
    await renderMermaidCharts()
  }
})

function copyMessage() {
  navigator.clipboard.writeText(props.message.content)
  ElMessage.success('已复制到剪贴板')
}

// 组件卸载时清理所有事件监听器
onUnmounted(() => {
  cleanupFunctions.forEach(fn => fn())
  cleanupFunctions.length = 0
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
