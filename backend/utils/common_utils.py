import time
import json
from typing import Dict, Any, List, Optional, Generator


def build_headers(api_key: str, auth_method: str = 'bearer') -> Dict[str, str]:
    """构建API请求头部
    
    Args:
        api_key: API密钥
        auth_method: 认证方式，默认为'bearer'
        
    Returns:
        头部字典
    """
    headers = {
        'Content-Type': 'application/json'
    }
    
    if auth_method == 'bearer' and api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    
    return headers


def build_messages(prompt: str, system_prompt: Optional[str] = None, history_messages: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
    """构建聊天消息格式
    
    Args:
        prompt: 用户提示词
        system_prompt: 系统提示词（可选）
        history_messages: 历史对话消息列表（可选）
        
    Returns:
        消息列表
    """
    messages = []
    
    if system_prompt:
        messages.append({
            'role': 'system',
            'content': system_prompt
        })
    
    # 添加历史对话消息（安全校验）
    if history_messages:
        allowed_roles = {'user', 'assistant', 'system'}
        for msg in history_messages:
            if not isinstance(msg, dict):
                continue
            role = msg.get('role', 'user')
            if role not in allowed_roles:
                role = 'user'
            content = str(msg.get('content', '')).strip()
            if not content:
                continue
            messages.append({
                'role': role,
                'content': content
            })
    
    messages.append({
        'role': 'user',
        'content': prompt
    })
    
    return messages


def extract_content(response: Dict[str, Any]) -> Optional[str]:
    """从API响应中提取内容
    
    Args:
        response: API响应字典
        
    Returns:
        提取的内容，如果没有则返回None
    """
    if 'choices' in response and len(response['choices']) > 0:
        choice = response['choices'][0]
        if 'message' in choice and 'content' in choice['message']:
            return choice['message']['content']
    return None


def check_rate_limit(cache: Dict[str, Any], api_name: str, rate_limit: int = 100) -> bool:
    """检查API调用速率限制
    
    Args:
        cache: 速率限制缓存
        api_name: API名称
        rate_limit: 每分钟最大调用次数
        
    Returns:
        是否允许调用
    """
    if api_name not in cache:
        cache[api_name] = {
            'count': 0,
            'reset_time': time.time() + 60  # 每分钟重置
        }
    
    cache_item = cache[api_name]
    current_time = time.time()
    
    if current_time >= cache_item['reset_time']:
        cache_item['count'] = 0
        cache_item['reset_time'] = current_time + 60
    
    if cache_item['count'] >= rate_limit:
        return False
    
    cache_item['count'] += 1
    return True


def validate_api_key(api_key: str) -> bool:
    """验证API密钥是否有效
    
    Args:
        api_key: API密钥
        
    Returns:
        是否有效
    """
    if not api_key:
        return False
    
    invalid_keys = ['', 'your_qwen_api_key', 'your_deepseek_api_key']
    if api_key in invalid_keys:
        return False
    
    return True


def validate_api_config(api_config: Dict[str, Any], api_name: str) -> bool:
    """验证API配置是否有效
    
    Args:
        api_config: API配置字典
        api_name: API名称
        
    Returns:
        是否有效
    """
    if not api_config:
        return False
    
    required_fields = ['name', 'api_type', 'base_url', 'api_key']
    for field in required_fields:
        if field not in api_config:
            return False
    
    if not validate_api_key(api_config.get('api_key')):
        return False
    
    if api_name == 'deepseek':
        base_url = api_config.get('base_url')
        if base_url != "https://api.deepseek.com/v1":
            return False
    
    return True



