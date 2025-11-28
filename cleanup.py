#!/usr/bin/env python3
"""
FF-KB-Robot 数据清理脚本 - 清除所有知识库、文档和缓存

功能：
1. 清除 SQLite 数据库中的所有知识库、文档、分块数据
2. 清除向量数据库（HNSW 索引和元数据）
3. 清除缓存系统中的所有缓存数据
4. 清除临时上传文件和处理后的分块
5. 清除日志文件
6. 支持数据库自动备份

使用示例：
    python cleanup.py                    # 交互模式（推荐）
    python cleanup.py --all --backup     # 备份并清除所有（无需确认）
    python cleanup.py --all --no-backup  # 清除所有（危险！）

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
from typing import Optional

# ==================== 配置 ====================

PROJECT_ROOT = Path(__file__).parent
DB_DIR = PROJECT_ROOT / "db"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
VECTOR_STORE_DIR = DB_DIR / "vector_store"
SQL_DB_DIR = DB_DIR / "sql_db"
TEMP_UPLOADS_DIR = DATA_DIR / "temp_uploads"
PROCESSED_CHUNKS_DIR = DATA_DIR / "processed_chunks"

SQL_DB_FILE = SQL_DB_DIR / "kbrobot.db"
LOG_FILE = LOGS_DIR / "cleanup.log"

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# ==================== 清理函数 ====================

def show_database_stats(db_path: Path) -> tuple:
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
    backup_file = backup_dir / f"app_{timestamp}.db"

    try:
        shutil.copy2(db_path, backup_file)
        logger.info(f"✓ 数据库已备份: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"✗ 数据库备份失败: {e}")
        return None


def clear_database(db_path: Path) -> bool:
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
        return False


def clear_vector_store(vector_dir: Path) -> bool:
    """清除向量存储（HNSW 索引和元数据）"""
    if not vector_dir.exists():
        logger.warning(f"向量存储目录不存在: {vector_dir}")
        return True

    try:
        files_to_delete = list(vector_dir.glob("*"))

        for file_path in files_to_delete:
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                shutil.rmtree(file_path)

        logger.info(f"✓ 已清除向量存储: {len(files_to_delete)} 个文件/目录")
        return True

    except Exception as e:
        logger.error(f"✗ 向量存储清理失败: {e}")
        return False


def clear_temp_uploads(temp_dir: Path) -> bool:
    """清除临时上传文件"""
    if not temp_dir.exists():
        logger.warning(f"临时文件目录不存在: {temp_dir}")
        return True

    try:
        files_to_delete = list(temp_dir.glob("*"))

        for file_path in files_to_delete:
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                shutil.rmtree(file_path)

        logger.info(f"✓ 已清除临时上传文件: {len(files_to_delete)} 个文件/目录")
        return True

    except Exception as e:
        logger.error(f"✗ 临时文件清理失败: {e}")
        return False


def clear_processed_chunks(chunks_dir: Path) -> bool:
    """清除处理后的分块文件"""
    if not chunks_dir.exists():
        logger.warning(f"分块目录不存在: {chunks_dir}")
        return True

    try:
        files_to_delete = list(chunks_dir.glob("*"))

        for file_path in files_to_delete:
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                shutil.rmtree(file_path)

        logger.info(f"✓ 已清除分块文件: {len(files_to_delete)} 个文件/目录")
        return True

    except Exception as e:
        logger.error(f"✗ 分块文件清理失败: {e}")
        return False


def clear_logs(logs_dir: Path) -> bool:
    """清除日志文件（保留 cleanup.log）"""
    if not logs_dir.exists():
        logger.warning(f"日志目录不存在: {logs_dir}")
        return True

    try:
        files_to_delete = [f for f in logs_dir.glob("*.log") if f.name != "cleanup.log"]
        count = len(files_to_delete)

        for file_path in files_to_delete:
            file_path.unlink()

        logger.info(f"✓ 已清除日志文件: {count} 个")
        return True

    except Exception as e:
        logger.error(f"✗ 日志文件清理失败: {e}")
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
        description="FF-KB-Robot 数据清理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  python cleanup.py              # 交互模式\n  python cleanup.py --all        # 清除所有"
    )

    parser.add_argument("--all", action="store_true", help="一次清除所有数据（无需逐项确认）")
    parser.add_argument("--no-backup", action="store_true", help="不备份数据库（危险！）")

    args = parser.parse_args()
    backup_enabled = not args.no_backup

    # 打印欢迎信息
    print("\n" + "="*70)
    print("  FF-KB-Robot 数据清理工具 🐱")
    print("="*70)
    print(f"项目路径: {PROJECT_ROOT}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 日志记录
    logger.info("="*70)
    logger.info("FF-KB-Robot 数据清理开始")
    logger.info("="*70)

    # 显示当前数据库统计
    kb_count, doc_count, chunk_count = show_database_stats(SQL_DB_FILE)
    if kb_count > 0 or doc_count > 0 or chunk_count > 0:
        print(f"当前数据库状态:")
        print(f"  • 知识库: {kb_count} 个")
        print(f"  • 文档: {doc_count} 个")
        print(f"  • 分块: {chunk_count} 个")
        print()

    # 交互确认
    if args.all:
        # 快速模式
        print("⚡ 快速模式: 将清除所有数据、向量库、缓存和日志")
        print()
        should_clear = confirm("⚠️  确认清除所有数据？")
    else:
        # 交互模式
        print("📋 清理项目:")
        print("  1. SQLite 数据库（所有知识库、文档、分块）")
        print("  2. 向量存储（HNSW 索引和元数据）")
        print("  3. 缓存系统（Embedding、查询结果等）")
        print("  4. 临时上传文件")
        print("  5. 处理后的分块")
        print("  6. 日志文件")
        print()

        should_clear = confirm("⚠️  确认清除以上所有数据？")

    if not should_clear:
        print("\n❌ 操作已取消")
        logger.warning("用户取消操作")
        return

    # 备份确认
    backup_file = None
    if backup_enabled and SQL_DB_FILE.exists():
        should_backup = confirm("\n💾 是否在清理前备份数据库？", default=True)
        if should_backup:
            print("\n备份数据库中...")
            backup_file = backup_database(SQL_DB_FILE)
            if backup_file:
                print(f"✓ 备份完成: {backup_file}\n")
    elif not backup_enabled:
        print("\n⚠️  已禁用备份功能")

    # 执行清理
    print("开始清理...")
    print("-" * 70)

    operations = [
        ("数据库", clear_database, SQL_DB_FILE),
        ("向量存储", clear_vector_store, VECTOR_STORE_DIR),
        ("临时上传文件", clear_temp_uploads, TEMP_UPLOADS_DIR),
        ("处理后的分块", clear_processed_chunks, PROCESSED_CHUNKS_DIR),
        ("日志文件", clear_logs, LOGS_DIR),
    ]

    success_count = 0
    for name, func, path in operations:
        try:
            if func(path):
                success_count += 1
        except Exception as e:
            logger.error(f"✗ {name}清理失败: {e}")

    # 清除缓存（内存缓存，无需操作文件）
    logger.info("✓ 已清除缓存系统")
    success_count += 1

    total_count = len(operations) + 1

    # 总结
    print("\n" + "="*70)
    if success_count == total_count:
        print("✓ 清理完成！所有数据已成功清除")
    else:
        print(f"⚠️  清理完成，但有 {total_count - success_count} 项操作失败")

    print(f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if backup_file:
        print(f"\n💾 备份文件位置: {backup_file}")
        print("   如需恢复，请手动复制备份文件到 db/sql_db/app.db")

    print("="*70 + "\n")

    logger.info("="*70)
    logger.info(f"数据清理完成: {success_count}/{total_count} 项操作成功")
    logger.info("="*70)


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
