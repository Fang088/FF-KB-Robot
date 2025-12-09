"""
KB 仓储层 - 处理知识库的数据库操作

功能：
1. 知识库的创建、查询、更新、删除
2. 文档信息的持久化
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from db import DBConnection, KBRepository, DocumentRepository

logger = logging.getLogger(__name__)


class KBStore:
    """
    知识库仓储 - 处理知识库的数据库操作

    建议的使用方式：
        store = KBStore(db_path)
        kb_info = store.create_kb(name, description)
        store.add_document(kb_id, doc_id, filename, chunk_count)
    """

    def __init__(self, db_path: str):
        """
        初始化KB仓储

        Args:
            db_path: 数据库文件路径
        """
        self.db = DBConnection(db_path)  # auto_init=True by default，自动初始化所有表
        self.kb_repo = KBRepository(self.db)
        self.doc_repo = DocumentRepository(self.db)
        logger.info(f"KB仓储已初始化: {db_path}")

    def create_kb(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """创建知识库"""
        try:
            kb_id = str(uuid.uuid4())
            now = datetime.now()

            with self.db.session() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO knowledge_bases
                    (id, name, description, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    kb_id,
                    name,
                    description,
                    ",".join(tags) if tags else None,
                    now.isoformat(),
                    now.isoformat()
                ))
                conn.commit()

            logger.info(f"知识库已创建: {kb_id} - {name}")
            return {
                "id": kb_id,
                "name": name,
                "description": description,
                "tags": tags or [],
                "created_at": now.isoformat(),
                "document_count": 0,
                "total_chunks": 0,
            }
        except Exception as e:
            logger.error(f"创建知识库失败: {e}")
            raise

    def get_kb(self, kb_id: str) -> Optional[Dict[str, Any]]:
        """获取知识库信息"""
        try:
            kb_info = self.kb_repo.get_knowledge_base(kb_id)
            if not kb_info:
                return None
            # 补充统计信息
            stats = self.get_kb_stats(kb_id)
            if stats:
                kb_info['document_count'] = stats.get('document_count', 0)
                kb_info['total_chunks'] = stats.get('total_chunks', 0)
                kb_info['updated_at'] = stats.get('updated_at', kb_info.get('created_at'))
            else:
                kb_info['document_count'] = 0
                kb_info['total_chunks'] = 0
                kb_info['updated_at'] = kb_info.get('created_at')
            return kb_info
        except Exception as e:
            logger.error(f"获取知识库失败: {e}")
            return None

    def list_kbs(self) -> List[Dict[str, Any]]:
        """列出所有知识库"""
        try:
            kbs = self.kb_repo.list_knowledge_bases()
            # 补充统计信息
            for kb in kbs:
                kb_id = kb.get('id')
                stats = self.get_kb_stats(kb_id)
                if stats:
                    kb['document_count'] = stats.get('document_count', 0)
                    kb['total_chunks'] = stats.get('total_chunks', 0)
                else:
                    kb['document_count'] = 0
                    kb['total_chunks'] = 0
            return kbs
        except Exception as e:
            logger.error(f"列出知识库失败: {e}")
            return []

    def add_document(
        self,
        kb_id: str,
        doc_id: str,
        filename: str,
        file_path: str,
        chunk_count: int,
    ) -> bool:
        """添加文档记录到知识库"""
        try:
            # 保存文档，传递完整参数包括 doc_id
            self.doc_repo.save_document(doc_id, kb_id, filename, file_path, chunk_count)

            # 更新知识库统计
            now = datetime.now()
            with self.db.session() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE knowledge_bases
                    SET document_count = document_count + 1,
                        total_chunks = total_chunks + ?,
                        updated_at = ?
                    WHERE id = ?
                """, (chunk_count, now.isoformat(), kb_id))
                conn.commit()

            logger.debug(f"文档已添加到知识库: {kb_id}/{filename}")
            return True
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            return False

    def delete_kb(self, kb_id: str) -> bool:
        """删除知识库"""
        try:
            # 删除关联的文档
            with self.db.session() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM text_chunks WHERE kb_id = ?", (kb_id,))
                cursor.execute("DELETE FROM documents WHERE kb_id = ?", (kb_id,))
                cursor.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))
                conn.commit()

            logger.info(f"知识库已删除: {kb_id}")
            return True
        except Exception as e:
            logger.error(f"删除知识库失败: {e}")
            return False

    def get_kb_stats(self, kb_id: str) -> Optional[Dict[str, Any]]:
        """获取知识库统计信息"""
        try:
            return self.kb_repo.get_kb_stats(kb_id)
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return None
