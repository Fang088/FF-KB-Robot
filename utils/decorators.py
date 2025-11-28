"""
统一装饰器模块 - 提供缓存等通用装饰器

功能：
1. @cache_result - 缓存结果装饰器（支持TTL和缓存级别）
2. CacheLevel - 缓存级别枚举（从 cache_manager 导入）
"""

import logging
import functools
import time
import asyncio
from typing import Any, Callable, Optional, TypeVar
import hashlib
import json

# 导入统一定义的 CacheLevel
from .cache_manager import CacheLevel

logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


# ==================== 缓存装饰器 ====================

_cache_storage = {}  # 全局缓存存储


def cache_result(
    level: CacheLevel = CacheLevel.QUERY_RESULT,
    ttl: int = 3600,
    key_prefix: Optional[str] = None,
    use_args: bool = True
) -> Callable[[F], F]:
    """
    缓存结果装饰器（支持同步和异步函数）

    Args:
        level: 缓存级别
        ttl: 缓存有效期（秒）
        key_prefix: 缓存键前缀
        use_args: 是否将函数参数作为缓存键的一部分

    Usage:
        @cache_result(level=CacheLevel.EMBEDDING, ttl=3600)
        def embed_text(text: str) -> List[float]:
            return expensive_operation(text)

        # 异步函数也支持
        @cache_result(level=CacheLevel.QUERY_RESULT, ttl=1800)
        async def search_docs(query: str) -> List[str]:
            return await async_search(query)
    """
    def decorator(func: F) -> F:
        prefix = key_prefix or f"{func.__module__}.{func.__name__}"

        def _generate_cache_key(*args, **kwargs) -> str:
            """生成缓存键"""
            if not use_args:
                return prefix

            # 构建缓存键
            key_parts = [prefix]

            # 添加位置参数（跳过self和cls）
            start_idx = 1 if args and isinstance(args[0], type) else 0
            if len(args) > start_idx:
                try:
                    args_hash = hashlib.md5(
                        json.dumps(args[start_idx:], default=str).encode()
                    ).hexdigest()[:8]
                    key_parts.append(args_hash)
                except (TypeError, ValueError):
                    key_parts.append(str(hash(args[start_idx:])))

            # 添加关键字参数
            if kwargs:
                try:
                    kwargs_hash = hashlib.md5(
                        json.dumps(kwargs, default=str, sort_keys=True).encode()
                    ).hexdigest()[:8]
                    key_parts.append(kwargs_hash)
                except (TypeError, ValueError):
                    key_parts.append(str(hash(tuple(sorted(kwargs.items())))))

            return ":".join(key_parts)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = _generate_cache_key(*args, **kwargs)

            # 检查缓存
            if cache_key in _cache_storage:
                cached_value, expire_time = _cache_storage[cache_key]
                if time.time() < expire_time:
                    logger.debug(f"缓存命中: {cache_key}")
                    return cached_value
                else:
                    # 缓存过期，删除
                    del _cache_storage[cache_key]

            # 执行函数
            result = func(*args, **kwargs)

            # 存储缓存
            expire_time = time.time() + ttl
            _cache_storage[cache_key] = (result, expire_time)
            logger.debug(f"缓存保存: {cache_key} (TTL: {ttl}s)")

            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache_key = _generate_cache_key(*args, **kwargs)

            # 检查缓存
            if cache_key in _cache_storage:
                cached_value, expire_time = _cache_storage[cache_key]
                if time.time() < expire_time:
                    logger.debug(f"缓存命中: {cache_key}")
                    return cached_value
                else:
                    del _cache_storage[cache_key]

            # 执行异步函数
            result = await func(*args, **kwargs)

            # 存储缓存
            expire_time = time.time() + ttl
            _cache_storage[cache_key] = (result, expire_time)
            logger.debug(f"缓存保存: {cache_key} (TTL: {ttl}s)")

            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore

    return decorator
