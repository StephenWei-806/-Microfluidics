# 微流控AI助手 - 前端

基于 Vue 3 + TypeScript + Vite 开发的前端应用。

## 技术栈

- Vue 3.4+
- TypeScript 5.3+
- Vite 5.0+
- Pinia 2.1+
- Vue Router 4.2+
- Element Plus 2.4+
- Axios 1.6+

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

访问 http://localhost:3000

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

## 功能特性

- API 配置页面：支持千问和 DeepSeek 两种 API
- 对话页面：实时流式输出，Markdown 渲染，代码高亮
- 对话历史管理：本地存储，支持多会话
- 响应式设计：现代化 UI 界面

## 项目结构

```
src/
├── api/              # API 接口
├── assets/           # 静态资源
├── components/       # 公共组件
├── router/           # 路由配置
├── stores/           # Pinia 状态管理
├── types/            # TypeScript 类型
├── views/            # 页面组件
├── App.vue
└── main.ts
```
