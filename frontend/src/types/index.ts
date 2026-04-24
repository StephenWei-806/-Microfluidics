export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  isStreaming?: boolean
  reasoningContent?: string
  toolStatus?: string
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
    thinkingEnabled: boolean
    reasoningEffort: 'high' | 'max'
  }
  isConfigValid: boolean
}

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

export interface ChipGrid {
  grid: number[][]
  description: string
}

export interface ChipStatistics {
  total_cells: number
  reachable_cells: number
  forbidden_cells: number
  rows: number
  cols: number
  is_custom: boolean
  description: string
}

export interface FloatingPanelState {
  visible: boolean
  minimized: boolean
  position: { x: number; y: number }
  opacity: number
}
