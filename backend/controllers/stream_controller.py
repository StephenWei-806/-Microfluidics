from flask import Blueprint, request, jsonify, Response
from .base import error_handler, SSE_HEADERS
from . import api_service
from . import config_service
from . import tool_registry
import uuid
import time
import json
import logging
import requests as req_lib

logger = logging.getLogger(__name__)

stream_bp = Blueprint('stream', __name__, url_prefix='/api')

# 流式请求参数暂存（两步式 EventSource 方案）
_stream_requests = {}
_STREAM_REQUEST_TTL = 60  # 秒，请求参数过期时间


def _cleanup_expired_streams():
    """清理过期的流式请求参数"""
    now = time.time()
    expired = [sid for sid, data in _stream_requests.items() if now - data['created_at'] > _STREAM_REQUEST_TTL]
    for sid in expired:
        del _stream_requests[sid]


def stream_api_response(api_name, model, prompt, tools_enabled=False, **kwargs):
    """SSE流式响应生成器
    
    生成SSE格式的流式响应数据，用于Server-Sent Events推送。
    
    Args:
        api_name: API名称
        model: 模型名称
        prompt: 用户提示词
        tools_enabled: 是否启用工具调用（Agent Loop模式）
        **kwargs: 额外的请求参数（max_tokens, temperature等）
        
    Yields:
        str: SSE格式的数据行（data: {...}\n\n）
        
    Raises:
        不抛出异常，内部捕获并返回错误信息
    """
    logger.info(f'[SSE] 开始发送SSE流: api_name={api_name}, model={model}, tools_enabled={tools_enabled}')
    chunk_count = 0
    try:
        if tools_enabled:
            # 千问 API 降级：千问不支持 function calling，自动回退到普通流式对话
            api_config = api_service.get_api_config(api_name)
            api_type = api_config.get('api_type', 'openai') if api_config else 'openai'
            
            if api_type == 'qwen':
                logger.info(f'[SSE] 千问 API 不支持工具调用，降级为普通流式对话: api_name={api_name}')
                for chunk in api_service.stream_api(api_name, model, prompt, **kwargs):
                    chunk_str = json.dumps(chunk)
                    chunk_count += 1
                    yield f'data: {chunk_str}\n\n'
            else:
                # OpenAI 兼容 API（DeepSeek 等）：使用流式优先 Agent Loop
                for chunk in api_service.agentic_stream_api(
                    api_name, model, prompt,
                    tool_registry=tool_registry,
                    **kwargs
                ):
                    chunk_str = json.dumps(chunk)
                    chunk_count += 1
                    yield f'data: {chunk_str}\n\n'
        else:
            # 现有逻辑：普通流式调用
            for chunk in api_service.stream_api(api_name, model, prompt, **kwargs):
                chunk_str = json.dumps(chunk)
                chunk_count += 1
                yield f'data: {chunk_str}\n\n'
        logger.info('[SSE] 流式传输完成')
        yield 'data: [DONE]\n\n'
    except req_lib.exceptions.ReadTimeout as e:
        logger.error(f'[SSE] 流式传输读取超时: {str(e)}', exc_info=True)
        yield f'data: {json.dumps({"error": "API响应超时，请稍后重试或缩短提问内容"})}\n\n'
        yield 'data: [DONE]\n\n'
    except req_lib.exceptions.ConnectionError as e:
        logger.error(f'[SSE] 流式传输连接错误: {str(e)}', exc_info=True)
        yield f'data: {json.dumps({"error": "无法连接到API服务，请检查网络连接"})}\n\n'
        yield 'data: [DONE]\n\n'
    except Exception as e:
        logger.error(f'[SSE] 流式传输异常: {str(e)}', exc_info=True)
        yield f'data: {json.dumps({"error": str(e)})}\n\n'
        yield 'data: [DONE]\n\n'


