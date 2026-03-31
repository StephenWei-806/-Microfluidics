import json
from typing import Dict, Any, List, Optional, Generator


class ChatCompletionRequest:
    """统一的聊天完成请求模型"""
    def __init__(self, model: str, messages: List[Dict[str, str]], max_tokens: int = 1024, 
                 temperature: float = 0.7, stream: bool = False, top_p: float = 1.0, 
                 frequency_penalty: float = 0.0, presence_penalty: float = 0.0, 
                 n: int = 1, stop: Optional[List[str]] = None, 
                 logprobs: Optional[int] = None, echo: bool = False, 
                 stop_reason: Optional[str] = None, user: Optional[str] = None):
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
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
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
            'user': self.user
        }


class ChatCompletionResponse:
    """统一的聊天完成响应模型"""
    def __init__(self, id: str, object: str, created: int, model: str, 
                 choices: List[Dict[str, Any]], usage: Dict[str, int]):
        self.id = id
        self.object = object
        self.created = created
        self.model = model
        self.choices = choices
        self.usage = usage
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
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
                'content': choice.message.content
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
                    'content': choice.delta.content if choice.delta.content else None
                },
                'finish_reason': choice.finish_reason
            }
            for choice in chunk.choices
        ]
    }
    
    return chunk_data


def parse_qwen_stream_chunk(data: Dict[str, Any]) -> Dict[str, Any]:
    """解析千问流式响应chunk
    
    Args:
        data: 千问API流式响应数据
        
    Returns:
        解析后的chunk数据
    """
    if 'output' in data and 'text' in data['output']:
        return {
            'id': data.get('request_id', ''),
            'object': 'chat.completion.chunk',
            'created': int(data.get('created', 0)),
            'model': data.get('model', ''),
            'choices': [
                {
                    'index': 0,
                    'delta': {
                        'role': 'assistant',
                        'content': data['output']['text']
                    },
                    'finish_reason': None
                }
            ]
        }
    return None
