"""结构化日志配置.

使用 structlog 提供 JSON 格式的结构化日志，便于后续分析和监控。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import structlog


def configure_logging(
    log_level: str = "INFO",
    log_file: Path | None = None,
    json_format: bool = False,
) -> None:
    """配置结构化日志.

    Args:
        log_level: 日志级别，可选 DEBUG/INFO/WARNING/ERROR
        log_file: 日志文件路径，为 None 时只输出到控制台
        json_format: 是否使用 JSON 格式输出（生产环境推荐）
    """
    # 配置标准库 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # 配置 structlog
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if json_format:
        processors.extend([
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ])
    else:
        processors.extend([
            structlog.dev.ConsoleRenderer(
                colors=True,
                sort_keys=False,
            ),
        ])

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 如果指定了日志文件，添加文件处理器
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(getattr(logging, log_level.upper()))
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """获取结构化日志记录器.

    Args:
        name: 日志记录器名称，通常使用 __name__

    Returns:
        配置好的结构化日志记录器
    """
    return structlog.get_logger(name)
