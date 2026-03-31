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
import { computed } from 'vue'
import { ChatDotRound, DocumentCopy } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { Message } from '@/types'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

marked.setOptions({
  highlight: function(code, lang) {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext'
    return hljs.highlight(code, { language }).value
  }
})

interface Props {
  message: Message
}

const props = defineProps<Props>()

const renderedContent = computed(() => {
  // 只在非流式状态下进行 Markdown 解析
  if (props.message.isStreaming) {
    return ''
  }
  return marked(props.message.content)
})

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
</style>
