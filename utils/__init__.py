"""
Utils 模块 - 通用工具函数和装饰器

核心功能：
1. Decorators - 统一的装饰器系统
2. Cache Manager - 多层缓存管理
3. Performance Tracker - 性能追踪
4. Logger - 日志工具
5. File Utils - 文件操作工具
6. Common - 基础工具函数

快速开始：
    from utils import (
        cache_result, handle_api_error, CacheLevel,
        get_cache_manager, PerformanceTracker,
        setup_logger, save_temp_file
    )

    @handle_api_error()
    @cache_result(level=CacheLevel.EMBEDDING)
    def my_function():
        pass
"""

from .decorators import (
    handle_api_error,
    cache_result,
    CacheLevel,
    track_performance,
    auto_log,
    retry,
    singleton,
)
from .cache_manager import get_cache_manager
from .performance_tracker import PerformanceTracker
from .logger import setup_logger, get_logger
from .file_utils import (
    save_temp_file,
    get_file_info,
    validate_file,
    cleanup_temp_files,
    get_file_extension,
    is_supported_file_type,
)
from .common import (
    generate_id,
    ensure_dir,
    save_json,
    load_json,
    delete_file,
    file_exists,
    get_file_size,
)

__all__ = [
    # Decorators
    "handle_api_error",
    "cache_result",
    "CacheLevel",
    "track_performance",
    "auto_log",
    "retry",
    "singleton",
    # Cache & Performance
    "get_cache_manager",
    "PerformanceTracker",
    # Logger
    "setup_logger",
    "get_logger",
    # File Operations
    "save_temp_file",
    "get_file_info",
    "validate_file",
    "cleanup_temp_files",
    "get_file_extension",
    "is_supported_file_type",
    # Common
    "generate_id",
    "ensure_dir",
    "save_json",
    "load_json",
    "delete_file",
    "file_exists",
    "get_file_size",
]
