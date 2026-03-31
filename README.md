# 微流控AI助手

基于 Vue 3 + Flask 的全栈 AI 对话应用。

## 项目概述

微流控AI助手是一个功能完整的AI对话应用，支持：
- 多种API配置（千问、DeepSeek）
- 实时流式对话输出
- Markdown渲染和代码高亮
- 多会话对话历史管理
- 现代化UI界面（参考豆包设计）

## 技术架构

### 前端
- Vue 3.4 + TypeScript
- Vite 5.0
- Pinia 2.1（状态管理）
- Vue Router 4.2（路由）
- Element Plus 2.4（UI组件库）
- Axios 1.6（HTTP客户端）

### 后端
- Flask 2.0.1
- PyYAML 6.0.1
- SSE（Server-Sent Events）实时通信

## 快速开始

### 前置要求

- Python 3.9+
- Node.js 18+
- npm 或 yarn

### 项目结构

```
微流控/
├── backend/          # Flask后端
├── frontend/         # Vue3前端
└── README.md         # 本文件
```

### 1. 启动后端服务

```bash
cd backend
pip install -r requirements.txt
python app.py
```

后端服务将运行在 http://localhost:5000

### 2. 启动前端服务

打开新的终端窗口：

```bash
cd frontend
npm install
npm run dev
```

前端服务将运行在 http://localhost:3000

### 3. 开始使用

1. 访问 http://localhost:3000
2. 首次使用会跳转到配置页面
3. 配置您的API密钥（千问或DeepSeek）
4. 保存配置后开始对话！

## 功能特性

### API配置页面
- 支持千问（Qwen）和DeepSeek两种API
- 可配置模型参数（最大Token数、温度、Top P）
- 连接测试功能
- 配置本地持久化

### 对话页面
- 实时流式输出
- Markdown渲染支持
- 代码高亮显示
- 消息复制功能
- 多会话管理
- 对话历史本地存储
- 停止生成功能
- 清空对话功能

## API接口

后端提供以下RESTful API接口：

| 接口 | 方法 | 功能 |
|-----|------|------|
| `/` | GET | 健康检查 |
| `/api/health` | GET | API健康检查 |
| `/api/settings` | GET | 获取系统设置 |
| `/api/api/config` | GET | 获取API配置 |
| `/api/api/key` | POST | 更新API密钥 |
| `/api/api/models/<api_name>` | GET | 获取模型列表 |
| `/api/api/validate/<api_name>` | GET | 验证API配置 |
| `/api/api/call` | POST | 调用API |
| `/api/api/stream` | POST | 流式调用API（SSE） |
| `/api/prompts/*` | * | 提示词管理接口 |

详细API文档请参考 `backend/API文档.md`

## 配置说明

### 后端配置

编辑 `backend/config/api.yaml` 文件配置API密钥：

```yaml
apis:
  qwen:
    api_key: "your_qwen_api_key"
  deepseek:
    api_key: "your_deepseek_api_key"
```

### 前端配置

前端配置通过UI界面进行，会自动保存到localStorage。

## 开发指南

### 后端开发

```bash
cd backend
# 安装依赖
pip install -r requirements.txt
# 启动开发服务器
python app.py
```

### 前端开发

```bash
cd frontend
# 安装依赖
npm install
# 启动开发服务器
npm run dev
# 构建生产版本
npm run build
```

## 常见问题

### 后端启动失败

- 确保Python版本 >= 3.9
- 确保已安装所有依赖：`pip install -r requirements.txt`
- 检查端口5000是否被占用

### 前端启动失败

- 确保Node.js版本 >= 18
- 确保已安装所有依赖：`npm install`
- 检查端口3000是否被占用

### API调用失败

- 检查API密钥是否正确配置
- 检查网络连接
- 确认API服务可用

### 对话没有实时输出

- 确认使用的是 `/api/api/stream` 接口
- 检查浏览器是否支持SSE
- 查看浏览器控制台错误信息

## 许可证

本项目为毕业论文项目，仅供学习和研究使用。
