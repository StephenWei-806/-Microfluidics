# 微流控后端API接口文档

## 1. 项目概述

微流控后端服务是一个基于Flask框架开发的RESTful API服务，主要提供以下功能：

- 配置管理：加载和管理YAML配置文件
- 提示词管理：多级分类、版本控制、模板渲染
- API调用：统一封装千问和DeepSeek API，支持标准调用和流式调用
- 健康检查：监控服务状态

## 2. 接口列表

| 接口路径 | 请求方法 | 功能描述 |
|---------|---------|--------|
| `/` | GET | 服务健康检查 |
| `/api/health` | GET | 服务健康检查 |
| `/api/settings` | GET | 获取系统设置 |
| `/api/api/config` | GET | 获取API配置 |
| `/api/api/key` | POST | 更新API密钥 |
| `/api/api/models/<api_name>` | GET | 获取API支持的模型列表 |
| `/api/api/validate/<api_name>` | GET | 验证API配置是否有效 |
| `/api/api/call` | POST | 调用API |
| `/api/api/stream` | POST | 流式调用API |
| `/api/prompts/versions` | GET | 获取提示词版本列表 |
| `/api/prompts/modules` | GET | 获取提示词模块列表 |
| `/api/prompts/<module_name>` | GET | 获取指定模块的提示词 |
| `/api/prompts/render` | POST | 渲染提示词 |
| `/api/prompts/search` | GET | 搜索提示词 |
| `/api/prompts/statistics` | GET | 获取提示词统计信息 |

## 3. 接口详细说明

### 3.1 健康检查

#### 接口路径：`/`
#### 请求方法：GET

**返回值格式：**

```json
{
  "message": "微流控后端服务运行中",
  "version": "1.0.0",
  "status": "healthy"
}
```

#### 接口路径：`/api/health`
#### 请求方法：GET

**返回值格式：**

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

### 3.2 系统设置

#### 接口路径：`/api/settings`
#### 请求方法：GET

**返回值格式：**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "server": {
      "host": "0.0.0.0",
      "port": 5000,
      "debug": true
    },
    "config": {
      "cache_enabled": true,
      "cache_ttl": 3600,
      "reload_interval": 60
    },
    "logging": {
      "level": "INFO",
      "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
      "file": "logs/app.log"
    },
    "api": {
      "timeout": 30,
      "retry_count": 3,
      "retry_delay": 1,
      "rate_limit": 100
    }
  }
}
```

### 3.3 API配置管理

#### 接口路径：`/api/api/config`
#### 请求方法：GET

**返回值格式：**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "apis": {
      "qwen": {
        "name": "qwen",
        "base_url": "https://dashscope.aliyuncs.com/api/v1",
        "api_key": "your_qwen_api_key",
        "timeout": 30,
        "retry_count": 3,
        "models": [
          {
            "name": "qwen-turbo",
            "max_tokens": 1024
          },
          {
            "name": "qwen-plus",
            "max_tokens": 2048
          }
        ]
      },
      "deepseek": {
        "name": "deepseek",
        "base_url": "https://api.deepseek.com/v1",
        "api_key": "your_deepseek_api_key",
        "timeout": 30,
        "retry_count": 3,
        "models": [
          {
            "name": "deepseek-chat",
            "max_tokens": 1024
          },
          {
            "name": "deepseek-llm",
            "max_tokens": 2048
          }
        ]
      }
    },
    "global": {
      "timeout": 30,
      "retry_delay": 1,
      "rate_limit": 100
    }
  }
}
```

#### 接口路径：`/api/api/key`
#### 请求方法：POST

**请求参数：**

| 参数名 | 类型 | 必填 | 描述 |
|-------|------|------|------|
| api_name | string | 是 | API名称，如 "qwen" 或 "deepseek" |
| api_key | string | 是 | 新的API密钥 |

**请求示例：**

```json
{
  "api_name": "qwen",
  "api_key": "new_qwen_api_key"
}
```

**返回值格式：**

```json
{
  "code": 200,
  "message": "更新成功",
  "data": {
    "api_name": "qwen"
  }
}
```

#### 接口路径：`/api/api/models/<api_name>`
#### 请求方法：GET

**路径参数：**

| 参数名 | 类型 | 必填 | 描述 |
|-------|------|------|------|
| api_name | string | 是 | API名称，如 "qwen" 或 "deepseek" |

