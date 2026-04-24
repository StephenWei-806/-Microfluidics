import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ApiConfig } from '@/types'
import { apiClient } from '@/api'

const STORAGE_KEY = 'microfluidic_api_config'

export const useApiConfigStore = defineStore('apiConfig', () => {
  const config = ref<ApiConfig>({
    currentApi: 'qwen',
    apiKeys: {
      qwen: '',
      deepseek: ''
    },
    modelConfig: {
      model: '',
      maxTokens: 1024,
      temperature: 0.7,
      topP: 1.0,
      thinkingEnabled: false,
      reasoningEffort: 'high' as const
    },
    isConfigValid: false
  })

  const isQwenSelected = computed(() => config.value.currentApi === 'qwen')
  const isDeepSeekSelected = computed(() => config.value.currentApi === 'deepseek')

  function setApiType(type: 'qwen' | 'deepseek') {
    config.value.currentApi = type
    saveConfig()
  }

  function setApiKey(api: 'qwen' | 'deepseek', key: string) {
    config.value.apiKeys[api] = key
    saveConfig()
  }

  function setModelConfig(modelConfig: Partial<ApiConfig['modelConfig']>) {
    config.value.modelConfig = { ...config.value.modelConfig, ...modelConfig }
    saveConfig()
  }

  async function validateConfig(): Promise<boolean> {
    try {
      const response = await apiClient.validateApiConfig(config.value.currentApi)
      config.value.isConfigValid = response.data.valid
      return response.data.valid
    } catch {
      config.value.isConfigValid = false
      return false
    }
  }

  async function saveConfig(): Promise<void> {
    try {
      await apiClient.updateApiKey(
        config.value.currentApi,
        config.value.apiKeys[config.value.currentApi]
      )
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config.value))
    } catch {
      // 静默处理配置保存失败
    }
  }

  function loadConfig() {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const parsed = JSON.parse(saved)
        config.value = { ...config.value, ...parsed }
      } catch {
        // 静默处理本地配置解析失败
      }
    }
  }

  function getCurrentApiKey() {
    return config.value.apiKeys[config.value.currentApi]
  }

  return {
    config,
    isQwenSelected,
    isDeepSeekSelected,
    setApiType,
    setApiKey,
    setModelConfig,
    validateConfig,
    saveConfig,
    loadConfig,
    getCurrentApiKey
  }
})
