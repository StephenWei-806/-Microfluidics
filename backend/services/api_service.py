import time
import json
import logging
from typing import Dict, Any, Optional, Generator, List
from services.config_service import ConfigService
from services.chip_layout_service import ChipLayoutService
from services.api_client import ApiClientFactory, BaseApiClient, ChatCompletionRequest, ChatCompletionResponse
from utils.common_utils import build_messages, extract_content, check_rate_limit, validate_api_config

logger = logging.getLogger(__name__)

class ApiService:
    """API调用服务
    
    提供统一的API调用接口，支持多种API类型（OpenAI、千问等），
    包含速率限制、客户端缓存、提示词模板合并等功能。
    """
    
    def __init__(self, config_service: ConfigService, chip_layout_service: ChipLayoutService, prompt_service=None):
        """初始化API服务
        
        Args:
            config_service: 配置服务实例
            chip_layout_service: 芯片布局服务实例
            prompt_service: 提示词服务实例，可选
        """
        self.config_service = config_service
        self.chip_layout_service = chip_layout_service
        self.prompt_service = prompt_service
        self.api_config = config_service.get_api_config()
        self.rate_limit_cache: Dict[str, Dict[str, Any]] = {}
        self.clients: Dict[str, Any] = {}  # 缓存API客户端
    
    def get_api_config(self, api_name: str) -> Optional[Dict[str, Any]]:
        """获取指定API的配置
        
        Args:
            api_name: API名称
            
        Returns:
            Optional[Dict[str, Any]]: API配置字典，不存在时返回None
        """
        apis = self.api_config.get('apis', {})
        return apis.get(api_name)
    
    def get_global_config(self) -> Dict[str, Any]:
        """获取全局API配置
        
        Returns:
            Dict[str, Any]: 全局配置字典
        """
        return self.api_config.get('global', {})
    
    def _check_rate_limit(self, api_name: str) -> bool:
        """检查API调用速率限制
        
        Args:
            api_name: API名称
            
        Returns:
            bool: 是否允许调用（未超过限制）
        """
        global_config = self.get_global_config()
        rate_limit = global_config.get('rate_limit', 100)
        return check_rate_limit(self.rate_limit_cache, api_name, rate_limit)
    
    def _get_api_client(self, api_name: str):
        """获取或创建API客户端
        
        使用缓存机制避免重复创建客户端实例。
        
        Args:
            api_name: API名称
            
        Returns:
            BaseApiClient: API客户端实例
        """
        if api_name in self.clients:
            return self.clients[api_name]
        
        api_config = self.get_api_config(api_name)
        client = ApiClientFactory.create_client(api_name, api_config)
        
        self.clients[api_name] = client
        return client
    
    def _build_messages(self, prompt: str, system_prompt: Optional[str] = None, history_messages: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        """构建聊天消息列表
        
        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词，可选
            history_messages: 历史对话消息列表，可选
            
        Returns:
            List[Dict[str, str]]: 消息列表，包含角色和内容
        """
        return build_messages(prompt, system_prompt, history_messages)
    
    def _build_request_params(self, api_name: str, model: str, prompt: str, **kwargs):
        """构建API请求参数
        
        统一构建同步和流式API调用所需的请求参数，
        包括速率限制检查、消息构建和请求对象创建。
        
        Args:
            api_name: API名称
            model: 模型名称
            prompt: 用户提示词
            **kwargs: 可选参数（system_prompt, max_tokens, temperature等）
            
        Returns:
            tuple: (client, request) 客户端实例和请求对象
        """
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
        thinking_enabled = kwargs.get('thinking_enabled', False)
        reasoning_effort = kwargs.get('reasoning_effort', 'high')
        history_messages = kwargs.get('history_messages')
        
        messages = self._build_messages(prompt, system_prompt, history_messages)
        
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
            user=user,
            thinking_enabled=thinking_enabled,
            reasoning_effort=reasoning_effort
        )
        
        client = self._get_api_client(api_name)
        return client, request
    
    def call_api(self, api_name: str, model: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """同步调用API进行聊天完成
        
        Args:
            api_name: API名称
            model: 模型名称
            prompt: 用户提示词
            **kwargs: 可选参数（system_prompt, max_tokens, temperature等）
            
        Returns:
            Dict[str, Any]: API响应字典
        """
        client, request = self._build_request_params(api_name, model, prompt, **kwargs)
        response = client.chat_completions(request)
        
        return response.to_dict()
    
    def _load_prompt_template(self, version: str = 'v1') -> Optional[Dict[str, Any]]:
        """加载提示词模板配置
        
        Args:
            version: 提示词版本，默认为'v1'
            
        Returns:
            Optional[Dict[str, Any]]: 提示词配置字典，加载失败时返回None
        """
        if not self.prompt_service:
            return None
        try:
            config = self.prompt_service.get_prompt_config(version)
            return config
        except Exception as e:
            logger.warning(f"加载提示词模板失败: {e}")
            return None

    def _merge_prompt_with_template(self, user_input: str, prompt_config: Dict[str, Any]) -> str:
        """将用户输入与提示词模板合并
        
        使用芯片布局信息填充模板中的{chip_layout}占位符，
        使用用户输入填充{user_requirements}占位符。
        
        Args:
            user_input: 用户原始输入
            prompt_config: 提示词配置字典
            
        Returns:
            str: 合并后的提示词，合并失败时返回原始用户输入
        """
        template = prompt_config.get('prompt_template', '')
        if not template:
            logger.warning("提示词模板为空，使用原始用户输入")
            return user_input

        chip_layout_str = self.chip_layout_service.format_for_prompt()

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
        """流式调用API进行聊天完成
        
        会先加载提示词模板并与用户输入合并，然后发起流式请求。
        
        Args:
            api_name: API名称
            model: 模型名称
            prompt: 用户提示词
            **kwargs: 可选参数（system_prompt, max_tokens, temperature, skip_prompt_merge等）
            
        Yields:
            Dict[str, Any]: 流式响应数据块
        """
        skip_prompt_merge = kwargs.pop('skip_prompt_merge', False)
        
        # 加载提示词模板并与用户输入合并
        if not skip_prompt_merge:
            prompt_config = self._load_prompt_template('v1')
            if prompt_config:
                logger.info(f"已加载v1提示词模板，开始合并用户输入")
                prompt = self._merge_prompt_with_template(prompt, prompt_config)
            else:
                logger.info("未能加载提示词模板，直接使用用户原始输入")
        else:
            logger.info("[stream_api] 跳过提示词模板合并（已由上游处理）")
        
        client, request = self._build_request_params(api_name, model, prompt, **kwargs)
        for chunk in client.stream_chat_completions(request):
            yield chunk
    
    def agentic_stream_api(self, api_name: str, model: str, prompt: str,
                           tool_registry, **kwargs) -> Generator[Dict[str, Any], None, None]:
        """流式优先的 Agent Loop API
        
        流式调用同时累积 tool_calls → 流结束后检查并执行工具 → 继续下一轮。
        文本内容在流式调用过程中实时输出到前端。
        
        Yields SSE 数据块：
        - {"type": "tool_status", "message": "..."} 工具状态事件
        - {"type": "tool_result", "tool_name": "...", "result": "..."} 工具执行结果
        - {"choices": [...]} 常规文本流数据块
        
        Args:
            api_name: API名称
            model: 模型名称
            prompt: 用户提示词
            tool_registry: ToolRegistry 实例
            **kwargs: 额外参数（max_tokens, temperature, thinking_enabled 等）
        """
        # 1. 加载提示词模板并合并（复用现有逻辑）
        prompt_config = self._load_prompt_template('v1')
        if prompt_config:
            logger.info("已加载v1提示词模板，开始合并用户输入（agentic模式）")
            prompt = self._merge_prompt_with_template(prompt, prompt_config)
        else:
            logger.info("未能加载提示词模板，直接使用用户原始输入（agentic模式）")
        
        # 2. 构建初始消息列表
        history_messages = kwargs.get('history_messages')
        messages = self._build_messages(prompt, history_messages=history_messages)
        tools = tool_registry.get_tool_definitions()
        
        max_iterations = 5
        client = self._get_api_client(api_name)
        api_config = self.get_api_config(api_name)
        
        # 从 kwargs 提取参数
        max_tokens = kwargs.get('max_tokens', 1024)
        temperature = kwargs.get('temperature', 0.7)
        thinking_enabled = kwargs.get('thinking_enabled', False)
        reasoning_effort = kwargs.get('reasoning_effort', 'high')
        
        for iteration in range(max_iterations):
            logger.info(f"[AgentLoop] 迭代 {iteration + 1}/{max_iterations}")
            
            # 3. 流式调用（带工具定义），实时输出 + 同时累积 tool_calls
            request_obj = ChatCompletionRequest(
                model=model or api_config.get('default_model', ''),
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                thinking_enabled=thinking_enabled,
                reasoning_effort=reasoning_effort,
                tools=tools,
                tool_choice='auto'
            )
            
            # 速率限制检查
            self._check_rate_limit(api_name)
            
            accumulated_content = ""
            accumulated_reasoning = ""
            accumulated_tool_calls = {}
            
            # 流式调用，实时推送文本/思维链内容到前端，同时累积 tool_calls
            for chunk in client.stream_chat_completions(request_obj):
                choices = chunk.get('choices', [])
                if not choices:
                    continue
                
                delta = choices[0].get('delta', {})
                
                # 实时推送文本/思维链内容到前端
                has_content = delta.get('content')
                has_reasoning = delta.get('reasoning_content')
                if has_content or has_reasoning:
                    yield chunk  # 直接推送到前端
                
                # 累积文本内容
                if has_content:
                    accumulated_content += has_content
                if has_reasoning:
                    accumulated_reasoning += has_reasoning
                
                # 累积 tool_calls 增量
                tool_calls_delta = delta.get('tool_calls')
                if tool_calls_delta:
                    _accumulate_tool_calls(accumulated_tool_calls, tool_calls_delta)
            
            # 4. 流结束后判断是否有工具调用
            if accumulated_tool_calls:
                tool_calls_list = [accumulated_tool_calls[k] for k in sorted(accumulated_tool_calls.keys())]
                logger.info(f"[AgentLoop] AI 请求调用 {len(tool_calls_list)} 个工具")
                
                # 将 assistant 消息（含 tool_calls）加入对话历史
                assistant_msg = {
                    "role": "assistant",
                    "content": accumulated_content,
                    "tool_calls": tool_calls_list
                }
                messages.append(assistant_msg)
                
                # 逐个执行工具
                for tc in tool_calls_list:
                    tool_name = tc['function']['name']
                    logger.info(f"[AgentLoop] 执行工具: {tool_name}, 参数: {tc['function']['arguments'][:200]}")
                    
                    yield {"type": "tool_status", "message": f"正在执行: {tool_name}..."}
                    
                    try:
                        arguments = json.loads(tc['function']['arguments'])
                        result = tool_registry.execute_tool(tool_name, arguments)
                    except Exception as e:
                        logger.error(f"[AgentLoop] 工具执行失败: {tool_name}, 错误: {e}")
                        result = json.dumps({"error": str(e), "tool_name": tool_name}, ensure_ascii=False)
                    
                    logger.info(f"[AgentLoop] 工具 {tool_name} 执行完成, 结果: {result[:200]}")
                    
                    # 追加 tool result 到 messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc['id'],
                        "content": result
                    })
                    
                    yield {"type": "tool_result", "tool_name": tool_name, "result": result}
                    yield {"type": "tool_status", "message": f"工具 {tool_name} 执行完成"}
                
                # 继续下一轮（以工具结果为上下文重新流式调用）
                continue
            else:
                # 无工具调用，流式内容已全部输出，结束
                break
        else:
            # 达到最大迭代次数
            logger.warning(f"[AgentLoop] 达到最大迭代次数 {max_iterations}")
            yield {
                "type": "tool_status",
                "message": f"警告：工具调用循环已达最大次数({max_iterations})，已停止"
            }
    
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


def _accumulate_tool_calls(accumulated: dict, delta_tool_calls: list):
    """从流式 delta 中累积 tool_calls 信息
    
    Args:
        accumulated: 累积的 tool_calls 字典，key 为 index
        delta_tool_calls: 当前 chunk 中的 tool_calls 增量列表
    """
    for tc in delta_tool_calls:
        idx = tc.get('index', 0)
        if idx not in accumulated:
            accumulated[idx] = {
                'id': tc.get('id', ''),
                'type': 'function',
                'function': {
                    'name': tc.get('function', {}).get('name', ''),
                    'arguments': ''
                }
            }
        else:
            if tc.get('id'):
                accumulated[idx]['id'] = tc['id']
            if tc.get('function', {}).get('name'):
                accumulated[idx]['function']['name'] = tc['function']['name']
        
        if tc.get('function', {}).get('arguments'):
            accumulated[idx]['function']['arguments'] += tc['function']['arguments']


