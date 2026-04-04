import time
import logging
from typing import Dict, Any, Optional, Generator, List
from services.config_service import ConfigService
from services.api_client import ApiClientFactory, ChatCompletionRequest, ChatCompletionResponse
from utils.common_utils import build_messages, extract_content, check_rate_limit, validate_api_config

logger = logging.getLogger(__name__)

class ApiService:
    """API调用服务"""
    
    def __init__(self, config_service: ConfigService, prompt_service=None):
        self.config_service = config_service
        self.prompt_service = prompt_service
        self.api_config = config_service.get_api_config()
        self.rate_limit_cache: Dict[str, Dict[str, Any]] = {}
        self.clients: Dict[str, Any] = {}  # 缓存API客户端
        self._custom_chip_layout = None
    
    def get_api_config(self, api_name: str) -> Optional[Dict[str, Any]]:
        apis = self.api_config.get('apis', {})
        return apis.get(api_name)
    
    def get_global_config(self) -> Dict[str, Any]:
        return self.api_config.get('global', {})
    
    def _check_rate_limit(self, api_name: str) -> bool:
        global_config = self.get_global_config()
        rate_limit = global_config.get('rate_limit', 100)
        return check_rate_limit(self.rate_limit_cache, api_name, rate_limit)
    
    def _get_api_client(self, api_name: str):
        if api_name in self.clients:
            return self.clients[api_name]
        
        api_config = self.get_api_config(api_name)
        client = ApiClientFactory.create_client(api_name, api_config)
        
        self.clients[api_name] = client
        return client
    
    def _build_messages(self, prompt: str, system_prompt: Optional[str] = None) -> List[Dict[str, str]]:
        return build_messages(prompt, system_prompt)
    
    def call_api(self, api_name: str, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        self._check_rate_limit(api_name)
        
        api_config = self.get_api_config(api_name)
        
        system_prompt = kwargs.get('system_prompt')
        max_tokens = kwargs.get('max_tokens', 1024)
        temperature = kwargs.get('temperature', 0.7)
        top_p = kwargs.get('top_p', 1.0)
        frequency_penalty = kwargs.get('frequency_penalty', 0.0)
        presence_penalty = kwargs.get('presence_penalty', 0.0)
        n = kwargs.get('n', 1)
        stop = kwargs.get('stop')
        logprobs = kwargs.get('logprobs')
        echo = kwargs.get('echo', False)
        user = kwargs.get('user')
        
        messages = self._build_messages(prompt, system_prompt)
        
        request = ChatCompletionRequest(
            model=model or api_config.get('default_model', ''),
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            n=n,
            stop=stop,
            logprobs=logprobs,
            echo=echo,
            user=user
        )
        
        client = self._get_api_client(api_name)
        response = client.chat_completions(request)
        
        return response.to_dict()
    
    def _load_prompt_template(self, version: str = 'v1') -> Optional[Dict[str, Any]]:
        """加载提示词模板配置"""
        if not self.prompt_service:
            return None
        try:
            config = self.prompt_service.get_prompt_config(version)
            return config
        except Exception as e:
            logger.warning(f"加载提示词模板失败: {e}")
            return None

    def set_custom_chip_layout(self, grid: List[List[int]]):
        """设置自定义芯片网格布局"""
        self._custom_chip_layout = grid
        logger.info("自定义芯片网格布局已更新")

    def get_current_chip_layout(self) -> Dict[str, Any]:
        """获取当前生效的芯片网格配置"""
        if self._custom_chip_layout is not None:
            return {
                'grid': self._custom_chip_layout,
                'description': '用户自定义芯片网格布局'
            }
        # 从 YAML 加载默认值
        prompt_config = self._load_prompt_template('v1')
        if prompt_config and 'chip_layout' in prompt_config:
            return prompt_config['chip_layout']
        return {
            'grid': [],
            'description': '默认芯片网格布局'
        }

    def _format_chip_layout(self, chip_layout: Dict[str, Any]) -> str:
        """格式化芯片布局数据为可读字符串"""
        try:
            chip_layout = chip_layout or {}
            grid = chip_layout.get('grid', [])
            description = chip_layout.get('description', '')
            lines = []
            if description:
                lines.append(description)
            lines.append('网格布局:')
            for row in grid:
                lines.append(str(row))
            return '\n'.join(lines)
        except Exception as e:
            logger.warning(f"格式化芯片布局失败: {e}，忽略芯片布局信息")
            return ''

    def _merge_prompt_with_template(self, user_input: str, prompt_config: Dict[str, Any]) -> str:
        """将用户输入与提示词模板合并"""
        template = prompt_config.get('prompt_template', '')
        if not template:
            logger.warning("提示词模板为空，使用原始用户输入")
            return user_input

        chip_layout = prompt_config.get('chip_layout', {})
        # 如果存在自定义芯片布局，则替换
        if self._custom_chip_layout is not None:
            chip_layout = dict(chip_layout)  # 复制一份避免修改原配置
            chip_layout['grid'] = self._custom_chip_layout
            chip_layout['description'] = '用户自定义芯片网格布局'
        chip_layout_str = self._format_chip_layout(chip_layout)

        try:
            merged = template.format(
                chip_layout=chip_layout_str,
                user_requirements=user_input
            )
            logger.info(f"提示词模板合并成功，合并后长度: {len(merged)}")
            return merged
        except Exception as e:
            logger.warning(f"提示词模板渲染失败: {e}，使用原始用户输入")
            return user_input

    def stream_api(self, api_name: str, model: str, prompt: str, **kwargs) -> Generator[Dict[str, Any], None, None]:
        self._check_rate_limit(api_name)

        # 加载提示词模板并与用户输入合并
        prompt_config = self._load_prompt_template('v1')
        if prompt_config:
            logger.info(f"已加载v1提示词模板，开始合并用户输入")
            prompt = self._merge_prompt_with_template(prompt, prompt_config)
        else:
            logger.info("未能加载提示词模板，直接使用用户原始输入")
        
        api_config = self.get_api_config(api_name)
        
        system_prompt = kwargs.get('system_prompt')
        max_tokens = kwargs.get('max_tokens', 1024)
        temperature = kwargs.get('temperature', 0.7)
        top_p = kwargs.get('top_p', 1.0)
        frequency_penalty = kwargs.get('frequency_penalty', 0.0)
        presence_penalty = kwargs.get('presence_penalty', 0.0)
        n = kwargs.get('n', 1)
        stop = kwargs.get('stop')
        logprobs = kwargs.get('logprobs')
        echo = kwargs.get('echo', False)
        user = kwargs.get('user')
        
        messages = self._build_messages(prompt, system_prompt)
        
        request = ChatCompletionRequest(
            model=model or api_config.get('default_model', ''),
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
            top_p=top_p,
            frequency_penalty=frequency_penalty,
            presence_penalty=presence_penalty,
            n=n,
            stop=stop,
            logprobs=logprobs,
            echo=echo,
            user=user
        )
        
        client = self._get_api_client(api_name)
        for chunk in client.stream_chat_completions(request):
            yield chunk
    
    def get_models(self, api_name: str) -> List[str]:
        client = self._get_api_client(api_name)
        return client.get_models()
    
    def validate_api_config(self, api_name: str) -> bool:
        api_config = self.get_api_config(api_name)
        return validate_api_config(api_config, api_name)
    
    def update_api_key(self, api_name: str, api_key: str) -> bool:
        api_config = self.get_api_config(api_name)
        if api_config:
            api_config['api_key'] = api_key
            
            if api_name in self.clients:
                del self.clients[api_name]
            
            return True
        return False
    
    def extract_content(self, response: Dict[str, Any]) -> Optional[str]:
        return extract_content(response)
