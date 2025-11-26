"""
统一装饰器模块 - 提供错误处理、缓存、性能追踪等通用装饰器

功能：
1. @handle_api_error - API错误处理装饰器
2. @cache_result - 缓存结果装饰器（支持TTL和缓存级别）
3. @track_performance - 性能追踪装饰器
4. @auto_log - 自动日志装饰器
5. @retry - 自动重试装饰器
"""

import logging
import functools
import time
import asyncio
from typing import Any, Callable, Optional, TypeVar, Union
from enum import Enum
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger(__name__)

T = TypeVar('T')
F = TypeVar('F', bound=Callable[..., Any])


class CacheLevel(str, Enum):
    """缓存级别"""
    EMBEDDING = "embedding"
    QUERY_RESULT = "query_result"
    RETRIEVAL = "retrieval"
    DOCUMENT = "document"


# ==================== 错误处理装饰器 ====================

def handle_api_error(
    default_return: Any = None,
    raise_exception: bool = True,
    log_level: str = "error"
) -> Callable[[F], F]:
    """
    API 错误处理装饰器

    自动捕获异常，记录日志，可选返回默认值或抛出异常

    Args:
        default_return: 出错时的默认返回值
        raise_exception: 是否抛出异常
        log_level: 日志级别（'error', 'warning', 'info'）

    Usage:
        @handle_api_error(default_return=[], raise_exception=True)
        def embed_text(text: str) -> List[float]:
            return api.embeddings.create(...)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log_msg = f"{func.__name__} 执行失败: {str(e)}"
                getattr(logger, log_level)(log_msg, exc_info=True)

                if raise_exception:
                    raise
                return default_return

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                log_msg = f"{func.__name__} 执行失败: {str(e)}"
                getattr(logger, log_level)(log_msg, exc_info=True)

                if raise_exception:
                    raise
                return default_return

        # 判断是否为异步函数
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore

    return decorator


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


# ==================== 性能追踪装饰器 ====================

def track_performance(
    log_level: str = "info",
    threshold_ms: Optional[float] = None
) -> Callable[[F], F]:
    """
    性能追踪装饰器（支持同步和异步函数）

    记录函数执行时间，如果超过阈值则警告

    Args:
        log_level: 日志级别
        threshold_ms: 时间阈值（毫秒），超过则以warning记录

    Usage:
        @track_performance(log_level="info", threshold_ms=1000)
        def heavy_operation():
            time.sleep(2)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.time() - start_time) * 1000
                msg = f"{func.__name__} 执行耗时: {elapsed_ms:.2f}ms"

                if threshold_ms and elapsed_ms > threshold_ms:
                    logger.warning(f"⚠️ {msg} (超过阈值 {threshold_ms}ms)")
                else:
                    getattr(logger, log_level)(msg)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                elapsed_ms = (time.time() - start_time) * 1000
                msg = f"{func.__name__} 执行耗时: {elapsed_ms:.2f}ms"

                if threshold_ms and elapsed_ms > threshold_ms:
                    logger.warning(f"⚠️ {msg} (超过阈值 {threshold_ms}ms)")
                else:
                    getattr(logger, log_level)(msg)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore

    return decorator


# ==================== 自动日志装饰器 ====================

def auto_log(
    log_args: bool = True,
    log_result: bool = True,
    log_level: str = "debug"
) -> Callable[[F], F]:
    """
    自动日志装饰器

    自动记录函数调用和返回值

    Args:
        log_args: 是否记录参数
        log_result: 是否记录返回值
        log_level: 日志级别

    Usage:
        @auto_log(log_args=True, log_result=True)
        def process_data(data: dict) -> str:
            return json.dumps(data)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 记录调用
            if log_args:
                logger.log(
                    getattr(logging, log_level.upper()),
                    f"调用 {func.__name__} | args: {args} | kwargs: {kwargs}"
                )

            # 执行函数
            result = func(*args, **kwargs)

            # 记录返回值
            if log_result:
                logger.log(
                    getattr(logging, log_level.upper()),
                    f"{func.__name__} 返回: {result}"
                )

            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if log_args:
                logger.log(
                    getattr(logging, log_level.upper()),
                    f"调用 {func.__name__} | args: {args} | kwargs: {kwargs}"
                )

            result = await func(*args, **kwargs)

            if log_result:
                logger.log(
                    getattr(logging, log_level.upper()),
                    f"{func.__name__} 返回: {result}"
                )

            return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore

    return decorator


# ==================== 重试装饰器 ====================

def retry(
    max_attempts: int = 3,
    delay_seconds: float = 1,
    backoff_factor: float = 2,
    exceptions: tuple = (Exception,)
) -> Callable[[F], F]:
    """
    自动重试装饰器（支持指数退避）

    Args:
        max_attempts: 最大尝试次数
        delay_seconds: 初始延迟（秒）
        backoff_factor: 退避因子（延迟 = delay * backoff_factor^attempt）
        exceptions: 触发重试的异常元组

    Usage:
        @retry(max_attempts=3, delay_seconds=1, exceptions=(ConnectionError,))
        def unreliable_api_call():
            return requests.get(url)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay_seconds

            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(
                            f"{func.__name__} 重试 {max_attempts} 次后仍失败: {str(e)}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} 失败，{current_delay:.1f}秒后重试 "
                        f"({attempt}/{max_attempts-1}): {str(e)}"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff_factor

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay_seconds

            while attempt < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(
                            f"{func.__name__} 重试 {max_attempts} 次后仍失败: {str(e)}"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} 失败，{current_delay:.1f}秒后重试 "
                        f"({attempt}/{max_attempts-1}): {str(e)}"
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff_factor

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore

    return decorator


# ==================== 单例装饰器 ====================

def singleton(cls):
    """
    单例装饰器

    Usage:
        @singleton
        class Config:
            pass
    """
    instances = {}

    @functools.wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance
