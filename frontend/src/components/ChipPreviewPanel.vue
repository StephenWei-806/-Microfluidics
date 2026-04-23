<template>
  <Teleport to="body">
    <div
      v-show="chipLayoutStore.floatingPanel.visible"
      class="chip-preview-panel"
      :class="{ minimized: chipLayoutStore.floatingPanel.minimized }"
      :style="panelStyle"
      ref="panelRef"
    >
      <!-- 标题栏（可拖拽） -->
      <div
        class="panel-header"
        @pointerdown="startDrag"
      >
        <span class="panel-title">
          <el-icon><Grid /></el-icon>
          芯片网格预览
        </span>
        <div class="panel-actions">
          <el-button link size="small" @click.stop="chipLayoutStore.toggleMinimize()" :title="chipLayoutStore.floatingPanel.minimized ? '展开' : '最小化'">
            <el-icon>
              <component :is="chipLayoutStore.floatingPanel.minimized ? FullScreen : Minus" />
            </el-icon>
          </el-button>
          <el-button link size="small" @click.stop="goToGridConfig" title="编辑配置">
            <el-icon><Setting /></el-icon>
          </el-button>
          <el-button link size="small" @click.stop="chipLayoutStore.togglePanel()" title="关闭">
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 内容区域（最小化时隐藏） -->
      <div class="panel-body" v-show="!chipLayoutStore.floatingPanel.minimized">
        <!-- 网格缩略图 -->
        <div class="grid-preview-wrapper" v-if="chipLayoutStore.grid.length > 0">
          <ChipGridMini
            :grid="chipLayoutStore.grid"
            :cell-size="cellSize"
            :interactive="true"
            @cell-click="onCellClick"
          />
        </div>
        <div v-else class="empty-grid">
          <el-icon :size="32" color="#c0c4cc"><Warning /></el-icon>
          <span>暂无网格数据</span>
        </div>

        <!-- 统计信息 -->
        <div class="stats-bar" v-if="chipLayoutStore.statistics">
          <span class="stat-item">
            <strong>可达:</strong> {{ chipLayoutStore.statistics.reachable_cells }}
          </span>
          <span class="stat-item">
            <strong>禁止:</strong> {{ chipLayoutStore.statistics.forbidden_cells }}
          </span>
          <span class="stat-item" :class="{ 'custom-tag': chipLayoutStore.statistics.is_custom }">
            {{ chipLayoutStore.statistics.is_custom ? '自定义' : '默认' }}
          </span>
        </div>

        <!-- 透明度调节 -->
        <div class="opacity-control">
          <span class="opacity-label">透明度</span>
          <el-slider
            v-model="opacityPercent"
            :min="30"
            :max="100"
            :step="5"
            size="small"
            @change="onOpacityChange"
          />
        </div>
      </div>

      <!-- loading 状态 -->
      <div class="panel-loading" v-if="chipLayoutStore.isLoading">
        <el-icon class="is-loading"><Loading /></el-icon>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Grid, Setting, Close, Minus, FullScreen, Warning, Loading } from '@element-plus/icons-vue'
import { useChipLayoutStore } from '@/stores/chipLayout'
import ChipGridMini from './ChipGridMini.vue'

const router = useRouter()
const chipLayoutStore = useChipLayoutStore()
const panelRef = ref<HTMLElement | null>(null)

const cellSize = 8

// 拖拽状态
const isDragging = ref(false)
const dragOffset = ref({ x: 0, y: 0 })

// 透明度百分比（双向映射）
const opacityPercent = ref(Math.round(chipLayoutStore.floatingPanel.opacity * 100))

const panelStyle = computed(() => {
  const panel = chipLayoutStore.floatingPanel
  const style: Record<string, string> = {
    opacity: String(panel.opacity)
  }
  if (panel.position.x >= 0 && panel.position.y >= 0) {
    style.left = `${panel.position.x}px`
    style.top = `${panel.position.y}px`
    style.right = 'auto'
    style.bottom = 'auto'
  }
  return style
})

// 拖拽逻辑
function startDrag(e: PointerEvent) {
  if ((e.target as HTMLElement).closest('.panel-actions')) return
  isDragging.value = true
  const rect = panelRef.value!.getBoundingClientRect()
  dragOffset.value = {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  }
  document.addEventListener('pointermove', onDrag)
  document.addEventListener('pointerup', stopDrag)
}

function onDrag(e: PointerEvent) {
  if (!isDragging.value) return
  const x = Math.max(0, Math.min(e.clientX - dragOffset.value.x, window.innerWidth - 240))
  const y = Math.max(0, Math.min(e.clientY - dragOffset.value.y, window.innerHeight - 40))
  chipLayoutStore.setPosition(x, y)
}

function stopDrag() {
  isDragging.value = false
  document.removeEventListener('pointermove', onDrag)
  document.removeEventListener('pointerup', stopDrag)
}

function onOpacityChange(val: number) {
  chipLayoutStore.setOpacity(val / 100)
}

function goToGridConfig() {
  router.push('/grid-config')
}

function onCellClick(_row: number, _col: number, _value: number) {
  // 预留交互接口：未来可在这里添加单元格操作逻辑
}

// 轮询定时器
let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  chipLayoutStore.loadFloatingPanelState()
  opacityPercent.value = Math.round(chipLayoutStore.floatingPanel.opacity * 100)
  chipLayoutStore.fetchLayout()
  
  // 每30秒轮询一次
  pollTimer = setInterval(() => {
    if (chipLayoutStore.floatingPanel.visible && !chipLayoutStore.floatingPanel.minimized) {
      chipLayoutStore.fetchLayout()
    }
  }, 30000)
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<style scoped lang="scss">
.chip-preview-panel {
  position: fixed;
  left: 20px;
  bottom: 80px;
  z-index: 100;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
  min-width: 230px;
  max-width: 320px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;

  &.minimized {
    max-width: 200px;
    min-width: auto;
  }
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  cursor: grab;
  user-select: none;

  &:active {
    cursor: grabbing;
  }

  .panel-title {
    font-size: 13px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .panel-actions {
    display: flex;
    gap: 2px;

    .el-button {
      color: white !important;
      &:hover {
        opacity: 0.8;
      }
    }
  }
}

.panel-body {
  padding: 12px;
}

.grid-preview-wrapper {
  display: flex;
  justify-content: center;
  padding: 8px;
  background: #fafafa;
  border-radius: 8px;
  margin-bottom: 8px;
  overflow: auto;
}

.empty-grid {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  color: #c0c4cc;
  font-size: 13px;
}

.stats-bar {
  display: flex;
  justify-content: center;
  gap: 12px;
  padding: 6px 8px;
  background: #f5f7fa;
  border-radius: 6px;
  margin-bottom: 8px;
  flex-wrap: wrap;

  .stat-item {
    font-size: 12px;
    color: #606266;

    strong {
      color: #303133;
    }
  }

  .custom-tag {
    color: #e6a23c;
    font-weight: 600;
  }
}

.opacity-control {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;

  .opacity-label {
    font-size: 12px;
    color: #909399;
    white-space: nowrap;
  }

  .el-slider {
    flex: 1;
  }
}

.panel-loading {
  position: absolute;
  top: 40px;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 0 0 12px 12px;
}

// 响应式：小屏幕时固定底部
@media (max-width: 768px) {
  .chip-preview-panel {
    left: 8px !important;
    bottom: 80px !important;
    right: auto !important;
    top: auto !important;
    max-width: 280px;
  }
}
</style>