**返回值格式：**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "api_name": "qwen",
    "models": ["qwen-turbo", "qwen-plus"]
  }
}
```

#### 接口路径：`/api/api/validate/<api_name>`
#### 请求方法：GET

**路径参数：**

| 参数名 | 类型 | 必填 | 描述 |
|-------|------|------|------|
| api_name | string | 是 | API名称，如 "qwen" 或 "deepseek" |

**返回值格式：**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "api_name": "qwen",
    "valid": true
  }
}
```

### 3.4 API调用

#### 接口路径：`/api/api/call`
#### 请求方法：POST

**请求参数：**

| 参数名 | 类型 | 必填 | 描述 | 默认值 |
|-------|------|------|------|--------|
| api_name | string | 是 | API名称，如 "qwen" 或 "deepseek" | - |
| model | string | 是 | 模型名称 | - |
| prompt | string | 是 | 提示词 | - |
| max_tokens | integer | 否 | 最大令牌数 | 1024 |
| temperature | number | 否 | 温度参数 | 0.7 |

**请求示例：**

```json
{
  "api_name": "qwen",
  "model": "qwen-turbo",
  "prompt": "请生成一段关于人工智能的介绍",
  "max_tokens": 500,
  "temperature": 0.7
}
```

**返回值格式：**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "id": "chatcmpl-123",
    "object": "chat.completion",
    "created": 1677858242,
    "model": "qwen-turbo",
    "choices": [
      {
        "index": 0,
        "message": {
          "role": "assistant",
          "content": "人工智能（Artificial Intelligence，简称AI）是指通过计算机程序模拟人类智能的技术..."
        },
        "finish_reason": "stop"
      }
    ],
    "usage": {
      "prompt_tokens": 10,
      "completion_tokens": 150,
      "total_tokens": 160
    }
  }
}
```

#### 接口路径：`/api/api/stream`
#### 请求方法：POST

**请求参数：**

| 参数名 | 类型 | 必填 | 描述 | 默认值 |
|-------|------|------|------|--------|
| api_name | string | 是 | API名称，如 "qwen" 或 "deepseek" | - |
| model | string | 是 | 模型名称 | - |
| prompt | string | 是 | 提示词 | - |
| max_tokens | integer | 否 | 最大令牌数 | 1024 |
| temperature | number | 否 | 温度参数 | 0.7 |

**请求示例：**

```json
{
  "api_name": "qwen",
  "model": "qwen-turbo",
  "prompt": "请生成一段关于人工智能的介绍",
  "max_tokens": 500,
  "temperature": 0.7
}
```

**返回值格式：**

流式响应，使用Server-Sent Events格式：

```
data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677858242,"model":"qwen-turbo","choices":[{"index":0,"delta":{"role":"assistant","content":"人工智能"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677858242,"model":"qwen-turbo","choices":[{"index":0,"delta":{"content":"（Artificial Intelligence，简称AI）是指通过计算机程序模拟人类智能的技术"},"finish_reason":null}]}

data: {"id":"chatcmpl-123","object":"chat.completion.chunk","created":1677858242,"model":"qwen-turbo","choices":[{"index":0,"delta":{"content":"..."},"finish_reason":"stop"}]}

data: [DONE]
```

### 3.5 提示词管理

#### 接口路径：`/api/prompts/versions`
#### 请求方法：GET

**返回值格式：**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "versions": ["v1", "v2"],
    "history": [
      {
        "version": "v1",
        "description": "基础提示词模板",
        "config_version": "1.0"
      },
      {
        "version": "v2",
        "description": "增强版提示词模板",
        "config_version": "2.0"
      }
    ]
  }
}
```

#### 接口路径：`/api/prompts/modules`
#### 请求方法：GET

**查询参数：**

| 参数名 | 类型 | 必填 | 描述 | 默认值 |
|-------|------|------|------|--------|
| version | string | 否 | 提示词版本 | "v1" |

**返回值格式：**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "ppt": {
      "name": "PPT生成",
      "description": "用于生成PPT内容的提示词",
      "prompts": {
        "title": {
          "name": "标题生成",
          "description": "为PPT生成吸引人的标题",
          "template": "请为主题 '{topic}' 生成5个吸引人的PPT标题，要求简洁明了，突出主题。"
        },
        "outline": {
          "name": "大纲生成",
          "description": "为PPT生成详细的大纲",
          "template": "请为主题 '{topic}' 生成一个详细的PPT大纲，包含标题和每个章节的主要内容，要求结构清晰，逻辑连贯。"
        }
      }
    },
    "copywriting": {
      "name": "文案生成",
      "description": "用于生成各种文案的提示词",
      "prompts": {
        "marketing": {
          "name": "营销文案",
          "description": "生成产品营销文案",
          "template": "请为产品 '{product}' 生成一段营销文案，突出产品特点和优势，吸引目标客户。"
        }
      }
    }
  }
}
```

#### 接口路径：`/api/prompts/<module_name>`
#### 请求方法：GET

**路径参数：**

| 参数名 | 类型 | 必填 | 描述 |
|-------|------|------|------|
| module_name | string | 是 | 模块名称，如 "ppt" 或 "copywriting" |

**查询参数：**

| 参数名 | 类型 | 必填 | 描述 | 默认值 |
|-------|------|------|------|--------|
| version | string | 否 | 提示词版本 | "v1" |

**返回值格式：**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "title": {
      "name": "标题生成",
      "description": "为PPT生成吸引人的标题",
      "template": "请为主题 '{topic}' 生成5个吸引人的PPT标题，要求简洁明了，突出主题。"
    },
    "outline": {
      "name": "大纲生成",
      "description": "为PPT生成详细的大纲",
      "template": "请为主题 '{topic}' 生成一个详细的PPT大纲，包含标题和每个章节的主要内容，要求结构清晰，逻辑连贯。"
    }
  }
}
```

