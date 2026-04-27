# 微流控 AI 助手 — 前端开发者参考文档

## 1. 前端架构概览

| 类别 | 技术 | 版本 |
|------|------|------|
| 框架 | Vue 3 | 3.4.21 |
| 语言 | TypeScript | 5.4.2 |
| 构建工具 | Vite | 5.1.6 |
| 状态管理 | Pinia | 2.1.7 |
| UI 库 | Element Plus | 2.5.6 |
| 路由 | Vue Router | 4.3.0 |
| HTTP 客户端 | Axios | 1.6.7 |
| Markdown 渲染 | Marked | 12.0.0 |
| 图表渲染 | Mermaid | 11.13.0 |
| 代码高亮 | Highlight.js | 11.9.0 |
| 样式预处理 | SCSS（sass） | 1.71.1 |

---

## 2. 目录结构

```
src/
├── api/index.ts              # API 客户端（162行）
├── assets/vue.svg            # 静态资源
├── components/               # 可复用组件
│   ├── ChatInput.vue         # 聊天输入框（105行）
│   ├── MessageBubble.vue     # 消息气泡（996行）
│   ├── ChipGridMini.vue      # 网格缩略图（81行）
│   ├── ChipPreviewPanel.vue  # 悬浮预览面板（326行）
│   └── message/              # 内容处理模块
│       ├── types.ts          # 类型定义（12行）
│       ├── ContentParser.ts  # 内容解析（105行）
│       ├── MermaidRenderer.ts # Mermaid渲染（195行）
│       └── SvgExporter.ts    # SVG导出（152行）
├── router/index.ts           # 路由配置（32行）
├── stores/                   # Pinia 状态管理
│   ├── chat.ts              # 对话Store（335行）
│   ├── apiConfig.ts         # 配置Store（98行）
│   └── chipLayout.ts        # 网格Store（130行）
├── types/index.ts            # 全局类型定义（84行）
├── views/                    # 页面视图
│   ├── ChatRoom.vue         # 对话页面（291行）
│   ├── ApiConfig.vue        # 配置页面（256行）
│   └── GridConfig.vue       # 网格配置页面（311行）
├── App.vue                   # 根组件（20行）
├── main.ts                   # 应用入口（20行）
└── style.css                 # 全局样式（24行）
```

---

## 3. 应用入口

### main.ts 初始化步骤

1. `createApp(App)` — 创建 Vue 应用实例
2. 注册 Pinia — 全局状态管理
3. 注册 Element Plus + 自动注册所有 `@element-plus/icons-vue` 图标
4. 注册 Vue Router — 路由系统
5. `app.mount('#app')` — 挂载到 DOM

### App.vue

根组件，仅包含 `<router-view />`，承载全局样式重置，不包含业务逻辑。

---

## 4. 路由系统（router/index.ts）

| 路径 | 名称 | 组件 | 加载方式 |
|------|------|------|---------|
| `/` | — | 重定向 → `/chat` | — |
| `/chat` | Chat | ChatRoom.vue | 懒加载 |
| `/config` | Config | ApiConfig.vue | 懒加载 |
| `/grid-config` | GridConfig | GridConfig.vue | 懒加载 |

使用 `createRouter` + `createWebHistory`，所有页面组件均通过动态 `import()` 实现路由级代码分割。

---

## 5. 组件系统详解

### 5.1 ChatInput.vue — 聊天输入框

**Props：**

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `isLoading` | `boolean` | — | 是否发送中，禁用输入 |

**Emits：**

| 事件 | 参数 | 说明 |
|------|------|------|
| `send` | `value: string` | 发送消息 |

**方法：**

- `handleKeydown(event)` — Enter 发送，Shift+Enter 换行
- `sendMessage()` — 触发 `send` emit
- `clearInput()` — 清空输入框

**UI 特征：**

- 多行文本框，默认 3 行高
- `max-length` 4096
- 圆角 12px
- 紫色渐变发送按钮

