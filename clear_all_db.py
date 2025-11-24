"""
完整数据库清理脚本 - 清除向量数据库 + SQLite 数据库中的所有文档和知识库数据
"""

import os
import sqlite3
import shutil
import logging
from pathlib import Path
from datetime import datetime
from config.settings import settings
from retrieval.vector_store_client import VectorStoreClient

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DatabaseCleaner:
    """数据库清理工具"""

    def __init__(self):
        """初始化清理工具"""
        self.db_path = str(settings.PROJECT_ROOT / settings.DATABASE_URL.replace("sqlite:///./", ""))
        self.vector_db_path = settings.VECTOR_STORE_PATH
        self.temp_upload_path = settings.TEMP_UPLOAD_PATH
        self.processed_chunks_path = settings.PROCESSED_CHUNKS_PATH

        logger.info("数据库清理工具已初始化")
        logger.info(f"SQLite 数据库: {self.db_path}")
        logger.info(f"向量数据库: {self.vector_db_path}")

    def backup_database(self):
        """备份数据库"""
        logger.info("\n[步骤1] 备份数据库...")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(self.db_path).parent / "backup"
        backup_dir.mkdir(exist_ok=True)

        # 备份 SQLite 数据库
        if os.path.exists(self.db_path):
            backup_db_path = backup_dir / f"kbrobot_{timestamp}.db"
            shutil.copy2(self.db_path, backup_db_path)
            logger.info(f"✓ SQLite 数据库已备份: {backup_db_path}")

        # 备份向量数据库目录
        if os.path.exists(self.vector_db_path):
            backup_vector_path = backup_dir / f"vector_store_{timestamp}"
            shutil.copytree(self.vector_db_path, backup_vector_path)
            logger.info(f"✓ 向量数据库已备份: {backup_vector_path}")

        logger.info(f"✓ 所有数据已备份到: {backup_dir}")
        return backup_dir

    def clean_sqlite_database(self):
        """清除 SQLite 数据库中的所有数据"""
        logger.info("\n[步骤2] 清除 SQLite 数据库数据...")

        if not os.path.exists(self.db_path):
            logger.warning(f"⚠️  SQLite 数据库不存在: {self.db_path}")
            return 0, 0, 0

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            conn.execute("BEGIN TRANSACTION")

            # 清除所有数据，但保留表结构
            cursor.execute("DELETE FROM text_chunks")
            chunks_deleted = cursor.rowcount
            logger.info(f"  ✓ 已删除 {chunks_deleted} 个文本分块")

            cursor.execute("DELETE FROM documents")
            docs_deleted = cursor.rowcount
            logger.info(f"  ✓ 已删除 {docs_deleted} 个文档")

            cursor.execute("DELETE FROM knowledge_bases")
            kbs_deleted = cursor.rowcount
            logger.info(f"  ✓ 已删除 {kbs_deleted} 个知识库")

            conn.commit()
            logger.info("  ✓ SQLite 数据库已清空")

            return chunks_deleted, docs_deleted, kbs_deleted

        except Exception as e:
            conn.rollback()
            logger.error(f"  ❌ SQLite 数据库清空失败: {e}")
            raise
        finally:
            conn.close()

    def clean_vector_database(self):
        """清除向量数据库"""
        logger.info("\n[步骤3] 清除向量数据库...")

        try:
            # 初始化向量存储客户端
            vector_store = VectorStoreClient(
                store_type=settings.VECTOR_STORE_TYPE,
                path_or_url=self.vector_db_path,
                collection_name=settings.VECTOR_STORE_COLLECTION_NAME,
            )

            # 尝试清空集合
            try:
                vector_store.clear_collection()
                logger.info(f"  ✓ 集合已清空: {settings.VECTOR_STORE_COLLECTION_NAME}")
            except Exception as e:
                logger.info(f"  ℹ️  集合清空异常（可能不存在）: {e}")

            # 删除整个向量数据库目录
            if os.path.exists(self.vector_db_path):
                logger.info(f"  删除向量数据库目录: {self.vector_db_path}")
                shutil.rmtree(self.vector_db_path)
                logger.info(f"  ✓ 向量数据库目录已删除")

                # 重新创建空目录
                os.makedirs(self.vector_db_path, exist_ok=True)
                logger.info(f"  ✓ 向量数据库目录已重新创建")
            else:
                logger.info(f"  ℹ️  向量数据库目录不存在")

        except Exception as e:
            logger.error(f"  ❌ 向量数据库清除失败: {e}")

    def clean_temp_files(self):
        """清除临时文件"""
        logger.info("\n[步骤4] 清除临时文件...")

        deleted_count = 0
        if os.path.exists(self.temp_upload_path):
            for filename in os.listdir(self.temp_upload_path):
                file_path = os.path.join(self.temp_upload_path, filename)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"  ⚠️  删除失败: {filename}, 错误: {e}")

            logger.info(f"  ✓ 已删除 {deleted_count} 个临时文件")
        else:
            logger.info(f"  ℹ️  临时文件目录不存在")

        return deleted_count

    def clean_chunk_files(self):
        """清除分块文件"""
        logger.info("\n[步骤5] 清除分块文件...")

        deleted_count = 0
        if os.path.exists(self.processed_chunks_path):
            for filename in os.listdir(self.processed_chunks_path):
                file_path = os.path.join(self.processed_chunks_path, filename)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"  ⚠️  删除失败: {filename}, 错误: {e}")

            logger.info(f"  ✓ 已删除 {deleted_count} 个分块文件")
        else:
            logger.info(f"  ℹ️  分块文件目录不存在")

        return deleted_count

    def verify_cleanup(self):
        """验证清理结果"""
        logger.info("\n[步骤6] 验证清理结果...")

        # 验证 SQLite 数据库
        logger.info("\n  📊 SQLite 数据库统计:")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM knowledge_bases")
        kb_count = cursor.fetchone()[0]
        logger.info(f"    - 知识库数: {kb_count}")

        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]
        logger.info(f"    - 文档数: {doc_count}")

        cursor.execute("SELECT COUNT(*) FROM text_chunks")
        chunk_count = cursor.fetchone()[0]
        logger.info(f"    - 分块数: {chunk_count}")

        conn.close()

        # 验证向量数据库
        logger.info("\n  📊 向量数据库统计:")
        try:
            vector_store = VectorStoreClient(
                store_type=settings.VECTOR_STORE_TYPE,
                path_or_url=self.vector_db_path,
                collection_name=settings.VECTOR_STORE_COLLECTION_NAME,
            )
            stats = vector_store.get_collection_stats()
            logger.info(f"    - 集合: {stats.get('collection_name')}")
            logger.info(f"    - 向量数: {stats.get('count', 0)}")
        except Exception as e:
            logger.info(f"    - 集合: 空 (异常: {e})")

        # 验证文件系统
        logger.info("\n  📊 文件系统统计:")
        temp_count = len(os.listdir(self.temp_upload_path)) if os.path.exists(self.temp_upload_path) else 0
        chunk_count_fs = len(os.listdir(self.processed_chunks_path)) if os.path.exists(self.processed_chunks_path) else 0
        logger.info(f"    - 临时文件: {temp_count}")
        logger.info(f"    - 分块文件: {chunk_count_fs}")

        # 总体判断
        is_clean = kb_count == 0 and doc_count == 0 and chunk_count == 0 and temp_count == 0 and chunk_count_fs == 0

        if is_clean:
            logger.info("\n  ✅ 数据库已完全清空！")
        else:
            logger.warning("\n  ⚠️  数据库中仍有残留数据")

        return is_clean

    def full_cleanup(self, backup=True):
        """执行完整清理"""
        logger.info("="*60)
        logger.info("开始执行完整数据库清理")
        logger.info("="*60)

        try:
            # 备份
            if backup:
                backup_dir = self.backup_database()

            # 清理各个部分
            chunks_del, docs_del, kbs_del = self.clean_sqlite_database()
            self.clean_vector_database()
            temp_files_del = self.clean_temp_files()
            chunk_files_del = self.clean_chunk_files()

            # 验证
            is_clean = self.verify_cleanup()

            # 总结
            logger.info("\n" + "="*60)
            logger.info("数据库清理完成")
            logger.info("="*60)
            logger.info("\n📊 清理摘要:")
            logger.info(f"  - SQLite 数据库:")
            logger.info(f"    • 删除知识库: {kbs_del} 个")
            logger.info(f"    • 删除文档: {docs_del} 个")
            logger.info(f"    • 删除分块: {chunks_del} 个")
            logger.info(f"  - 向量数据库: 已清空")
            logger.info(f"  - 临时文件: {temp_files_del} 个")
            logger.info(f"  - 分块文件: {chunk_files_del} 个")

            if backup:
                logger.info(f"  - 备份位置: {backup_dir}")

            if is_clean:
                logger.info("\n✅ 所有数据已彻底清除！")
            else:
                logger.warning("\n⚠️  清理完成，但仍有残留数据")

            return True

        except Exception as e:
            logger.error(f"❌ 清理失败: {e}", exc_info=True)
            return False


