from flask import jsonify

SSE_HEADERS = {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'X-Accel-Buffering': 'no',
    'Connection': 'keep-alive',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
}


def error_handler(func):
    """错误处理装饰器
    
    捕获被装饰函数中的异常，统一返回JSON格式的错误响应。
    
    Args:
        func: 被装饰的函数
        
    Returns:
        wrapper: 包装后的函数，捕获异常并返回统一格式的错误响应
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'code': 500,
                'message': str(e),
                'data': None
            }), 500
    wrapper.__name__ = func.__name__
    return wrapper
