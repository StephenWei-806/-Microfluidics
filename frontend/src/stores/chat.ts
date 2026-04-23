import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Conversation, Message } from '@/types'
import { apiClient, createEventSource, type EventSourceCallbacks } from '@/api'
import { useApiConfigStore } from './apiConfig'

function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substr(2)
}

const STORAGE_KEY = 'microfluidic_conversations'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<Conversation[]>([])
  const currentConversationId = ref<string | null>(null)
  const isLoading = ref(false)
  const isStreaming = ref(false)
  const error = ref<string | null>(null)
  const eventSource = ref<EventSource | null>(null)

  const currentConversation = computed(() => {
    return conversations.value.find(c => c.id === currentConversationId.value)
  })

  const currentMessages = computed(() => {
    return currentConversation.value?.messages || []
  })

  function loadConversations() {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        conversations.value = JSON.parse(saved)
        if (conversations.value.length > 0 && !currentConversationId.value) {
          currentConversationId.value = conversations.value[0].id
        }
      } catch {
        // 静默处理本地对话数据解析失败
      }
    }
  }

  function saveConversations() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.value))
  }

  function createConversation(): string {
    const conversation: Conversation = {
      id: generateId(),
      title: '新对话',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
    conversations.value.unshift(conversation)
    currentConversationId.value = conversation.id
    saveConversations()
    return conversation.id
  }

  function selectConversation(id: string) {
    currentConversationId.value = id
  }

  function deleteConversation(id: string) {
    const index = conversations.value.findIndex(c => c.id === id)
    if (index !== -1) {
      conversations.value.splice(index, 1)
      if (currentConversationId.value === id) {
        currentConversationId.value = conversations.value[0]?.id || null
      }
      saveConversations()
    }
  }

  async function sendMessage(content: string): Promise<void> {
    const apiConfig = useApiConfigStore()

    if (!currentConversationId.value) {
      createConversation()
    }

    const conversation = currentConversation.value
    if (!conversation) return

    isLoading.value = true
    error.value = null

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content,
      timestamp: Date.now()
    }

    conversation.messages.push(userMessage)

    const assistantMessage: Message = {
      id: generateId(),
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
      isStreaming: true
    }
    const assistantMessageIndex = conversation.messages.length
    conversation.messages.push(assistantMessage)

    if (conversation.messages.length === 2) {
      conversation.title = content.slice(0, 30) + (content.length > 30 ? '...' : '')
    }

    conversation.updatedAt = Date.now()
    saveConversations()

    try {
      isStreaming.value = true

      // 1. 初始化流式请求，获取 stream_id
      const streamId = await apiClient.initStream({
        api_name: apiConfig.config.currentApi,
        model: apiConfig.config.modelConfig.model,
        prompt: content,
        max_tokens: apiConfig.config.modelConfig.maxTokens,
        temperature: apiConfig.config.modelConfig.temperature
      })

      // 2. 创建 EventSource 连接
      const callbacks: EventSourceCallbacks = {
        onMessage: (chunk) => {
          // 从 chunk.choices[0].delta.content 取出内容
          const deltaContent = chunk.choices?.[0]?.delta?.content
          if (deltaContent) {
            // 通过数组索引直接替换对象，确保Vue响应性追踪
            const currentMessage = conversation.messages[assistantMessageIndex]
            if (currentMessage) {
              conversation.messages[assistantMessageIndex] = {
                ...currentMessage,
                content: currentMessage.content + deltaContent
              }
            }
            // 触发Vue响应性更新 - 通过更新时间戳
            conversation.updatedAt = Date.now()
          }
        },
        onComplete: () => {
          const currentMessage = conversation.messages[assistantMessageIndex]
          if (currentMessage) {
            conversation.messages[assistantMessageIndex] = {
              ...currentMessage,
              isStreaming: false
            }
          }
          isLoading.value = false
          isStreaming.value = false
          eventSource.value = null
          conversation.updatedAt = Date.now()
          saveConversations()
        },
        onError: (errorMsg) => {
          error.value = errorMsg
          const currentMessage = conversation.messages[assistantMessageIndex]
          if (currentMessage) {
            conversation.messages[assistantMessageIndex] = {
              ...currentMessage,
              content: currentMessage.content + `\n[错误: ${errorMsg}]`,
              isStreaming: false
            }
          }
          isLoading.value = false
          isStreaming.value = false
          eventSource.value = null
          conversation.updatedAt = Date.now()
          saveConversations()
        }
      }

      eventSource.value = createEventSource(streamId, callbacks)

    } catch (err) {
      error.value = err instanceof Error ? err.message : '发送失败'
      const currentMessage = conversation.messages[assistantMessageIndex]
      if (currentMessage) {
        conversation.messages[assistantMessageIndex] = {
          ...currentMessage,
          content: error.value,
          isStreaming: false
        }
      }
      isLoading.value = false
      isStreaming.value = false
      conversation.updatedAt = Date.now()
      saveConversations()
    }
  }

  function stopGeneration() {
    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
    }
    isLoading.value = false
    isStreaming.value = false

    const conversation = currentConversation.value
    if (conversation) {
      const lastMessage = conversation.messages[conversation.messages.length - 1]
      if (lastMessage && lastMessage.isStreaming) {
        lastMessage.isStreaming = false
      }
      conversation.updatedAt = Date.now()
      saveConversations()
    }
  }

  function clearCurrentConversation() {
    const conversation = currentConversation.value
    if (conversation) {
      conversation.messages = []
      conversation.updatedAt = Date.now()
      saveConversations()
    }
  }

  return {
    conversations,
    currentConversationId,
    currentConversation,
    currentMessages,
    isLoading,
    isStreaming,
    error,
    loadConversations,
    createConversation,
    selectConversation,
    deleteConversation,
    sendMessage,
    stopGeneration,
    clearCurrentConversation
  }
})
