#!/usr/bin/env python3
"""
FF-KB-Robot 数据清理脚本 - 全面清除所有数据和缓存

功能：
1. 清除 SQLite 数据库中的所有知识库、文档、分块数据
2. 清除向量数据库（HNSW 索引和元数据）
3. 清除运行时缓存（Embedding、查询结果、分类器缓存）
4. 清除临时上传文件和处理后的分块
5. 清除日志文件
6. 清除 Python 编译缓存（__pycache__、.pyc）
7. 清除其他开发缓存（.pytest_cache、.mypy_cache 等）
8. 支持数据库自动备份

使用示例：
    python cleanup.py                    # 交互模式（推荐）
    python cleanup.py --all --backup     # 备份并清除所有（无需确认）
    python cleanup.py --all --no-backup  # 清除所有（危险！）
    python cleanup.py --only-cache       # 仅清除缓存（保留数据）

注意：此操作不可逆！强烈建议先备份！
"""

import os
import sys
import shutil
import sqlite3
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple

# ==================== 配置 ====================

PROJECT_ROOT = Path(__file__).parent
DB_DIR = PROJECT_ROOT / "db"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# 数据目录
VECTOR_STORE_DIR = DB_DIR / "vector_store"
SQL_DB_DIR = DB_DIR / "sql_db"
TEMP_UPLOADS_DIR = DATA_DIR / "temp_uploads"
PROCESSED_CHUNKS_DIR = DATA_DIR / "processed_chunks"

# 数据库文件
SQL_DB_FILE = SQL_DB_DIR / "kbrobot.db"

# 缓存目录模式
PYCACHE_PATTERN = "**/__pycache__"
PYTEST_CACHE_DIR = PROJECT_ROOT / ".pytest_cache"
MYPY_CACHE_DIR = PROJECT_ROOT / ".mypy_cache"
RUFF_CACHE_DIR = PROJECT_ROOT / ".ruff_cache"

# 确保日志目录存在
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "cleanup.log"

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ==================== 统计类 ====================

class CleanupStats:
    """清理统计"""
    def __init__(self):
        self.files_deleted = 0
        self.dirs_deleted = 0
        self.bytes_freed = 0
        self.errors = []

    def add_file(self, size: int = 0):
        self.files_deleted += 1
        self.bytes_freed += size

    def add_dir(self):
        self.dirs_deleted += 1

    def add_error(self, msg: str):
        self.errors.append(msg)

    def format_size(self) -> str:
        """格式化字节大小"""
        size = self.bytes_freed
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    def summary(self) -> str:
        return f"{self.files_deleted} 文件, {self.dirs_deleted} 目录, 释放 {self.format_size()}"


# ==================== 清理函数 ====================

def show_database_stats(db_path: Path) -> Tuple[int, int, int]:
    """显示数据库统计信息"""
    if not db_path.exists():
        return 0, 0, 0

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM knowledge_bases")
        kb_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM text_chunks")
        chunk_count = cursor.fetchone()[0]

        conn.close()
        return kb_count, doc_count, chunk_count

    except sqlite3.Error:
        return 0, 0, 0


