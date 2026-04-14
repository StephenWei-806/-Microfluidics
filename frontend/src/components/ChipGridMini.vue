<template>
  <div class="chip-grid-mini" :style="gridStyle">
    <template v-for="(row, i) in grid" :key="i">
      <el-tooltip
        v-for="(cell, j) in row"
        :key="`${i}-${j}`"
        :content="`行${i + 1} 列${j + 1}: ${cell}`"
        :disabled="!interactive"
        placement="top"
        :show-after="300"
      >
        <div
          class="grid-cell"
          :style="cellStyle(cell)"
          :class="{ interactive }"
          @click="handleCellClick(i, j, cell)"
        />
      </el-tooltip>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  grid: number[][]
  cellSize?: number
  interactive?: boolean
}>(), {
  cellSize: 8,
  interactive: false
})

const emit = defineEmits<{
  'cell-click': [row: number, col: number, value: number]
}>()

const gridStyle = computed(() => ({
  display: 'grid',
  gridTemplateColumns: `repeat(22, ${props.cellSize}px)`,
  gap: '1px'
}))

function colorMap(value: number): string {
  if (value === 0) return '#e0e0e0'
  if (value <= 64) return `hsl(120, 60%, ${85 - value * 0.5}%)`
  return `hsl(210, 70%, ${85 - (value - 64) * 0.5}%)`
}

function cellStyle(value: number) {
  return {
    backgroundColor: colorMap(value),
    width: `${props.cellSize}px`,
    height: `${props.cellSize}px`,
    borderRadius: '1px'
  }
}

function handleCellClick(row: number, col: number, value: number) {
  if (props.interactive) {
    emit('cell-click', row, col, value)
  }
}
</script>

<style scoped lang="scss">
.chip-grid-mini {
  line-height: 0;
}
.grid-cell {
  transition: opacity 0.15s;
  &.interactive {
    cursor: pointer;
    &:hover {
      opacity: 0.7;
    }
  }
}
</style>
