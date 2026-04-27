# 微流控后端 API 接口文档

## 基础信息

| 项目 | 说明 |
|------|------|
| 基础 URL | `http://localhost:5000/api` |
| 协议 | HTTP / SSE |
| 数据格式 | JSON |
| 字符编码 | UTF-8 |

## 统一响应格式

### 成功响应

```json
{
  "code": 200,
  "message": "ok",
  "data": { ... }
}
```

### 错误响应

```json
{
  "code": 400,
  "message": "错误描述"
}
```

> 错误码遵循 HTTP 标准状态码，常见值为 `400`、`404`、`500`。

---

## 一、健康检查接口（3 个）

### 1. 根路由健康检查

| 项目 | 说明 |
|------|------|
| 路径 | `/` |
| 方法 | `GET` |
| 说明 | 根路由，不在 `/api` 前缀下 |

**响应示例**

```json
{
  "message": "微流控后端服务运行中",
  "version": "1.0.0",
  "status": "healthy"
}
```

---

### 2. 服务健康状态

| 项目 | 说明 |
|------|------|
| 路径 | `/api/health` |
| 方法 | `GET` |
| 说明 | 检查服务是否正常运行 |

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "status": "healthy",
    "service": "微流控后端服务"
  }
}
```

---

### 3. 获取系统设置

| 项目 | 说明 |
|------|------|
| 路径 | `/api/settings` |
| 方法 | `GET` |
| 说明 | 返回完整的 `settings.yaml` 配置内容 |

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "server": { "host": "0.0.0.0", "port": 5000, "debug": true },
    "config": { "prompts_dir": "config/prompts", "default_version": "v1" },
    "logging": { "level": "DEBUG", "file": "logs/app.log" },
    "api": { "timeout": 30, "max_retries": 3 },
    "serial": { "port": "COM3", "baudrate": 115200 }
  }
}
```

---

## 二、API 管理接口（5 个）

### 4. 获取 API 配置

| 项目 | 说明 |
|------|------|
| 路径 | `/api/api/config` |
| 方法 | `GET` |
| 说明 | 返回所有 API 配置信息，`api_key` 字段脱敏显示 |

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "qwen": {
      "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
      "api_key": "sk-****xxx",
      "models": ["qwen-plus", "qwen-turbo", "qwen-max"]
    },
    "deepseek": {
      "base_url": "https://api.deepseek.com/v1",
      "api_key": "sk-****xxx",
      "models": ["deepseek-chat", "deepseek-reasoner"]
    }
  }
}
```

---

### 5. 更新 API 密钥

| 项目 | 说明 |
|------|------|
| 路径 | `/api/api/key` |
| 方法 | `POST` |
| Content-Type | `application/json` |

**请求参数**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `api_name` | string | 是 | API 名称，可选值：`qwen`、`deepseek` |
| `api_key` | string | 是 | 新的 API 密钥 |

**请求示例**

```json
{
  "api_name": "qwen",
  "api_key": "sk-xxxxxxxxxxxxxxxx"
}
```

**成功响应**

```json
{
  "code": 200,
  "message": "API密钥更新成功"
}
```

**错误响应（400）**

```json
{
  "code": 400,
  "message": "缺少必要参数: api_name, api_key"
}
```

---

### 6. 获取模型列表

| 项目 | 说明 |
|------|------|
| 路径 | `/api/api/models/<api_name>` |
| 方法 | `GET` |

**路径参数**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `api_name` | string | API 名称，可选值：`qwen`、`deepseek` |

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "models": ["qwen-plus", "qwen-turbo", "qwen-max"]
  }
}
```

---

### 7. 验证 API 配置

| 项目 | 说明 |
|------|------|
| 路径 | `/api/api/validate/<api_name>` |
| 方法 | `GET` |

