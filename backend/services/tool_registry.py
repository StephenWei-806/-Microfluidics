"""工具注册中心 —— 管理 AI 可调用的工具定义和执行。"""

import json
import logging
from typing import Dict, Any, List, Optional

from services.droplet_tool_service import DropletToolService

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册中心，管理 AI 可调用的工具定义和执行"""

    def __init__(self, droplet_service: DropletToolService):
        self.droplet_service = droplet_service
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._register_tools()

    def _register_tools(self):
        """注册所有可用工具"""
        self._tools['dispense_droplet'] = {
            'definition': {
                "type": "function",
                "function": {
                    "name": "dispense_droplet",
                    "description": "控制微流控芯片执行液滴分配操作。当用户明确要求执行、运行、发送液滴移动操作时调用此工具。仅用于实际执行操作，不用于路径规划讨论。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "electrode_sequences": {
                                "type": "array",
                                "description": "多个液滴的电极序列。每个元素代表一个液滴的时间步序列，每个时间步是一组同时激活的电极编号列表。例如：[[[58,5,6],[5,6,22]], [[58,5,6],[5,6,50]]]",
                                "items": {
                                    "type": "array",
                                    "items": {
                                        "type": "array",
                                        "items": {"type": "integer"}
                                    }
                                }
                            },
                            "interval": {
                                "type": "number",
                                "description": "每个时间步之间的间隔秒数，默认1.0",
                                "default": 1.0
                            }
                        },
                        "required": ["electrode_sequences"]
                    }
                }
            },
            'handler': self._handle_dispense_droplet
        }

    def get_tool_definitions(self) -> List[Dict]:
        """返回所有工具的 OpenAI tools 格式定义列表"""
        return [tool['definition'] for tool in self._tools.values()]

    def execute_tool(self, tool_name: str, arguments: dict) -> str:
        """执行指定工具并返回结果字符串

        Args:
            tool_name: 工具名称
            arguments: 工具参数字典

        Returns:
            str: 工具执行结果的 JSON 字符串
        """
        if tool_name not in self._tools:
            return json.dumps({"error": f"未知工具: {tool_name}"}, ensure_ascii=False)

        handler = self._tools[tool_name]['handler']
        try:
            result = handler(arguments)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error(f"工具 {tool_name} 执行异常: {e}")
            return json.dumps({"error": f"工具执行异常: {str(e)}"}, ensure_ascii=False)

    def _handle_dispense_droplet(self, arguments: dict) -> dict:
        """处理液滴分配工具调用"""
        electrode_sequences = arguments.get('electrode_sequences', [])
        interval = arguments.get('interval', 1.0)

        if not electrode_sequences:
            return {"success": False, "error": "electrode_sequences 不能为空"}

        return self.droplet_service.execute_dispense(
            electrode_sequences=electrode_sequences,
            interval=interval
        )