#### 接口路径：`/api/prompts/render`
#### 请求方法：POST

**请求参数：**

| 参数名 | 类型 | 必填 | 描述 | 默认值 |
|-------|------|------|------|--------|
| module_name | string | 是 | 模块名称，如 "ppt" | - |
| prompt_name | string | 是 | 提示词名称，如 "title" | - |
| params | object | 是 | 提示词参数，如 {"topic": "人工智能"} | - |
| version | string | 否 | 提示词版本 | "v1" |

**请求示例：**

```json
{
  "module_name": "ppt",
  "prompt_name": "title",
  "params": {
    "topic": "人工智能发展趋势"
  },
  "version": "v1"
}
```

**返回值格式：**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "prompt": "请为主题 '人工智能发展趋势' 生成5个吸引人的PPT标题，要求简洁明了，突出主题。"
  }
}
```

#### 接口路径：`/api/prompts/search`
#### 请求方法：GET

**查询参数：**

| 参数名 | 类型 | 必填 | 描述 | 默认值 |
|-------|------|------|------|--------|
| keyword | string | 是 | 搜索关键词 | - |
| version | string | 否 | 提示词版本 | "v1" |

**返回值格式：**

```json
{
  "code": 200,
  "message": "ok",
  "data": [
    {
      "module": "ppt",
      "name": "title",
      "prompt": {
        "name": "标题生成",
        "description": "为PPT生成吸引人的标题",
        "template": "请为主题 '{topic}' 生成5个吸引人的PPT标题，要求简洁明了，突出主题。"
      }
    }
  ]
}
```

#### 接口路径：`/api/prompts/statistics`
#### 请求方法：GET

**查询参数：**

| 参数名 | 类型 | 必填 | 描述 | 默认值 |
|-------|------|------|------|--------|
| version | string | 否 | 提示词版本 | "v1" |

**返回值格式：**

```json
{
  "code": 200,
  "message": "ok",
  "data": {
    "total_modules": 2,
    "total_prompts": 3,
    "prompts_by_module": {
      "ppt": 2,
      "copywriting": 1
    }
  }
}
```

## 4. 错误码表

| 错误码 | 描述 |
|-------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 5. 速率限制

- 每个API每分钟最多调用100次
- 超过速率限制时，接口会返回错误信息

## 6. 认证方式

目前API接口不需要认证，直接调用即可。

## 7. 最佳实践

1. 建议使用流式调用API获取实时响应
2. 在调用API前，建议先验证API配置是否有效
3. 合理设置max_tokens和temperature参数，以获得最佳效果
4. 对于频繁调用的场景，建议实现本地缓存，减少API调用次数

## 8. 常见问题

### 8.1 API调用失败

- 检查API密钥是否正确配置
- 检查网络连接是否正常
- 检查模型名称是否正确

### 8.2 提示词渲染失败

- 检查模块名称和提示词名称是否正确
- 检查参数是否完整
- 检查提示词版本是否存在

### 8.3 速率限制

- 如遇到速率限制错误，请稍后再试
- 建议实现指数退避重试策略
