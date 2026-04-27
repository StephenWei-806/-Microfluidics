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
      // 仅对支持工具调用的 API（OpenAI 兼容接口，如 deepseek）启用工具
      const isToolSupported = ['deepseek'].includes(apiConfig.config.currentApi)

      // 收集对话历史（排除刚添加的当前 userMessage 和 assistantMessage 占位消息，保留最近 N 条）
      const MAX_HISTORY_MESSAGES = 20
      const allHistory = conversation.messages.slice(0, assistantMessageIndex - 1)
      const start = Math.max(0, allHistory.length - MAX_HISTORY_MESSAGES)
      const historyMessages = allHistory
        .slice(start)
        .map(msg => ({ role: msg.role, content: msg.content }))

      const streamId = await apiClient.initStream({
        api_name: apiConfig.config.currentApi,
        model: apiConfig.config.modelConfig.model,
        prompt: content,
        messages: historyMessages,
        max_tokens: apiConfig.config.modelConfig.maxTokens,
        temperature: apiConfig.config.modelConfig.temperature,
        thinking_enabled: apiConfig.config.modelConfig.thinkingEnabled,
        reasoning_effort: apiConfig.config.modelConfig.reasoningEffort,
        tools_enabled: isToolSupported
      })

      // 2. 创建 EventSource 连接
      const callbacks: EventSourceCallbacks = {
        onMessage: (chunk) => {
          // 处理工具状态事件
          // 后端有两种 tool_status 消息：
          //   a) “正在执行: {tool_name}...”  → 起始信号，追加一条 executing 记录
          //   b) “工具 {tool_name} 执行完成”   → 志愿性完成信号，已由 tool_result 驱动，此处忽略
          if (chunk.type === 'tool_status') {
            const currentMessage = conversation.messages[assistantMessageIndex]
            if (currentMessage) {
              const msg: string = chunk.message || ''
              const startMatch = msg.match(/正在执行[:：]\s*([A-Za-z_][A-Za-z0-9_]*)/)
              if (startMatch) {
                const toolName = startMatch[1]
                const toolCalls = [...(currentMessage.toolCalls || [])]
                toolCalls.push({
                  toolName,
                  status: 'executing',
                  timestamp: Date.now()
                })
                conversation.messages[assistantMessageIndex] = {
                  ...currentMessage,
                  toolCalls
                }
                conversation.updatedAt = Date.now()
              }
              // “工具 X 执行完成” 消息不再做 UI 改变（避免与 tool_result 重复更新）
            }
            return
          }

          // 处理工具执行结果事件：权威完成信号
          // 将对应 toolName 的最后一条 executing 记录升级为 completed，并写入 result
          if (chunk.type === 'tool_result') {
            const currentMessage = conversation.messages[assistantMessageIndex]
            if (currentMessage) {
              const toolCalls = [...(currentMessage.toolCalls || [])]
              let matchedIdx = -1
              for (let i = toolCalls.length - 1; i >= 0; i--) {
                if (toolCalls[i].toolName === chunk.tool_name && toolCalls[i].status === 'executing') {
                  matchedIdx = i
                  break
                }
              }
              if (matchedIdx >= 0) {
                toolCalls[matchedIdx] = {
                  ...toolCalls[matchedIdx],
                  status: 'completed',
                  result: chunk.result
                }
              } else {
                // 防御：理论上不会走到（缺失起始事件），直接以 completed 追加
                toolCalls.push({
                  toolName: chunk.tool_name,
                  status: 'completed',
                  result: chunk.result,
                  timestamp: Date.now()
                })
              }
              conversation.messages[assistantMessageIndex] = {
                ...currentMessage,
                toolCalls
              }
              conversation.updatedAt = Date.now()
            }
            return
          }

          // 从 chunk.choices[0].delta.content 取出内容
          const deltaContent = chunk.choices?.[0]?.delta?.content

          // 处理 reasoning_content（DeepSeek Thinking Mode）
          const deltaReasoningContent = chunk.choices?.[0]?.delta?.reasoning_content
          if (deltaReasoningContent) {
            const currentMessage = conversation.messages[assistantMessageIndex]
            if (currentMessage) {
              conversation.messages[assistantMessageIndex] = {
                ...currentMessage,
                reasoningContent: (currentMessage.reasoningContent || '') + deltaReasoningContent
              }
              conversation.updatedAt = Date.now()
            }
          }

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
