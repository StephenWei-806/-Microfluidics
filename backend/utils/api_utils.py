import json
from typing import Dict, Any, List, Optional, Generator


class ChatCompletionRequest:
    """统一的聊天完成请求模型
    
    用于封装各种API（OpenAI、千问等）的聊天完成请求参数，
    提供统一的接口来构建和转换请求数据。
    """
    
    def __init__(self, model: str, messages: List[Dict[str, str]], max_tokens: int = 1024,
                 temperature: float = 0.7, stream: bool = False, top_p: float = 1.0,
                 frequency_penalty: float = 0.0, presence_penalty: float = 0.0,
                 n: int = 1, stop: Optional[List[str]] = None,
                 logprobs: Optional[int] = None, echo: bool = False,
                 stop_reason: Optional[str] = None, user: Optional[str] = None,
                 thinking_enabled: bool = False, reasoning_effort: str = "high"):
        """初始化聊天完成请求对象
        
        Args:
            model: 模型名称
            messages: 消息列表，包含角色和内容
            max_tokens: 最大生成token数，默认1024
            temperature: 采样温度，默认0.7
            stream: 是否使用流式响应，默认False
            top_p: 核采样参数，默认1.0
            frequency_penalty: 频率惩罚，默认0.0
            presence_penalty: 存在惩罚，默认0.0
            n: 生成结果数量，默认1
            stop: 停止词列表，可选
            logprobs: 是否返回log概率，可选
            echo: 是否回显输入，默认False
            stop_reason: 停止原因，可选
            user: 用户标识，可选
            thinking_enabled: 是否启用思考模式，默认False
            reasoning_effort: 思考强度，"high"或"max"，默认"high"
        """
        self.model = model
        self.messages = messages
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.stream = stream
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
        self.n = n
        self.stop = stop
        self.logprobs = logprobs
        self.echo = echo
        self.stop_reason = stop_reason
        self.user = user
        self.thinking_enabled = thinking_enabled
        self.reasoning_effort = reasoning_effort
    
    def to_dict(self) -> Dict[str, Any]:
        """将请求对象转换为字典格式
        
        Returns:
            Dict[str, Any]: 包含所有请求参数的字典
        """
        return {
            'model': self.model,
            'messages': self.messages,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'stream': self.stream,
            'top_p': self.top_p,
            'frequency_penalty': self.frequency_penalty,
            'presence_penalty': self.presence_penalty,
            'n': self.n,
            'stop': self.stop,
            'logprobs': self.logprobs,
            'echo': self.echo,
            'user': self.user,
            'thinking_enabled': self.thinking_enabled,
            'reasoning_effort': self.reasoning_effort
        }


class ChatCompletionResponse:
    """统一的聊天完成响应模型
    
    用于封装各种API（OpenAI、千问等）的聊天完成响应数据，
    提供统一的接口来访问和转换响应数据。
    """
    
    def __init__(self, id: str, object: str, created: int, model: str, 
                 choices: List[Dict[str, Any]], usage: Dict[str, int]):
        """初始化聊天完成响应对象
        
        Args:
            id: 响应唯一标识符
            object: 对象类型（如"chat.completion"）
            created: 创建时间戳
            model: 使用的模型名称
            choices: 生成的结果列表
            usage: token使用量统计
        """
        self.id = id
        self.object = object
        self.created = created
        self.model = model
        self.choices = choices
        self.usage = usage
    
    def to_dict(self) -> Dict[str, Any]:
        """将响应对象转换为字典格式
        
        Returns:
            Dict[str, Any]: 包含所有响应字段的字典
        """
        return {
            'id': self.id,
            'object': self.object,
            'created': self.created,
            'model': self.model,
            'choices': self.choices,
            'usage': self.usage
        }


def build_qwen_request(request: ChatCompletionRequest) -> Dict[str, Any]:
    """构建千问API请求格式
    
    Args:
        request: 统一的请求对象
        
    Returns:
        千问API格式的请求字典
    """
    user_content = ""
    for msg in request.messages:
        if msg['role'] == 'user':
            user_content = msg['content']
            break
    
    qwen_request = {
        'model': request.model,
        'input': {
            'prompt': user_content
        },
        'parameters': {
            'max_tokens': request.max_tokens,
            'temperature': request.temperature,
            'top_p': request.top_p
        }
    }
    
    return qwen_request


def parse_qwen_response(response_data: Dict[str, Any]) -> ChatCompletionResponse:
    """解析千问API响应
    
    Args:
        response_data: 千问API响应数据
        
    Returns:
        统一的响应对象
    """
    choices = []
    if 'output' in response_data and 'text' in response_data['output']:
        choices.append({
            'index': 0,
            'message': {
                'role': 'assistant',
                'content': response_data['output']['text']
            },
            'finish_reason': 'stop'
        })
    
    usage = response_data.get('usage', {
        'prompt_tokens': 0,
        'completion_tokens': 0,
        'total_tokens': 0
    })
    
    return ChatCompletionResponse(
        id=response_data.get('request_id', ''),
        object='chat.completion',
        created=int(response_data.get('created', 0)),
        model=response_data.get('model', ''),
        choices=choices,
        usage=usage
    )


def parse_openai_response(response) -> ChatCompletionResponse:
    """解析OpenAI格式响应
    
    Args:
        response: OpenAI客户端响应对象
        
    Returns:
        统一的响应对象
    """
    choices = [
        {
            'index': choice.index,
            'message': {
                'role': choice.message.role,
                'content': choice.message.content,
                'reasoning_content': getattr(choice.message, 'reasoning_content', None)
            },
            'finish_reason': choice.finish_reason
        }
        for choice in response.choices
    ]
    
    usage = {
        'prompt_tokens': response.usage.prompt_tokens,
        'completion_tokens': response.usage.completion_tokens,
        'total_tokens': response.usage.total_tokens
    }
    
    return ChatCompletionResponse(
        id=response.id,
        object=response.object,
        created=response.created,
        model=response.model,
        choices=choices,
        usage=usage
    )


def parse_openai_stream_chunk(chunk) -> Dict[str, Any]:
    """解析OpenAI流式响应chunk
    
    Args:
        chunk: OpenAI客户端流式响应chunk
        
    Returns:
        解析后的chunk数据
    """
    chunk_data = {
        'id': chunk.id,
        'object': chunk.object,
        'created': chunk.created,
        'model': chunk.model,
        'choices': [
            {
                'index': choice.index,
                'delta': {
                    'role': choice.delta.role if choice.delta.role else None,
                    'content': choice.delta.content if choice.delta.content else None,
                    'reasoning_content': getattr(choice.delta, 'reasoning_content', None)
                },
                'finish_reason': choice.finish_reason
            }
            for choice in chunk.choices
        ]
    }
    
    return chunk_data



