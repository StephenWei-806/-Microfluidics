# 微流控液滴路径规划 — 后端服务架构文档

## 1. 后端架构概览

### 分层架构

```
Controllers（表现层）→ Services（业务层）→ Utils/Config（基础层）
```

### 技术栈

- Python + Flask 2.0.1
- OpenAI SDK >= 2.32.0
- PyYAML 6.0.1
- Flask-Cors 3.0.10
- Requests 2.27.1

### 目录结构

```
backend/
├── app.py                    # 应用入口
├── requirements.txt          # 依赖清单
├── controllers/              # 控制器（5个蓝图）
│   ├── __init__.py          # 蓝图注册中心
│   ├── base.py              # SSE 头、错误装饰器
│   ├── health_controller.py
│   ├── api_controller.py
│   ├── stream_controller.py
│   ├── prompt_controller.py
│   └── chip_layout_controller.py
├── services/                 # 服务层（7个服务）
│   ├── config_service.py
│   ├── api_service.py
│   ├── api_client.py
│   ├── prompt_service.py
│   ├── chip_layout_service.py
│   ├── droplet_tool_service.py
│   └── tool_registry.py
├── utils/                    # 工具类
│   ├── api_utils.py
│   ├── common_utils.py
│   └── config_utils.py
├── config/                   # 配置文件
│   ├── api.yaml
│   ├── settings.yaml
│   └── prompts/v1/
│       └── prompt_config.yaml
├── data/                     # 数据持久化
└── logs/                     # 运行日志
```

---

## 2. 服务类详解

### 2.1 ConfigService（config_service.py）

**职责：** 统一管理 YAML 配置文件的加载、缓存和访问

**公开方法：**

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `load_yaml` | `file_path: str` | `Dict` | 加载 YAML 文件 |
| `get_settings` | - | `Dict` | 获取 settings.yaml 内容 |
| `get_api_config` | - | `Dict` | 获取 api.yaml 内容 |
| `get_prompt_config` | `version: str = 'v1'` | `Dict` | 获取提示词配置 |
| `get_all_prompt_versions` | - | `List[str]` | 获取所有版本列表 |
| `clear_cache` | - | `None` | 清除配置缓存 |
| `set_cache_ttl` | `ttl: int` | `None` | 设置缓存过期时间（秒） |
| `enable_cache` | `enable: bool` | `None` | 启用/禁用缓存 |

**内部机制：** 使用 ConfigLoader 实现文件缓存，监测文件修改时间自动刷新。

---

### 2.2 ApiService（api_service.py）

**职责：** 统一封装多种 AI API 的调用逻辑，支持同步、流式和 Agent Loop 模式

**构造函数：** `__init__(self, config_service, chip_layout_service, prompt_service)`

**核心公开方法：**

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get_api_config` | `api_name: str` | `Optional[Dict]` | 获取指定 API 配置 |
| `get_global_config` | - | `Dict` | 获取全局配置 |
| `get_models` | `api_name: str` | `List[str]` | 获取可用模型列表 |
| `validate_api_config` | `api_name: str` | `bool` | 验证 API 配置有效性 |
| `update_api_key` | `api_name: str, api_key: str` | `bool` | 更新 API 密钥 |
| `call_api` | `api_name, model, prompt, **kwargs` | `Dict` | 同步调用 API |
| `stream_api` | `api_name, model, prompt, **kwargs` | `Generator` | 流式调用 API |
| `agentic_stream_api` | `api_name, model, prompt, tool_registry, **kwargs` | `Generator` | Agent Loop 模式 |
| `extract_content` | `response` | `Optional[str]` | 提取响应文本 |

**内部方法：**

| 方法 | 说明 |
|------|------|
| `_get_api_client(api_name)` | 获取/缓存 API 客户端实例 |
| `_build_messages(prompt, system_prompt, history)` | 构建消息列表 |
| `_build_request_params(api_name, model, prompt, **kwargs)` | 构建请求对象 |
| `_load_prompt_template(version)` | 加载提示词模板 |
| `_merge_prompt_with_template(user_input, config)` | 合并提示词与芯片布局 |

**关键特性：**

- **客户端缓存：** 同一 API 只创建一个客户端实例
- **速率限制：** 检查每分钟调用次数
- **提示词模板自动合并：** 芯片布局信息自动注入 `{chip_layout}` 占位符
- **Agent Loop：** 最多 5 次迭代，流式推送工具状态和结果

---

### 2.3 API 客户端（api_client.py）

**抽象基类 BaseApiClient：**

```python
class BaseApiClient(ABC):
    @abstractmethod
    def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse
    @abstractmethod
    def stream_chat_completions(request) -> Generator[Dict, None, None]
    @abstractmethod
    def get_models() -> List[str]
