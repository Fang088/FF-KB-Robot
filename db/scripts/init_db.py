"""
数据库初始化脚本
创建必要的数据库表和配置
"""

import os
import sqlite3
import logging
from pathlib import Path
from config.settings import settings

logger = logging.getLogger(__name__)


def init_database():
    """初始化数据库"""
    db_path = settings.DATABASE_URL.replace("sqlite:///./", "")
    db_full_path = settings.PROJECT_ROOT / db_path

    logger.info(f"初始化数据库: {db_full_path}")

    # 确保目录存在
    db_full_path.parent.mkdir(parents=True, exist_ok=True)

    # 连接数据库
    conn = sqlite3.connect(str(db_full_path))
    cursor = conn.cursor()

    try:
        # 创建知识库表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                document_count INTEGER DEFAULT 0,
                total_chunks INTEGER DEFAULT 0
            )
        """)

        # 创建文档表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                kb_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                content_path TEXT,
                chunk_count INTEGER DEFAULT 0,
                metadata TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id)
            )
        """)

        # 创建文本分块表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS text_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                kb_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER,
                metadata TEXT,
                vector_id TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id),
                FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id)
            )
        """)

        # 创建模型配置表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS model_configs (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                model_name TEXT NOT NULL,
                api_key TEXT,
                api_base TEXT,
                temperature REAL,
                max_tokens INTEGER,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)

        # 创建查询历史表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id TEXT PRIMARY KEY,
                kb_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT,
                retrieved_docs TEXT,
                confidence REAL,
                response_time_ms REAL,
                created_at TIMESTAMP,
                FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id)
            )
        """)

        # 创建索引以提高查询性能
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_kb_id ON documents(kb_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_text_chunks_kb_id ON text_chunks(kb_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_query_history_kb_id ON query_history(kb_id)"
        )

        conn.commit()
        logger.info("数据库初始化完成")
        print("✓ 数据库已初始化")

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        print(f"✗ 数据库初始化失败: {e}")
        conn.rollback()
        raise

    finally:
        conn.close()


def create_default_config():
    """创建默认配置记录"""
    # TODO: 在数据库中创建默认的模型配置
    pass


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # 初始化数据库
    init_database()
