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
            :disabled="form.currentApi === 'deepseek' && form.modelConfig.thinkingEnabled"
          />
        </el-form-item>

        <!-- Thinking Mode 开关 - 仅 DeepSeek 时显示 -->
        <el-form-item label="思考模式" v-if="form.currentApi === 'deepseek'">
          <el-switch
            v-model="form.modelConfig.thinkingEnabled"
            active-text="启用"
            inactive-text="禁用"
          />
          <el-text v-if="form.modelConfig.thinkingEnabled" type="warning" style="margin-left: 12px; font-size: 12px;">
            启用后 Temperature 和 Top P 参数将不生效
          </el-text>
        </el-form-item>

        <!-- Reasoning Effort 选择 - 仅 DeepSeek 且启用思考模式时显示 -->
        <el-form-item label="思考强度" v-if="form.currentApi === 'deepseek' && form.modelConfig.thinkingEnabled">
          <el-radio-group v-model="form.modelConfig.reasoningEffort">
            <el-radio value="high">标准 (High)</el-radio>
            <el-radio value="max">深度 (Max)</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="Top P">
          <el-slider
            v-model="form.modelConfig.topP"
            :min="0"
            :max="1"
            :step="0.1"
            show-input
            :disabled="form.currentApi === 'deepseek' && form.modelConfig.thinkingEnabled"
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

/**
 * 从后端响应中安全提取 models 数组
 * 后端返回格式: {code, message, data: {api_name, models: [...]}}
 * apiClient 已做一层 response.data 解包，所以 result = {code, message, data: {...}}
 */
function extractModels(result: any): string[] {
  // 路径1: result.data.models （标准路径）
  if (result?.data?.models && Array.isArray(result.data.models)) {
    return result.data.models
  }
  // 路径2: result.models （如果 interceptor 进一步解包了 data）
  if (result?.models && Array.isArray(result.models)) {
    return result.models
  }
  // 路径3: result 本身就是数组
  if (Array.isArray(result)) {
    return result
  }
  return []
}

async function loadModels() {
  try {
    const result = await apiClient.getModels(form.currentApi)
    availableModels.value = extractModels(result)
  } catch {
    availableModels.value = []
  }
}

async function handleApiTypeChange() {
  apiConfigStore.setApiType(form.currentApi)
  await loadModels()
  // 切换 API 后，如果当前模型不在新列表中，重置为第一个可用模型
  if (availableModels.value.length > 0 && !availableModels.value.includes(form.modelConfig.model)) {
    form.modelConfig.model = availableModels.value[0]
    apiConfigStore.setModelConfig({ model: form.modelConfig.model })
  }
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
  // 同步 form 初始值与 store，确保 loadModels 使用正确的 API 类型
  form.currentApi = apiConfigStore.config.currentApi
  form.apiKeys = { ...apiConfigStore.config.apiKeys }
  form.modelConfig = { ...apiConfigStore.config.modelConfig }
  form.isConfigValid = apiConfigStore.config.isConfigValid
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
