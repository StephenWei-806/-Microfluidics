export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  isStreaming?: boolean
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: number
  updatedAt: number
}

export interface ApiConfig {
  currentApi: 'qwen' | 'deepseek'
  apiKeys: {
    qwen: string
    deepseek: string
  }
  modelConfig: {
    model: string
    maxTokens: number
    temperature: number
    topP: number
  }
  isConfigValid: boolean
}

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}
