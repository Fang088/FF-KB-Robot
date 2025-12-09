"""
数据格式化工具

功能：统一的数据格式化函数

作者: FF-KB-Robot Team
"""

from datetime import datetime
from typing import Union


def format_datetime(
    dt: Union[str, datetime],
    format_str: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    格式化日期时间

    Args:
        dt: 日期时间对象或 ISO 格式字符串
        format_str: 格式化字符串

    Returns:
        str: 格式化后的日期时间字符串
    """
    try:
        if isinstance(dt, str):
            # 尝试解析 ISO 格式
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))

        return dt.strftime(format_str)
    except Exception:
        return str(dt)


def format_filesize(size_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        str: 格式化后的文件大小字符串
    """
    try:
        size_bytes = int(size_bytes)

        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    except Exception:
        return "未知"


def format_duration(milliseconds: int) -> str:
    """
    格式化时间间隔

    Args:
        milliseconds: 毫秒数

    Returns:
        str: 格式化后的时间间隔字符串
    """
    try:
        milliseconds = int(milliseconds)

        if milliseconds < 1000:
            return f"{milliseconds}ms"
        elif milliseconds < 60000:
            return f"{milliseconds / 1000:.2f}s"
        else:
            minutes = milliseconds // 60000
            seconds = (milliseconds % 60000) / 1000
            return f"{minutes}m {seconds:.1f}s"
    except Exception:
        return "未知"


def format_confidence(confidence: float) -> str:
    """
    格式化置信度

    Args:
        confidence: 置信度值 (0.0-1.0)

    Returns:
        str: 格式化后的置信度字符串（包含星级）
    """
    try:
        confidence = float(confidence)
        percentage = f"{confidence:.1%}"

        if confidence >= 0.8:
            stars = "⭐⭐⭐⭐⭐"
            level = "非常高"
        elif confidence >= 0.6:
            stars = "⭐⭐⭐⭐"
            level = "高"
        elif confidence >= 0.4:
            stars = "⭐⭐⭐"
            level = "中等"
        elif confidence >= 0.2:
            stars = "⭐⭐"
            level = "低"
        else:
            stars = "⭐"
            level = "非常低"

        return f"{percentage} ({level} {stars})"
    except Exception:
        return "未知"


def format_number(number: Union[int, float], decimals: int = 2) -> str:
    """
    格式化数字（添加千位分隔符）

    Args:
        number: 数字
        decimals: 小数位数

    Returns:
        str: 格式化后的数字字符串
    """
    try:
        if isinstance(number, int):
            return f"{number:,}"
        else:
            return f"{number:,.{decimals}f}"
    except Exception:
        return str(number)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本

    Args:
        text: 文本
        max_length: 最大长度
        suffix: 后缀

    Returns:
        str: 截断后的文本
    """
    try:
        if len(text) <= max_length:
            return text
        else:
            return text[:max_length - len(suffix)] + suffix
    except Exception:
        return str(text)
