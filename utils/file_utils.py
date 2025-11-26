"""
文件工具模块 - 从DocumentManager迁移的文件操作函数

功能：
1. 临时文件管理（保存、清理）
2. 文件信息获取
3. 文件验证
4. 目录管理

这是从 retrieval/document_manager.py 中提取的文件操作工具，
避免与文档处理逻辑混在一起。
"""

import os
import shutil
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def save_temp_file(
    file_path: str,
    temp_upload_dir: str = "data/temp_uploads",
    doc_id: str = None,
) -> str:
    """
    保存原始文件到临时目录

    Args:
        file_path: 原始文件路径
        temp_upload_dir: 临时文件目录
        doc_id: 文档ID（可选）

    Returns:
        保存后的文件路径

    Raises:
        FileNotFoundError: 文件不存在
        OSError: 保存失败
    """
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        # 确保临时目录存在
        os.makedirs(temp_upload_dir, exist_ok=True)

        # 生成唯一的文件名
        original_name = os.path.basename(file_path)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{original_name}"

        if doc_id:
            unique_filename = f"{doc_id}_{unique_filename}"

        temp_path = os.path.join(temp_upload_dir, unique_filename)

        # 复制文件
        shutil.copyfile(file_path, temp_path)
        logger.info(f"临时文件已保存: {temp_path}")

        return temp_path
    except Exception as e:
        logger.error(f"保存临时文件失败: {e}")
        raise


def get_file_info(file_path: str) -> Optional[Dict[str, Any]]:
    """
    获取文件信息

    Args:
        file_path: 文件路径

    Returns:
        文件信息字典，包含大小、修改时间等

    Usage:
        info = get_file_info("/path/to/file.pdf")
        print(info['file_size'], info['file_type'])
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return None

        file_stat = os.stat(file_path)
        return {
            "filename": os.path.basename(file_path),
            "file_path": file_path,
            "file_size": file_stat.st_size,
            "file_size_mb": round(file_stat.st_size / (1024 * 1024), 2),
            "file_type": os.path.splitext(file_path)[1],
            "modified_time": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            "exists": True,
        }
    except Exception as e:
        logger.error(f"获取文件信息失败: {e}")
        return None


def validate_file(file_path: str, max_size_mb: Optional[int] = None) -> bool:
    """
    验证文件的有效性

    Args:
        file_path: 文件路径
        max_size_mb: 最大文件大小（MB），None表示不限制

    Returns:
        文件是否有效
    """
    try:
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return False

        if not os.path.isfile(file_path):
            logger.warning(f"不是文件: {file_path}")
            return False

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            logger.warning(f"文件为空: {file_path}")
            return False

        if max_size_mb is not None:
            max_size_bytes = max_size_mb * 1024 * 1024
            if file_size > max_size_bytes:
                logger.warning(
                    f"文件过大: {file_path} ({file_size / (1024*1024):.2f}MB > {max_size_mb}MB)"
                )
                return False

        return True
    except Exception as e:
        logger.error(f"文件验证失败: {e}")
        return False


def cleanup_temp_files(
    temp_upload_dir: str = "data/temp_uploads",
    days: int = 7,
) -> int:
    """
    清理老旧的临时文件

    Args:
        temp_upload_dir: 临时文件目录
        days: 保留天数（超过此时间的文件将被删除）

    Returns:
        删除的文件数量

    Usage:
        deleted_count = cleanup_temp_files(days=7)
        print(f"删除了 {deleted_count} 个文件")
    """
    try:
        if not os.path.exists(temp_upload_dir):
            logger.debug(f"临时目录不存在: {temp_upload_dir}")
            return 0

        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0

        for filename in os.listdir(temp_upload_dir):
            file_path = os.path.join(temp_upload_dir, filename)
            if os.path.isfile(file_path):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_mtime < cutoff_time:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        logger.debug(f"已删除临时文件: {file_path}")
                    except Exception as e:
                        logger.warning(f"删除文件失败: {file_path}, {e}")

        logger.info(f"清理完成: 删除 {deleted_count} 个文件 (保留 {days} 天)")
        return deleted_count
    except Exception as e:
        logger.error(f"清理临时文件失败: {e}")
        return 0


def ensure_dir(dir_path: str) -> Path:
    """
    确保目录存在（创建如不存在）

    Args:
        dir_path: 目录路径

    Returns:
        转换为Path对象的目录路径

    Usage:
        path = ensure_dir("data/temp_uploads")
        print(path.exists())  # True
    """
    try:
        path = Path(dir_path)
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception as e:
        logger.error(f"创建目录失败: {e}")
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
            logger.debug(f"文件已删除: {file_path}")
            return True
        else:
            logger.warning(f"文件不存在: {file_path}")
            return False
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        return False


def get_file_extension(file_path: str) -> str:
    """
    获取文件扩展名

    Args:
        file_path: 文件路径

    Returns:
        扩展名（包含点号），如 .pdf

    Usage:
        ext = get_file_extension("document.pdf")
        print(ext)  # ".pdf"
    """
    return os.path.splitext(file_path)[1].lower()


def is_supported_file_type(
    file_path: str,
    supported_types: set = None,
) -> bool:
    """
    检查文件类型是否支持

    Args:
        file_path: 文件路径
        supported_types: 支持的文件类型集合，如 {'.pdf', '.txt', '.docx'}
                        如果为None，使用默认支持的类型

    Returns:
        是否支持该文件类型

    Usage:
        if is_supported_file_type("doc.pdf"):
            print("支持处理")
    """
    if supported_types is None:
        supported_types = {".pdf", ".txt", ".docx", ".doc", ".xlsx", ".xls"}

    file_ext = get_file_extension(file_path)
    return file_ext in supported_types
