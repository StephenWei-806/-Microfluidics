<template>
  <div class="api-config-container">
    <div class="config-card">
      <h2>模型 API 配置</h2>
      
      <el-form :model="form" label-width="120px" class="config-form">
        <el-form-item label="API 类型">
          <el-radio-group v-model="form.currentApi" @change="handleApiTypeChange">
            <el-radio value="qwen">千问 (Qwen)</el-radio>
            <el-radio value="deepseek">DeepSeek</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="API 密钥">
          <el-input
            v-model="form.apiKeys[form.currentApi]"
            type="password"
            show-password
            placeholder="请输入 API 密钥"
            style="width: 100%"
          />
        </el-form-item>

        <el-form-item label="模型选择">
          <el-select v-model="form.modelConfig.model" placeholder="请选择模型" style="width: 100%">
            <el-option
              v-for="model in availableModels"
              :key="model"
              :label="model"
              :value="model"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="最大 Token 数">
          <el-slider
            v-model="form.modelConfig.maxTokens"
            :min="256"
            :max="32768"
            :step="256"
            show-input
          />
        </el-form-item>

        <el-form-item label="温度参数">
          <el-slider
            v-model="form.modelConfig.temperature"
            :min="0"
            :max="2"
            :step="0.1"
            show-input
          />
        </el-form-item>

        <el-form-item label="Top P">
          <el-slider
            v-model="form.modelConfig.topP"
            :min="0"
            :max="1"
            :step="0.1"
            show-input
          />
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="testConnection" :loading="testing">
            <el-icon><Connection /></el-icon>
            测试连接
          </el-button>
          <el-button type="success" @click="saveConfig" :loading="saving">
            <el-icon><Check /></el-icon>
            保存配置
          </el-button>
          <el-button @click="goToGridConfig">
            <el-icon><Grid /></el-icon>
            网格配置
          </el-button>
          <el-tag v-if="form.isConfigValid" type="success">配置有效</el-tag>
          <el-tag v-else type="danger">配置无效</el-tag>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Connection, Check, Grid } from '@element-plus/icons-vue'
import { useApiConfigStore } from '@/stores/apiConfig'
import { apiClient } from '@/api'

const router = useRouter()
const apiConfigStore = useApiConfigStore()

const testing = ref(false)
const saving = ref(false)
const availableModels = ref<string[]>([])

const form = reactive({
  currentApi: apiConfigStore.config.currentApi,
  apiKeys: { ...apiConfigStore.config.apiKeys },
  modelConfig: { ...apiConfigStore.config.modelConfig },
  isConfigValid: apiConfigStore.config.isConfigValid
})

watch(() => apiConfigStore.config, (newConfig) => {
  form.currentApi = newConfig.currentApi
  form.apiKeys = { ...newConfig.apiKeys }
  form.modelConfig = { ...newConfig.modelConfig }
  form.isConfigValid = newConfig.isConfigValid
}, { deep: true })

async function loadModels() {
  try {
    const response = await apiClient.getModels(form.currentApi)
    availableModels.value = response.data.models
  } catch {
    // 静默处理模型列表加载失败
  }
}

async function handleApiTypeChange() {
  apiConfigStore.setApiType(form.currentApi)
  await loadModels()
}

async function testConnection() {
  testing.value = true
  try {
    apiConfigStore.setApiKey(form.currentApi, form.apiKeys[form.currentApi])
    apiConfigStore.setModelConfig(form.modelConfig)
    const isValid = await apiConfigStore.validateConfig()
    if (isValid) {
      ElMessage.success('连接测试成功！')
    } else {
      ElMessage.error('连接测试失败，请检查配置')
    }
  } catch (error) {
    ElMessage.error('连接测试失败')
  } finally {
    testing.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    apiConfigStore.setApiType(form.currentApi)
    apiConfigStore.setApiKey(form.currentApi, form.apiKeys[form.currentApi])
    apiConfigStore.setModelConfig(form.modelConfig)
    await apiConfigStore.saveConfig()
    ElMessage.success('配置保存成功！')
    router.push('/chat')
  } catch (error) {
    ElMessage.error('配置保存失败')
  } finally {
    saving.value = false
  }
}

function goToGridConfig() {
  router.push('/grid-config')
}

onMounted(() => {
  apiConfigStore.loadConfig()
  loadModels()
})
</script>

<style scoped lang="scss">
.api-config-container {
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
  max-width: 600px;
  width: 100%;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);

  h2 {
    text-align: center;
    margin-bottom: 32px;
    color: #1f2937;
    font-size: 24px;
  }
}

.config-form {
  margin-top: 24px;
}
</style>