---

### 5.2 MessageBubble.vue — 消息气泡（核心组件，996 行）

**Props：**

| 名称 | 类型 | 说明 |
|------|------|------|
| `message` | `Message` | 完整消息对象 |

**Message 类型：**

```typescript
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  isStreaming?: boolean
  reasoningContent?: string    // 思维链（DeepSeek）
  toolCalls?: ToolCall[]       // 工具调用列表
}
```

**功能模块：**

1. **思维链展示** — 可折叠面板，显示"思考中…/思考完成"状态，内容经 Markdown 渲染
2. **工具调用状态** — 列表展示 `executing` → `completed` 状态转换，`TransitionGroup` 动画，结果 JSON 格式化
3. **流式内容渲染** — 分段渲染，未闭合 Mermaid 块末尾显示光标
4. **内容解析** — Markdown → HTML、Mermaid → SVG、代码 → 高亮 HTML、代码一键复制
5. **Mermaid 交互** — 点击全屏查看、右键菜单（复制/下载 PNG）、渲染失败降级为代码块

**计算属性：**

| 属性 | 说明 |
|------|------|
| `toolCallList` | 综合工具调用列表 |
| `hasReasoningContent` | 是否存在思维链内容 |
| `reasoningPhase` | 思维链状态阶段 |
| `streamSegments` | 流式阶段内容分段 |
| `finalSegments` | 完成阶段内容分段 |
| `renderedReasoningContent` | 渲染后的思维链 HTML |

**关键方法：**

| 方法 | 说明 |
|------|------|
| `updateStreamingContent()` | 防抖 80ms + 互斥锁，避免并发渲染 |
| `updateFinalContent()` | 完成阶段最终渲染 |
| `copyMessage()` | 复制消息文本 |
| `copyChart()` | 复制图表为 PNG 到剪贴板 |
| `downloadChart()` | 下载图表为 PNG 文件 |

**样式特点：**

- 用户消息：紫色渐变背景（`#667eea` → `#764ba2`）
- 助手消息：白色背景带阴影
- 工具调用：蓝色（执行中）/ 绿色（完成）条纹
- 思维链：紫灰色背景，可折叠展开

---

### 5.3 ChipGridMini.vue — 网格缩略图

**Props：**

| 名称 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `grid` | `number[][]` | — | 网格数据 |
| `cellSize` | `number` | `8` | 单元格大小（px） |
| `interactive` | `boolean` | `false` | 是否可交互 |

**Emits：**

| 事件 | 参数 | 说明 |
|------|------|------|
| `cell-click` | `row, col, value` | 单元格点击 |

**颜色映射规则：**

| 值范围 | 颜色 |
|--------|------|
| `0` | 灰色（`#e0e0e0`） |
| `1–64` | 绿色渐变（HSL 120°） |
| `65+` | 蓝色渐变（HSL 210°） |

---

### 5.4 ChipPreviewPanel.vue — 悬浮预览面板

**功能概述：** 通过 `Teleport` 挂载到 `body` 的悬浮面板，实时展示芯片网格状态。

**核心特性：**

- **拖拽移动** — 通过标题栏 `pointerdown` / `pointermove` / `pointerup` 事件实现
- **最小化/展开** — 切换面板折叠状态
- **透明度调节** — 滑块控制面板透明度
- **自动轮询** — 每 30 秒更新网格数据
- **边界约束** — `x: 0 ~ innerWidth - 240`，`y: 0 ~ innerHeight - 40`
- **状态持久化** — 面板位置、透明度、展开状态保存到 `localStorage`

**使用的子组件：** ChipGridMini

**操作按钮：** 最小化、编辑（导航到 GridConfig）、关闭

---

## 6. 消息内容处理管线（message/ 模块）

### 6.1 ContentParser.ts

**导出函数：**

