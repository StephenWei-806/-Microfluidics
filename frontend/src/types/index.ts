// 工具执行结果类型
export interface ToolResult {
  toolName: string
  result: string   // JSON 字符串
  timestamp: number
}

// 单次工具调用的全生命周期状态
// 'executing' = 后端正在执行该工具
// 'completed' = 后端已返回 tool_result，执行完成
export type ToolCallStatus = 'executing' | 'completed'

export interface ToolCall {
  toolName: string
  status: ToolCallStatus
  result?: string       // JSON 字符串，仅在 completed 状态下存在
  timestamp: number     // 起始或完成时戳，用作列表 key 保障过渡动画稳定
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  isStreaming?: boolean
  reasoningContent?: string
  toolStatus?: string               // 历史字段，仅保留结构兼容，不再用于展示
  toolResults?: ToolResult[]        // 历史字段，仅用于旧 localStorage 数据的 UI 回放兼容
  toolCalls?: ToolCall[]            // 工具调用列表（流式中从 executing 过渡到 completed）
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
