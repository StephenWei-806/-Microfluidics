<template>
  <div class="chat-input-container">
    <div class="input-wrapper">
      <el-input
        v-model="inputValue"
        type="textarea"
        :rows="3"
        placeholder="输入消息... (Shift+Enter 换行，Enter 发送)"
        :maxlength="4096"
        show-word-limit
        @keydown="handleKeydown"
        :disabled="isLoading"
        resize="none"
        class="chat-textarea"
      />
      <div class="input-actions">
        <el-button @click="clearInput" :disabled="isLoading" link>
          清空
        </el-button>
        <el-button
          type="primary"
          @click="sendMessage"
          :loading="isLoading"
          :disabled="!inputValue.trim()"
        >
          <template v-if="!isLoading">
            <el-icon><Position /></el-icon>
            发送
          </template>
          <template v-else>
            发送中...
          </template>
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Position } from '@element-plus/icons-vue'

interface Props {
  isLoading: boolean
}

interface Emits {
  (e: 'send', value: string): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const inputValue = ref('')

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    if (inputValue.value.trim() && !props.isLoading) {
      sendMessage()
    }
  }
}

function sendMessage() {
  if (inputValue.value.trim() && !props.isLoading) {
    emit('send', inputValue.value)
    inputValue.value = ''
  }
}

function clearInput() {
  inputValue.value = ''
}
</script>

<style scoped lang="scss">
.chat-input-container {
  padding: 20px;
  background: white;
  border-top: 1px solid #e5e7eb;
}

.input-wrapper {
  max-width: 900px;
  margin: 0 auto;
}

.chat-textarea {
  :deep(.el-textarea__inner) {
    border-radius: 12px;
    font-size: 15px;
    line-height: 1.5;
    padding: 16px;
  }
}

.input-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 12px;
}
</style>