def backup_database(db_path: Path) -> Optional[Path]:
    """备份数据库文件"""
    if not db_path.exists():
        logger.warning(f"数据库文件不存在，跳过备份: {db_path}")
        return None

    backup_dir = PROJECT_ROOT / "db_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"kbrobot_{timestamp}.db"

    try:
        shutil.copy2(db_path, backup_file)
        logger.info(f"✓ 数据库已备份: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"✗ 数据库备份失败: {e}")
        return None


def clear_database(db_path: Path, stats: CleanupStats) -> bool:
    """清除 SQLite 数据库中的所有知识库、文档、分块数据"""
    if not db_path.exists():
        logger.warning(f"数据库文件不存在，跳过清理: {db_path}")
        return True

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 获取清理前的数据统计
        cursor.execute("SELECT COUNT(*) FROM knowledge_bases")
        kb_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM text_chunks")
        chunk_count = cursor.fetchone()[0]

        # 清除数据（保留表结构）
        cursor.execute("DELETE FROM text_chunks")
        cursor.execute("DELETE FROM documents")
        cursor.execute("DELETE FROM knowledge_bases")

        conn.commit()
        conn.close()

        logger.info(f"✓ 已清除数据库: {kb_count} 个知识库、{doc_count} 个文档、{chunk_count} 个分块")
        return True

    except sqlite3.Error as e:
        logger.error(f"✗ 数据库清理失败: {e}")
        stats.add_error(f"数据库清理失败: {e}")
        return False


def clear_directory(dir_path: Path, stats: CleanupStats, description: str) -> bool:
    """清除目录下的所有文件和子目录"""
    if not dir_path.exists():
        logger.warning(f"{description}目录不存在: {dir_path}")
        return True

    try:
        count = 0
        for item in dir_path.iterdir():
            try:
                if item.is_file():
                    size = item.stat().st_size
                    item.unlink()
                    stats.add_file(size)
                    count += 1
                elif item.is_dir():
                    shutil.rmtree(item)
                    stats.add_dir()
                    count += 1
            except Exception as e:
                stats.add_error(f"删除失败 {item}: {e}")

        logger.info(f"✓ 已清除{description}: {count} 个文件/目录")
        return True

    except Exception as e:
        logger.error(f"✗ {description}清理失败: {e}")
        stats.add_error(f"{description}清理失败: {e}")
        return False


def clear_pycache(stats: CleanupStats) -> bool:
    """清除所有 __pycache__ 目录"""
    try:
        count = 0
        for pycache_dir in PROJECT_ROOT.glob(PYCACHE_PATTERN):
            try:
                shutil.rmtree(pycache_dir)
                stats.add_dir()
                count += 1
            except Exception as e:
                stats.add_error(f"删除失败 {pycache_dir}: {e}")

        # 清除 .pyc 文件
        for pyc_file in PROJECT_ROOT.glob("**/*.pyc"):
            try:
                size = pyc_file.stat().st_size
                pyc_file.unlink()
                stats.add_file(size)
                count += 1
            except Exception as e:
                stats.add_error(f"删除失败 {pyc_file}: {e}")

        # 清除 .pyo 文件
        for pyo_file in PROJECT_ROOT.glob("**/*.pyo"):
            try:
                size = pyo_file.stat().st_size
                pyo_file.unlink()
                stats.add_file(size)
                count += 1
            except Exception as e:
                stats.add_error(f"删除失败 {pyo_file}: {e}")

        logger.info(f"✓ 已清除 Python 编译缓存: {count} 个文件/目录")
        return True

    except Exception as e:
        logger.error(f"✗ Python 缓存清理失败: {e}")
        stats.add_error(f"Python 缓存清理失败: {e}")
        return False


def clear_dev_caches(stats: CleanupStats) -> bool:
    """清除开发工具缓存（pytest, mypy, ruff 等）"""
    dev_cache_dirs = [
        (PYTEST_CACHE_DIR, ".pytest_cache"),
        (MYPY_CACHE_DIR, ".mypy_cache"),
        (RUFF_CACHE_DIR, ".ruff_cache"),
    ]

    count = 0
    for cache_dir, name in dev_cache_dirs:
        if cache_dir.exists():
            try:
                shutil.rmtree(cache_dir)
                stats.add_dir()
                count += 1
            except Exception as e:
                stats.add_error(f"删除失败 {name}: {e}")

    if count > 0:
        logger.info(f"✓ 已清除开发工具缓存: {count} 个目录")
    else:
        logger.info("✓ 无开发工具缓存需要清理")

    return True


def clear_runtime_cache() -> bool:
    """清除运行时内存缓存（CacheManager）"""
    try:
        # 尝试导入并清理缓存管理器
        from utils.cache_manager import get_cache_manager, _cache_manager_instance

        # 如果缓存管理器已初始化，清空它
        if _cache_manager_instance is not None:
            _cache_manager_instance.clear_all()
            logger.info("✓ 已清除运行时缓存（CacheManager）")
        else:
            logger.info("✓ 运行时缓存未初始化，无需清理")

        return True

    except ImportError:
        logger.warning("⚠ 无法导入缓存管理器，跳过运行时缓存清理")
        return True
    except Exception as e:
        logger.warning(f"⚠ 运行时缓存清理失败: {e}")
        return True  # 不算失败，因为是可选清理


def clear_logs(logs_dir: Path, stats: CleanupStats, keep_cleanup_log: bool = True) -> bool:
    """清除日志文件"""
    if not logs_dir.exists():
        logger.warning(f"日志目录不存在: {logs_dir}")
        return True

    try:
        count = 0
        for log_file in logs_dir.glob("*.log"):
            if keep_cleanup_log and log_file.name == "cleanup.log":
                continue
            try:
                size = log_file.stat().st_size
                log_file.unlink()
                stats.add_file(size)
                count += 1
            except Exception as e:
                stats.add_error(f"删除失败 {log_file}: {e}")

        logger.info(f"✓ 已清除日志文件: {count} 个")
        return True

    except Exception as e:
        logger.error(f"✗ 日志文件清理失败: {e}")
        stats.add_error(f"日志文件清理失败: {e}")
        return False


def confirm(prompt: str, default: bool = False) -> bool:
    """确认用户选择"""
    default_text = "yes" if default else "no"
    response = input(f"{prompt} (yes/no) [{default_text}]: ").strip().lower()

    if response in ['yes', 'y']:
        return True
    elif response in ['no', 'n']:
        return False
    else:
        return default


# ==================== 主函数 ====================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FF-KB-Robot 数据清理工具 🐱",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cleanup.py              # 交互模式（推荐）
  python cleanup.py --all        # 清除所有数据和缓存
  python cleanup.py --only-cache # 仅清除缓存（保留数据）
  python cleanup.py --backup     # 清理前自动备份
"""
    )

    parser.add_argument("--all", action="store_true", help="一次清除所有数据（无需逐项确认）")
    parser.add_argument("--only-cache", action="store_true", help="仅清除缓存（保留数据库和文档）")
    parser.add_argument("--backup", action="store_true", help="清理前自动备份数据库")
    parser.add_argument("--no-backup", action="store_true", help="不备份数据库（危险！）")

    args = parser.parse_args()

    # 初始化统计
    stats = CleanupStats()

    # 打印欢迎信息
    print("\n" + "=" * 70)
    print("  FF-KB-Robot 数据清理工具 🐱")
    print("=" * 70)
    print(f"项目路径: {PROJECT_ROOT}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 日志记录
    logger.info("=" * 70)
    logger.info("FF-KB-Robot 数据清理开始")
    logger.info("=" * 70)

    # 显示当前数据库统计
    if SQL_DB_FILE.exists():
        kb_count, doc_count, chunk_count = show_database_stats(SQL_DB_FILE)
        if kb_count > 0 or doc_count > 0 or chunk_count > 0:
            print("📊 当前数据库状态:")
            print(f"  • 知识库: {kb_count} 个")
            print(f"  • 文档: {doc_count} 个")
            print(f"  • 分块: {chunk_count} 个")
            print()

    # 显示清理项目
    if args.only_cache:
        print("📋 仅清理缓存模式:")
        print("  1. Python 编译缓存 (__pycache__, .pyc)")
        print("  2. 开发工具缓存 (.pytest_cache, .mypy_cache 等)")
        print("  3. 运行时缓存 (CacheManager)")
        print("  4. 日志文件")
        print()
    else:
        print("📋 清理项目:")
        print("  1. SQLite 数据库（知识库、文档、分块）")
        print("  2. 向量存储（HNSW 索引和元数据）")
        print("  3. 临时上传文件")
        print("  4. 处理后的分块")
        print("  5. Python 编译缓存 (__pycache__, .pyc)")
        print("  6. 开发工具缓存 (.pytest_cache, .mypy_cache 等)")
        print("  7. 运行时缓存 (CacheManager)")
        print("  8. 日志文件")
        print()

    # 确认
    if args.all or args.only_cache:
        mode = "缓存" if args.only_cache else "所有数据"
        should_clear = confirm(f"⚠️  确认清除{mode}？")
    else:
        should_clear = confirm("⚠️  确认清除以上所有数据？")

    if not should_clear:
        print("\n❌ 操作已取消")
        logger.warning("用户取消操作")
        return

    # 备份确认
    backup_file = None
    if not args.only_cache and not args.no_backup and SQL_DB_FILE.exists():
        if args.backup:
            should_backup = True
        else:
            should_backup = confirm("\n💾 是否在清理前备份数据库？", default=True)

        if should_backup:
            print("\n备份数据库中...")
            backup_file = backup_database(SQL_DB_FILE)
            if backup_file:
                print(f"✓ 备份完成: {backup_file}\n")
    elif args.no_backup:
        print("\n⚠️  已禁用备份功能")

    # 执行清理
    print("开始清理...")
    print("-" * 70)

    success_count = 0
    total_count = 0

    if not args.only_cache:
        # 数据清理
        data_operations = [
            ("数据库", lambda: clear_database(SQL_DB_FILE, stats)),
            ("向量存储", lambda: clear_directory(VECTOR_STORE_DIR, stats, "向量存储")),
            ("临时上传文件", lambda: clear_directory(TEMP_UPLOADS_DIR, stats, "临时上传文件")),
            ("处理后的分块", lambda: clear_directory(PROCESSED_CHUNKS_DIR, stats, "处理后的分块")),
        ]

        for name, func in data_operations:
            total_count += 1
            try:
                if func():
                    success_count += 1
            except Exception as e:
                logger.error(f"✗ {name}清理失败: {e}")
                stats.add_error(f"{name}清理失败: {e}")

    # 缓存清理（始终执行）
    cache_operations = [
        ("Python 编译缓存", lambda: clear_pycache(stats)),
        ("开发工具缓存", lambda: clear_dev_caches(stats)),
        ("运行时缓存", clear_runtime_cache),
        ("日志文件", lambda: clear_logs(LOGS_DIR, stats)),
    ]

    for name, func in cache_operations:
        total_count += 1
        try:
            if func():
                success_count += 1
        except Exception as e:
            logger.error(f"✗ {name}清理失败: {e}")
            stats.add_error(f"{name}清理失败: {e}")

    # 总结
    print("\n" + "=" * 70)
    if success_count == total_count:
        print("✓ 清理完成！所有数据已成功清除")
    else:
        print(f"⚠️  清理完成，但有 {total_count - success_count} 项操作失败")

    print(f"\n📊 清理统计: {stats.summary()}")

    if stats.errors:
        print(f"\n❌ 错误列表 ({len(stats.errors)} 个):")
        for error in stats.errors[:5]:  # 最多显示5个错误
            print(f"   • {error}")
        if len(stats.errors) > 5:
            print(f"   ... 还有 {len(stats.errors) - 5} 个错误")

    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if backup_file:
        print(f"\n💾 备份文件位置: {backup_file}")
        print(f"   如需恢复，请手动复制备份文件到 {SQL_DB_FILE}")

    print("=" * 70 + "\n")

    logger.info("=" * 70)
    logger.info(f"数据清理完成: {success_count}/{total_count} 项操作成功")
    logger.info(f"清理统计: {stats.summary()}")
    logger.info("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        logger.warning("用户中断清理操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 清理脚本出错: {e}")
        logger.error(f"清理脚本出错: {e}", exc_info=True)
        sys.exit(1)
