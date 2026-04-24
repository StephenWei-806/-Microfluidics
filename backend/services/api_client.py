import abc
import json
from typing import Dict, Any, List, Optional, Generator
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from openai import OpenAI
from utils.api_utils import ChatCompletionRequest, ChatCompletionResponse, build_qwen_request, parse_qwen_response, parse_openai_response, parse_openai_stream_chunk
from utils.common_utils import build_headers

class BaseApiClient(abc.ABC):
    """API客户端抽象基类
    
    定义所有API客户端必须实现的接口，提供通用的配置初始化和请求头构建功能。
    子类需要实现chat_completions、stream_chat_completions和get_models方法。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化API客户端
        
        Args:
            config: 客户端配置字典，包含以下字段:
                - api_key: API密钥
                - base_url: API基础URL
                - auth_method: 认证方式，默认为'bearer'
                - timeout: 请求超时时间（秒），默认60
                - stream_timeout: 流式请求超时时间（秒），默认120
                - connect_timeout: 连接超时时间（秒），默认10
                - retry_count: 重试次数，默认3
                - retry_delay: 重试延迟（秒），默认1
                - request_mapping: 请求参数映射配置
                - response_mapping: 响应参数映射配置
        """
        self.config = config
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url')
        self.auth_method = config.get('auth_method', 'bearer')
        self.timeout = config.get('timeout', 60)
        self.stream_timeout = config.get('stream_timeout', 120)
        self.connect_timeout = config.get('connect_timeout', 10)
        self.retry_count = config.get('retry_count', 3)
        self.retry_delay = config.get('retry_delay', 1)
        self.request_mapping = config.get('request_mapping', {})
        self.response_mapping = config.get('response_mapping', {})
    
    @abc.abstractmethod
    def chat_completions(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """执行聊天完成请求（非流式）
        
        Args:
            request: 聊天完成请求对象
            
        Returns:
            ChatCompletionResponse: 聊天完成响应对象
            
        Raises:
            子类实现可能抛出各种API调用异常
        """
        pass
    
    @abc.abstractmethod
    def stream_chat_completions(self, request: ChatCompletionRequest) -> Generator[Dict[str, Any], None, None]:
        """执行聊天完成请求（流式）
        
        Args:
            request: 聊天完成请求对象
            
        Yields:
            Dict[str, Any]: 流式响应数据块
            
        Raises:
            子类实现可能抛出各种API调用异常
        """
        pass
    
    @abc.abstractmethod
    def get_models(self) -> List[str]:
        """获取支持的模型列表
        
        Returns:
            List[str]: 模型名称列表
        """
        pass
    
    def _build_headers(self) -> Dict[str, str]:
        """构建请求头
        
        Returns:
            Dict[str, str]: 包含认证信息的请求头字典
        """
        return build_headers(self.api_key, self.auth_method)

    def chat_completions_with_tools(self, request: ChatCompletionRequest):
        """非流式调用，返回原始响应对象（含 tool_calls）
        
        子类可选择实现。默认抛出 NotImplementedError。
        """
        raise NotImplementedError(f"{self.__class__.__name__} 不支持工具调用")

class OpenAIClient(BaseApiClient):
    """OpenAI兼容的API客户端（用于DeepSeek API）
    
    支持OpenAI API格式的客户端实现，可用于DeepSeek等兼容OpenAI规范的API服务。
    使用openai库进行底层通信。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化OpenAI客户端
        
        Args:
            config: 客户端配置字典，包含api_key、base_url等
        """
        super().__init__(config)
        self._client = None  # 延迟初始化，避免仅读取配置时也强制创建SDK客户端

    @property
    def client(self):
        """延迟初始化OpenAI SDK客户端"""
        if self._client is None:
            self._client = OpenAI(
                api_key=self.api_key or 'placeholder',
                base_url=self.base_url
            )
        return self._client
    
    def chat_completions(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """执行非流式聊天完成请求

        Args:
            request: 聊天完成请求对象

        Returns:
            ChatCompletionResponse: 解析后的统一响应对象

        Raises:
            OpenAIError: API调用失败时抛出
        """
        kwargs = {
            'model': request.model,
            'messages': request.messages,
            'max_tokens': request.max_tokens,
            'n': request.n,
            'stop': request.stop,
            'logprobs': request.logprobs,
            'user': request.user,
            'stream': False
        }

        if request.thinking_enabled:
            kwargs['extra_body'] = {"thinking": {"type": "enabled"}}
            kwargs['reasoning_effort'] = request.reasoning_effort
        else:
            kwargs['temperature'] = request.temperature
            kwargs['top_p'] = request.top_p
            kwargs['frequency_penalty'] = request.frequency_penalty
            kwargs['presence_penalty'] = request.presence_penalty

        # 支持工具调用
        if request.tools:
            kwargs['tools'] = request.tools
            kwargs['tool_choice'] = request.tool_choice

        response = self.client.chat.completions.create(**kwargs)

        return parse_openai_response(response)
    
    def stream_chat_completions(self, request: ChatCompletionRequest) -> Generator[Dict[str, Any], None, None]:
        """执行流式聊天完成请求

        Args:
            request: 聊天完成请求对象

        Yields:
            Dict[str, Any]: 流式响应数据块

        Raises:
            OpenAIError: API调用失败时抛出
        """
        kwargs = {
            'model': request.model,
            'messages': request.messages,
            'max_tokens': request.max_tokens,
            'n': request.n,
            'stop': request.stop,
            'logprobs': request.logprobs,
            'user': request.user,
            'stream': True
        }

        if request.thinking_enabled:
            kwargs['extra_body'] = {"thinking": {"type": "enabled"}}
            kwargs['reasoning_effort'] = request.reasoning_effort
        else:
            kwargs['temperature'] = request.temperature
            kwargs['top_p'] = request.top_p
            kwargs['frequency_penalty'] = request.frequency_penalty
            kwargs['presence_penalty'] = request.presence_penalty

        # 支持工具调用
        if request.tools:
            kwargs['tools'] = request.tools
            kwargs['tool_choice'] = request.tool_choice

        response = self.client.chat.completions.create(**kwargs)

        for chunk in response:
            chunk_data = parse_openai_stream_chunk(chunk)
            yield chunk_data
    
    def get_models(self) -> List[str]:
        """获取支持的模型列表
        
        Returns:
            List[str]: 模型名称列表
        """
        models = self.config.get('models', [])
        return [model['name'] for model in models]

    def chat_completions_with_tools(self, request: ChatCompletionRequest):
        """非流式调用，返回原始 OpenAI 响应对象（含 tool_calls）
        
        专为 Agent Loop 设计，保留完整的 tool_calls 信息。
        
        Args:
            request: 聊天完成请求对象
            
        Returns:
            OpenAI ChatCompletion 原始响应对象
        """
        kwargs = {
            'model': request.model,
            'messages': request.messages,
            'max_tokens': request.max_tokens,
            'n': request.n,
            'stop': request.stop,
            'user': request.user,
            'stream': False
        }
        
        if request.thinking_enabled:
            kwargs['extra_body'] = {"thinking": {"type": "enabled"}}
            kwargs['reasoning_effort'] = request.reasoning_effort
        else:
            kwargs['temperature'] = request.temperature
            kwargs['top_p'] = request.top_p
            kwargs['frequency_penalty'] = request.frequency_penalty
            kwargs['presence_penalty'] = request.presence_penalty
        
        # 工具定义
        if request.tools:
            kwargs['tools'] = request.tools
            kwargs['tool_choice'] = request.tool_choice
        
        response = self.client.chat.completions.create(**kwargs)
        return response  # 返回原始响应对象

class QwenClient(BaseApiClient):
    """千问API客户端（适配OpenAI规范）
    
    阿里云千问(DashScope) API的客户端实现，将千问API适配为OpenAI兼容格式。
    使用requests库进行HTTP通信，支持重试机制和流式响应。
    """
    
    def __init__(self, config: Dict[str, Any]):
        """初始化千问客户端
        
        Args:
            config: 客户端配置字典，包含api_key、base_url等
        """
        super().__init__(config)
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.retry_count,
            backoff_factor=self.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
    
    def _build_qwen_request(self, request: ChatCompletionRequest) -> Dict[str, Any]:
        """构建千问API请求格式
        
        Args:
            request: 统一的聊天完成请求对象
            
        Returns:
            Dict[str, Any]: 千问API格式的请求字典
        """
        return build_qwen_request(request)
    
    def _parse_qwen_response(self, response_data: Dict[str, Any]) -> ChatCompletionResponse:
        """解析千问API响应
        
        Args:
            response_data: 千问API原始响应数据
            
        Returns:
            ChatCompletionResponse: 解析后的统一响应对象
        """
        return parse_qwen_response(response_data)
    
    def chat_completions(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """执行非流式聊天完成请求
        
        Args:
            request: 聊天完成请求对象
            
        Returns:
            ChatCompletionResponse: 解析后的统一响应对象
            
        Raises:
            requests.RequestException: HTTP请求失败时抛出
        """
        qwen_request = self._build_qwen_request(request)
        headers = self._build_headers()
        
        response = self.session.post(
            f"{self.base_url}/services/aigc/text-generation/generation",
            json=qwen_request,
            headers=headers,
            timeout=(self.connect_timeout, self.timeout)
        )
        
        response_data = response.json()
        return self._parse_qwen_response(response_data)
    
    def stream_chat_completions(self, request: ChatCompletionRequest) -> Generator[Dict[str, Any], None, None]:
        """执行流式聊天完成请求
        
        通过SSE协议获取流式响应，并将千问格式转换为OpenAI兼容格式。
        千问API返回的是累积文本，需要计算增量内容。
        
        Args:
            request: 聊天完成请求对象
            
        Yields:
            Dict[str, Any]: 流式响应数据块，OpenAI兼容格式
            
        Raises:
            requests.RequestException: HTTP请求失败时抛出
        """
        qwen_request = self._build_qwen_request(request)
        qwen_request['parameters']['stream'] = True
        headers = self._build_headers()
        # DashScope API需要这个header来启用SSE流式返回
        headers['X-DashScope-SSE'] = 'enable'
        
        response = self.session.post(
            f"{self.base_url}/services/aigc/text-generation/generation",
            json=qwen_request,
            headers=headers,
            timeout=(self.connect_timeout, self.stream_timeout),
            stream=True
        )
        
        # 确保响应成功
        response.raise_for_status()
        
        previous_text = ""  # 用于计算增量内容
        
        for line in response.iter_lines(decode_unicode=True):
            if line:
                chunk_str = line if isinstance(line, str) else line.decode('utf-8')
                
                # 处理SSE格式: id:xxx\nevent:xxx\ndata:xxx\n\n
                if chunk_str.startswith('id:'):
                    continue
                if chunk_str.startswith('event:'):
                    continue
                # 跳过HTTP状态行 (如 :HTTP_STATUS/200)
                if chunk_str.startswith(':HTTP'):
                    continue
                
                # 千问API的data字段格式是 "data:{...}" (无空格)
                if chunk_str.startswith('data:'):
                    chunk_str = chunk_str[5:]
                
                if chunk_str == '[DONE]':
                    break
                
                try:
                    data = json.loads(chunk_str)
                except json.JSONDecodeError:
                    continue
                
                if 'output' in data and 'text' in data['output']:
                    current_text = data['output']['text']
                    # 千问API返回的是累积文本，需要计算增量
                    delta_text = current_text[len(previous_text):]
                    previous_text = current_text
                    
                    # 只发送有实际内容的delta
                    if delta_text or 'finish_reason' in data.get('output', {}):
                        yield {
                            'id': data.get('request_id', ''),
                            'object': 'chat.completion.chunk',
                            'created': int(data.get('created', 0)),
                            'model': data.get('model', ''),
                            'choices': [
                                {
                                    'index': 0,
                                    'delta': {
                                        'role': 'assistant',
                                        'content': delta_text
                                    },
                                    'finish_reason': data.get('output', {}).get('finish_reason')
                                }
                            ]
                        }
    
    def get_models(self) -> List[str]:
        """获取支持的模型列表
        
        Returns:
            List[str]: 模型名称列表
        """
        models = self.config.get('models', [])
        return [model['name'] for model in models]

class ApiClientFactory:
    """API客户端工厂类
    
    使用工厂模式管理API客户端的创建，支持动态注册新的客户端类型。
    通过api_type配置自动选择对应的客户端实现类。
    """
    
    # 注册的API客户端类
    _client_registry = {
        'openai': OpenAIClient,
        'qwen': QwenClient
    }
    
    @classmethod
    def register_client(cls, api_type: str, client_class):
        """注册新的API客户端类型
        
        Args:
            api_type: API类型标识符
            client_class: 客户端类，必须是BaseApiClient的子类
        """
        cls._client_registry[api_type] = client_class
    
    @classmethod
    def create_client(cls, api_name: str, config: Dict[str, Any]) -> BaseApiClient:
        """创建API客户端实例
        
        根据配置中的api_type自动选择对应的客户端类并创建实例。
        
        Args:
            api_name: API名称（用于日志标识）
            config: 客户端配置字典，必须包含api_type字段
            
        Returns:
            BaseApiClient: API客户端实例
            
        Raises:
            KeyError: 当api_type未注册时抛出
        """
        api_type = config.get('api_type', 'openai')
        return cls._client_registry[api_type](config)
    
    @classmethod
    def get_supported_api_types(cls) -> List[str]:
        """获取支持的API类型列表
        
        Returns:
            List[str]: 已注册的API类型标识符列表
        """
        return list(cls._client_registry.keys())
