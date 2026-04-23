import os
from flask import Flask

from services.config_service import ConfigService
from services.prompt_service import PromptService
from services.api_service import ApiService
from services.chip_layout_service import ChipLayoutService

config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
config_service = ConfigService(config_dir)
prompt_service = PromptService(config_service)
chip_layout_service = ChipLayoutService(config_service, persist_dir='./data')
api_service = ApiService(config_service, chip_layout_service, prompt_service)


def register_blueprints(app: Flask):
    """统一注册所有 Flask Blueprint

    Args:
        app: Flask 应用实例
    """
    from .health_controller import health_bp
    from .api_controller import api_mgmt_bp
    from .stream_controller import stream_bp
    from .prompt_controller import prompt_bp
    from .chip_layout_controller import chip_layout_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(api_mgmt_bp)
    app.register_blueprint(stream_bp)
    app.register_blueprint(prompt_bp)
    app.register_blueprint(chip_layout_bp)
