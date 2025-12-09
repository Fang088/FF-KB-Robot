"""
数据库访问层 - 统一管理所有数据库操作

核心功能：
1. DBConnection - 数据库连接管理和上下文管理器
2. DocumentRepository - 文档仓储
3. KBRepository - 知识库仓储

快速开始：
    from db import DBConnection, KBRepository

    db = DBConnection(db_path)
    kb_repo = KBRepository(db)
    kb = kb_repo.get_knowledge_base(kb_id)
"""

import sqlite3
import logging
from typing import Optional, List, Tuple, Dict, Any
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """数据库操作异常"""
    pass


class DBConnection:
    """
    数据库连接管理器 - 统一管理数据库连接和表初始化

    特性：
    1. 自动表初始化（CREATE TABLE IF NOT EXISTS）
    2. 上下文管理器支持
    3. 错误处理和日志记录
    4. 通用SQL执行接口

    Usage:
        db = DBConnection(db_path)

        # 上下文管理器（推荐）
        with db.session() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents")
    """

    def __init__(self, db_path: str, auto_init: bool = True):
        """
        初始化数据库连接管理器

        Args:
            db_path: 数据库文件路径
            auto_init: 是否自动初始化表（默认True）
        """
        self.db_path = str(db_path)
        self._ensure_dir()
        if auto_init:
            self._initialize_tables()
        logger.debug(f"数据库已初始化: {self.db_path}")

    def _ensure_dir(self):
        """确保数据库目录存在"""
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    def _initialize_tables(self):
        """初始化所有必要的数据库表"""
        with self.session() as conn:
            cursor = conn.cursor()
            try:
                # 知识库表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_bases (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT,
                        tags TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        document_count INTEGER DEFAULT 0,
                        total_chunks INTEGER DEFAULT 0
                    )
                """)

                # 文档表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        kb_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        file_path TEXT,
                        chunk_count INTEGER,
                        created_at TIMESTAMP,
                        FOREIGN KEY(kb_id) REFERENCES knowledge_bases(id)
                    )
                """)

                # 文本分块表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS text_chunks (
                        id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        kb_id TEXT NOT NULL,
                        content TEXT,
                        chunk_index INTEGER,
                        vector_id TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP,
                        FOREIGN KEY(document_id) REFERENCES documents(id),
                        FOREIGN KEY(kb_id) REFERENCES knowledge_bases(id)
                    )
                """)

                conn.commit()
                logger.debug("数据库表初始化完成")
            except sqlite3.Error as e:
                logger.error(f"初始化表失败: {e}")
                raise DatabaseError(f"初始化表失败: {str(e)}")

    def get_connection(self) -> sqlite3.Connection:
        """
        获取数据库连接

        Returns:
            sqlite3.Connection: 数据库连接对象

        Raises:
            DatabaseError: 连接失败
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 返回字典形式的行
            return conn
        except sqlite3.Error as e:
            raise DatabaseError(f"数据库连接失败: {str(e)}")

    @contextmanager
    def session(self):
        """
        上下文管理器 - 自动管理连接的打开和关闭

        Usage:
            with db.session() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM documents")
                result = cursor.fetchall()
        """
        conn = self.get_connection()
        try:
            yield conn
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"数据库操作错误: {str(e)}")
            raise DatabaseError(f"数据库操作失败: {str(e)}")
        finally:
            conn.close()

    def execute_query(self, sql: str, params: tuple = ()) -> List[Tuple]:
        """
        执行查询SQL并返回结果

        Args:
            sql: SQL查询语句
            params: SQL参数

        Returns:
            List[Tuple]: 查询结果列表
        """
        with self.session() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                return cursor.fetchall()
            except sqlite3.Error as e:
                raise DatabaseError(f"查询失败: {str(e)}")

    def execute_update(self, sql: str, params: tuple = ()) -> int:
        """
        执行更新/插入/删除SQL

        Args:
            sql: SQL语句
            params: SQL参数

        Returns:
            int: 受影响的行数
        """
        with self.session() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                conn.commit()
                return cursor.rowcount
            except sqlite3.Error as e:
                conn.rollback()
                raise DatabaseError(f"更新失败: {str(e)}")

    def execute_many(self, sql: str, params_list: List[tuple]) -> int:
        """
        批量执行SQL语句

        Args:
            sql: SQL语句
            params_list: 参数列表

        Returns:
            int: 总共受影响的行数
        """
        with self.session() as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(sql, params_list)
                conn.commit()
                return cursor.rowcount
            except sqlite3.Error as e:
                conn.rollback()
                raise DatabaseError(f"批量操作失败: {str(e)}")


