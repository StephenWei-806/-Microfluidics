import yaml
import os
import time
from typing import Dict, Any, Optional


class ConfigLoader:
    """配置文件加载器"""
    
    def __init__(self, cache_enabled: bool = True, cache_ttl: int = 3600):
        """初始化配置加载器
        
        Args:
            cache_enabled: 是否启用缓存
            cache_ttl: 缓存过期时间（秒）
        """
        self.config_cache: Dict[str, Dict[str, Any]] = {}
        self.last_modified: Dict[str, float] = {}
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl
    
    def load_yaml(self, file_path: str) -> Dict[str, Any]:
        """加载YAML文件
        
        Args:
            file_path: YAML文件路径
            
        Returns:
            解析后的配置字典
        """
        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        # 检查缓存
        if self.cache_enabled:
            file_mtime = os.path.getmtime(file_path)
            cache_key = file_path
            
            # 如果缓存存在且未过期
            if cache_key in self.config_cache and cache_key in self.last_modified:
                if file_mtime <= self.last_modified[cache_key] and \
                   time.time() - self.last_modified[cache_key] < self.cache_ttl:
                    return self.config_cache[cache_key]
        
        # 加载文件
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 更新缓存
        if self.cache_enabled:
            cache_key = file_path
            self.config_cache[cache_key] = config
            self.last_modified[cache_key] = os.path.getmtime(file_path)
        
        return config
    
    def clear_cache(self) -> None:
        """清除配置缓存"""
        self.config_cache.clear()
        self.last_modified.clear()
    
    def set_cache_ttl(self, ttl: int) -> None:
        """设置缓存过期时间
        
        Args:
            ttl: 缓存过期时间（秒）
        """
        self.cache_ttl = ttl
    
    def enable_cache(self, enable: bool) -> None:
        """启用/禁用缓存
        
        Args:
            enable: 是否启用缓存
        """
        self.cache_enabled = enable
        if not enable:
            self.clear_cache()


def get_config_path(config_dir: str, config_file: str) -> str:
    """获取配置文件路径
    
    Args:
        config_dir: 配置目录
        config_file: 配置文件名
        
    Returns:
        完整的配置文件路径
    """
    return os.path.join(config_dir, config_file)


def get_prompt_config_path(config_dir: str, version: str = 'v1') -> str:
    """获取提示词配置文件路径
    
    Args:
        config_dir: 配置目录
        version: 提示词版本
        
    Returns:
        完整的提示词配置文件路径
    """
    return os.path.join(config_dir, 'prompts', version, 'prompt_config.yaml')


def list_prompt_versions(config_dir: str) -> list:
    """获取所有提示词版本
    
    Args:
        config_dir: 配置目录
        
    Returns:
        版本列表
    """
    prompts_dir = os.path.join(config_dir, 'prompts')
    if not os.path.exists(prompts_dir):
        return []
    
    versions = []
    for item in os.listdir(prompts_dir):
        item_path = os.path.join(prompts_dir, item)
        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, 'prompt_config.yaml')):
            versions.append(item)
    
    return versions
