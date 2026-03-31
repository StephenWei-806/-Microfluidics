import os
from typing import Dict, Any, Optional
from utils.config_utils import ConfigLoader, get_config_path, get_prompt_config_path, list_prompt_versions

class ConfigService:
    """配置管理服务"""
    
    def __init__(self, config_dir: str):
        """初始化配置服务
        
        Args:
            config_dir: 配置文件目录路径
        """
        self.config_dir = config_dir
        self.config_loader = ConfigLoader()
    
    def load_yaml(self, file_path: str) -> Dict[str, Any]:
        """加载YAML文件
        
        Args:
            file_path: YAML文件路径
            
        Returns:
            解析后的配置字典
        """
        return self.config_loader.load_yaml(file_path)
    
    def get_settings(self) -> Dict[str, Any]:
        """获取系统设置
        
        Returns:
            系统设置配置
        """
        settings_path = get_config_path(self.config_dir, 'settings.yaml')
        return self.load_yaml(settings_path)
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置
        
        Returns:
            API配置
        """
        api_config_path = get_config_path(self.config_dir, 'api.yaml')
        return self.load_yaml(api_config_path)
    
    def get_prompt_config(self, version: str = 'v1') -> Dict[str, Any]:
        """获取提示词配置
        
        Args:
            version: 提示词版本
            
        Returns:
            提示词配置
        """
        prompt_config_path = get_prompt_config_path(self.config_dir, version)
        return self.load_yaml(prompt_config_path)
    
    def get_all_prompt_versions(self) -> list:
        """获取所有提示词版本
        
        Returns:
            版本列表
        """
        return list_prompt_versions(self.config_dir)
    
    def clear_cache(self) -> None:
        """清除配置缓存"""
        self.config_loader.clear_cache()
    
    def set_cache_ttl(self, ttl: int) -> None:
        """设置缓存过期时间
        
        Args:
            ttl: 缓存过期时间（秒）
        """
        self.config_loader.set_cache_ttl(ttl)
    
    def enable_cache(self, enable: bool) -> None:
        """启用/禁用缓存
        
        Args:
            enable: 是否启用缓存
        """
        self.config_loader.enable_cache(enable)
