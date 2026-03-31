<template>
  <div class="chat-room-container">
    <div class="sidebar">
      <div class="sidebar-header">
        <h3>微流控AI助手</h3>
        <el-button type="primary" @click="createNewChat" size="small">
          <el-icon><Plus /></el-icon>
          新对话
        </el-button>
      </div>
      <div class="conversation-list">
        <div
          v-for="conv in chatStore.conversations"
          :key="conv.id"
          :class="['conversation-item', { active: conv.id === chatStore.currentConversationId }]"
          @click="chatStore.selectConversation(conv.id)"
        >
          <span class="conversation-title">{{ conv.title }}</span>
          <el-button
            link
            type="danger"
            size="small"
            @click.stop="deleteConversation(conv.id)"
          >
            <el-icon><Delete /></el-icon>
          </el-button>
        </div>
      </div>
      <div class="sidebar-footer">
        <el-button @click="goToConfig" link>
          <el-icon><Setting /></el-icon>
          API 配置
        </el-button>
      </div>
    </div>

    <div class="main-content">
      <div class="chat-header">
        <h2>AI 对话</h2>
        <div class="header-actions">
          <el-button
            v-if="chatStore.isStreaming"
            type="danger"
            @click="chatStore.stopGeneration"
          >
            <el-icon><VideoPause /></el-icon>
            停止生成
          </el-button>
          <el-button @click="chatStore.clearCurrentConversation" link>
            <el-icon><Delete /></el-icon>
            清空对话
          </el-button>
        </div>
      </div>

      <div class="messages-container" ref="messagesContainer">
        <div v-if="chatStore.currentMessages.length === 0" class="empty-state">
          <el-icon :size="80" color="#d1d5db"><ChatDotRound /></el-icon>
          <p>开始一段新的对话吧！</p>
        </div>
        <div v-else class="messages-list">
          <MessageBubble
            v-for="message in chatStore.currentMessages"
            :key="message.id"
            :message="message"
          />
        </div>
      </div>

      <ChatInput :isLoading="chatStore.isLoading" @send="handleSendMessage" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  Plus,
  Delete,
  Setting,
  VideoPause,
  ChatDotRound
} from '@element-plus/icons-vue'
import { useChatStore } from '@/stores/chat'
import { useApiConfigStore } from '@/stores/apiConfig'
import MessageBubble from '@/components/MessageBubble.vue'
import ChatInput from '@/components/ChatInput.vue'

const router = useRouter()
const chatStore = useChatStore()
const apiConfigStore = useApiConfigStore()
const messagesContainer = ref<HTMLElement | null>(null)

async function handleSendMessage(content: string) {
  if (!apiConfigStore.getCurrentApiKey()) {
    ElMessageBox.alert('请先配置 API 密钥', '提示', {
      confirmButtonText: '去配置',
      callback: () => {
        router.push('/config')
      }
    })
    return
  }
  await chatStore.sendMessage(content)
}

function createNewChat() {
  chatStore.createConversation()
}

async function deleteConversation(id: string) {
  try {
    await ElMessageBox.confirm('确定要删除这个对话吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    chatStore.deleteConversation(id)
  } catch {
  }
}

function goToConfig() {
  router.push('/config')
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 监听消息数组变化，触发滚动
watch(() => chatStore.currentMessages, () => {
  scrollToBottom()
}, { deep: true })

// 监听流式消息内容变化，确保实时滚动
watch(() => {
  const messages = chatStore.currentMessages
  const lastMessage = messages[messages.length - 1]
  // 返回流式消息的内容作为监听目标
  return lastMessage?.isStreaming ? lastMessage.content : null
}, (newContent, oldContent) => {
  // 内容变化时滚动到底部
  if (newContent !== null && newContent !== oldContent) {
    scrollToBottom()
  }
})

onMounted(() => {
  apiConfigStore.loadConfig()
  chatStore.loadConversations()
  
  if (chatStore.conversations.length === 0) {
    chatStore.createConversation()
  }
})
</script>

<style scoped lang="scss">
.chat-room-container {
  display: flex;
  height: 100vh;
  background: #f3f4f6;
}

.sidebar {
  width: 280px;
  background: white;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;

  .sidebar-header {
    padding: 20px;
    border-bottom: 1px solid #e5e7eb;

    h3 {
      margin: 0 0 16px 0;
      font-size: 18px;
      color: #1f2937;
    }
  }

  .conversation-list {
    flex: 1;
    overflow-y: auto;
    padding: 12px;

    .conversation-item {
      padding: 12px 16px;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 4px;
      transition: background 0.2s;

      &:hover {
        background: #f3f4f6;
      }

      &.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
      }

      .conversation-title {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 14px;
      }
    }
  }

  .sidebar-footer {
    padding: 16px;
    border-top: 1px solid #e5e7eb;
  }
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-header {
  padding: 16px 24px;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;

  h2 {
    margin: 0;
    font-size: 18px;
    color: #1f2937;
  }

  .header-actions {
    display: flex;
    gap: 12px;
  }
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #9ca3af;

    p {
      margin-top: 16px;
      font-size: 16px;
    }
  }

  .messages-list {
    max-width: 900px;
    margin: 0 auto;
  }
}
</style>