```

**实现类：**

| 类名 | API | 特点 |
|------|-----|------|
| `OpenAIClient` | DeepSeek（OpenAI 兼容） | openai SDK，支持工具调用、思维链 |
| `QwenClient` | 阿里云千问 | requests HTTP，SSE 流式，累积文本→增量计算 |

**OpenAIClient 额外方法：**

- `chat_completions_with_tools(request)` — 非流式调用，返回含 `tool_calls` 的原始响应

**QwenClient 内部方法：**

- `_build_qwen_request(request)` — 转换请求格式
- `_parse_qwen_response(data)` — 转换响应格式

**工厂类 ApiClientFactory：**

```python
ApiClientFactory.create_client(api_type: str, config: Dict) -> BaseApiClient
# api_type='openai' → OpenAIClient
# api_type='qwen'   → QwenClient
```

---

### 2.4 PromptService（prompt_service.py）

**职责：** 提示词版本管理、模块组织、模板渲染

**公开方法：**

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get_prompt_config` | `version: str` | `Dict` | 获取版本配置 |
| `get_all_versions` | - | `List[str]` | 所有版本列表 |
| `get_modules` | `version: str` | `Dict` | 模块列表 |
| `get_module` | `module_name, version` | `Optional[Dict]` | 指定模块 |
| `get_prompts` | `module_name, version` | `Optional[Dict]` | 模块下提示词 |
| `get_prompt` | `module_name, prompt_name, version` | `Optional[Dict]` | 指定提示词 |
| `render_prompt` | `module_name, prompt_name, params, version` | `str` | 渲染模板 |
| `get_version_history` | - | `List[Dict]` | 版本历史 |
| `validate_prompt` | `module_name, prompt_name, version` | `bool` | 验证提示词 |
| `search_prompts` | `keyword, version` | `List[Dict]` | 搜索提示词 |
| `get_prompt_statistics` | `version` | `Dict` | 统计信息 |

---

### 2.5 ChipLayoutService（chip_layout_service.py）

**职责：** 芯片网格配置的持久化、验证和统计

**常量：**

```python
ROWS = 17        # 网格行数
COLS = 22        # 网格列数
MAX_VALUE = 128  # 电极编号最大值
```

**公开方法：**

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get_current_layout` | - | `Dict` | 获取当前配置（自定义 > 默认） |
| `set_custom_layout` | `grid, description` | `None` | 设置自定义配置并持久化 |
| `reset_to_default` | - | `None` | 重置为 YAML 默认 |
| `validate_grid` | `grid: list` | `Tuple[bool, list]` | 验证网格 `(is_valid, errors)` |
| `format_for_prompt` | `layout: dict` | `str` | 格式化为 LLM 可读文本 |
| `get_statistics` | - | `Dict` | 返回统计信息 |

**验证规则：**

- 必须是二维数组
- 行数 = 17，列数 = 22
- 每个值为 0–128 的整数

**持久化路径：** `./data/chip_layout.json`

---

### 2.6 DropletToolService（droplet_tool_service.py）

**职责：** 微流控芯片串口通信协议实现

**核心函数：**

```python
def build_frame(nodes: list, voltage: int = 80, ac_on: bool = True,
                freq: int = 100, output_type: str = 'ElectrodeOnly') -> bytes
# 构建 29 字节通信帧
```

**类方法：**

```python
class DropletToolService:
    def execute_dispense(electrode_sequences, interval=1.0,
                        voltage=80, output_type='ElectrodeOnly') -> dict
    # 返回: {"success": bool, "total_steps": int, "executed_steps": int, "log_messages": list}