@stream_bp.route('/stream/init', methods=['POST'])
@error_handler
def init_stream():
    """初始化流式请求，返回 stream_id（两步式 EventSource 方案）"""
    data = request.get_json()
    api_name = data.get('api_name')
    model = data.get('model')
    prompt = data.get('prompt')
    max_tokens = data.get('max_tokens', 1024)
    temperature = data.get('temperature', 0.7)
    thinking_enabled = data.get('thinking_enabled', False)
    reasoning_effort = data.get('reasoning_effort', 'high')
    tools_enabled = data.get('tools_enabled', False)
    messages = data.get('messages', [])
    
    # 记录请求参数
    prompt_preview = prompt[:50] if prompt else ''
    logger.info(f'[SSE] 初始化流式请求: api_name={api_name}, model={model}, prompt={prompt_preview}...')
    
    # 验证必填参数
    if not api_name or not model or not prompt:
        return jsonify({
            'code': 400,
            'message': '缺少必要参数',
            'data': None
        }), 400
    
    # 清理过期项
    _cleanup_expired_streams()
    
    # 生成 stream_id
    stream_id = str(uuid.uuid4())
    logger.info(f'[SSE] 生成 stream_id: {stream_id}')
    
    # 存储请求参数
    _stream_requests[stream_id] = {
        'params': {
            'api_name': api_name,
            'model': model,
            'prompt': prompt,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'thinking_enabled': thinking_enabled,
            'reasoning_effort': reasoning_effort,
            'tools_enabled': tools_enabled,
            'messages': messages
        },
        'created_at': time.time()
    }
    
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': {'stream_id': stream_id}
    })


@stream_bp.route('/stream/<stream_id>', methods=['GET'])
def stream_by_id(stream_id):
    """通过 stream_id 获取 SSE 流（两步式 EventSource 方案）"""
    try:
        logger.info(f'[SSE] 连接建立: stream_id={stream_id}')
        
        # 从存储中取出参数（一次性使用）
        stream_data = _stream_requests.pop(stream_id, None)
        
        if stream_data is None:
            logger.warning(f'[SSE] 无效或过期的 stream_id: {stream_id}')
            # stream_id 不存在或已过期，返回 SSE 格式的错误
            def error_stream():
                yield 'data: {"error": "Invalid or expired stream_id"}\n\n'
                yield 'data: [DONE]\n\n'
            
            return Response(
                error_stream(),
                mimetype='text/event-stream',
                headers=SSE_HEADERS
            )
        
        # 获取参数并调用流式响应生成器
        params = stream_data['params']
        tools_enabled = params.get('tools_enabled', False)
        history_messages = params.get('messages', [])
        response = Response(
            stream_api_response(
                params['api_name'],
                params['model'],
                params['prompt'],
                tools_enabled=tools_enabled,
                history_messages=history_messages,
                max_tokens=params['max_tokens'],
                temperature=params['temperature'],
                thinking_enabled=params.get('thinking_enabled', False),
                reasoning_effort=params.get('reasoning_effort', 'high')
            ),
            mimetype='text/event-stream',
            headers=SSE_HEADERS
        )
        return response
    except Exception as e:
        logger.error(f'[SSE] stream_by_id异常: {str(e)}', exc_info=True)
        def error_stream():
            yield f'data: {json.dumps({"error": f"服务器内部错误: {str(e)}"})}\n\n'
            yield 'data: [DONE]\n\n'
        return Response(error_stream(), mimetype='text/event-stream', headers=SSE_HEADERS)


@stream_bp.route('/stream', methods=['POST'])
@error_handler
def stream_api():
    """流式API调用接口（POST方式）
    
    通过POST请求建立SSE流式连接，实时返回API响应。
    
    Args:
        从请求JSON中获取:
        - api_name: API名称（必填）
        - model: 模型名称（必填）
        - prompt: 用户提示词（必填）
        - max_tokens: 最大token数，默认1024
        - temperature: 采样温度，默认0.7
        - thinking_enabled: 是否启用思考模式，默认False
        - reasoning_effort: 推理努力程度，默认'high'
        
    Returns:
        Response: SSE流式响应或JSON错误响应
        - 成功时返回text/event-stream格式的流数据
        - 参数缺失时返回400错误
    """
    data = request.get_json()
    api_name = data.get('api_name')
    model = data.get('model')
    prompt = data.get('prompt')
    max_tokens = data.get('max_tokens', 1024)
    temperature = data.get('temperature', 0.7)
    thinking_enabled = data.get('thinking_enabled', False)
    reasoning_effort = data.get('reasoning_effort', 'high')
    tools_enabled = data.get('tools_enabled', False)
    history_messages = data.get('messages', [])
    
    logger.info(f'[SSE] POST /stream 连接开始: api_name={api_name}, model={model}')
    
    if not api_name or not model or not prompt:
        return jsonify({
            'code': 400,
            'message': '缺少必要参数',
            'data': None
        }), 400
    
    response = Response(
        stream_api_response(
            api_name, model, prompt,
            tools_enabled=tools_enabled,
            history_messages=history_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            thinking_enabled=thinking_enabled,
            reasoning_effort=reasoning_effort
        ),
        mimetype='text/event-stream',
        headers=SSE_HEADERS
    )
    return response
