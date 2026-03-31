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
      <div v-else class="content-text" v-html="renderedContent"></div>
      <div class="message-actions" v-if="!message.isStreaming">
        <el-button link type="primary" size="small" @click="copyMessage">
          <el-icon><DocumentCopy /></el-icon>
          复制
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, watch, nextTick } from 'vue'
import { ChatDotRound, DocumentCopy } from '@element-plus/icons-vue'
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

interface Props {
  message: Message
}

const props = defineProps<Props>()

const renderedContent = computed(() => {
  if (props.message.isStreaming) {
    return ''
  }
  return marked(props.message.content) as string
})

// 当流式传输完成后，渲染 mermaid 图表
watch(
  () => props.message.isStreaming,
  async (isStreaming) => {
    if (!isStreaming) {
      await nextTick()
      try {
        await mermaid.run({
          querySelector: '.mermaid',
        })
      } catch (err) {
        // 渲染失败时降级：将 .mermaid 元素内容替换为高亮源码显示
        const containers = document.querySelectorAll<HTMLElement>('.mermaid-container')
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
  }
)

function copyMessage() {
  navigator.clipboard.writeText(props.message.content)
  ElMessage.success('已复制到剪贴板')
}
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
</style>