```

**工作模式：**

- **Mock**（`mock_mode: true`）：生成帧数据和日志，不打开串口
- **真实**（`mock_mode: false`）：通过 pyserial 发送到串口

---

### 2.7 ToolRegistry（tool_registry.py）

**职责：** 管理 AI 可调用的工具定义和执行

**公开方法：**

| 方法 | 参数 | 返回值 | 说明 |
|------|------|--------|------|
| `get_tool_definitions` | - | `List[Dict]` | 返回 OpenAI tools 格式 |
| `execute_tool` | `tool_name: str, arguments: dict` | `str` (JSON) | 执行工具 |

**已注册工具：**

- `dispense_droplet` — 液滴分配，参数：`electrode_sequences`（必填）、`interval`（默认 1.0）

---

## 3. 工具层函数说明

### 3.1 api_utils.py — 请求/响应模型

**ChatCompletionRequest：**

`model`, `messages`, `max_tokens`(1024), `temperature`(0.7), `stream`(False), `top_p`(1.0), `thinking_enabled`(False), `reasoning_effort`("high"), `tools`(None), `tool_choice`("auto")

方法：`to_dict()`

**ChatCompletionResponse：**

`id`, `object`, `created`, `model`, `choices`, `usage`

方法：`to_dict()`

**转换函数：**

| 函数 | 说明 |
|------|------|
| `build_qwen_request(request)` | 转换为千问请求格式 |
| `parse_qwen_response(data)` | 转换千问响应为标准格式 |
| `parse_openai_response(response)` | 转换 OpenAI 响应为标准格式 |
| `parse_openai_stream_chunk(chunk)` | 解析 OpenAI 流式数据块 |
| `_serialize_tool_calls(tool_calls)` | 序列化工具调用列表 |

---

### 3.2 common_utils.py — 通用工具

| 函数 | 说明 |
|------|------|
| `build_headers(api_key, auth_method)` | 构建 Authorization 请求头 |
| `build_messages(prompt, system_prompt, history)` | 构建消息列表 |
| `extract_content(response)` | 提取响应文本 |
| `check_rate_limit(cache, api_name, rate_limit)` | 速率限制检查 |
| `validate_api_key(api_key)` | 验证密钥有效性 |
| `validate_api_config(api_config, api_name)` | 验证配置完整性 |

---

### 3.3 config_utils.py — 配置工具

**ConfigLoader 类：**

```python
class ConfigLoader:
    def __init__(cache_enabled=True, cache_ttl=3600)
    def load_yaml(file_path: str) -> Dict
    def clear_cache()
    def set_cache_ttl(ttl: int)
    def enable_cache(enable: bool)
```

**辅助函数：**

| 函数 | 说明 |
|------|------|
| `get_config_path(config_dir, config_file)` | 获取配置文件完整路径 |
| `get_prompt_config_path(config_dir, version='v1')` | 获取提示词配置路径 |
| `list_prompt_versions(config_dir)` | 列出所有提示词版本目录 |

---

## 4. 配置项说明

### settings.yaml

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `server.host` | `0.0.0.0` | 监听地址 |
| `server.port` | `5000` | 监听端口 |
| `server.debug` | `false` | 调试模式 |
| `config.cache_enabled` | `true` | 配置缓存开关 |
| `config.cache_ttl` | `3600` | 缓存过期时间（秒） |
| `logging.level` | `INFO` | 日志级别 |
| `logging.file` | `logs/app.log` | 日志文件 |
| `api.timeout` | `60` | 请求超时（秒） |
| `api.stream_timeout` | `120` | 流式超时（秒） |
| `api.rate_limit` | `100` | 每分钟最大调用次数 |
| `serial.port` | `COM6` | 串口号 |
| `serial.baud_rate` | `115200` | 波特率 |
| `serial.mock_mode` | `true` | 串口 Mock 模式 |

### api.yaml

| 配置项 | 说明 |
|--------|------|
| `apis.qwen` | 千问配置（`api_type: qwen`） |
| `apis.deepseek` | DeepSeek 配置（`api_type: openai`） |
| `apis.*.base_url` | API 基础 URL |
| `apis.*.api_key` | API 密钥 |
| `apis.*.models` | 支持的模型列表 |
| `apis.*.models.*.supports_thinking` | 是否支持思考模式 |
| `global.default_api` | 默认 API |
| `global.rate_limit` | 全局速率限制 |

---

## 5. 扩展指南

### 5.1 新增 API 支持

1. 在 api.yaml 添加新 API 配置节
2. 在 api_client.py 创建新客户端类（继承 `BaseApiClient`）
3. 在 `ApiClientFactory._client_registry` 注册
4. 实现 `chat_completions`、`stream_chat_completions`、`get_models`

### 5.2 新增工具

1. 在 tool_registry.py 的 `_register_tools()` 添加工具定义
2. 实现处理函数 `_handle_xxx_tool(arguments)`
3. 在 `execute_tool()` 方法中添加分派逻辑

### 5.3 新增提示词版本

1. 在 `config/prompts/` 下创建新目录（如 `v2/`）
2. 创建 `prompt_config.yaml`
3. API 自动发现新版本

---

## 6. 快速启动

```bash
cd backend
pip install -r requirements.txt
python app.py
# 服务运行在 http://0.0.0.0:5000
```

**依赖清单（requirements.txt）：**

- Flask==2.0.1
- flask-cors==3.0.10
- PyYAML==6.0.1
- requests==2.27.1
- openai>=2.32.0