| 函数 | 说明 |
|------|------|
| `escapeHtml(text)` | HTML 特殊字符转义（`<`, `>`, `&`, `"`, `'`） |
| `hashContent(content)` | 内容 hash 计算，用于渲染去重 |
| `parseContent(content)` | 将原始内容分解为 `text` / `mermaid` 段落，检测未闭合 mermaid 块 |

**ContentSegment 类型：**

```typescript
{
  type: 'text' | 'mermaid'
  content: string
  rendered?: string
  id?: string
  renderError?: boolean
}
```

### 6.2 MermaidRenderer.ts

**导出函数：**

| 函数 | 说明 |
|------|------|
| `sanitizeMermaidCode(code)` | 预处理节点标签，自动为特殊字符添加引号 |
| `renderMermaidSegment(segment, hashes)` | 渲染单个 Mermaid 段落，hash 去重，10s 超时保护 |
| `renderAllMermaidSegments(segments, hashes)` | 顺序渲染所有 Mermaid 段落 |
| `addMermaidEventListeners(container, callbacks, cleanup)` | 为渲染后的 SVG 添加交互事件监听 |

**Mermaid 全局配置：**

```javascript
{ startOnLoad: false, theme: 'default', securityLevel: 'loose' }
```

**降级策略（按优先级）：**

1. 净化代码后重新渲染
2. 使用原始代码渲染
3. Highlight.js 语法高亮显示为代码块
4. HTML 转义后显示纯文本

### 6.3 SvgExporter.ts

**导出函数：**

| 函数 | 说明 |
|------|------|
| `svgToCanvas(svg)` | SVG → Canvas 转换（克隆 + 内联样式 + 高分辨率，最小尺寸 1920×720） |
| `copyChart(svg, callback)` | 复制图表为 PNG 到剪贴板（`ClipboardItem` API） |
| `downloadChart(svg, callback)` | 下载图表为 PNG 文件 |

---

## 7. 页面视图

### 7.1 ChatRoom.vue — 对话主页面

**布局结构：** 左侧边栏（280px） + 主内容区（flex 自适应）

- **侧边栏：** 标题、新建对话按钮、对话列表（可滚动）、页脚（配置入口 + 预览面板切换）
- **主区域：** 对话标题、停止/清空按钮、消息列表（`MessageBubble` 循环渲染）、输入框（`ChatInput`）

**方法：**

| 方法 | 说明 |
|------|------|
| `handleSendMessage` | 处理消息发送 |
| `createNewChat` | 创建新对话 |
| `deleteConversation` | 删除对话 |
| `goToConfig` | 跳转配置页 |
| `scrollToBottom` | 滚动到消息列表底部 |

**生命周期：** `onMounted` 加载本地配置、对话列表、自动创建新对话

---

### 7.2 ApiConfig.vue — API 配置页面

**配置项：**

| 名称 | 类型 | 范围/选项 | 说明 |
|------|------|-----------|------|
| API 类型 | Radio | `qwen` / `deepseek` | API 提供商选择 |
| API 密钥 | Password Input | — | 自动脱敏显示 |
| 模型 | Select | 动态获取 | 可用模型下拉列表 |
| 最大 Token | Slider | 256–32768 | 步长 256 |
| 温度 | Slider | 0–2 | 步长 0.1（思考模式下禁用） |
| 思考模式 | Switch | on / off | 仅 DeepSeek 可用 |
| 思考强度 | Radio | `high` / `max` | 仅思考模式启用时可选 |
| Top P | Slider | 0–1 | 步长 0.1（思考模式下禁用） |

**方法：**

| 方法 | 说明 |
|------|------|
| `loadModels` | 加载可用模型列表 |
| `handleApiTypeChange` | 切换 API 类型时重载模型 |
| `testConnection` | 测试 API 连接 |
| `saveConfig` | 保存配置到本地 |

---

### 7.3 GridConfig.vue — 网格配置页面

**布局结构：** 17×22 网格表格 + 按钮组 + 统计信息栏

**方法：**

