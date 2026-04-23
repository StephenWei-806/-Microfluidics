from flask import Blueprint, jsonify
from .base import error_handler
from . import config_service

health_bp = Blueprint('health', __name__, url_prefix='/api')


@health_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查接口
    
    返回服务运行状态和健康信息。
    
    Returns:
        Response: JSON响应，包含服务状态信息
        - code: HTTP状态码200
        - message: 状态描述
        - data: 包含status和service字段的字典
    """
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': {
            'status': 'healthy',
            'service': '微流控后端服务'
        }
    })


@health_bp.route('/settings', methods=['GET'])
@error_handler
def get_settings():
    """获取系统设置
    
    返回当前系统的配置设置信息。
    
    Returns:
        Response: JSON响应，包含系统设置数据
        - code: HTTP状态码200
        - message: 状态描述
        - data: 系统设置字典
    """
    settings = config_service.get_settings()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': settings
    })
