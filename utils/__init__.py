"""
Utils 模块 - 通用工具函数和装饰器

核心功能：
1. Decorators - 缓存装饰器
2. Cache Manager - 多层缓存管理
3. Performance Tracker - 性能追踪
4. Logger - 日志工具

快速开始：
    from utils import (
        cache_result, CacheLevel,
        get_cache_manager, PerformanceTracker,
        setup_logger
    )

    @cache_result(level=CacheLevel.EMBEDDING)
    def my_function():
        pass
"""

from .decorators import (
    cache_result,
    CacheLevel,
)
from .cache_manager import get_cache_manager
from .performance_tracker import PerformanceTracker
from .logger import setup_logger, get_logger

__all__ = [
    # Decorators
    "cache_result",
    "CacheLevel",
    # Cache & Performance
    "get_cache_manager",
    "PerformanceTracker",
    # Logger
    "setup_logger",
    "get_logger",
]
