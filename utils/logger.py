"""
日志工具 - 项目日志配置和管理
"""

import logging
import os
from pathlib import Path
from config.settings import settings


def setup_logger(
    name: str = "ff_kb_robot",
    log_file: str = None,
    log_level: str = None,
) -> logging.Logger:
    """
    设置日志记录器

    Args:
        name: 日志记录器名称
        log_file: 日志文件路径
        log_level: 日志级别

    Returns:
        配置好的日志记录器
    """
    log_file = log_file or settings.LOG_FILE
    log_level = log_level or settings.LOG_LEVEL

    # 创建日志目录
    log_dir = os.path.dirname(log_file)
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)

    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level))

    # 移除已有的处理器
    logger.handlers.clear()

    # 创建格式化器
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 文件处理器
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(getattr(logging, log_level))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.info(f"日志记录器已设置: {name}")

    return logger


def get_logger(name: str = "ff_kb_robot") -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器
    """
    return logging.getLogger(name)


# 初始化根日志记录器 - 移动到main.py中
