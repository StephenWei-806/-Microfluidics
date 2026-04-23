from flask import Blueprint, request, jsonify
from .base import error_handler
from . import chip_layout_service
import logging

logger = logging.getLogger(__name__)

chip_layout_bp = Blueprint('chip_layout', __name__, url_prefix='/api')


@chip_layout_bp.route('/chip-layout', methods=['GET'])
@error_handler
def get_chip_layout():
    """获取当前生效的芯片网格配置"""
    layout = chip_layout_service.get_current_layout()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': layout
    })


@chip_layout_bp.route('/chip-layout', methods=['POST'])
@error_handler
def update_chip_layout():
    """更新芯片网格配置"""
    data = request.get_json()
    grid = data.get('grid')
    
    # 使用 ChipLayoutService 验证网格
    is_valid, errors = chip_layout_service.validate_grid(grid)
    if not is_valid:
        return jsonify({
            'code': 400,
            'message': '网格验证失败',
            'data': {'errors': errors}
        }), 400
    
    chip_layout_service.set_custom_layout(grid)
    logger.info(f'[ChipLayout] 用户更新了芯片网格配置')
    
    return jsonify({
        'code': 200,
        'message': '芯片网格配置更新成功',
        'data': None
    })


@chip_layout_bp.route('/chip-layout/reset', methods=['POST'])
@error_handler
def reset_chip_layout():
    """重置芯片网格配置为默认值"""
    layout = chip_layout_service.reset_to_default()
    return jsonify({
        'code': 200,
        'message': '芯片网格配置已重置为默认值',
        'data': layout
    })


@chip_layout_bp.route('/chip-layout/statistics', methods=['GET'])
@error_handler
def get_chip_layout_statistics():
    """获取芯片网格配置统计信息"""
    stats = chip_layout_service.get_statistics()
    return jsonify({
        'code': 200,
        'message': 'ok',
        'data': stats
    })