| 方法 | 说明 |
|------|------|
| `getCellStyle` | 根据单元格值和错误状态计算样式 |
| `clampValue` | 值域约束（0–100） |
| `loadCurrentConfig` | 加载当前网格配置 |
| `resetGrid` | 重置为空白网格 |
| `resetToDefault` | 重置为默认配置 |
| `submitConfig` | 提交网格配置到后端 |

**错误处理流程：**

1. 后端返回 `errors` 数组
2. 解析 `field` 字段，正则提取行列索引
3. 存入 `errorCells` Set 集合
4. 对应单元格红色高亮显示

---

## 8. 状态管理（Pinia Stores）

### 8.1 chatStore（chat.ts，335 行）

**State：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `conversations` | `Conversation[]` | 所有对话列表 |
| `currentConversationId` | `string \| null` | 当前选中对话 ID |
| `isLoading` | `boolean` | 加载状态 |
| `isStreaming` | `boolean` | 流式传输中 |
| `error` | `string \| null` | 错误信息 |
| `eventSource` | `EventSource \| null` | SSE 连接实例 |

**Getters：**

| 名称 | 说明 |
|------|------|
| `currentConversation` | 当前对话对象 |
| `currentMessages` | 当前对话消息列表 |

**Actions：**

| 名称 | 说明 |
|------|------|
| `loadConversations` | 从 localStorage 加载对话 |
| `saveConversations` | 保存对话到 localStorage |
| `createConversation` | 创建新对话 |
| `selectConversation` | 切换当前对话 |
| `deleteConversation` | 删除对话 |
| `sendMessage` | 发送消息（初始化 SSE 流） |
| `stopGeneration` | 中止当前生成 |
| `clearCurrentConversation` | 清空当前对话消息 |

**SSE 事件处理：**

| 事件类型 | 处理逻辑 |
|----------|----------|
| `tool_status` | 推入 `executing` 状态工具调用 |
| `tool_result` | 升级为 `completed` 状态 |
| `reasoning_content` | 追加到思维链内容 |
| `delta.content` | 追加到消息内容 |
| `[DONE]` | 关闭 SSE 连接 |

**持久化 Key：** `microfluidic_conversations`

---

### 8.2 apiConfigStore（apiConfig.ts，98 行）

**State：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `currentApi` | `string` | 当前 API 类型 |
| `apiKeys` | `Record<string, string>` | API 密钥映射 |
| `modelConfig` | `object` | 模型配置 |
| `isConfigValid` | `boolean` | 配置有效性 |

`modelConfig` 包含：`model`, `maxTokens`, `temperature`, `topP`, `thinkingEnabled`, `reasoningEffort`

**Getters：**

| 名称 | 说明 |
|------|------|
| `isQwenSelected` | 是否选择通义千问 |
| `isDeepSeekSelected` | 是否选择 DeepSeek |

**Actions：**

| 名称 | 说明 |
|------|------|
| `setApiType` | 设置 API 类型 |
| `setApiKey` | 设置 API 密钥 |
| `setModelConfig` | 更新模型配置 |
| `validateConfig` | 校验配置完整性 |
| `saveConfig` | 保存到 localStorage |
| `loadConfig` | 从 localStorage 加载 |
| `getCurrentApiKey` | 获取当前 API 密钥 |

**持久化 Key：** `microfluidic_api_config`

---

### 8.3 chipLayoutStore（chipLayout.ts，130 行）

**State：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `grid` | `number[][]` | 网格数据 |
| `statistics` | `ChipStatistics` | 网格统计信息 |
| `isLoading` | `boolean` | 加载状态 |
| `lastFetchTime` | `number` | 上次获取时间戳 |
| `floatingPanel` | `FloatingPanelState` | 悬浮面板状态 |

`floatingPanel` 包含：`visible`, `minimized`, `position`, `opacity`

**Actions：**

