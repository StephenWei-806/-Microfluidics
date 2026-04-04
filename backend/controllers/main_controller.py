from flask import Blueprint, request, jsonify, Response
from services.config_service import ConfigService
from services.prompt_service import PromptService
from services.api_service import ApiService
import os
import json
import uuid
import time
import logging
import requests as req_lib

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

# 流式请求参数暂存（两步式 EventSource 方案）
_stream_requests = {}
_STREAM_REQUEST_TTL = 60  # 秒，请求参数过期时间


def _cleanup_expired_streams():
    """清理过期的流式请求参数"""
    now = time.time()
    expired = [sid for sid, data in _stream_requests.items() if now - data['created_at'] > _STREAM_REQUEST_TTL]
    for sid in expired:
        del _stream_requests[sid]

config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
config_service = ConfigService(config_dir)
prompt_service = PromptService(config_service)
api_service = ApiService(config_service, prompt_service)

def error_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'code': 500,
                'message': str(e),
                'data': None
            }), 500
    wrapper.__name__ = func.__name__
    return wrapper

@main_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': {
            'status': 'healthy',
            'service': '微流控后端服务'
        }
    })

@main_bp.route('/settings', methods=['GET'])
@error_handler
def get_settings():
    settings = config_service.get_settings()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': settings
    })

@main_bp.route('/api/config', methods=['GET'])
@error_handler
def get_api_config():
    api_config = config_service.get_api_config()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': api_config
    })

@main_bp.route('/api/key', methods=['POST'])
@error_handler
def update_api_key():
    data = request.get_json()
    api_name = data.get('api_name')
    api_key = data.get('api_key')
    
    if not api_name or not api_key:
        return jsonify({
            'code': 400,
            'message': '缺少必要参数',
            'data': None
        }), 400
    
    success = api_service.update_api_key(api_name, api_key)
    return jsonify({
        'code': 200 if success else 400,
        'message': '更新成功' if success else '更新失败',
        'data': {'api_name': api_name}
    })

@main_bp.route('/prompts/versions', methods=['GET'])
@error_handler
def get_prompt_versions():
    versions = prompt_service.get_all_versions()
    version_history = prompt_service.get_version_history()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': {
            'versions': versions,
            'history': version_history
        }
    })

@main_bp.route('/prompts/modules', methods=['GET'])
@error_handler
def get_prompt_modules():
    version = request.args.get('version', 'v1')
    modules = prompt_service.get_modules(version)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': modules
    })

@main_bp.route('/prompts/<module_name>', methods=['GET'])
@error_handler
def get_module_prompts(module_name):
    version = request.args.get('version', 'v1')
    prompts = prompt_service.get_prompts(module_name, version)
    if prompts is None:
        return jsonify({
            'code': 404,
            'message': '模块不存在',
            'data': None
        }), 404
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': prompts
    })

@main_bp.route('/prompts/render', methods=['POST'])
@error_handler
def render_prompt():
    data = request.get_json()
    module_name = data.get('module_name')
    prompt_name = data.get('prompt_name')
    params = data.get('params', {})
    version = data.get('version', 'v1')
    
    if not module_name or not prompt_name:
        return jsonify({
            'code': 400,
            'message': '缺少必要参数',
            'data': None
        }), 400
    
    rendered_prompt = prompt_service.render_prompt(module_name, prompt_name, params, version)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': {
            'prompt': rendered_prompt
        }
    })

@main_bp.route('/prompts/search', methods=['GET'])
@error_handler
def search_prompts():
    keyword = request.args.get('keyword', '')
    version = request.args.get('version', 'v1')
    
    if not keyword:
        return jsonify({
            'code': 400,
            'message': '缺少搜索关键词',
            'data': None
        }), 400
    
    results = prompt_service.search_prompts(keyword, version)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': results
    })

@main_bp.route('/prompts/statistics', methods=['GET'])
@error_handler
def get_prompt_statistics():
    version = request.args.get('version', 'v1')
    statistics = prompt_service.get_prompt_statistics(version)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': statistics
    })

@main_bp.route('/api/models/<api_name>', methods=['GET'])
@error_handler
def get_api_models(api_name):
    models = api_service.get_models(api_name)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': {
            'api_name': api_name,
            'models': models
        }
    })

@main_bp.route('/api/validate/<api_name>', methods=['GET'])
@error_handler
def validate_api_config(api_name):
    valid = api_service.validate_api_config(api_name)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': {
            'api_name': api_name,
            'valid': valid
        }
    })

