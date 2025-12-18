"""
文件工具函数 - 处理文件相关的通用操作

功能：
1. 文件哈希生成（用于去重）
2. 文件编码（base64 等）
3. 文件类型检测
4. 文件大小验证
5. 文件内容提取和清洗

作者: FF-KB-Robot Team
"""

import hashlib
import base64
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from datetime import datetime
import mimetypes

logger = logging.getLogger(__name__)


def calculate_file_hash(
    file_path: str,
    algorithm: str = "sha256"
) -> str:
    """
    计算文件的哈希值（用于去重）

    Args:
        file_path: 文件路径
        algorithm: 哈希算法（默认 sha256）

    Returns:
        str: 文件哈希值（十六进制字符串）

    Raises:
        FileNotFoundError: 文件不存在
        IOError: 文件读取失败
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    try:
        hash_obj = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):  # 按 8KB 块读取
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    except IOError as e:
        logger.error(f"计算文件哈希失败 ({file_path}): {e}")
        raise


def calculate_content_hash(
    content: bytes,
    algorithm: str = "sha256"
) -> str:
    """
    计算内容的哈希值

    Args:
        content: 文件内容（字节）
        algorithm: 哈希算法（默认 sha256）

    Returns:
        str: 内容哈希值（十六进制字符串）
    """
    try:
        hash_obj = hashlib.new(algorithm)
        hash_obj.update(content)
        return hash_obj.hexdigest()
    except Exception as e:
        logger.error(f"计算内容哈希失败: {e}")
        raise


def encode_to_base64(file_path: str) -> str:
    """
    将文件编码为 base64 字符串

    Args:
        file_path: 文件路径

    Returns:
        str: base64 编码的字符串

    Raises:
        FileNotFoundError: 文件不存在
        IOError: 文件读取失败
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    try:
        with open(file_path, "rb") as f:
            content = f.read()
        return base64.b64encode(content).decode("utf-8")
    except IOError as e:
        logger.error(f"编码文件为 base64 失败 ({file_path}): {e}")
        raise


def decode_from_base64(encoded_str: str) -> bytes:
    """
    从 base64 字符串解码

    Args:
        encoded_str: base64 编码的字符串

    Returns:
        bytes: 解码后的二进制内容

    Raises:
        ValueError: 解码失败
    """
    try:
        return base64.b64decode(encoded_str)
    except Exception as e:
        logger.error(f"从 base64 解码失败: {e}")
        raise ValueError(f"base64 解码失败: {e}")


def get_file_type(file_path: str) -> str:
    """
    获取文件类型

    Args:
        file_path: 文件路径

    Returns:
        str: 文件类型（mime type 的简化版本）

    例如：
        - PDF 文件返回 "pdf"
        - DOCX 文件返回 "word"
        - 图片文件返回 "image"
        - 文本文件返回 "text"
        - 其他返回 "other"
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    # 按后缀判断
    if suffix in ['.pdf']:
        return "pdf"
    elif suffix in ['.doc', '.docx']:
        return "word"
    elif suffix in ['.xls', '.xlsx']:
        return "excel"
    elif suffix in ['.txt', '.md', '.markdown']:
        return "text"
    elif suffix in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']:
        return "image"
    elif suffix in ['.csv']:
        return "csv"
    else:
        # 尝试使用 mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            if mime_type.startswith("image"):
                return "image"
            elif mime_type.startswith("text"):
                return "text"
            elif "pdf" in mime_type:
                return "pdf"
        return "other"


def validate_file_size(
    file_path: str,
    max_size_mb: int = 100
) -> Tuple[bool, Optional[str]]:
    """
    验证文件大小是否在限制内

    Args:
        file_path: 文件路径
        max_size_mb: 最大文件大小（MB，默认 100MB）

    Returns:
        Tuple[bool, Optional[str]]: (是否有效, 错误消息)

    例如：
        - 文件超过限制：(False, "文件太大: 150MB > 100MB")
        - 文件有效：(True, None)
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return False, f"文件不存在: {file_path}"

    try:
        file_size_bytes = file_path.stat().st_size
        file_size_mb = file_size_bytes / (1024 * 1024)

        if file_size_mb > max_size_mb:
            return False, f"文件太大: {file_size_mb:.1f}MB > {max_size_mb}MB"

        return True, None
    except Exception as e:
        logger.error(f"验证文件大小失败 ({file_path}): {e}")
        return False, f"验证文件大小失败: {e}"


