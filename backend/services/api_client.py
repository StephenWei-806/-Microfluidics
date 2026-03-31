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
    """API客户端抽象基类"""
    
    def __init__(self, config: Dict[str, Any]):
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
        pass
    
    @abc.abstractmethod
    def stream_chat_completions(self, request: ChatCompletionRequest) -> Generator[Dict[str, Any], None, None]:
        pass
    
    @abc.abstractmethod
    def get_models(self) -> List[str]:
        pass
    
    def _build_headers(self) -> Dict[str, str]:
        return build_headers(self.api_key, self.auth_method)

class OpenAIClient(BaseApiClient):
    """OpenAI兼容的API客户端（用于DeepSeek API）"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def chat_completions(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        response = self.client.chat.completions.create(
            model=request.model,
            messages=request.messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            n=request.n,
            stop=request.stop,
            logprobs=request.logprobs,
            user=request.user,
            stream=False
        )
        
        return parse_openai_response(response)
    
    def stream_chat_completions(self, request: ChatCompletionRequest) -> Generator[Dict[str, Any], None, None]:
        response = self.client.chat.completions.create(
            model=request.model,
            messages=request.messages,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            n=request.n,
            stop=request.stop,
            logprobs=request.logprobs,
            user=request.user,
            stream=True
        )
        
        for chunk in response:
            chunk_data = parse_openai_stream_chunk(chunk)
            yield chunk_data
    
    def get_models(self) -> List[str]:
        models = self.config.get('models', [])
        return [model['name'] for model in models]

class QwenClient(BaseApiClient):
    """千问API客户端（适配OpenAI规范）"""
    
    def __init__(self, config: Dict[str, Any]):
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
        return build_qwen_request(request)
    
    def _parse_qwen_response(self, response_data: Dict[str, Any]) -> ChatCompletionResponse:
        return parse_qwen_response(response_data)
    
    def chat_completions(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
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
        models = self.config.get('models', [])
        return [model['name'] for model in models]

class ApiClientFactory:
    """API客户端工厂类"""
    
    # 注册的API客户端类
    _client_registry = {
        'openai': OpenAIClient,
        'qwen': QwenClient
    }
    
    @classmethod
    def register_client(cls, api_type: str, client_class):
        cls._client_registry[api_type] = client_class
    
    @classmethod
    def create_client(cls, api_name: str, config: Dict[str, Any]) -> BaseApiClient:
        api_type = config.get('api_type', 'openai')
        return cls._client_registry[api_type](config)
    
    @classmethod
    def get_supported_api_types(cls) -> List[str]:
        return list(cls._client_registry.keys())
