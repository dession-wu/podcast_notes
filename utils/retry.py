"""重试装饰器 — 基于 tenacity 的弹性模式.

为外部服务调用提供自动重试、指数退避和抖动功能。
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Callable, TypeVar

from tenacity import (
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential_jitter,
)
from tenacity import retry as tenacity_retry

F = TypeVar("F", bound=Callable[..., Any])

# 默认可重试的异常类型（网络/连接类错误）
DEFAULT_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)

logger = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    max_delay: int = 60,
    retryable_exceptions: tuple[type[BaseException], ...] | None = None,
    log_retries: bool = True,
) -> Callable[[F], F]:
    """为函数添加重试能力的装饰器.

    Args:
        max_attempts: 最大重试次数
        max_delay: 最大总等待时间（秒）
        retryable_exceptions: 可重试的异常类型元组，默认网络类错误
        log_retries: 是否在重试前记录日志

    Returns:
        装饰器函数

    Example:
        @with_retry(max_attempts=5)
        def fetch_data(url: str) -> dict:
            return requests.get(url).json()
    """
    exceptions = retryable_exceptions or DEFAULT_RETRYABLE_EXCEPTIONS

    retry_kwargs: dict[str, Any] = {
        "retry": retry_if_exception_type(exceptions),
        "stop": stop_after_attempt(max_attempts) | stop_after_delay(max_delay),
        "wait": wait_exponential_jitter(initial=1, max=30),
        "reraise": True,
    }

    if log_retries:
        retry_kwargs["before_sleep"] = before_sleep_log(logger, logging.WARNING)

    return tenacity_retry(**retry_kwargs)


def async_with_retry(
    max_attempts: int = 3,
    max_delay: int = 60,
    retryable_exceptions: tuple[type[BaseException], ...] | None = None,
    log_retries: bool = True,
) -> Callable[[F], F]:
    """为异步函数添加重试能力的装饰器.

    参数与 with_retry 相同，但支持 async 函数。
    """
    exceptions = retryable_exceptions or DEFAULT_RETRYABLE_EXCEPTIONS

    retry_kwargs: dict[str, Any] = {
        "retry": retry_if_exception_type(exceptions),
        "stop": stop_after_attempt(max_attempts) | stop_after_delay(max_delay),
        "wait": wait_exponential_jitter(initial=1, max=30),
        "reraise": True,
    }

    if log_retries:
        retry_kwargs["before_sleep"] = before_sleep_log(logger, logging.WARNING)

    return tenacity_retry(**retry_kwargs)
