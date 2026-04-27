import axios, { AxiosInstance, AxiosResponse, AxiosError } from 'axios'
import type { ApiResponse } from '@/types'

const baseURL = '/api'

const api: AxiosInstance = axios.create({
  baseURL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error: AxiosError) => {
    if (!error.response && !error.request) {
      // 静默处理无响应的网络错误
    }
    return Promise.reject(error)
  }
)

export const apiClient = {
  async getSettings(): Promise<ApiResponse<any>> {
    const response = await api.get('/settings')
    return response.data
  },

  async getApiConfig(): Promise<ApiResponse<any>> {
    const response = await api.get('/api/config')
    return response.data
  },

  async updateApiKey(apiName: string, apiKey: string): Promise<ApiResponse<any>> {
    const response = await api.post('/api/key', { api_name: apiName, api_key: apiKey })
    return response.data
  },

  async getModels(apiName: string): Promise<ApiResponse<any>> {
    const response = await api.get(`/api/models/${apiName}`)
    return response.data
  },

  async validateApiConfig(apiName: string): Promise<ApiResponse<any>> {
    const response = await api.get(`/api/validate/${apiName}`)
    return response.data
  },

  async callApi(params: {
    api_name: string
    model: string
    prompt: string
    max_tokens?: number
    temperature?: number
  }): Promise<ApiResponse<any>> {
    const response = await api.post('/api/call', params)
    return response.data
  },

  /**
   * 初始化流式请求，获取 stream_id
   */
  async initStream(params: {
    api_name: string
    model: string
    prompt: string
    messages?: Array<{ role: string; content: string }>
    max_tokens?: number
    temperature?: number
    thinking_enabled?: boolean
    reasoning_effort?: string
    tools_enabled?: boolean
  }): Promise<string> {
    try {
      const response = await api.post('/stream/init', params)
      const streamId = response.data.data.stream_id
      return streamId
    } catch {
      throw new Error('初始化流式请求失败')
    }
  },

  async getPromptVersions(): Promise<ApiResponse<any>> {
    const response = await api.get('/prompts/versions')
    return response.data
  },

  async getPromptModules(version?: string): Promise<ApiResponse<any>> {
    const response = await api.get('/prompts/modules', {
      params: { version }
    })
    return response.data
  },

  async getChipLayout(): Promise<ApiResponse<any>> {
    const response = await api.get('/chip-layout')
    return response.data
  },

  async updateChipLayout(grid: number[][]): Promise<ApiResponse<any>> {
    const response = await api.post('/chip-layout', { grid })
    return response.data
  },

  async resetChipLayout(): Promise<ApiResponse<any>> {
    const response = await api.post('/chip-layout/reset')
    return response.data
  },

  async getChipLayoutStatistics(): Promise<ApiResponse<any>> {
    const response = await api.get('/chip-layout/statistics')
    return response.data
  }
}

export interface EventSourceCallbacks {
  onMessage: (chunk: any) => void    // 收到数据块时调用
  onComplete: () => void             // 收到 [DONE] 信号时调用
  onError: (error: string) => void   // 发生错误时调用
}

/**
 * 创建 EventSource 连接
 */
export function createEventSource(
  streamId: string,
  callbacks: EventSourceCallbacks
): EventSource {
  const url = `${baseURL}/stream/${streamId}`
  const eventSource = new EventSource(url)

  eventSource.onmessage = (event) => {
    const rawData = event.data

    if (rawData === '[DONE]') {
      eventSource.close()
      callbacks.onComplete()
      return
    }

    try {
      const chunk = JSON.parse(rawData)
      callbacks.onMessage(chunk)
    } catch (err) {
      console.error('[SSE] JSON parse error:', err instanceof Error ? err.message : String(err))
    }
  }

  eventSource.onerror = () => {
    console.error('[SSE] Connection error')
    eventSource.close()
    callbacks.onError('SSE 连接发生错误')
  }

  return eventSource
}

export default api
