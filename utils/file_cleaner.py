"""
文件清理服务 - 管理临时文件的生命周期

功能：
1. TTL 清理：基于过期时间自动删除文件
2. 容量管理：监控目录大小，防止磁盘溢出
3. 单个对话清理：删除对话的所有临时文件
4. 批量清理：定期清理过期文件

作者: FF-KB-Robot Team
"""

import logging
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import shutil

logger = logging.getLogger(__name__)


class FileCleanerError(Exception):
    """文件清理异常"""
    pass


class FileCleaner:
    """
    文件清理管理器 - 负责临时文件的清理和容量管理

    特性：
    1. TTL 清理：自动删除过期文件
    2. 容量监控：防止磁盘空间耗尽
    3. 对话级别清理：对话删除时清理相关文件
    4. 日志记录：完整的清理操作日志
    """

    def __init__(
        self,
        temp_dir: str,
        max_storage_mb: int = 5000,
        cleanup_interval_hours: int = 1
    ):
        """
        初始化文件清理器

        Args:
            temp_dir: 临时文件目录
            max_storage_mb: 最大存储大小（MB）
            cleanup_interval_hours: 清理检查间隔（小时）
        """
        self.temp_dir = Path(temp_dir)
        self.max_storage_bytes = max_storage_mb * 1024 * 1024
        self.cleanup_interval = timedelta(hours=cleanup_interval_hours)
        self.last_cleanup_time = datetime.now()

        # 确保目录存在
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def cleanup_expired_files(
        self,
        ttl_hours: int = 24,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        清理过期的文件（基于 TTL）

        Args:
            ttl_hours: 文件保留时间（小时）
            dry_run: 是否只显示操作但不执行

        Returns:
            Dict[str, Any]: 清理统计
                - files_deleted: 删除的文件数
                - space_freed_bytes: 释放的空间（字节）
                - errors: 删除失败的文件列表
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=ttl_hours)
            files_deleted = 0
            space_freed = 0
            errors = []

            # 遍历所有会话目录
            for session_dir in self.temp_dir.iterdir():
                if not session_dir.is_dir():
                    continue

                # 遍历会话中的文件
                for file_path in session_dir.rglob("*"):
                    if not file_path.is_file():
                        continue

                    # 获取文件修改时间
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                    # 如果文件已过期
                    if mtime < cutoff_time:
                        try:
                            file_size = file_path.stat().st_size
                            if not dry_run:
                                file_path.unlink()
                            files_deleted += 1
                            space_freed += file_size
                            logger.info(f"清理过期文件: {file_path}")
                        except Exception as e:
                            logger.error(f"删除文件失败 ({file_path}): {e}")
                            errors.append(str(file_path))

            logger.info(
                f"TTL 清理完成 - 删除文件: {files_deleted}, "
                f"释放空间: {space_freed / (1024 * 1024):.2f}MB"
            )

            return {
                "files_deleted": files_deleted,
                "space_freed_bytes": space_freed,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"TTL 清理失败: {e}")
            raise FileCleanerError(f"TTL 清理失败: {e}")

    def get_directory_size(self, directory: Optional[Path] = None) -> int:
        """
        计算目录的总大小

        Args:
            directory: 目录路径（默认使用 temp_dir）

        Returns:
            int: 目录大小（字节）
        """
        if directory is None:
            directory = self.temp_dir

        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.error(f"计算目录大小失败 ({directory}): {e}")

        return total_size

    def cleanup_oldest_files(
        self,
        target_size_bytes: int,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        删除最旧的文件以达到目标大小

        Args:
            target_size_bytes: 目标大小（字节）
            dry_run: 是否只显示操作但不执行

        Returns:
            Dict[str, Any]: 清理统计
        """
        try:
            current_size = self.get_directory_size()

            if current_size <= target_size_bytes:
                return {
                    "files_deleted": 0,
                    "space_freed_bytes": 0,
                    "current_size_bytes": current_size,
                    "target_size_bytes": target_size_bytes
                }

            # 收集所有文件及其修改时间
            files_with_mtime = []
            for file_path in self.temp_dir.rglob("*"):
                if file_path.is_file():
                    mtime = file_path.stat().st_mtime
                    size = file_path.stat().st_size
                    files_with_mtime.append((file_path, mtime, size))

            # 按修改时间排序（最旧的在前）
            files_with_mtime.sort(key=lambda x: x[1])

            # 删除文件直到达到目标大小
            files_deleted = 0
            space_freed = 0
            errors = []

            for file_path, _, file_size in files_with_mtime:
                if current_size <= target_size_bytes:
                    break

                try:
                    if not dry_run:
                        file_path.unlink()
                    current_size -= file_size
                    files_deleted += 1
                    space_freed += file_size
                    logger.info(f"清理最旧文件: {file_path}")
                except Exception as e:
                    logger.error(f"删除文件失败 ({file_path}): {e}")
                    errors.append(str(file_path))

            logger.info(
                f"容量清理完成 - 删除文件: {files_deleted}, "
                f"释放空间: {space_freed / (1024 * 1024):.2f}MB"
            )

            return {
                "files_deleted": files_deleted,
                "space_freed_bytes": space_freed,
                "current_size_bytes": current_size,
                "target_size_bytes": target_size_bytes,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"容量清理失败: {e}")
            raise FileCleanerError(f"容量清理失败: {e}")

    def check_and_cleanup_capacity(
        self,
        cleanup_threshold_ratio: float = 0.9,
        target_ratio: float = 0.7,
        dry_run: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        检查容量并在必要时清理

        当使用空间 > 阈值时，清理到目标比例

        Args:
            cleanup_threshold_ratio: 触发清理的阈值比例（0-1）
            target_ratio: 清理到的目标比例（0-1）
            dry_run: 是否只显示操作但不执行

        Returns:
            Optional[Dict[str, Any]]: 清理统计，如果没有执行清理则为 None
        """
        try:
            current_size = self.get_directory_size()
            threshold_size = self.max_storage_bytes * cleanup_threshold_ratio
            target_size = self.max_storage_bytes * target_ratio

            current_usage_pct = (current_size / self.max_storage_bytes) * 100

            if current_size > threshold_size:
                logger.warning(
                    f"临时文件目录使用量过高: {current_usage_pct:.1f}% "
                    f"({current_size / (1024 * 1024):.2f}MB / "
                    f"{self.max_storage_bytes / (1024 * 1024):.2f}MB)"
                )
                return self.cleanup_oldest_files(target_size, dry_run)
            else:
                logger.debug(
                    f"临时文件目录使用量正常: {current_usage_pct:.1f}%"
                )
                return None

        except Exception as e:
            logger.error(f"容量检查失败: {e}")
            raise FileCleanerError(f"容量检查失败: {e}")

    def cleanup_conversation_files(
        self,
        conversation_id: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        清理特定对话的所有临时文件

        Args:
            conversation_id: 对话 ID
            dry_run: 是否只显示操作但不执行

        Returns:
            Dict[str, Any]: 清理统计
        """
        try:
            conv_dir = self.temp_dir / conversation_id
            if not conv_dir.exists():
                return {
                    "files_deleted": 0,
                    "space_freed_bytes": 0,
                    "conversation_id": conversation_id
                }

            files_deleted = 0
            space_freed = 0
            errors = []

            # 删除对话目录中的所有文件
            for file_path in conv_dir.rglob("*"):
                if file_path.is_file():
                    try:
                        file_size = file_path.stat().st_size
                        if not dry_run:
                            file_path.unlink()
                        files_deleted += 1
                        space_freed += file_size
                        logger.info(f"清理对话文件: {file_path}")
                    except Exception as e:
                        logger.error(f"删除文件失败 ({file_path}): {e}")
                        errors.append(str(file_path))

            # 删除对话目录
            try:
                if not dry_run and conv_dir.exists():
                    shutil.rmtree(conv_dir)
                logger.info(f"清理对话目录: {conv_dir}")
            except Exception as e:
                logger.error(f"删除对话目录失败 ({conv_dir}): {e}")
                errors.append(str(conv_dir))

            logger.info(
                f"对话清理完成 - 删除文件: {files_deleted}, "
                f"释放空间: {space_freed / (1024 * 1024):.2f}MB, "
                f"对话ID: {conversation_id}"
            )

            return {
                "files_deleted": files_deleted,
                "space_freed_bytes": space_freed,
                "conversation_id": conversation_id,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"对话清理失败: {e}")
            raise FileCleanerError(f"对话清理失败: {e}")

    def should_run_cleanup(self) -> bool:
        """
        检查是否应该运行清理（基于时间间隔）

        Returns:
            bool: 是否应该运行清理
        """
        if datetime.now() - self.last_cleanup_time >= self.cleanup_interval:
            self.last_cleanup_time = datetime.now()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """
        获取临时文件目录的统计信息

        Returns:
            Dict[str, Any]: 统计信息
                - total_size_bytes: 总大小（字节）
                - total_size_mb: 总大小（MB）
                - max_storage_mb: 最大存储（MB）
                - usage_percentage: 使用百分比（%）
                - file_count: 文件总数
                - dir_count: 目录总数
        """
        try:
            total_size = self.get_directory_size()
            file_count = 0
            dir_count = 0

            for item in self.temp_dir.rglob("*"):
                if item.is_file():
                    file_count += 1
                elif item.is_dir():
                    dir_count += 1

            usage_pct = (total_size / self.max_storage_bytes) * 100 if self.max_storage_bytes > 0 else 0

            return {
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "max_storage_mb": self.max_storage_bytes / (1024 * 1024),
                "usage_percentage": round(usage_pct, 2),
                "file_count": file_count,
                "dir_count": dir_count,
                "last_cleanup_time": self.last_cleanup_time.isoformat()
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
