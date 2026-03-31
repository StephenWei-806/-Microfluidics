# 微流控后端服务

## 项目概述

微流控后端服务是一个基于 Flask 框架开发的 RESTful API 服务，主要功能包括：

- **配置管理**：基于 YAML 的配置文件系统，支持配置缓存和热更新
- **提示词管理**：多级分类、版本控制、模板渲染等功能
- **API 调用**：统一封装千问和 DeepSeek API，支持标准调用和流式调用
- **健康检查**：监控服务状态

## 环境要求

- Python 3.9 或更高版本
- pip 包管理器

## 项目结构

```
backend/
├── app.py                 # 应用入口
├── requirements.txt       # 依赖文件
├── config/                # 配置文件目录
│   ├── prompts/           # 提示词配置目录
│   │   ├── v1/
│   │   └── v2/
│   ├── api.yaml           # API 配置
│   └── settings.yaml      # 系统设置
├── controllers/           # 控制器
│   └── main_controller.py # 主控制器
├── services/              # 业务服务
│   ├── config_service.py  # 配置管理服务
│   ├── prompt_service.py  # 提示词管理服务
│   ├── api_service.py     # API 调用服务
│   └── api_client.py      # API 客户端
├── utils/                 # 工具函数
│   ├── api_utils.py       # API 工具
│   ├── common_utils.py    # 通用工具
│   └── config_utils.py    # 配置工具
└── logs/                  # 日志目录（自动创建）
```

## 快速开始

### 1. 安装依赖

在 `backend` 目录下运行：

```bash
pip install -r requirements.txt
```

### 2. 配置 API 密钥

编辑 `config/api.yaml` 文件，填写实际的 API 密钥：

```yaml
apis:
  qwen:
    api_key: "your_qwen_api_key"  # 替换为你的千问 API 密钥
  deepseek:
    api_key: "your_deepseek_api_key"  # 替换为你的 DeepSeek API 密钥
```

### 3. 启动服务

```bash
python app.py
```

服务默认运行在 `http://0.0.0.0:5000/`

### 4. 验证服务

访问以下地址验证服务是否正常运行：

```bash
curl http://localhost:5000/
```

预期响应：

```json
{
  "message": "微流控后端服务运行中",
  "version": "1.0.0",
  "status": "healthy"
}
```

## 主要 API 接口

### 健康检查

- `GET /` - 服务健康检查
- `GET /api/health` - API 健康检查

### 配置管理

- `GET /api/settings` - 获取系统设置
- `GET /api/api/config` - 获取 API 配置
- `POST /api/api/key` - 更新 API 密钥

### 提示词管理

- `GET /api/prompts/versions` - 获取提示词版本列表
- `GET /api/prompts/modules` - 获取提示词模块列表
- `GET /api/prompts/<module_name>` - 获取指定模块的提示词
- `POST /api/prompts/render` - 渲染提示词
- `GET /api/prompts/search` - 搜索提示词
- `GET /api/prompts/statistics` - 获取提示词统计信息

### API 调用

- `GET /api/api/models/<api_name>` - 获取 API 支持的模型列表
- `GET /api/api/validate/<api_name>` - 验证 API 配置是否有效
- `POST /api/api/call` - 调用 API
- `POST /api/api/stream` - 流式调用 API

## 配置说明

### settings.yaml

系统配置文件，包含以下配置项：

```yaml
server:
  host: 0.0.0.0          # 服务监听地址
  port: 5000              # 服务端口
  debug: true             # 调试模式（生产环境建议设为 false）

config:
  cache_enabled: true     # 启用配置缓存
  cache_ttl: 3600         # 缓存过期时间（秒）
  reload_interval: 60     # 配置重载间隔（秒）

logging:
  level: INFO             # 日志级别
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: logs/app.log      # 日志文件路径

api:
  timeout: 30             # API 调用超时时间（秒）
  retry_count: 3          # 重试次数
  retry_delay: 1          # 重试延迟（秒）
  rate_limit: 100         # 速率限制（每分钟调用次数）
```

## 常见问题

### 1. 依赖安装问题

**问题**：安装 PyYAML 时出现编译错误

**解决方案**：使用预编译的 PyYAML 版本，`requirements.txt` 中已指定正确版本。

### 2. 版本兼容性问题

**问题**：Flask 与 Werkzeug 版本不兼容

**解决方案**：`requirements.txt` 中已指定兼容的版本组合。

### 3. 目录不存在问题

**问题**：启动服务时出现 `No such file or directory: 'logs/app.log'` 错误

**解决方案**：服务会自动创建 logs 目录，如仍有问题可手动创建：

```bash
mkdir logs
```

### 4. API 调用失败

**问题**：API 调用返回错误

**解决方案**：
- 检查 API 密钥是否正确配置
- 检查网络连接是否正常
- 检查模型名称是否正确

### 5. 提示词渲染失败

**问题**：提示词渲染返回错误

**解决方案**：
- 检查模块名称和提示词名称是否正确
- 检查参数是否完整
- 检查提示词版本是否存在

## 技术栈

| 技术/框架 | 版本 | 用途 |
|----------|------|------|
| Python | 3.9+ | 开发语言 |
| Flask | 2.0.1 | Web 框架 |
| PyYAML | 6.0.1 | YAML 文件解析 |
| Werkzeug | 2.0.3 | WSGI 工具库 |
| Flask-Cors | 3.0.10 | CORS 支持 |
| OpenAI | 1.6.1 | OpenAI API 客户端 |
| Requests | 2.27.1 | HTTP 请求库 |

## 许可证

本项目为毕业论文项目，仅供学习和研究使用。