@main_bp.route('/api/call', methods=['POST'])
@error_handler
def call_api():
    data = request.get_json()
    api_name = data.get('api_name')
    model = data.get('model')
    prompt = data.get('prompt')
    max_tokens = data.get('max_tokens', 1024)
    temperature = data.get('temperature', 0.7)
    
    if not api_name or not model or not prompt:
        return jsonify({
            'code': 400,
            'message': '缺少必要参数',
            'data': None
        }), 400
    
    response = api_service.call_api(
        api_name, model, prompt,
        max_tokens=max_tokens,
        temperature=temperature
    )
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': response
    })

def stream_api_response(api_name, model, prompt, **kwargs):
    logger.info(f'[SSE] 开始发送SSE流: api_name={api_name}, model={model}')
    try:
        for chunk in api_service.stream_api(api_name, model, prompt, **kwargs):
            chunk_str = json.dumps(chunk)
            logger.info(f'[SSE] 发送数据块: {chunk_str[:100]}...' if len(chunk_str) > 100 else f'[SSE] 发送数据块: {chunk_str}')
            yield f'data: {chunk_str}\n\n'
        logger.info('[SSE] 流式传输完成')
        yield 'data: [DONE]\n\n'
    except req_lib.exceptions.ReadTimeout as e:
        logger.error(f'[SSE] 流式传输读取超时: {str(e)}')
        yield f'data: {json.dumps({"error": "API响应超时，请稍后重试或缩短提问内容"})}\n\n'
        yield 'data: [DONE]\n\n'
    except req_lib.exceptions.ConnectionError as e:
        logger.error(f'[SSE] 流式传输连接错误: {str(e)}')
        yield f'data: {json.dumps({"error": "无法连接到API服务，请检查网络连接"})}\n\n'
        yield 'data: [DONE]\n\n'
    except Exception as e:
        logger.error(f'[SSE] 流式传输异常: {str(e)}')
        yield f'data: {json.dumps({"error": str(e)})}\n\n'
        yield 'data: [DONE]\n\n'

@main_bp.route('/stream/init', methods=['POST'])
@error_handler
def init_stream():
    """初始化流式请求，返回 stream_id（两步式 EventSource 方案）"""
    data = request.get_json()
    api_name = data.get('api_name')
    model = data.get('model')
    prompt = data.get('prompt')
    max_tokens = data.get('max_tokens', 1024)
    temperature = data.get('temperature', 0.7)
    
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
            'temperature': temperature
        },
        'created_at': time.time()
    }
    
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': {'stream_id': stream_id}
    })


@main_bp.route('/stream/<stream_id>', methods=['GET'])
def stream_by_id(stream_id):
    """通过 stream_id 获取 SSE 流（两步式 EventSource 方案）"""
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
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control',
            }
        )
    
    # 获取参数并调用流式响应生成器
    params = stream_data['params']
    response = Response(
        stream_api_response(
            params['api_name'],
            params['model'],
            params['prompt'],
            max_tokens=params['max_tokens'],
            temperature=params['temperature']
        ),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control',
        }
    )
    return response


@main_bp.route('/stream', methods=['POST'])
@error_handler
def stream_api():
    data = request.get_json()
    api_name = data.get('api_name')
    model = data.get('model')
    prompt = data.get('prompt')
    max_tokens = data.get('max_tokens', 1024)
    temperature = data.get('temperature', 0.7)
    
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
            max_tokens=max_tokens,
            temperature=temperature
        ),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Cache-Control',
        }
    )
    return response


@main_bp.route('/chip-layout', methods=['GET'])
@error_handler
def get_chip_layout():
    """获取当前生效的芯片网格配置"""
    layout = api_service.get_current_chip_layout()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': layout
    })


@main_bp.route('/chip-layout', methods=['POST'])
@error_handler
def update_chip_layout():
    """更新芯片网格配置"""
    data = request.get_json()
    grid = data.get('grid')
    
    if grid is None:
        return jsonify({
            'code': 400,
            'message': '缺少 grid 参数',
            'data': None
        }), 400
    
    # 校验格式
    if not isinstance(grid, list) or len(grid) != 17:
        return jsonify({
            'code': 400,
            'message': '网格必须为17行',
            'data': None
        }), 400
    
    for i, row in enumerate(grid):
        if not isinstance(row, list) or len(row) != 22:
            return jsonify({
                'code': 400,
                'message': f'第{i+1}行必须为22列',
                'data': None
            }), 400
        for j, val in enumerate(row):
            if not isinstance(val, int) or val < 0 or val > 128:
                return jsonify({
                    'code': 400,
                    'message': f'网格值必须为0-128的整数 (行{i+1}, 列{j+1})',
                    'data': None
                }), 400
    
    api_service.set_custom_chip_layout(grid)
    logger.info(f'[ChipLayout] 用户更新了芯片网格配置')
    
    return jsonify({
        'code': 200,
        'message': '芯片网格配置更新成功',
        'data': None
    })
