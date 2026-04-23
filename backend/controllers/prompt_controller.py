from flask import Blueprint, request, jsonify
from .base import error_handler
from . import prompt_service

prompt_bp = Blueprint('prompt', __name__, url_prefix='/api')


@prompt_bp.route('/prompts/versions', methods=['GET'])
@error_handler
def get_prompt_versions():
    """获取所有提示词版本
    
    返回系统中所有可用的提示词版本列表及历史记录。
    
    Returns:
        Response: JSON响应
        - code: HTTP状态码200
        - message: 状态描述
        - data: 包含versions和history的字典
    """
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


@prompt_bp.route('/prompts/modules', methods=['GET'])
@error_handler
def get_prompt_modules():
    """获取提示词模块列表
    
    返回指定版本下的所有提示词模块。
    
    Args:
        version: 查询参数，提示词版本，默认为'v1'
        
    Returns:
        Response: JSON响应
        - code: HTTP状态码200
        - message: 状态描述
        - data: 模块列表
    """
    version = request.args.get('version', 'v1')
    modules = prompt_service.get_modules(version)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': modules
    })


@prompt_bp.route('/prompts/<module_name>', methods=['GET'])
@error_handler
def get_module_prompts(module_name):
    """获取指定模块的提示词
    
    返回指定模块和版本下的所有提示词。
    
    Args:
        module_name: URL参数，模块名称
        version: 查询参数，提示词版本，默认为'v1'
        
    Returns:
        Response: JSON响应
        - code: HTTP状态码200成功或404模块不存在
        - message: 状态描述
        - data: 提示词列表或None
    """
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


@prompt_bp.route('/prompts/render', methods=['POST'])
@error_handler
def render_prompt():
    """渲染提示词模板
    
    根据参数渲染指定的提示词模板。
    
    Args:
        从请求JSON中获取:
        - module_name: 模块名称（必填）
        - prompt_name: 提示词名称（必填）
        - params: 模板参数，默认为空字典
        - version: 提示词版本，默认为'v1'
        
    Returns:
        Response: JSON响应
        - code: HTTP状态码200成功或400参数缺失
        - message: 状态描述
        - data: 包含渲染后prompt的字典
    """
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


@prompt_bp.route('/prompts/search', methods=['GET'])
@error_handler
def search_prompts():
    """搜索提示词
    
    根据关键词搜索提示词。
    
    Args:
        keyword: 查询参数，搜索关键词（必填）
        version: 查询参数，提示词版本，默认为'v1'
        
    Returns:
        Response: JSON响应
        - code: HTTP状态码200成功或400参数缺失
        - message: 状态描述
        - data: 搜索结果列表
    """
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


@prompt_bp.route('/prompts/statistics', methods=['GET'])
@error_handler
def get_prompt_statistics():
    """获取提示词统计信息
    
    返回指定版本提示词的统计信息。
    
    Args:
        version: 查询参数，提示词版本，默认为'v1'
        
    Returns:
        Response: JSON响应
        - code: HTTP状态码200
        - message: 状态描述
        - data: 统计信息字典
    """
    version = request.args.get('version', 'v1')
    statistics = prompt_service.get_prompt_statistics(version)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': statistics
    })
