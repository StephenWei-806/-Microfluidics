"""流式响应完整记录日志工具

提供 StreamResponseAccumulator：在流式传输过程中非阻塞地累积每个 chunk，
待流结束后将完整响应（合并后的 content/reasoning_content/tool_calls 等）
写入专用的流式日志文件（logs/stream_response.log），便于后续调试与分析。

设计要点：
- 使用独立的 logger (stream_response)，与主应用日志隔离，不污染 app.log
- 基于 QueueHandler + QueueListener 实现真正的非阻塞日志写入，
  日志 I/O 在独立线程中进行，不会阻塞 SSE 流的实时推送
- 累积器自身只做内存拼接，开销极小
"""
import json
import logging
import os
import queue
import threading
import time
import uuid
from logging.handlers import QueueHandler, QueueListener
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# 专用日志器初始化（模块级单例，进程启动时初始化一次）
# ---------------------------------------------------------------------------
_STREAM_LOGGER_NAME = 'stream_response'
_STREAM_LOG_FILENAME = 'stream_response.log'

_logger_lock = threading.Lock()
_logger_initialized = False
_queue_listener: Optional[QueueListener] = None


def _init_stream_logger() -> logging.Logger:
    """初始化流式响应专用 logger（带非阻塞队列处理）。

    只初始化一次，多次调用返回同一 logger 实例。
    """
    global _logger_initialized, _queue_listener

    logger = logging.getLogger(_STREAM_LOGGER_NAME)

    with _logger_lock:
        if _logger_initialized:
            return logger

        logger.setLevel(logging.INFO)
        # 禁止向 root 传播，避免重复输出到 app.log
        logger.propagate = False

        # 日志目录（与主应用一致）
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_path = os.path.join(log_dir, _STREAM_LOG_FILENAME)

        # 真正执行 I/O 的 handler
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )

        # 队列 + 监听线程，使 logger.info() 调用变为非阻塞
        log_queue: queue.Queue = queue.Queue(-1)
        queue_handler = QueueHandler(log_queue)

        logger.addHandler(queue_handler)

        listener = QueueListener(log_queue, file_handler, respect_handler_level=True)
        listener.daemon = True  # 进程退出时自动关闭
        listener.start()

        _queue_listener = listener
        _logger_initialized = True

    return logger


# 模块加载时立即初始化
stream_logger = _init_stream_logger()


