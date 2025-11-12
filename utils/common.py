"""
通用辅助函数 - ID 生成、文件操作等常用工具
"""

import uuid
import os
import json
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def generate_id(prefix: str = "") -> str:
    """
    生成唯一 ID

    Args:
        prefix: ID 前缀

    Returns:
        生成的 ID
    """
    unique_id = str(uuid.uuid4()).replace("-", "")
    return f"{prefix}_{unique_id}" if prefix else unique_id


def ensure_dir(dir_path: str) -> Path:
    """
    确保目录存在

    Args:
        dir_path: 目录路径

    Returns:
        目录 Path 对象
    """
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"目录已确保存在: {dir_path}")
    return path


def save_json(data: Dict[str, Any], file_path: str):
    """
    保存 JSON 文件

    Args:
        data: 数据字典
        file_path: 文件路径
    """
    try:
        # 确保目录存在
        ensure_dir(os.path.dirname(file_path))

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON 已保存: {file_path}")
    except Exception as e:
        logger.error(f"保存 JSON 失败: {e}")
        raise


def load_json(file_path: str) -> Dict[str, Any]:
    """
    加载 JSON 文件

    Args:
        file_path: 文件路径

    Returns:
        加载的数据字典
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"JSON 已加载: {file_path}")
        return data
    except Exception as e:
        logger.error(f"加载 JSON 失败: {e}")
        raise


def delete_file(file_path: str) -> bool:
    """
    删除文件

    Args:
        file_path: 文件路径

    Returns:
        是否删除成功
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"文件已删除: {file_path}")
            return True
        else:
            logger.warning(f"文件不存在: {file_path}")
            return False
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        return False


def file_exists(file_path: str) -> bool:
    """
    检查文件是否存在

    Args:
        file_path: 文件路径

    Returns:
        文件是否存在
    """
    return os.path.exists(file_path)


def get_file_size(file_path: str) -> int:
    """
    获取文件大小（字节）

    Args:
        file_path: 文件路径

    Returns:
        文件大小
    """
    try:
        return os.path.getsize(file_path)
    except Exception as e:
        logger.error(f"获取文件大小失败: {e}")
        return 0
