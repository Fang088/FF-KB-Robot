"""
知识库管理器 - 知识库的创建、管理、文档上传、检索等功能
"""

from typing import List, Dict, Any, Optional
import uuid
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from .document_processor import DocumentProcessor
from .vector_store_client import VectorStoreClient
from models.embedding_service import EmbeddingService
from config.settings import settings

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """
    知识库管理器
    负责知识库的创建、管理、文档上传、检索等操作
    """

    def __init__(self):
        """初始化知识库管理器"""
        self.doc_processor = DocumentProcessor(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
        )
        self.embedding_service = EmbeddingService(
            provider=settings.EMBEDDING_PROVIDER,
            api_key=settings.EMBEDDING_API_KEY,
            api_base=settings.EMBEDDING_API_BASE,
            model_name=settings.EMBEDDING_MODEL_NAME,
        )
        self.vector_store = VectorStoreClient(
            store_type=settings.VECTOR_STORE_TYPE,
            path_or_url=settings.VECTOR_STORE_PATH,
            collection_name=settings.VECTOR_STORE_COLLECTION_NAME,
        )

        # 数据库连接
        self.db_path = str(settings.PROJECT_ROOT / settings.DATABASE_URL.replace("sqlite:///./", ""))
        self._initialize_db()

        logger.info("知识库管理器已初始化")

    def _initialize_db(self):
        """确保数据库表存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # 确保知识库表存在
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
            conn.commit()
        except Exception as e:
            logger.error(f"初始化数据库表失败: {e}")
            raise
        finally:
            conn.close()

    def create_knowledge_base(
        self,
        name: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        创建知识库

        Args:
            name: 知识库名称
            description: 知识库描述
            tags: 标签列表

        Returns:
            知识库信息
        """
        try:
            kb_id = str(uuid.uuid4())
            created_at = datetime.now()

            # 准备知识库信息
            kb_info = {
                "id": kb_id,
                "name": name,
                "description": description,
                "tags": tags or [],
                "created_at": created_at.isoformat(),
                "document_count": 0,
                "total_chunks": 0,
            }

            # 存储到数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO knowledge_bases
                    (id, name, description, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    kb_id,
                    name,
                    description,
                    ",".join(tags) if tags else None,
                    created_at.isoformat(),
                    created_at.isoformat()
                ))
                conn.commit()
            finally:
                conn.close()

            logger.info(f"知识库已创建: {kb_id} - {name}")
            return kb_info
        except Exception as e:
            logger.error(f"创建知识库失败: {e}")
            raise

    def upload_document(
        self,
        kb_id: str,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        save_to_temp: bool = True,
        save_chunks: bool = True,
    ) -> Dict[str, Any]:
        """
        上传文档到知识库

        Args:
            kb_id: 知识库 ID
            file_path: 文档文件路径
            metadata: 文档元数据
            save_to_temp: 是否保存原始文件到临时目录
            save_chunks: 是否保存处理后的分块到processed_chunks目录

        Returns:
            文档信息
        """
        try:
            logger.info(f"开始上传文档: kb_id={kb_id}, file_path={file_path}")

            # 保存原始文件到临时目录
            temp_file_path = None
            if save_to_temp:
                from config.settings import settings
                import os
                import shutil

                # 确保目录存在
                os.makedirs(settings.TEMP_UPLOAD_PATH, exist_ok=True)

                # 生成唯一的文件名
                filename = os.path.basename(file_path)
                unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                temp_file_path = os.path.join(settings.TEMP_UPLOAD_PATH, unique_filename)

                # 复制文件
                shutil.copyfile(file_path, temp_file_path)
                logger.info(f"原始文件已保存到临时目录: {temp_file_path}")

            # 处理文档
            chunks = self.doc_processor.process_document(file_path, save_chunks=save_chunks)

            # 生成嵌入
            embeddings = self.embedding_service.embed_texts(chunks)

            # 准备元数据
            doc_id = str(uuid.uuid4())
            created_at = datetime.now()

            # 上传到向量数据库
            metadatas = [
                {
                    "kb_id": kb_id,
                    "doc_id": doc_id,
                    "chunk_index": i,
                    "filename": file_path.split("/")[-1],
                    **(metadata or {}),
                }
                for i in range(len(chunks))
            ]

            # 添加到向量数据库
            chunk_ids = self.vector_store.add_documents(
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )

            # 更新数据库记录
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                # 插入文档记录
                cursor.execute("""
                    INSERT INTO documents
                    (id, kb_id, filename, temp_path, chunk_count, metadata, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    kb_id,
                    file_path.split("/")[-1],
                    temp_file_path,
                    len(chunks),
                    str(metadata),
                    created_at.isoformat(),
                    created_at.isoformat()
                ))

                # 更新知识库统计信息
                cursor.execute("""
                    UPDATE knowledge_bases
                    SET document_count = document_count + 1,
                        total_chunks = total_chunks + ?,
                        updated_at = ?
                    WHERE id = ?
                """, (len(chunks), created_at.isoformat(), kb_id))

                conn.commit()
            finally:
                conn.close()

            doc_info = {
                "id": doc_id,
                "kb_id": kb_id,
                "filename": file_path.split("/")[-1],
                "original_path": file_path,
                "temp_path": temp_file_path,
                "chunk_count": len(chunks),
                "chunk_ids": chunk_ids,
                "created_at": created_at.isoformat(),
                "metadata": metadata,
            }

            logger.info(f"文档上传成功: {doc_id}, {len(chunks)} 个分块")
            return doc_info

        except Exception as e:
            logger.error(f"上传文档失败: {e}")
            raise

    def search(
        self,
        kb_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        搜索知识库

        Args:
            kb_id: 知识库 ID
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            搜索结果
        """
        try:
            logger.info(f"搜索知识库: kb_id={kb_id}, query={query}, top_k={top_k}")

            # 生成查询嵌入
            query_embedding = self.embedding_service.embed_text(query)

            # 搜索向量数据库
            results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k,
            )

            # 过滤结果（只保留相同知识库的文档）
            filtered_results = [
                r for r in results
                if r.get("metadata", {}).get("kb_id") == kb_id
            ]

            logger.info(f"搜索完成: 返回 {len(filtered_results)} 个结果")
            return filtered_results

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            raise

    def delete_knowledge_base(self, kb_id: str) -> bool:
        """
        删除知识库

        Args:
            kb_id: 知识库 ID

        Returns:
            是否删除成功
        """
        try:
            # 1. 从数据库中删除知识库相关的所有数据
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                # 开始事务
                conn.execute("BEGIN TRANSACTION")

                # 删除文本块
                cursor.execute("DELETE FROM text_chunks WHERE kb_id = ?", (kb_id,))
                # 删除文档
                cursor.execute("DELETE FROM documents WHERE kb_id = ?", (kb_id,))
                # 删除知识库本身
                cursor.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))

                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

            # 2. 从向量存储中删除知识库相关的所有向量
            try:
                # 对于chroma向量存储，直接删除整个知识库目录
                import shutil
                import os
                vector_kb_path = os.path.join(self.vector_store_path, kb_id)
                if os.path.exists(vector_kb_path):
                    shutil.rmtree(vector_kb_path)
            except Exception as e:
                logger.warning(f"删除向量存储失败（不影响整体删除）: {e}")

            logger.info(f"知识库已删除: {kb_id}")
            return True
        except Exception as e:
            logger.error(f"删除知识库失败: {e}")
            return False

    def delete_document(self, doc_id: str) -> bool:
        """
        删除文档

        Args:
            doc_id: 文档 ID

        Returns:
            是否删除成功
        """
        try:
            # 1. 检查文档是否存在
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT id, kb_id, filename FROM documents WHERE id = ?", (doc_id,))
                doc_info = cursor.fetchone()
                if not doc_info:
                    logger.error(f"文档不存在: {doc_id}")
                    return False
                doc_id, kb_id, filename = doc_info
            finally:
                conn.close()

            # 2. 从数据库中删除文档相关的所有数据
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                # 开始事务
                conn.execute("BEGIN TRANSACTION")

                # 删除文本块
                cursor.execute("DELETE FROM text_chunks WHERE document_id = ?", (doc_id,))

                # 删除文档本身
                cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))

                # 更新知识库的文档数和总块数
                cursor.execute("""
                    UPDATE knowledge_bases
                    SET document_count = document_count - 1,
                        total_chunks = (
                            SELECT COUNT(*) FROM text_chunks WHERE kb_id = ?
                        )
                    WHERE id = ?
                """, (kb_id, kb_id))

                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()

            # 3. 从向量存储中删除文档相关的所有向量
            try:
                self.embedding_service.vector_store.delete_document(doc_id)
            except Exception as e:
                logger.warning(f"删除向量存储失败（不影响整体删除）: {e}")

            logger.info(f"文档已删除: {filename} (ID: {doc_id})")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    def check_kb_exists(self, kb_id: str) -> bool:
        """
        检查知识库 ID 是否存在

        Args:
            kb_id: 知识库 ID

        Returns:
            是否存在
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT id FROM knowledge_bases WHERE id = ?", (kb_id,))
                result = cursor.fetchone()
                return result is not None
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"检查知识库是否存在失败: {e}")
            return False

    def get_all_kbs(self) -> List[Dict[str, Any]]:
        """
        获取所有知识库列表

        Returns:
            知识库列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM knowledge_bases ORDER BY created_at DESC")
                rows = cursor.fetchall()

                kbs = []
                for row in rows:
                    kbs.append({
                        "id": row[0],
                        "name": row[1],
                        "description": row[2],
                        "tags": row[3].split(",") if row[3] else [],
                        "created_at": row[4],
                        "updated_at": row[5],
                        "document_count": row[6],
                        "total_chunks": row[7]
                    })
                return kbs
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"获取知识库列表失败: {e}")
            return []