# ---------------------------------------------------------------------------
# 流式响应累积器
# ---------------------------------------------------------------------------
class StreamResponseAccumulator:
    """累积流式 API 返回的所有 chunk，在流结束后输出完整合并响应到日志。

    支持的 chunk 类型：
    1. OpenAI / DeepSeek 标准 chunk：{choices:[{delta:{content, reasoning_content, tool_calls}}]}
    2. 千问格式 chunk（经 api_client 适配后，结构与 1 兼容）
    3. Agent Loop 自定义事件：
       - {"type": "tool_status", "message": "..."}
       - {"type": "tool_result", "tool_name": "...", "result": "..."}
    4. 错误事件：{"error": "..."}

    线程安全：单次 SSE 请求在一个生成器中顺序调用，无需加锁。
    """

    def __init__(
        self,
        api_name: str,
        model: str,
        prompt: Optional[str] = None,
        tools_enabled: bool = False,
        request_id: Optional[str] = None,
    ):
        self.api_name = api_name
        self.model = model
        self.prompt_preview = (prompt or '')[:200]
        self.tools_enabled = tools_enabled
        self.request_id = request_id or str(uuid.uuid4())

        self.start_time = time.time()
        self.start_timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.start_time))

        # 文本累积
        self._content_parts: List[str] = []
        self._reasoning_parts: List[str] = []

        # tool_calls 累积：key 为 index
        self._tool_calls: Dict[int, Dict[str, Any]] = {}

        # Agent Loop 事件序列
        self._events: List[Dict[str, Any]] = []

        # 统计
        self.chunk_count = 0
        self.error: Optional[str] = None
        self.finish_reason: Optional[str] = None

    # ------------------------------------------------------------------
    # 累积接口
    # ------------------------------------------------------------------
    def accumulate(self, chunk: Any) -> None:
        """累积单个 chunk（非阻塞，仅做内存拼接）。"""
        self.chunk_count += 1

        if not isinstance(chunk, dict):
            return

        # 错误事件
        if 'error' in chunk and 'choices' not in chunk:
            self.error = str(chunk['error'])
            return

        # Agent Loop 自定义事件
        chunk_type = chunk.get('type')
        if chunk_type in ('tool_status', 'tool_result'):
            self._events.append(chunk)
            return

        # 标准 chat completion chunk
        choices = chunk.get('choices')
        if not choices:
            return

        choice0 = choices[0] if isinstance(choices, list) and choices else {}
        if not isinstance(choice0, dict):
            return

        # finish_reason 记录
        fr = choice0.get('finish_reason')
        if fr:
            self.finish_reason = fr

        delta = choice0.get('delta') or {}
        if not isinstance(delta, dict):
            return

        content = delta.get('content')
        if content:
            self._content_parts.append(str(content))

        reasoning = delta.get('reasoning_content')
        if reasoning:
            self._reasoning_parts.append(str(reasoning))

        tool_calls_delta = delta.get('tool_calls')
        if tool_calls_delta:
            self._accumulate_tool_calls(tool_calls_delta)

    def _accumulate_tool_calls(self, delta_tool_calls: List[Dict[str, Any]]) -> None:
        for tc in delta_tool_calls:
            if not isinstance(tc, dict):
                continue
            idx = tc.get('index', 0)
            entry = self._tool_calls.setdefault(
                idx,
                {'id': '', 'type': 'function', 'function': {'name': '', 'arguments': ''}},
            )
            if tc.get('id'):
                entry['id'] = tc['id']
            fn = tc.get('function') or {}
            if fn.get('name'):
                entry['function']['name'] = fn['name']
            if fn.get('arguments'):
                entry['function']['arguments'] += fn['arguments']

    # ------------------------------------------------------------------
    # 输出日志
    # ------------------------------------------------------------------
    def finalize(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """流结束后调用，组装完整响应并写入日志。

        Args:
            extra: 额外元数据（可选）

        Returns:
            Dict[str, Any]: 完整响应摘要字典
        """
        end_time = time.time()
        duration_ms = int((end_time - self.start_time) * 1000)

        full_content = ''.join(self._content_parts)
        full_reasoning = ''.join(self._reasoning_parts)
        tool_calls_list = [self._tool_calls[k] for k in sorted(self._tool_calls.keys())]

        summary: Dict[str, Any] = {
            'request_id': self.request_id,
            'api_name': self.api_name,
            'model': self.model,
            'tools_enabled': self.tools_enabled,
            'start_time': self.start_timestamp,
            'duration_ms': duration_ms,
            'chunk_count': self.chunk_count,
            'finish_reason': self.finish_reason,
            'prompt_preview': self.prompt_preview,
            'content_length': len(full_content),
            'reasoning_length': len(full_reasoning),
            'tool_calls_count': len(tool_calls_list),
            'events_count': len(self._events),
            'content': full_content,
            'reasoning_content': full_reasoning,
            'tool_calls': tool_calls_list,
            'events': self._events,
            'error': self.error,
        }
        if extra:
            summary['extra'] = extra

        # 分隔符 + 人类可读 JSON，便于直接查看；单行 JSON 结构完整，便于日志解析
        try:
            payload = json.dumps(summary, ensure_ascii=False)
        except Exception as e:
            payload = json.dumps(
                {
                    'request_id': self.request_id,
                    'api_name': self.api_name,
                    'model': self.model,
                    'serialize_error': str(e),
                    'chunk_count': self.chunk_count,
                },
                ensure_ascii=False,
            )

        # 非阻塞：QueueHandler 将消息放入队列后立即返回，真正的 I/O 由后台线程处理
        stream_logger.info(
            '[STREAM_COMPLETE] request_id=%s api=%s model=%s duration_ms=%d chunks=%d payload=%s',
            self.request_id,
            self.api_name,
            self.model,
            duration_ms,
            self.chunk_count,
            payload,
        )

        return summary
