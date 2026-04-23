import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import type { ChipStatistics, FloatingPanelState } from '@/types'
import { apiClient } from '@/api'

const STORAGE_KEY = 'chip-preview-panel-state'
const CACHE_TTL = 30000

export const useChipLayoutStore = defineStore('chipLayout', () => {
  const grid = ref<number[][]>([])
  const statistics = ref<ChipStatistics | null>(null)
  const isLoading = ref(false)
  const lastFetchTime = ref(0)
  
  const floatingPanel = reactive<FloatingPanelState>({
    visible: true,
    minimized: false,
    position: { x: -1, y: -1 },
    opacity: 0.95
  })

  // BroadcastChannel
  let channel: BroadcastChannel | null = null
  try {
    channel = new BroadcastChannel('chip-layout-sync')
    channel.onmessage = (event) => {
      if (event.data?.type === 'layout-updated') {
        fetchLayout(true)
      }
    }
  } catch {
    // 静默处理 BroadcastChannel 不支持的情况
  }

  async function fetchLayout(force = false) {
    if (!force && Date.now() - lastFetchTime.value < CACHE_TTL && grid.value.length > 0) {
      return
    }
    isLoading.value = true
    try {
      const response = await apiClient.getChipLayout()
      if (response.data?.grid) {
        grid.value = response.data.grid
      }
      lastFetchTime.value = Date.now()
      await fetchStatistics()
    } catch {
      // 静默处理网格数据获取失败
    } finally {
      isLoading.value = false
    }
  }

  async function fetchStatistics() {
    try {
      const response = await apiClient.getChipLayoutStatistics()
      if (response.data) {
        statistics.value = response.data
      }
    } catch {
      // 静默处理统计信息获取失败
    }
  }

  function notifyLayoutUpdated() {
    channel?.postMessage({ type: 'layout-updated' })
  }

  function togglePanel() {
    floatingPanel.visible = !floatingPanel.visible
    saveFloatingPanelState()
  }

  function toggleMinimize() {
    floatingPanel.minimized = !floatingPanel.minimized
    saveFloatingPanelState()
  }

  function setPosition(x: number, y: number) {
    floatingPanel.position = { x, y }
    saveFloatingPanelState()
  }

  function setOpacity(val: number) {
    floatingPanel.opacity = val
    saveFloatingPanelState()
  }

  function saveFloatingPanelState() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      visible: floatingPanel.visible,
      minimized: floatingPanel.minimized,
      position: floatingPanel.position,
      opacity: floatingPanel.opacity
    }))
  }

  function loadFloatingPanelState() {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      try {
        const state = JSON.parse(saved) as FloatingPanelState
        floatingPanel.visible = state.visible ?? true
        floatingPanel.minimized = state.minimized ?? false
        floatingPanel.position = state.position ?? { x: -1, y: -1 }
        floatingPanel.opacity = state.opacity ?? 0.95
      } catch {
        // 静默处理面板状态解析失败
      }
    }
  }

  return {
    grid,
    statistics,
    isLoading,
    lastFetchTime,
    floatingPanel,
    fetchLayout,
    fetchStatistics,
    notifyLayoutUpdated,
    togglePanel,
    toggleMinimize,
    setPosition,
    setOpacity,
    saveFloatingPanelState,
    loadFloatingPanelState
  }
})