class DocumentRepository:
    """
    文档仓储 - 处理所有文档相关的数据库操作
    """

    def __init__(self, db: DBConnection):
        """
        初始化文档仓储

        Args:
            db: DBConnection实例
        """
        self.db = db

    def get_document_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """获取指定ID的文档（ID为字符串类型）"""
        try:
            result = self.db.execute_query(
                "SELECT id, kb_id, filename, file_path, chunk_count, created_at "
                "FROM documents WHERE id = ?",
                (doc_id,)
            )
            if result:
                return dict(result[0])
            return None
        except DatabaseError as e:
            logger.error(f"获取文档失败 (ID: {doc_id}): {str(e)}")
            raise

    def get_documents_by_kb(self, kb_id: str) -> List[Dict[str, Any]]:
        """获取知识库内的所有文档（KB_ID为字符串类型）"""
        try:
            results = self.db.execute_query(
                "SELECT id, kb_id, filename, file_path, chunk_count, created_at "
                "FROM documents WHERE kb_id = ? ORDER BY created_at DESC",
                (kb_id,)
            )
            return [dict(row) for row in results]
        except DatabaseError as e:
            logger.error(f"获取知识库文档失败 (KB_ID: {kb_id}): {str(e)}")
            raise

    def save_document(
        self,
        doc_id: str,
        kb_id: str,
        filename: str,
        file_path: str,
        chunk_count: int
    ) -> str:
        """保存新文档记录（所有ID为字符串类型）"""
        try:
            self.db.execute_update(
                "INSERT INTO documents (id, kb_id, filename, file_path, chunk_count, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (doc_id, kb_id, filename, file_path, chunk_count, datetime.now().isoformat())
            )
            return doc_id
        except DatabaseError as e:
            logger.error(f"保存文档失败 ({filename}): {str(e)}")
            raise

    def delete_document(self, doc_id: str) -> int:
        """删除文档记录（ID为字符串类型）"""
        try:
            return self.db.execute_update(
                "DELETE FROM documents WHERE id = ?",
                (doc_id,)
            )
        except DatabaseError as e:
            logger.error(f"删除文档失败 (ID: {doc_id}): {str(e)}")
            raise

    def update_document_chunks(self, doc_id: str, chunk_count: int) -> int:
        """更新文档的文本块数量（ID为字符串类型）"""
        try:
            return self.db.execute_update(
                "UPDATE documents SET chunk_count = ? WHERE id = ?",
                (chunk_count, doc_id)
            )
        except DatabaseError as e:
            logger.error(f"更新文档块数失败 (ID: {doc_id}): {str(e)}")
            raise


class KBRepository:
    """
    知识库仓储 - 处理所有知识库相关的数据库操作
    """

    def __init__(self, db: DBConnection):
        """
        初始化知识库仓储

        Args:
            db: DBConnection实例
        """
        self.db = db

    def create_knowledge_base(self, kb_id: str, name: str, description: str = "", tags: str = "") -> str:
        """创建新的知识库（ID为字符串类型UUID）"""
        try:
            self.db.execute_update(
                "INSERT INTO knowledge_bases (id, name, description, tags, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (kb_id, name, description, tags, datetime.now().isoformat())
            )
            return kb_id
        except DatabaseError as e:
            logger.error(f"创建知识库失败 ({name}): {str(e)}")
            raise

    def get_knowledge_base(self, kb_id: str) -> Optional[Dict[str, Any]]:
        """获取知识库信息（ID为字符串类型）"""
        try:
            result = self.db.execute_query(
                "SELECT id, name, description, tags, created_at FROM knowledge_bases WHERE id = ?",
                (kb_id,)
            )
            if result:
                return dict(result[0])
            return None
        except DatabaseError as e:
            logger.error(f"获取知识库失败 (ID: {kb_id}): {str(e)}")
            raise

    def list_knowledge_bases(self) -> List[Dict[str, Any]]:
        """列出所有知识库"""
        try:
            results = self.db.execute_query(
                "SELECT id, name, description, tags, created_at "
                "FROM knowledge_bases ORDER BY created_at DESC"
            )
            return [dict(row) for row in results]
        except DatabaseError as e:
            logger.error(f"���出知识库失败: {str(e)}")
            raise

    def delete_knowledge_base(self, kb_id: str) -> int:
        """删除知识库（ID为字符串类型）"""
        try:
            return self.db.execute_update(
                "DELETE FROM knowledge_bases WHERE id = ?",
                (kb_id,)
            )
        except DatabaseError as e:
            logger.error(f"删除知识库失败 (ID: {kb_id}): {str(e)}")
            raise

    def get_kb_stats(self, kb_id: str) -> Dict[str, Any]:
        """获取知识库统计信息（ID为字符串类型）"""
        try:
            kb_info = self.get_knowledge_base(kb_id)
            if not kb_info:
                raise DatabaseError(f"知识库不存在: {kb_id}")

            doc_stats = self.db.execute_query(
                "SELECT COUNT(*) as doc_count, SUM(chunk_count) as total_chunks "
                "FROM documents WHERE kb_id = ?",
                (kb_id,)
            )

            count_row = dict(doc_stats[0]) if doc_stats else {}
            return {
                "kb_id": kb_id,
                "name": kb_info["name"],
                "description": kb_info["description"],
                "document_count": count_row.get("doc_count", 0),
                "total_chunks": count_row.get("total_chunks", 0),
                "created_at": kb_info["created_at"]
            }
        except DatabaseError as e:
            logger.error(f"获取知识库统计失败 (ID: {kb_id}): {str(e)}")
            raise