| 名称 | 说明 |
|------|------|
| `fetchLayout` | 获取网格数据（30s 缓存） |
| `fetchStatistics` | 获取网格统计信息 |
| `notifyLayoutUpdated` | 通过 BroadcastChannel 通知其他标签页 |
| `togglePanel` | 切换面板显示/隐藏 |
| `toggleMinimize` | 切换面板最小化 |
| `setPosition` | 设置面板位置 |
| `setOpacity` | 设置面板透明度 |
| `saveFloatingPanelState` | 持久化面板状态 |
| `loadFloatingPanelState` | 加载面板状态 |

**持久化 Key：** `chip-preview-panel-state`

**跨标签页同步：** `BroadcastChannel("chip-layout-sync")`

---

## 9. API 客户端（api/index.ts，162 行）

### Axios 实例配置

```typescript
{ baseURL: '/api', timeout: 30000 }
```

### 端点函数列表

| 函数 | 方法 | 端点 | 功能 |
|------|------|------|------|
| `getSettings` | GET | `/settings` | 获取系统设置 |
| `getApiConfig` | GET | `/api/config` | 获取 API 配置 |
| `updateApiKey` | POST | `/api/key` | 更新密钥 |
| `getModels` | GET | `/api/models/{apiName}` | 获取模型列表 |
| `validateApiConfig` | GET | `/api/validate/{apiName}` | 验证配置 |
| `callApi` | POST | `/api/call` | 同步调用 |
| `initStream` | POST | `/stream/init` | 初始化流式请求 |
| `getPromptVersions` | GET | `/prompts/versions` | 提示词版本列表 |
| `getPromptModules` | GET | `/prompts/modules` | 提示词模块列表 |
| `getChipLayout` | GET | `/chip-layout` | 获取网格配置 |
| `updateChipLayout` | POST | `/chip-layout` | 更新网格配置 |
| `resetChipLayout` | POST | `/chip-layout/reset` | 重置网格配置 |
| `getChipLayoutStatistics` | GET | `/chip-layout/statistics` | 获取网格统计 |

### EventSource 管理

```typescript
createEventSource(streamId, { onMessage, onComplete, onError }) → EventSource
// 连接 /api/stream/{streamId}，解析 JSON 数据
// 收到 [DONE] 信号时自动关闭连接
```

---

## 10. 全局类型定义（types/index.ts）

| 接口 | 说明 |
|------|------|
| `Message` | 消息（含 role、content、思维链、工具调用） |
| `Conversation` | 对话（消息列表 + 元数据） |
| `ToolResult` | 工具调用结果 |
| `ToolCall` | 工具调用请求 |
| `ToolCallStatus` | 工具调用状态（executing / completed） |
| `ApiConfig` | API 配置 |
| `ApiResponse` | API 响应 |
| `ChipGrid` | 芯片网格数据 |
| `ChipStatistics` | 网格统计信息 |
| `FloatingPanelState` | 悬浮面板状态 |

---

## 11. 构建与开发配置

### Vite 配置（vite.config.ts）

| 配置项 | 值 | 说明 |
|--------|-----|------|
| 插件 | `vue()` | Vue 3 SFC 支持 |
| 路径别名 | `@ → ./src` | 模块导入简写 |
| SCSS | `modern-compiler` | 现代 SCSS 编译器 |
| 开发端口 | `3000` | 开发服务器端口 |
| 代理 | `/api → http://localhost:5000` | 后端 API 代理 |

> SSE 相关路由（`/api/stream`）代理配置中禁用缓存，确保流式数据实时传输。

### TypeScript 配置

- `target`: ES2020
- `strict`: true
- `noUnusedLocals`: true
- `noUnusedParameters`: true

### 构建命令

| 命令 | 说明 |
|------|------|
| `npm run dev` | 启动开发服务器（热更新） |
| `npm run build` | `vue-tsc` 类型检查 + `vite build` 生产构建 |
| `npm run preview` | 预览生产构建产物 |
