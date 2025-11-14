#!/usr/bin/env python3
"""
文件清理工具 - 清理临时文件和旧的处理分块
"""

import os
import time
from datetime import datetime, timedelta
from config.settings import settings

def cleanup_temp_files(days: int = 7):
    """
    清理旧的临时文件

    Args:
        days: 保留天数
    """
    temp_dir = settings.TEMP_UPLOAD_PATH
    print(f"清理临时文件目录: {temp_dir}")

    cutoff_time = datetime.now() - timedelta(days=days)
    files_deleted = 0
    size_deleted = 0

    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        if os.path.isfile(file_path):
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if mtime < cutoff_time:
                file_size = os.path.getsize(file_path)
                os.remove(file_path)
                files_deleted += 1
                size_deleted += file_size

    print(f"✓ 清理完成: {files_deleted} 个文件 ({size_deleted/1024/1024:.2f} MB)")
    return files_deleted, size_deleted

def cleanup_processed_chunks(days: int = 30):
    """
    清理旧的处理分块

    Args:
        days: 保留天数
    """
    chunks_dir = settings.PROCESSED_CHUNKS_PATH
    print(f"清理处理分块目录: {chunks_dir}")

    cutoff_time = datetime.now() - timedelta(days=days)
    files_deleted = 0
    size_deleted = 0

    for filename in os.listdir(chunks_dir):
        file_path = os.path.join(chunks_dir, filename)
        if os.path.isfile(file_path):
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            if mtime < cutoff_time:
                file_size = os.path.getsize(file_path)
                os.remove(file_path)
                files_deleted += 1
                size_deleted += file_size

    print(f"✓ 清理完成: {files_deleted} 个文件 ({size_deleted/1024/1024:.2f} MB)")
    return files_deleted, size_deleted

def main():
    """主函数"""
    print("FF-KB-Robot 文件清理工具")
    print("-" * 50)

    import argparse

    parser = argparse.ArgumentParser(description="清理临时文件和处理分块")
    parser.add_argument("--temp", type=int, default=7, help="临时文件保留天数")
    parser.add_argument("--chunks", type=int, default=30, help="处理分块保留天数")
    args = parser.parse_args()

    print()
    temp_files, temp_size = cleanup_temp_files(args.temp)
    print()
    chunks_files, chunks_size = cleanup_processed_chunks(args.chunks)
    print()
    print("=" * 50)
    total_files = temp_files + chunks_files
    total_size = temp_size + chunks_size
    print(f"总清理: {total_files} 个文件 ({total_size/1024/1024:.2f} MB)")
    print("清理完成！")

if __name__ == "__main__":
    main()