from flask import Flask
from flask_cors import CORS
from controllers.main_controller import main_bp, config_service, chip_layout_service
import os
import logging

# 创建Flask应用实例
app = Flask(__name__)

# 配置CORS
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# 注册蓝图
app.register_blueprint(main_bp, url_prefix='/api')

# 确保日志目录存在
log_dir = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 配置日志
log_file = os.path.join(log_dir, 'app.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 健康检查路由
@app.route('/')
def index():
    """根路由处理函数，返回服务状态信息
    
    Returns:
        dict: 包含服务状态信息的字典
        - message: 服务描述信息
        - version: 服务版本号
        - status: 服务健康状态
    """
    return {
        'message': '微流控后端服务运行中',
        'version': '1.0.0',
        'status': 'healthy'
    }

# 错误处理
@app.errorhandler(404)
def not_found(error):
    """404错误处理函数
    
    Args:
        error: Flask错误对象
        
    Returns:
        tuple: (包含错误信息的字典, HTTP状态码404)
        - code: 错误代码404
        - message: 错误描述信息
        - data: 数据字段，固定为None
    """
    return {
        'code': 404,
        'message': '接口不存在',
        'data': None
    }, 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理函数
    
    Args:
        error: Flask错误对象
        
    Returns:
        tuple: (包含错误信息的字典, HTTP状态码500)
        - code: 错误代码500
        - message: 错误描述信息
        - data: 数据字段，固定为None
    """
    return {
        'code': 500,
        'message': '服务器内部错误',
        'data': None
    }, 500

if __name__ == '__main__':
    # 获取配置
    import json
    import yaml
    config_path = os.path.join(os.path.dirname(__file__), 'config', 'settings.yaml')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        server_config = config.get('server', {})
        host = server_config.get('host', '0.0.0.0')
        port = server_config.get('port', 5000)
        debug = server_config.get('debug', True)
    except Exception:
        # 默认配置
        host = '0.0.0.0'
        port = 5000
        debug = True
    
    # 启动服务
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )
