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

                # 对话表 - 用于保存聊天对话
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        kb_id TEXT NOT NULL,
                        kb_name TEXT,
                        title TEXT NOT NULL,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        message_count INTEGER DEFAULT 0,
                        FOREIGN KEY(kb_id) REFERENCES knowledge_bases(id)
                    )
                """)

                # 对话消息表 - 存储具体的聊天消息
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_messages (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP,
                        confidence REAL,
                        confidence_level TEXT,
                        response_time_ms INTEGER,
                        from_cache BOOLEAN,
                        is_welcome BOOLEAN,
                        error BOOLEAN,
                        retrieved_docs TEXT,
                        metadata TEXT,
                        uploaded_files TEXT,           -- 【新增】JSON格式的上传文件列表
                        file_metadata TEXT,            -- 【新增】JSON格式的文件元数据
                        FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                    )
                """)

                # 【新增】对话文件引用表 - 存储对话中上传文件的元数据
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_file_refs (
                        id TEXT PRIMARY KEY,
                        message_id TEXT NOT NULL,
                        conversation_id TEXT NOT NULL,
                        filename TEXT NOT NULL,
                        file_hash TEXT UNIQUE,
                        file_size INTEGER,
                        file_type TEXT,
                        content_preview TEXT,
                        created_at TIMESTAMP,
                        expires_at TIMESTAMP,
                        FOREIGN KEY(message_id) REFERENCES conversation_messages(id),
                        FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                    )
                """)

                # 【新增】会话临时文件表 - 管理对话中的临时上传文件
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS session_temporary_files (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        file_hash TEXT UNIQUE,
                        filename TEXT NOT NULL,
                        file_path TEXT,
                        file_size INTEGER,
                        created_at TIMESTAMP,
                        expires_at TIMESTAMP,
                        status TEXT DEFAULT 'active',
                        FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                    )
                """)

                # 【新增】为新表创建索引
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conv_files_conv_id
                    ON conversation_file_refs(conversation_id)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conv_files_expires
                    ON conversation_file_refs(expires_at)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_session_files_conv_id
                    ON session_temporary_files(conversation_id)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_session_files_expires
                    ON session_temporary_files(expires_at)
                """)


                conn.commit()
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


class ConversationRepository:
    """
    对话仓储 - 处理所有对话和消息相关的数据库操作
    """

    def __init__(self, db: DBConnection):
        """
        初始化对话仓储

        Args:
            db: DBConnection实例
        """
        self.db = db

    def create_conversation(self, conv_id: str, kb_id: str, kb_name: str, title: str) -> str:
        """创建新对话"""
        try:
            self.db.execute_update(
                "INSERT INTO conversations (id, kb_id, kb_name, title, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (conv_id, kb_id, kb_name, title, datetime.now().isoformat(), datetime.now().isoformat())
            )
            return conv_id
        except DatabaseError as e:
            logger.error(f"创建对话失败 (ID: {conv_id}): {str(e)}")
            raise

    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        """获取对话信息"""
        try:
            result = self.db.execute_query(
                "SELECT id, kb_id, kb_name, title, created_at, updated_at, message_count "
                "FROM conversations WHERE id = ?",
                (conv_id,)
            )
            if result:
                return dict(result[0])
            return None
        except DatabaseError as e:
            logger.error(f"获取对话失败 (ID: {conv_id}): {str(e)}")
            raise

    def list_conversations(self, kb_id: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """列出所有对话（可按知识库过滤）"""
        try:
            if kb_id:
                results = self.db.execute_query(
                    "SELECT id, kb_id, kb_name, title, created_at, updated_at, message_count "
                    "FROM conversations WHERE kb_id = ? ORDER BY created_at DESC LIMIT ?",
                    (kb_id, limit)
                )
            else:
                results = self.db.execute_query(
                    "SELECT id, kb_id, kb_name, title, created_at, updated_at, message_count "
                    "FROM conversations ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )

            conversations = []
            for row in results:
                conv_dict = dict(row)
                # 加载消息
                conv_dict["messages"] = self.get_messages(conv_dict["id"])
                conversations.append(conv_dict)

            return conversations
        except DatabaseError as e:
            logger.error(f"列出对话失败: {str(e)}")
            raise

    def get_messages(self, conv_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取对话的所有消息"""
        try:
            if limit:
                results = self.db.execute_query(
                    "SELECT id, role, content, timestamp, confidence, confidence_level, "
                    "response_time_ms, from_cache, is_welcome, error, retrieved_docs, metadata "
                    "FROM conversation_messages WHERE conversation_id = ? "
                    "ORDER BY timestamp ASC LIMIT ?",
                    (conv_id, limit)
                )
            else:
                results = self.db.execute_query(
                    "SELECT id, role, content, timestamp, confidence, confidence_level, "
                    "response_time_ms, from_cache, is_welcome, error, retrieved_docs, metadata "
                    "FROM conversation_messages WHERE conversation_id = ? "
                    "ORDER BY timestamp ASC",
                    (conv_id,)
                )

            messages = []
            for row in results:
                msg_dict = dict(row)
                # 反序列化 JSON 数据
                if msg_dict.get("retrieved_docs"):
                    try:
                        import json
                        msg_dict["retrieved_docs"] = json.loads(msg_dict["retrieved_docs"])
                    except:
                        msg_dict["retrieved_docs"] = []

                if msg_dict.get("metadata"):
                    try:
                        import json
                        msg_dict["metadata"] = json.loads(msg_dict["metadata"])
                    except:
                        msg_dict["metadata"] = {}

                messages.append(msg_dict)

            return messages
        except DatabaseError as e:
            logger.error(f"获取消息失败 (对话ID: {conv_id}): {str(e)}")
            raise

    def add_message(self, msg_id: str, conv_id: str, role: str, content: str, **kwargs) -> str:
        """添加消息到对话"""
        try:
            import json

            # 序列化复杂数据
            retrieved_docs_json = None
            metadata_json = None

            if "retrieved_docs" in kwargs:
                try:
                    retrieved_docs_json = json.dumps(kwargs.pop("retrieved_docs", []))
                except:
                    retrieved_docs_json = None

            if "metadata" in kwargs:
                try:
                    metadata_json = json.dumps(kwargs.pop("metadata", {}))
                except:
                    metadata_json = None

            # 提取其他字段
            confidence = kwargs.pop("confidence", None)
            confidence_level = kwargs.pop("confidence_level", None)
            response_time_ms = kwargs.pop("response_time_ms", None)
            from_cache = kwargs.pop("from_cache", False)
            is_welcome = kwargs.pop("is_welcome", False)
            error = kwargs.pop("error", False)

            self.db.execute_update(
                "INSERT INTO conversation_messages "
                "(id, conversation_id, role, content, timestamp, confidence, confidence_level, "
                "response_time_ms, from_cache, is_welcome, error, retrieved_docs, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (msg_id, conv_id, role, content, datetime.now().isoformat(),
                 confidence, confidence_level, response_time_ms, from_cache, is_welcome, error,
                 retrieved_docs_json, metadata_json)
            )

            # 更新对话的消息计数
            self.db.execute_update(
                "UPDATE conversations SET message_count = message_count + 1, updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), conv_id)
            )

            return msg_id
        except DatabaseError as e:
            logger.error(f"添加消息失败 (消息ID: {msg_id}): {str(e)}")
            raise

    def delete_conversation(self, conv_id: str) -> int:
        """删除对话（级联删除消息）"""
        try:
            return self.db.execute_update(
                "DELETE FROM conversations WHERE id = ?",
                (conv_id,)
            )
        except DatabaseError as e:
            logger.error(f"删除对话失败 (ID: {conv_id}): {str(e)}")
            raise

    def update_conversation_title(self, conv_id: str, new_title: str) -> bool:
        """更新对话标题"""
        try:
            affected = self.db.execute_update(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
                (new_title, datetime.now().isoformat(), conv_id)
            )
            return affected > 0
        except DatabaseError as e:
            logger.error(f"更新对话标题失败 (ID: {conv_id}): {str(e)}")
            raise

    def clear_messages(self, conv_id: str) -> int:
        """清空对话消息"""
        try:
            result = self.db.execute_update(
                "DELETE FROM conversation_messages WHERE conversation_id = ?",
                (conv_id,)
            )

            # 重置消息计数
            self.db.execute_update(
                "UPDATE conversations SET message_count = 0 WHERE id = ?",
                (conv_id,)
            )

            return result
        except DatabaseError as e:
            logger.error(f"清空消息失败 (对话ID: {conv_id}): {str(e)}")
            raise

    def get_conversation_stats(self, conv_id: str) -> Dict[str, Any]:
        """获取对话统计信息"""
        try:
            conv_info = self.get_conversation(conv_id)
            if not conv_info:
                raise DatabaseError(f"对话不存在: {conv_id}")

            msg_count = self.db.execute_query(
                "SELECT COUNT(*) as count FROM conversation_messages WHERE conversation_id = ?",
                (conv_id,)
            )

            count = dict(msg_count[0]).get("count", 0) if msg_count else 0

            return {
                "conv_id": conv_id,
                "title": conv_info["title"],
                "kb_id": conv_info["kb_id"],
                "kb_name": conv_info["kb_name"],
                "message_count": count,
                "created_at": conv_info["created_at"],
                "updated_at": conv_info["updated_at"]
            }
        except DatabaseError as e:
            logger.error(f"获取对话统计失败 (ID: {conv_id}): {str(e)}")
            raise