def get_file_info(file_path: str) -> Dict[str, Any]:
    """
    获取文件的详细信息

    Args:
        file_path: 文件路径

    Returns:
        Dict[str, Any]: 文件信息字典，包含：
            - filename: 文件名
            - file_type: 文件类型
            - file_size: 文件大小（字节）
            - file_size_mb: 文件大小（MB）
            - created_time: 创建时间
            - modified_time: 修改时间
            - extension: 文件扩展名

    Raises:
        FileNotFoundError: 文件不存在
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    try:
        stat = file_path.stat()
        return {
            "filename": file_path.name,
            "file_type": get_file_type(str(file_path)),
            "file_size": stat.st_size,
            "file_size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": file_path.suffix.lower(),
        }
    except Exception as e:
        logger.error(f"获取文件信息失败 ({file_path}): {e}")
        raise


def truncate_text(
    text: str,
    max_length: int = 5000,
    suffix: str = "..."
) -> str:
    """
    截断文本到指定长度

    Args:
        text: 原始文本
        max_length: 最大长度（字符数）
        suffix: 超长时添加的后缀

    Returns:
        str: 截断后的文本
    """
    if len(text) <= max_length:
        return text

    # 保留的长度（为后缀留出空间）
    keep_length = max_length - len(suffix)
    return text[:keep_length] + suffix


def sanitize_filename(filename: str) -> str:
    """
    清洗文件名，移除不安全的字符

    Args:
        filename: 原始文件名

    Returns:
        str: 清洗后的文件名
    """
    import re
    # 移除或替换不安全的字符
    # 只保留字母、数字、下划线、连字符和点
    sanitized = re.sub(r'[^\w\-\.]', '_', filename)
    # 移除连续的下划线
    sanitized = re.sub(r'_+', '_', sanitized)
    # 移除开头和结尾的下划线和点
    sanitized = sanitized.strip('_.')
    return sanitized if sanitized else "file"


def generate_unique_filename(
    original_filename: str,
    timestamp: Optional[datetime] = None
) -> str:
    """
    生成唯一的文件名（添加时间戳）

    Args:
        original_filename: 原始文件名
        timestamp: 时间戳（默认使用当前时间）

    Returns:
        str: 唯一的文件名

    例如：
        - 输入: "report.pdf"
        - 输出: "report_20251211_154530.pdf"
    """
    if timestamp is None:
        timestamp = datetime.now()

    file_path = Path(original_filename)
    stem = file_path.stem  # 文件名（不含扩展名）
    suffix = file_path.suffix  # 扩展名

    # 生成时间戳字符串
    time_str = timestamp.strftime("%Y%m%d_%H%M%S")

    # 组合新文件名
    unique_filename = f"{stem}_{time_str}{suffix}"

    return sanitize_filename(unique_filename)


# 支持的文件格式配置
SUPPORTED_FILE_FORMATS = {
    "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
    "document": [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".md", ".csv"],
    "all": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".md", ".csv"]
}


def is_supported_format(
    filename: str,
    supported_formats: str = "all"
) -> bool:
    """
    检查文件格式是否受支持

    Args:
        filename: 文件名
        supported_formats: 支持的格式类别（"all", "image", "document"）

    Returns:
        bool: 是否受支持
    """
    file_path = Path(filename)
    suffix = file_path.suffix.lower()

    formats = SUPPORTED_FILE_FORMATS.get(supported_formats, SUPPORTED_FILE_FORMATS["all"])
    return suffix in formats


def get_supported_extensions(category: str = "all") -> list:
    """
    获取支持的文件扩展名列表

    Args:
        category: 类别（"all", "image", "document"）

    Returns:
        list: 扩展名列表
    """
    return SUPPORTED_FILE_FORMATS.get(category, SUPPORTED_FILE_FORMATS["all"])
