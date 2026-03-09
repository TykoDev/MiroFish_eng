"""
错误处理工具
提供统一的错误响应格式，避免在生产环境中泄露敏感信息
"""

import traceback
from typing import Dict, Any, Optional
from flask import jsonify

from ..config import Config


def error_response(
    message: str,
    status_code: int = 500,
    include_traceback: Optional[bool] = None,
    original_error: Optional[Exception] = None
) -> tuple:
    """
    创建统一的错误响应

    只在DEBUG模式下返回详细的traceback信息，避免在生产环境中泄露敏感信息

    Args:
        message: 错误消息
        status_code: HTTP状态码
        include_traceback: 是否包含traceback（默认根据DEBUG模式自动判断）
        original_error: 原始异常对象（用于获取traceback）

    Returns:
        (jsonify_response, status_code) 元组
    """
    error_data = {
        "success": False,
        "error": message
    }

    # 只有在DEBUG模式下才返回traceback
    if include_traceback is None:
        include_traceback = Config.DEBUG

    if include_traceback and original_error:
        error_data["traceback"] = traceback.format_exc()

    return jsonify(error_data), status_code


def log_error(logger, error: Exception, context: str = ""):
    """
    记录错误日志

    Args:
        logger: 日志记录器
        error: 异常对象
        context: 上下文信息
    """
    if context:
        logger.error(f"{context}: {str(error)}")
    else:
        logger.error(str(error))

    # 总是在日志中记录traceback
    logger.debug(traceback.format_exc())
