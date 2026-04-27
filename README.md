# 微流控液滴路径规划系统

基于 AI 大模型的微流控液滴路径规划系统，通过自然语言交互实现芯片网格配置、液滴路径规划和硬件控制。

## 核心能力

- **AI 对话** — 支持千问和 DeepSeek 双模型
- **SSE 实时流式通信** — 服务端推送，逐字输出
- **Mermaid 流程图可视化** — 自动渲染，多层降级容错
- **Agent Loop 工具调用** — AI 自动调用硬件控制工具
- **芯片网格配置与管理** — 17×22 可视化编辑
- **思维链展示** — DeepSeek Thinking Mode 推理过程可视化

---

## 功能特性

### AI 智能对话

多模型支持（千问、DeepSeek），SSE 流式响应，DeepSeek 思维链展示，Markdown 富文本渲染。

### 芯片网格配置

17×22 网格可视化编辑，实时统计各类型单元格数量，多标签页同步更新。

### Mermaid 图表

AI 回复中的流程图自动渲染，支持复制 / 下载为 PNG，多层降级容错保证渲染稳定性。

### 工具调用（Agent Loop）

AI 自动调用 `dispense_droplet` 工具控制芯片硬件，实现液滴分配的闭环自动化。

### 提示词模板系统

版本化管理（`config/prompts/v1/`），动态渲染，芯片布局自动注入上下文。

### 悬浮预览面板

可拖拽、可最小化、透明度可调的芯片网格预览面板，在对话过程中随时查看芯片状态。

---

## 技术栈

### 后端

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.8+ | 运行时 |
| Flask | 2.0.1 | Web 框架 |
| OpenAI SDK | ≥ 2.32.0 | AI 模型调用（DeepSeek 兼容） |
| PyYAML | 6.0.1 | 配置管理 |
| Flask-Cors | 3.0.10 | 跨域支持 |

### 前端

| 依赖 | 版本 | 用途 |
|------|------|------|
| Vue | 3.4.21 | UI 框架 |
| TypeScript | 5.4.2 | 类型系统 |
| Vite | 5.1.6 | 构建工具 |
| Pinia | 2.1.7 | 状态管理 |
| Vue Router | 4.3.0 | 路由管理 |
| Element Plus | 2.5.6 | UI 组件库 |
| Axios | 1.6.7 | HTTP 客户端 |
| Marked | 12.0.0 | Markdown 渲染 |
| Mermaid | 11.13.0 | 流程图渲染 |
| Highlight.js | 11.9.0 | 代码高亮 |

---

## 项目目录结构

```
微流控/
├── backend/                    # 后端服务
│   ├── app.py                 # Flask 应用入口
│   ├── controllers/           # 控制器层（5个控制器）
│   │   ├── api_controller.py
│   │   ├── stream_controller.py
│   │   ├── chip_layout_controller.py
│   │   ├── prompt_controller.py
│   │   └── health_controller.py
│   ├── services/              # 服务层（7个服务）
│   │   ├── api_service.py
│   │   ├── api_client.py
│   │   ├── chip_layout_service.py
│   │   ├── config_service.py
│   │   ├── prompt_service.py
│   │   ├── droplet_tool_service.py
│   │   └── tool_registry.py
│   ├── utils/                 # 工具类
│   ├── config/                # 配置文件
│   │   ├── api.yaml          # API 配置
│   │   ├── settings.yaml     # 系统设置
│   │   └── prompts/v1/       # 提示词模板
│   └── data/                  # 数据持久化
├── frontend/                   # 前端应用
│   ├── src/
│   │   ├── api/              # API 客户端
│   │   │   └── index.ts
│   │   ├── components/       # 可复用组件
│   │   │   ├── ChatInput.vue
│   │   │   ├── MessageBubble.vue
│   │   │   ├── ChipGridMini.vue
│   │   │   ├── ChipPreviewPanel.vue
│   │   │   └── message/      # 消息解析与渲染
│   │   ├── views/            # 页面视图（3个）
│   │   │   ├── ChatRoom.vue
│   │   │   ├── ApiConfig.vue
│   │   │   └── GridConfig.vue
│   │   ├── stores/           # Pinia 状态管理（3个）
│   │   │   ├── chat.ts
│   │   │   ├── apiConfig.ts
│   │   │   └── chipLayout.ts
│   │   ├── types/            # TypeScript 类型定义
│   │   └── router/           # 路由配置
│   └── ...
└── data/                       # 全局数据
    └── chip_layout.json       # 芯片布局持久化
```

---

## 快速开始

### 环境要求

- Python 3.8+
- Node.js 16+
- npm 或 yarn

### 后端启动

```bash
cd backend
pip install -r requirements.txt
python app.py
# 后端运行在 http://localhost:5000
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
# 前端运行在 http://localhost:3000
# API 代理自动指向后端 localhost:5000
```

### 配置 API 密钥

1. 启动后访问 http://localhost:3000/config
2. 选择 API 类型（千问 / DeepSeek）
3. 填入 API 密钥并保存

---

## 使用指南

**对话功能：** 首页即为对话页面，输入问题即可获得 AI 流式回复，DeepSeek 模型支持展开查看思维链。

**网格配置：** 侧边栏点击「预览切换」显示悬浮面板，点击「编辑」进入网格配置页面，支持 17×22 网格逐格编辑。

**Mermaid 图表：** AI 回复中的 Mermaid 图表自动渲染，可点击全屏查看，右键可复制 / 下载为 PNG。

---

## 路由页面

| 路径 | 页面 | 功能 |
|------|------|------|
| `/chat` | 对话室 | 主对话页面，支持多会话 |
| `/config` | API 配置 | 配置 API 密钥、模型参数 |
| `/grid-config` | 网格配置 | 编辑 17×22 芯片网格 |

---

## 项目架构

```
用户浏览器 (Vue 3 SPA)
    ↕ HTTP / SSE
Vite Dev Server (端口 3000, 代理 /api → 5000)
    ↕
Flask 后端 (端口 5000)
    ↕
AI API (千问 / DeepSeek) + 串口硬件
```

---

## 浏览器兼容性

| 浏览器 | 最低版本 |
|--------|----------|
| Chrome | 88+ |
| Firefox | 78+ |
| Safari | 14+ |
| Edge | 88+ |