**路径参数**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `api_name` | string | API 名称，可选值：`qwen`、`deepseek` |

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "valid": true,
    "message": "API配置验证通过"
  }
}
```

---

### 8. 同步调用 API

| 项目 | 说明 |
|------|------|
| 路径 | `/api/api/call` |
| 方法 | `POST` |
| Content-Type | `application/json` |

**请求参数**

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `api_name` | string | 是 | — | API 名称 |
| `model` | string | 是 | — | 模型名称 |
| `prompt` | string | 是 | — | 用户问题 |
| `max_tokens` | integer | 否 | 1024 | 最大生成 token 数 |
| `temperature` | float | 否 | 0.7 | 温度参数（0-2） |

**请求示例**

```json
{
  "api_name": "deepseek",
  "model": "deepseek-v4-flash",
  "prompt": "用户问题",
  "max_tokens": 1024,
  "temperature": 0.7
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "id": "chatcmpl-xxxxx",
    "object": "chat.completion",
    "choices": [
      {
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "回答内容"
        },
        "finish_reason": "stop"
      }
    ],
    "usage": {
      "prompt_tokens": 10,
      "completion_tokens": 50,
      "total_tokens": 60
    }
  }
}
```

---

## 三、流式通信接口（3 个）

### 9. 初始化流式请求

| 项目 | 说明 |
|------|------|
| 路径 | `/api/stream/init` |
| 方法 | `POST` |
| Content-Type | `application/json` |
| 说明 | 两步式流式调用的第一步，返回 `stream_id` |

**请求参数**

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `api_name` | string | 是 | — | API 名称 |
| `model` | string | 是 | — | 模型名称 |
| `prompt` | string | 是 | — | 用户输入 |
| `max_tokens` | integer | 否 | 1024 | 最大生成 token 数 |
| `temperature` | float | 否 | 0.7 | 温度参数 |
| `top_p` | float | 否 | 1.0 | 核采样参数 |
| `tools_enabled` | boolean | 否 | true | 是否启用工具调用 |
| `thinking_enabled` | boolean | 否 | false | 是否启用思维链 |
| `reasoning_effort` | string | 否 | "high" | 推理深度：`low`/`medium`/`high` |
| `history_messages` | array | 否 | [] | 历史对话消息列表 |

**请求示例**

```json
{
  "api_name": "deepseek",
  "model": "deepseek-v4-flash",
  "prompt": "用户输入",
  "max_tokens": 1024,
  "temperature": 0.7,
  "top_p": 1.0,
  "tools_enabled": true,
  "thinking_enabled": false,
  "reasoning_effort": "high",
  "history_messages": [
    { "role": "user", "content": "你好" },
    { "role": "assistant", "content": "你好！有什么可以帮助你的？" }
  ]
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "stream_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

---

### 10. 建立 SSE 连接

| 项目 | 说明 |
|------|------|
| 路径 | `/api/stream/<stream_id>` |
| 方法 | `GET` |
| 响应类型 | `text/event-stream` |
| 说明 | 两步式流式调用的第二步，通过 `stream_id` 建立 SSE 长连接 |

**路径参数**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `stream_id` | string | 由 `/api/stream/init` 返回的流式请求 ID |

**SSE 事件格式**

文本内容推送：

```
data: {"choices": [{"delta": {"content": "文本片段"}}]}
```

思维链内容推送（DeepSeek 模型）：

```
data: {"choices": [{"delta": {"reasoning_content": "思考过程内容"}}]}
```

工具状态通知：

```
data: {"type": "tool_status", "message": "正在执行: dispense_droplet..."}
```

工具执行结果：

```
data: {"type": "tool_result", "tool_name": "dispense_droplet", "result": "液滴分配成功"}
```

流结束标志：

```
data: [DONE]
```

---

### 11. 直接流式调用

| 项目 | 说明 |
|------|------|
| 路径 | `/api/stream` |
| 方法 | `POST` |
| Content-Type | `application/json` |
| 响应类型 | `text/event-stream` |
| 说明 | 一步式替代方案，无需 `stream_id`，直接返回 SSE 流 |

**请求参数**

与 [9. 初始化流式请求](#9-初始化流式请求) 完全一致。

**请求示例**

```json
{
  "api_name": "deepseek",
  "model": "deepseek-v4-flash",
  "prompt": "用户输入",
  "max_tokens": 1024,
  "temperature": 0.7,
  "tools_enabled": true
}
```

**SSE 事件格式**

与 [10. 建立 SSE 连接](#10-建立-sse-连接) 完全一致。

---

## 四、提示词管理接口（6 个）

### 12. 获取版本列表

| 项目 | 说明 |
|------|------|
| 路径 | `/api/prompts/versions` |
| 方法 | `GET` |
| 说明 | 获取所有可用的提示词版本 |

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "versions": ["v1"]
  }
}
```

---

### 13. 获取模块列表

| 项目 | 说明 |
|------|------|
| 路径 | `/api/prompts/modules` |
| 方法 | `GET` |

**查询参数**

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `version` | string | 否 | v1 | 提示词版本 |

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "modules": ["ppt", "system", "tools"]
  }
}
```

---

### 14. 获取模块提示词

| 项目 | 说明 |
|------|------|
| 路径 | `/api/prompts/<module_name>` |
| 方法 | `GET` |

**路径参数**

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `module_name` | string | 模块名称 |

**查询参数**

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `version` | string | 否 | v1 | 提示词版本 |

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "module": "ppt",
    "prompts": {
      "title": "生成PPT标题的提示词模板...",
      "outline": "生成PPT大纲的提示词模板..."
    }
  }
}
```

---

### 15. 渲染提示词

| 项目 | 说明 |
|------|------|
| 路径 | `/api/prompts/render` |
| 方法 | `POST` |
| Content-Type | `application/json` |
| 说明 | 使用参数渲染提示词模板 |

**请求参数**

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `module_name` | string | 是 | — | 模块名称 |
| `prompt_name` | string | 是 | — | 提示词名称 |
| `params` | object | 否 | {} | 模板渲染参数 |
| `version` | string | 否 | v1 | 提示词版本 |

**请求示例**

```json
{
  "module_name": "ppt",
  "prompt_name": "title",
  "params": { "topic": "AI" },
  "version": "v1"
}
```

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "prompt": "渲染后的提示词文本"
  }
}
```

---

### 16. 搜索提示词

