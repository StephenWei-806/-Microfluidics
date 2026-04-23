from flask import Blueprint, request, jsonify
from .base import error_handler
from . import api_service, config_service

api_mgmt_bp = Blueprint('api_mgmt', __name__, url_prefix='/api')


@api_mgmt_bp.route('/api/config', methods=['GET'])
@error_handler
def get_api_config():
    """获取API配置
    
    返回当前配置的API信息（不包含敏感信息如API密钥）。
    
    Returns:
        Response: JSON响应，包含API配置数据
        - code: HTTP状态码200
        - message: 状态描述
        - data: API配置字典
    """
    api_config = config_service.get_api_config()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': api_config
    })


@api_mgmt_bp.route('/api/key', methods=['POST'])
@error_handler
def update_api_key():
    """更新API密钥
    
    更新指定API的访问密钥。
    
    Args:
        从请求JSON中获取:
        - api_name: API名称
        - api_key: 新的API密钥
        
    Returns:
        Response: JSON响应
        - code: HTTP状态码200成功或400失败
        - message: 操作结果描述
        - data: 包含api_name的字典
    """
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


@api_mgmt_bp.route('/api/models/<api_name>', methods=['GET'])
@error_handler
def get_api_models(api_name):
    """获取API支持的模型列表
    
    返回指定API支持的所有模型。
    
    Args:
        api_name: URL参数，API名称
        
    Returns:
        Response: JSON响应
        - code: HTTP状态码200
        - message: 状态描述
        - data: 包含api_name和models的字典
    """
    models = api_service.get_models(api_name)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': {
            'api_name': api_name,
            'models': models
        }
    })


@api_mgmt_bp.route('/api/validate/<api_name>', methods=['GET'])
@error_handler
def validate_api_config(api_name):
    """验证API配置
    
    验证指定API的配置是否有效。
    
    Args:
        api_name: URL参数，API名称
        
    Returns:
        Response: JSON响应
        - code: HTTP状态码200
        - message: 状态描述
        - data: 包含api_name和valid验证结果的字典
    """
    valid = api_service.validate_api_config(api_name)
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': {
            'api_name': api_name,
            'valid': valid
        }
    })


@api_mgmt_bp.route('/api/call', methods=['POST'])
@error_handler
def call_api():
    """调用API进行聊天完成
    
    同步调用指定API进行聊天完成请求。
    
    Args:
        从请求JSON中获取:
        - api_name: API名称（必填）
        - model: 模型名称（必填）
        - prompt: 用户提示词（必填）
        - max_tokens: 最大token数，默认1024
        - temperature: 采样温度，默认0.7
        
    Returns:
        Response: JSON响应
        - code: HTTP状态码200成功或400参数缺失
        - message: 状态描述
        - data: API响应数据
    """
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