def main():
    """主函数"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("用法:")
        print("  python clear_all_db.py          # 清除所有数据库（包含备份）")
        print("  python clear_all_db.py --no-backup # 清除所有数据库（不备份）")
        print("  python clear_all_db.py --help   # 显示帮助信息")
        sys.exit(0)

    # 二次确认
    print("\n" + "="*60)
    print("⚠️  严重警告：您即将清除ALL数据库！")
    print("="*60)
    print("\n这将永久删除:")
    print("  ✗ SQLite 数据库中的所有知识库")
    print("  ✗ SQLite 数据库中的所有文档")
    print("  ✗ SQLite 数据库中的所有文本分块")
    print("  ✗ HNSW 向量数据库中的所有向量")
    print("  ✗ data/temp_uploads 中的所有临时文件")
    print("  ✗ data/processed_chunks 中的所有分块文件")
    print("\n此操作无法撤销！")
    print("="*60)

    # 获取用户确认
    response = input("\n您确定要继续吗？(请输入 'yes' 确认): ").strip().lower()

    if response == "yes":
        backup = "--no-backup" not in sys.argv
        print("\n正在清除数据库...\n")

        cleaner = DatabaseCleaner()
        success = cleaner.full_cleanup(backup=backup)

        if success:
            print("\n✅ 清理完成！")
        else:
            print("\n❌ 清理过程中发生错误")

    else:
        print("\n❌ 操作已取消")


if __name__ == "__main__":
    main()
