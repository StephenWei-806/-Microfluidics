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
    console.group(`%c[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, 'color: #4CAF50; font-weight: bold')
    console.log('Status:', response.status, response.statusText)
    console.log('Headers:', response.headers)
    console.log('Data:', response.data)
    console.groupEnd()
    return response
  },
  (error: AxiosError) => {
    if (error.response) {
      console.group(`%c[API Error] ${error.config?.method?.toUpperCase()} ${error.config?.url}`, 'color: #F44336; font-weight: bold')
      console.log('Status:', error.response.status, error.response.statusText)
      console.log('Headers:', error.response.headers)
      console.log('Data:', error.response.data)
      console.groupEnd()
    } else if (error.request) {
      console.group(`%c[API Error] No Response`, 'color: #F44336; font-weight: bold')
      console.log('Request:', error.request)
      console.log('Message:', error.message)
      console.groupEnd()
    } else {
      console.error('[API Error]', error.message)
    }
    return Promise.reject(error)
  }
)

async function fetchWithLogger(url: string, options: RequestInit = {}): Promise<Response> {
  const startTime = Date.now()
  console.group(`%c[Fetch Request] ${options.method || 'GET'} ${url}`, 'color: #2196F3; font-weight: bold')
  console.log('Options:', options)
  console.groupEnd()

  try {
    const response = await fetch(url, options)
    const duration = Date.now() - startTime
    
    console.group(`%c[Fetch Response] ${options.method || 'GET'} ${url}`, 'color: #4CAF50; font-weight: bold')
    console.log('Status:', response.status, response.statusText)
    console.log('Duration:', `${duration}ms`)
    console.log('Headers:', Object.fromEntries(response.headers.entries()))
    
    const contentType = response.headers.get('content-type')
    if (contentType && contentType.includes('text/event-stream')) {
      console.log('Body: [SSE Stream - chunks will be logged separately]')
    } else {
      const clonedResponse = response.clone()
      try {
        const body = await clonedResponse.text()
        console.log('Body:', body.length > 1000 ? body.substring(0, 1000) + '...(truncated)' : body)
      } catch {
        console.log('Body: [Unable to read]')
      }
    }
    console.groupEnd()
    
    return response
  } catch (error) {
    const duration = Date.now() - startTime
    console.group(`%c[Fetch Error] ${options.method || 'GET'} ${url}`, 'color: #F44336; font-weight: bold')
    console.log('Duration:', `${duration}ms`)
    console.log('Error:', error)
    console.groupEnd()
    throw error
  }
}

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
    max_tokens?: number
    temperature?: number
  }): Promise<string> {
    console.group('%c[API Request] POST /api/stream/init', 'color: #2196F3; font-weight: bold')
    console.log('Params:', params)
    console.groupEnd()

    try {
      const response = await api.post('/stream/init', params)
      const streamId = response.data.data.stream_id

      console.group('%c[API Response] POST /api/stream/init', 'color: #4CAF50; font-weight: bold')
      console.log('Stream ID:', streamId)
      console.groupEnd()

      return streamId
    } catch (error) {
      console.error('[Init Stream Error]', error)
      throw error
    }
  },

  /** @deprecated 使用 initStream + createEventSource 替代 */
  async *streamApi(params: {
    api_name: string
    model: string
    prompt: string
    max_tokens?: number
    temperature?: number
  }): AsyncGenerator<any, void, unknown> {
    const response = await fetchWithLogger('/api/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(params)
    })

    if (!response.ok) {
      throw new Error(`Stream request failed: ${response.status} ${response.statusText}`)
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()

    try {
      let chunkCount = 0
      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          console.log(`%c[Stream Complete] Total chunks: ${chunkCount}`, 'color: #9C27B0; font-weight: bold')
          break
        }

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') {
              console.log('%c[Stream End] Received [DONE] signal', 'color: #9C27B0; font-weight: bold')
              return
            }
            try {
              const parsed = JSON.parse(data)
              chunkCount++
              console.log(`%c[Stream Chunk #${chunkCount}]`, 'color: #FF9800', parsed)
              yield parsed
            } catch (e) {
              console.warn('[Stream Parse Error]', e, 'Raw:', data)
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
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

  console.group('%c[EventSource] Connecting', 'color: #9C27B0; font-weight: bold')
  console.log('URL:', url)
  console.groupEnd()

  const eventSource = new EventSource(url)

  eventSource.onopen = () => {
    console.log('%c[EventSource] Connection opened', 'color: #9C27B0; font-weight: bold')
  }

  eventSource.onmessage = (event) => {
    const rawData = event.data

    // 检测完成信号
    if (rawData === '[DONE]') {
      console.log('%c[EventSource] Received [DONE] signal', 'color: #9C27B0; font-weight: bold')
      eventSource.close()
      callbacks.onComplete()
      return
    }

    try {
      const chunk = JSON.parse(rawData)
      console.log('%c[EventSource] Message received', 'color: #FF9800', chunk)
      callbacks.onMessage(chunk)
    } catch (e) {
      console.error('[EventSource] 解析 SSE 数据失败:', e, 'Raw:', rawData)
    }
  }

  eventSource.onerror = (event) => {
    console.error('[EventSource] Connection error', event)
    eventSource.close()
    callbacks.onError('SSE 连接发生错误，请稍后重试')
  }

  return eventSource
}

export default api
