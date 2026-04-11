import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from services.config_service import ConfigService

logger = logging.getLogger(__name__)

class ChipLayoutService:
    """独立的微流控芯片网格配置管理服务"""
    
    ROWS = 17
    COLS = 22
    MAX_VALUE = 128
    
    def __init__(self, config_service: ConfigService, persist_dir: str = './data'):
        """初始化芯片布局服务
        
        Args:
            config_service: 配置服务实例
            persist_dir: 持久化数据存储目录，默认'./data'
        """
        self.config_service = config_service
        self.persist_dir = persist_dir
        self._custom_layout: Optional[Dict[str, Any]] = None
        self._default_layout: Optional[Dict[str, Any]] = None
        
        # 确保持久化目录存在
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # 加载默认配置
        self._default_layout = self._load_default_layout()
        
        # 尝试恢复持久化的自定义配置
        persisted = self._load_persisted_layout()
        if persisted:
            self._custom_layout = persisted
            logger.info("已从持久化存储恢复自定义芯片网格配置")
    
    def get_current_layout(self) -> Dict[str, Any]:
        """获取当前生效的网格配置（优先自定义 > YAML默认）"""
        if self._custom_layout is not None:
            return {
                'grid': self._custom_layout['grid'],
                'description': self._custom_layout.get('description', '用户自定义芯片网格布局')
            }
        if self._default_layout:
            return self._default_layout
        return {'grid': [], 'description': '默认芯片网格布局'}
    
    def set_custom_layout(self, grid: List[List[int]], description: str = '用户自定义芯片网格布局'):
        """设置自定义网格并持久化
        
        Args:
            grid: 网格数据，二维整数列表
            description: 布局描述信息
        """
        self._custom_layout = {
            'grid': grid,
            'description': description,
            'updated_at': datetime.now().isoformat()
        }
        self._persist_layout()
        logger.info("自定义芯片网格布局已更新并持久化")
    
    def reset_to_default(self) -> Dict[str, Any]:
        """重置为 YAML 默认配置"""
        self._custom_layout = None
        # 删除持久化文件
        persist_file = os.path.join(self.persist_dir, 'chip_layout.json')
        if os.path.exists(persist_file):
            os.remove(persist_file)
            logger.info("已删除持久化的自定义芯片网格配置")
        # 重新加载默认配置
        self._default_layout = self._load_default_layout()
        logger.info("芯片网格配置已重置为默认值")
        return self.get_current_layout()
    
    def validate_grid(self, grid) -> Tuple[bool, List[Dict[str, str]]]:
        """统一的网格验证逻辑"""
        errors = []
        
        if grid is None:
            errors.append({'field': 'grid', 'message': 'grid 字段必填'})
            return False, errors
        
        if not isinstance(grid, list):
            errors.append({'field': 'grid', 'message': f'grid 必须是数组，实际类型: {type(grid).__name__}'})
            return False, errors
        
        if len(grid) != self.ROWS:
            errors.append({'field': 'grid', 'message': f'网格行数必须为{self.ROWS}，实际: {len(grid)}'})
            return False, errors
        
        for i, row in enumerate(grid):
            if not isinstance(row, list):
                errors.append({'field': f'grid[{i}]', 'message': f'第{i+1}行应为数组，实际: {type(row).__name__}'})
                continue
            if len(row) != self.COLS:
                errors.append({'field': f'grid[{i}]', 'message': f'第{i+1}行列数应为{self.COLS}，实际: {len(row)}'})
                continue
            for j, val in enumerate(row):
                if not isinstance(val, (int, float)) or isinstance(val, bool):
                    errors.append({'field': f'grid[{i}][{j}]', 'message': f'第{i+1}行第{j+1}列应为整数，实际: {type(val).__name__}'})
                elif int(val) != val:
                    errors.append({'field': f'grid[{i}][{j}]', 'message': f'第{i+1}行第{j+1}列应为整数，实际为浮点数: {val}'})
                elif val < 0 or val > self.MAX_VALUE:
                    errors.append({'field': f'grid[{i}][{j}]', 'message': f'第{i+1}行第{j+1}列值应在0-{self.MAX_VALUE}范围内，实际: {val}'})
        
        return len(errors) == 0, errors
    
    def format_for_prompt(self, layout: Dict[str, Any] = None) -> str:
        """格式化网格数据为 LLM 可读的文本
        
        将网格配置转换为自然语言描述格式，便于在提示词中使用。
        
        Args:
            layout: 布局数据字典，为None时使用当前布局
            
        Returns:
            str: 格式化后的文本描述
        """
        try:
            if layout is None:
                layout = self.get_current_layout()
            
            grid = layout.get('grid', [])
            description = layout.get('description', '')
            
            if not grid:
                return ''
            
            lines = []
            if description:
                lines.append(description)
            lines.append(f'网格布局（{len(grid)}行x{len(grid[0])}列）:')
            for i, row in enumerate(grid):
                lines.append(str(row))
            
            return '\n'.join(lines)
        except Exception as e:
            logger.warning(f"格式化芯片布局失败: {e}，忽略芯片布局信息")
            return ''
    
    def get_statistics(self) -> Dict[str, Any]:
        """返回网格统计信息
        
        计算并返回网格的统计信息，包括总单元格数、可到达单元格数等。
        
        Returns:
            Dict[str, Any]: 统计信息字典，包含:
                - total_cells: 总单元格数
                - reachable_cells: 可到达单元格数（值不为0的单元格）
                - forbidden_cells: 禁止单元格数（值为0的单元格）
                - rows: 行数
                - cols: 列数
                - is_custom: 是否为自定义布局
                - description: 布局描述
        """
        layout = self.get_current_layout()
        grid = layout.get('grid', [])
        
        if not grid:
            return {'total_cells': 0, 'reachable_cells': 0, 'forbidden_cells': 0, 'rows': 0, 'cols': 0, 'is_custom': False, 'description': ''}
        
        total = sum(len(row) for row in grid)
        reachable = sum(1 for row in grid for cell in row if cell != 0)
        
        return {
            'total_cells': total,
            'reachable_cells': reachable,
            'forbidden_cells': total - reachable,
            'rows': len(grid),
            'cols': len(grid[0]) if grid else 0,
            'is_custom': self._custom_layout is not None,
            'description': layout.get('description', '')
        }
    
    def _load_default_layout(self) -> Optional[Dict[str, Any]]:
        """从 prompt_config.yaml 加载默认 chip_layout"""
        try:
            prompt_config = self.config_service.get_prompt_config('v1')
            if prompt_config and 'chip_layout' in prompt_config:
                return prompt_config['chip_layout']
        except Exception as e:
            logger.warning(f"加载默认芯片网格配置失败: {e}")
        return None
    
    def _persist_layout(self):
        """持久化当前自定义配置到 JSON 文件"""
        if self._custom_layout is None:
            return
        try:
            persist_file = os.path.join(self.persist_dir, 'chip_layout.json')
            with open(persist_file, 'w', encoding='utf-8') as f:
                json.dump(self._custom_layout, f, ensure_ascii=False, indent=2)
            logger.info(f"芯片网格配置已持久化到 {persist_file}")
        except Exception as e:
            logger.error(f"持久化芯片网格配置失败: {e}")
    
    def _load_persisted_layout(self) -> Optional[Dict[str, Any]]:
        """启动时从持久化文件恢复"""
        try:
            persist_file = os.path.join(self.persist_dir, 'chip_layout.json')
            if os.path.exists(persist_file):
                with open(persist_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # 验证加载的数据
                if 'grid' in data:
                    is_valid, errors = self.validate_grid(data['grid'])
                    if is_valid:
                        return data
                    else:
                        logger.warning(f"持久化的网格配置验证失败: {errors}")
        except Exception as e:
            logger.warning(f"加载持久化芯片网格配置失败: {e}")
        return None