| 项目 | 说明 |
|------|------|
| 路径 | `/api/prompts/search` |
| 方法 | `GET` |

**查询参数**

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `keyword` | string | 是 | — | 搜索关键词 |
| `version` | string | 否 | v1 | 提示词版本 |

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "results": [
      {
        "module": "ppt",
        "name": "title",
        "content": "匹配的提示词内容..."
      }
    ]
  }
}
```

---

### 17. 获取统计信息

| 项目 | 说明 |
|------|------|
| 路径 | `/api/prompts/statistics` |
| 方法 | `GET` |

**查询参数**

| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `version` | string | 否 | v1 | 提示词版本 |

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "version": "v1",
    "module_count": 3,
    "prompt_count": 12,
    "modules": {
      "ppt": 4,
      "system": 5,
      "tools": 3
    }
  }
}
```

---

## 五、芯片布局接口（4 个）

### 18. 获取当前芯片网格配置

| 项目 | 说明 |
|------|------|
| 路径 | `/api/chip-layout` |
| 方法 | `GET` |
| 说明 | 获取当前芯片的网格配置数据 |

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "grid": [
      [0, 0, 1, 2, 0, "..."],
      ["... 共 17 行，每行 22 列"]
    ],
    "description": "自定义配置"
  }
}
```

> 网格为 17×22 的二维数组，单元格值范围 0-128。

---

### 19. 更新芯片网格配置

| 项目 | 说明 |
|------|------|
| 路径 | `/api/chip-layout` |
| 方法 | `POST` |
| Content-Type | `application/json` |

**请求参数**

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `grid` | array | 是 | 17×22 二维数组，单元格值范围 0-128 |

**请求示例**

```json
{
  "grid": [
    [0, 0, 1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "... 共 17 行"
  ]
}
```

**成功响应**

```json
{
  "code": 200,
  "message": "配置更新成功"
}
```

**验证失败响应（400）**

```json
{
  "code": 400,
  "message": "网格数据验证失败",
  "errors": [
    { "field": "grid[0][3]", "message": "值必须在 0-128 之间" }
  ]
}
```

---

### 20. 重置为默认配置

| 项目 | 说明 |
|------|------|
| 路径 | `/api/chip-layout/reset` |
| 方法 | `POST` |
| 说明 | 将芯片网格重置为系统默认配置 |

**响应示例**

```json
{
  "code": 200,
  "message": "已重置为默认配置"
}
```

---

### 21. 获取网格统计信息

| 项目 | 说明 |
|------|------|
| 路径 | `/api/chip-layout/statistics` |
| 方法 | `GET` |
| 说明 | 获取当前网格的统计分析数据 |

**响应示例**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "total_cells": 374,
    "reachable_cells": 128,
    "forbidden_cells": 246,
    "rows": 17,
    "cols": 22,
    "is_custom": true,
    "description": "自定义配置"
  }
}
```

---

## 附录

### A. 通用错误码表

| 错误码 | 含义 | 说明 |
|--------|------|------|
| 200 | 成功 | 请求处理成功 |
| 400 | 请求错误 | 参数缺失、格式错误或验证失败 |
| 404 | 未找到 | 请求的资源不存在 |
| 500 | 服务器错误 | 服务端内部异常 |

### B. SSE 事件类型汇总表

| 事件数据格式 | 说明 | 触发场景 |
|-------------|------|---------|
| `{"choices": [{"delta": {"content": "..."}}]}` | 文本内容推送 | 模型生成文本时逐块推送 |
| `{"choices": [{"delta": {"reasoning_content": "..."}}]}` | 思维链内容推送 | DeepSeek 模型启用 `thinking_enabled` 时推送推理过程 |
| `{"type": "tool_status", "message": "..."}` | 工具执行状态 | 工具调用开始或执行中 |
| `{"type": "tool_result", "tool_name": "...", "result": "..."}` | 工具执行结果 | 工具调用完成后返回结果 |
| `[DONE]` | 流结束标志 | 整个流式响应结束 |

> 所有 SSE 事件均以 `data: ` 为前缀，每条事件以双换行符 `\n\n` 结尾。

### C. 注意事项

1. **CORS 策略**：后端已启用 CORS，允许所有来源访问（`Access-Control-Allow-Origin: *`）。生产环境部署时应限制为指定域名。

2. **流式超时**：SSE 连接默认无超时限制。客户端应实现断线重连机制，推荐使用 `EventSource` API 或自定义 `fetch` + `ReadableStream`。

3. **stream_id 有效期**：通过 `/api/stream/init` 获取的 `stream_id` 为一次性使用，获取后应立即建立 SSE 连接。

4. **请求体编码**：所有 POST 请求的 `Content-Type` 必须为 `application/json`，请求体使用 UTF-8 编码。

5. **API 密钥安全**：`GET /api/api/config` 返回的 `api_key` 为脱敏值，仅显示末尾部分字符。完整密钥仅在更新时通过 POST 提交。

6. **网格数据约束**：芯片网格固定为 17 行 × 22 列，单元格值为整数，范围 0-128。`0` 表示禁止区域，其他值表示可达电极编号。
