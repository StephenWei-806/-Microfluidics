<template>
  <div class="grid-config-container">
    <div class="config-card">
      <h2>微流控芯片网格配置</h2>

      <div class="grid-wrapper">
        <table class="grid-table">
          <tbody>
            <tr v-for="(row, rowIndex) in grid" :key="rowIndex">
              <td v-for="(cell, colIndex) in row" :key="colIndex">
                <input
                  v-model.number="grid[rowIndex][colIndex]"
                  type="number"
                  min="0"
                  max="100"
                  :style="getCellStyle(cell, rowIndex, colIndex)"
                  @blur="clampValue(rowIndex, colIndex)"
                  @input="clampValue(rowIndex, colIndex)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="button-group">
        <el-button type="warning" @click="resetGrid">
          重置为全零
        </el-button>
        <el-button type="danger" @click="resetToDefault" :loading="resetting">
          恢复默认配置
        </el-button>
        <el-button type="success" @click="submitConfig" :loading="submitting">
          提交配置
        </el-button>
        <el-button @click="router.push('/chat')">
          返回对话
        </el-button>
      </div>

      <div class="statistics-bar" v-if="statistics">
        <span class="stat-item">
          <strong>网格规模:</strong> {{ statistics.rows }} × {{ statistics.cols }}
        </span>
        <span class="stat-item">
          <strong>可达位置:</strong> {{ statistics.reachable_cells }}
        </span>
        <span class="stat-item">
          <strong>禁止区域:</strong> {{ statistics.forbidden_cells }}
        </span>
        <span class="stat-item" :class="{ 'custom-tag': statistics.is_custom }">
          {{ statistics.is_custom ? '自定义配置' : '默认配置' }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiClient } from '@/api'
import { useChipLayoutStore } from '@/stores/chipLayout'

const router = useRouter()
const chipLayoutStore = useChipLayoutStore()
const ROWS = 17
const COLS = 22
const submitting = ref(false)
const resetting = ref(false)
const statistics = ref<{
  total_cells: number
  reachable_cells: number
  forbidden_cells: number
  rows: number
  cols: number
  is_custom: boolean
  description: string
} | null>(null)
const errorCells = ref<Set<string>>(new Set())  // 存储有错误的单元格 "row-col" 格式

const grid = reactive<number[][]>(
  Array.from({ length: ROWS }, () => Array(COLS).fill(0))
)

function getCellStyle(value: number, rowIndex?: number, colIndex?: number) {
  const isError = rowIndex !== undefined && colIndex !== undefined &&
    errorCells.value.has(`${rowIndex}-${colIndex}`)

  if (isError) {
    return {
      backgroundColor: '#ff5252',
      color: '#fff',
      boxShadow: '0 0 0 2px #ff1744'
    }
  }
  return {
    backgroundColor: value !== 0 ? '#4CAF50' : '#e0e0e0',
    color: value !== 0 ? '#fff' : '#333'
  }
}

function clampValue(row: number, col: number) {
  let v = grid[row][col]
  if (v < 0) grid[row][col] = 0
  if (v > 100) grid[row][col] = 100
  if (isNaN(v) || v === null) grid[row][col] = 0
  // 清除该单元格的错误标记
  errorCells.value.delete(`${row}-${col}`)
}

async function loadCurrentConfig() {
  try {
    const response = await apiClient.getChipLayout()
    if (response.data && response.data.grid) {
      const loadedGrid = response.data.grid
      for (let i = 0; i < ROWS; i++) {
        for (let j = 0; j < COLS; j++) {
          if (loadedGrid[i] && loadedGrid[i][j] !== undefined) {
            grid[i][j] = loadedGrid[i][j]
          }
        }
      }
      ElMessage.success('配置加载成功！')
    } else {
      ElMessage.warning('返回数据格式不正确')
    }
  } catch (error) {
    console.error('Failed to load chip layout:', error)
    ElMessage.error('加载配置失败')
  }
}

function resetGrid() {
  for (let i = 0; i < ROWS; i++) {
    for (let j = 0; j < COLS; j++) {
      grid[i][j] = 0
    }
  }
  errorCells.value.clear()
  ElMessage.success('网格已重置为全零')
}

async function resetToDefault() {
  resetting.value = true
  try {
    const response = await apiClient.resetChipLayout()
    if (response.data && response.data.grid) {
      const loadedGrid = response.data.grid
      for (let i = 0; i < ROWS; i++) {
        for (let j = 0; j < COLS; j++) {
          if (loadedGrid[i] && loadedGrid[i][j] !== undefined) {
            grid[i][j] = loadedGrid[i][j]
          }
        }
      }
    }
    errorCells.value.clear()
    ElMessage.success('已重置为默认配置！')
    await chipLayoutStore.fetchLayout(true)
    chipLayoutStore.notifyLayoutUpdated()
    await loadStatistics()
  } catch (error) {
    console.error('Failed to reset chip layout:', error)
    ElMessage.error('重置配置失败')
  } finally {
    resetting.value = false
  }
}

async function loadStatistics() {
  try {
    const response = await apiClient.getChipLayoutStatistics()
    if (response.data) {
      statistics.value = response.data
    }
  } catch (error) {
    console.error('Failed to load statistics:', error)
  }
}

async function submitConfig() {
  submitting.value = true
  errorCells.value.clear()
  try {
    const gridData = grid.map(row => [...row])
    await apiClient.updateChipLayout(gridData)
    ElMessage.success('配置提交成功！')
    await chipLayoutStore.fetchLayout(true)
    chipLayoutStore.notifyLayoutUpdated()
    await loadStatistics()
  } catch (error: any) {
    console.error('Failed to update chip layout:', error)
    // 解析后端返回的详细错误信息
    const apiData = error.response?.data
    const fieldErrors = apiData?.data?.errors ?? apiData?.errors

    if (Array.isArray(fieldErrors) && fieldErrors.length > 0) {
      fieldErrors.forEach((err: any) => {
        // 解析 field 格式如 "grid[0][3]"
        const match = err.field?.match(/grid\[(\d+)\]\[(\d+)\]/)
        if (match) {
          errorCells.value.add(`${match[1]}-${match[2]}`)
        }
      })
      ElMessage.error(`提交配置失败: ${fieldErrors.length}个单元格有误`)
    } else {
      ElMessage.error('提交配置失败')
    }
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadCurrentConfig()
  loadStatistics()
})
</script>

<style scoped lang="scss">
.grid-config-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 40px 20px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.config-card {
  background: white;
  border-radius: 16px;
  padding: 40px;
  max-width: 1200px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);

  h2 {
    text-align: center;
    margin-bottom: 32px;
    color: #1f2937;
    font-size: 24px;
  }
}

.grid-wrapper {
  overflow-x: auto;
  margin-bottom: 24px;
}

.grid-table {
  border-collapse: collapse;
  margin: 0 auto;

  td {
    padding: 2px;
  }

  input[type="number"] {
    width: 45px;
    height: 32px;
    border: none;
    border-radius: 4px;
    text-align: center;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.2s ease;
    outline: none;

    &::-webkit-inner-spin-button,
    &::-webkit-outer-spin-button {
      -webkit-appearance: none;
      margin: 0;
    }

    -moz-appearance: textfield;

    &:focus {
      box-shadow: 0 0 0 2px rgba(76, 175, 80, 0.4);
    }
  }
}

.button-group {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.statistics-bar {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 16px;
  padding: 12px 20px;
  background: #f5f7fa;
  border-radius: 8px;
  flex-wrap: wrap;

  .stat-item {
    font-size: 14px;
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
</style>
