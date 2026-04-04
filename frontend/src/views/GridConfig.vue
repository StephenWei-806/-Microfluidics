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
                  :style="getCellStyle(cell)"
                  @blur="clampValue(rowIndex, colIndex)"
                  @input="clampValue(rowIndex, colIndex)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="button-group">
        <el-button type="primary" @click="loadCurrentConfig" :loading="loading">
          加载当前配置
        </el-button>
        <el-button type="warning" @click="resetGrid">
          重置为全零
        </el-button>
        <el-button type="success" @click="submitConfig" :loading="submitting">
          提交配置
        </el-button>
        <el-button @click="router.push('/chat')">
          返回对话
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { apiClient } from '@/api'

const router = useRouter()
const ROWS = 17
const COLS = 22
const loading = ref(false)
const submitting = ref(false)

const grid = reactive<number[][]>(
  Array.from({ length: ROWS }, () => Array(COLS).fill(0))
)

function getCellStyle(value: number) {
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
}

async function loadCurrentConfig() {
  loading.value = true
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
  } finally {
    loading.value = false
  }
}

function resetGrid() {
  for (let i = 0; i < ROWS; i++) {
    for (let j = 0; j < COLS; j++) {
      grid[i][j] = 0
    }
  }
  ElMessage.success('网格已重置为全零')
}

async function submitConfig() {
  submitting.value = true
  try {
    const gridData = grid.map(row => [...row])
    await apiClient.updateChipLayout(gridData)
    ElMessage.success('配置提交成功！')
  } catch (error) {
    console.error('Failed to update chip layout:', error)
    ElMessage.error('提交配置失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadCurrentConfig()
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
</style>
