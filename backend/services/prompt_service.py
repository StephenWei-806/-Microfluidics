import os
from typing import Dict, Any, List, Optional
from services.config_service import ConfigService

class PromptService:
    """提示词管理服务"""
    
    def __init__(self, config_service: ConfigService):
        """初始化提示词服务
        
        Args:
            config_service: 配置管理服务实例
        """
        self.config_service = config_service
        self.prompt_cache: Dict[str, Dict[str, Any]] = {}
    
    def get_prompt_config(self, version: str = 'v1') -> Dict[str, Any]:
        """获取指定版本的提示词配置
        
        Args:
            version: 提示词版本
            
        Returns:
            提示词配置字典
        """
        return self.config_service.get_prompt_config(version)
    
    def get_all_versions(self) -> List[str]:
        """获取所有提示词版本
        
        Returns:
            版本列表
        """
        return self.config_service.get_all_prompt_versions()
    
    def get_modules(self, version: str = 'v1') -> Dict[str, Any]:
        """获取指定版本的所有业务模块
        
        Args:
            version: 提示词版本
            
        Returns:
            业务模块字典
        """
        prompt_config = self.get_prompt_config(version)
        return prompt_config.get('modules', {})
    
    def get_module(self, module_name: str, version: str = 'v1') -> Optional[Dict[str, Any]]:
        """获取指定模块的配置
        
        Args:
            module_name: 模块名称
            version: 提示词版本
            
        Returns:
            模块配置字典，如果不存在则返回None
        """
        modules = self.get_modules(version)
        return modules.get(module_name)
    
    def get_prompts(self, module_name: str, version: str = 'v1') -> Optional[Dict[str, Any]]:
        """获取指定模块的所有提示词
        
        Args:
            module_name: 模块名称
            version: 提示词版本
            
        Returns:
            提示词字典，如果模块不存在则返回None
        """
        module = self.get_module(module_name, version)
        if module:
            return module.get('prompts', {})
        return None
    
    def get_prompt(self, module_name: str, prompt_name: str, version: str = 'v1') -> Optional[Dict[str, Any]]:
        """获取指定的提示词模板
        
        Args:
            module_name: 模块名称
            prompt_name: 提示词名称
            version: 提示词版本
            
        Returns:
            提示词模板字典，如果不存在则返回None
        """
        prompts = self.get_prompts(module_name, version)
        if prompts:
            return prompts.get(prompt_name)
        return None
    
    def render_prompt(self, module_name: str, prompt_name: str, params: Dict[str, Any], version: str = 'v1') -> str:
        """渲染提示词模板
        
        Args:
            module_name: 模块名称
            prompt_name: 提示词名称
            params: 提示词参数
            version: 提示词版本
            
        Returns:
            渲染后的提示词字符串
        """
        prompt = self.get_prompt(module_name, prompt_name, version)
        if not prompt:
            raise Exception(f"提示词不存在: {module_name}.{prompt_name}")
        
        template = prompt.get('template', '')
        try:
            return template.format(**params)
        except KeyError as e:
            raise Exception(f"提示词参数缺失: {str(e)}")
    
    def get_version_history(self) -> List[Dict[str, Any]]:
        """获取提示词版本历史
        
        Returns:
            版本历史列表，包含版本信息和描述
        """
        versions = self.get_all_versions()
        version_history = []
        
        for version in versions:
            try:
                prompt_config = self.get_prompt_config(version)
                version_info = {
                    'version': version,
                    'description': prompt_config.get('description', ''),
                    'config_version': prompt_config.get('version', '')
                }
                version_history.append(version_info)
            except Exception:
                # 跳过加载失败的版本
                pass
        
        return version_history
    
    def validate_prompt(self, module_name: str, prompt_name: str, version: str = 'v1') -> bool:
        """验证提示词模板是否有效
        
        Args:
            module_name: 模块名称
            prompt_name: 提示词名称
            version: 提示词版本
            
        Returns:
            如果提示词有效则返回True，否则返回False
        """
        try:
            prompt = self.get_prompt(module_name, prompt_name, version)
            if not prompt:
                return False
            
            # 检查必要字段
            required_fields = ['name', 'description', 'template']
            for field in required_fields:
                if field not in prompt:
                    return False
            
            return True
        except Exception:
            return False
    
    def search_prompts(self, keyword: str, version: str = 'v1') -> List[Dict[str, Any]]:
        """搜索提示词
        
        Args:
            keyword: 搜索关键词
            version: 提示词版本
            
        Returns:
            匹配的提示词列表
        """
        modules = self.get_modules(version)
        matching_prompts = []
        
        for module_name, module in modules.items():
            prompts = module.get('prompts', {})
            for prompt_name, prompt in prompts.items():
                # 搜索关键词是否在提示词名称、描述或模板中
                if keyword.lower() in prompt.get('name', '').lower() or \
                   keyword.lower() in prompt.get('description', '').lower() or \
                   keyword.lower() in prompt.get('template', '').lower():
                    matching_prompts.append({
                        'module': module_name,
                        'name': prompt_name,
                        'prompt': prompt
                    })
        
        return matching_prompts
    
    def get_prompt_statistics(self, version: str = 'v1') -> Dict[str, Any]:
        """获取提示词统计信息
        
        Args:
            version: 提示词版本
            
        Returns:
            统计信息字典
        """
        modules = self.get_modules(version)
        total_modules = len(modules)
        total_prompts = 0
        prompts_by_module = {}
        
        for module_name, module in modules.items():
            prompts = module.get('prompts', {})
            module_prompt_count = len(prompts)
            total_prompts += module_prompt_count
            prompts_by_module[module_name] = module_prompt_count
        
        return {
            'total_modules': total_modules,
            'total_prompts': total_prompts,
            'prompts_by_module': prompts_by_module
        }
