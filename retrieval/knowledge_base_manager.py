"""
知识库管理器 - 知识库的创建、管理、文档上传、检索等功能
"""

import os
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
from utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """
    知识库管理器
    负责知识库的创建、管理、文档上传、检索等操作
    """

    def __init__(self):
        """初始化知识库管理器"""
        self.doc_processor = DocumentProcessor(
            chunk_size=settings.TEXT_CHUNK_SIZE,
            chunk_overlap=settings.TEXT_CHUNK_OVERLAP,
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
        top_k: Optional[int] = None,
        use_postprocessor: bool = True,
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        搜索知识库 - 带后处理和多层缓存的改进版

        缓存策略：
        1. 检索分类缓存（L3）- 问题分类结果（7天 TTL）
        2. Embedding 缓存（L1）- 查询文本的 embedding（24小时 TTL）
        3. 向量搜索结果缓存（可选）

        Args:
            kb_id: 知识库 ID
            query: 查询文本
            top_k: 返回结果数量（为 None 则使用 settings 中的配置）
            use_postprocessor: 是否使用后处理器进行优化
            use_cache: 是否使用缓存

        Returns:
            搜索结果
        """
        # 使用配置的默认值
        if top_k is None:
            top_k = settings.RETRIEVAL_TOP_K

        try:
            logger.info(
                f"搜索知识库: kb_id={kb_id}, query={query[:50]}..., "
                f"top_k={top_k}, postprocessor={use_postprocessor}, "
                f"cache={'enabled' if use_cache else 'disabled'}"
            )

            # 缓存管理器
            cache_manager = get_cache_manager() if use_cache else None

            # 步骤 1: 检查检索分类缓存（L3）- 低频更新的分类信息
            retrieval_classification = None
            if use_cache and cache_manager:
                retrieval_classification = cache_manager.classifier_cache.get_classification(query)
                if retrieval_classification:
                    logger.debug(f"检索分类缓存命中: {retrieval_classification.get('type')}")

            # 如果分类缓存未命中，进行分类（这里简化，实际可调用 RAG 优化器）
            if not retrieval_classification:
                retrieval_classification = {
                    "type": self._classify_query(query),
                    "timestamp": datetime.now().isoformat(),
                }
                if use_cache and cache_manager:
                    cache_manager.classifier_cache.set_classification(query, retrieval_classification)

            # 步骤 2: 生成查询嵌入（会自动使用 L1 缓存）
            query_embedding = self.embedding_service.embed_text(query)

            # 搜索向量数据库（获取更多结果用于后处理）
            # 策略：向量库获取更多结果，然后用后处理器精选
            retrieval_top_k = max(top_k * settings.RETRIEVAL_FETCH_MULTIPLIER, 15)

            results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=retrieval_top_k,
            )

            # 后处理流程
            if use_postprocessor:
                from .retrieval_postprocessor import RetrievalPostProcessor

                postprocessor = RetrievalPostProcessor(
                    similarity_threshold=settings.RETRIEVAL_SIMILARITY_THRESHOLD,
                    dedup_threshold=settings.RETRIEVAL_DEDUP_THRESHOLD,
                    top_k=top_k,
                )

                # 后处理：过滤 + 去重 + 重排
                processed_results = postprocessor.process(
                    results=results,
                    kb_id=kb_id,
                    query=query,
                )

                logger.info(
                    f"搜索完成: "
                    f"原始 {len(results)} 个 → "
                    f"处理后 {len(processed_results)} 个结果 "
                    f"(classification={retrieval_classification.get('type')}, "
                    f"cache={'hit' if retrieval_classification.get('from_cache') else 'miss'})"
                )

                return processed_results
            else:
                # 降级：仅做基本过滤
                filtered_results = [
                    r for r in results
                    if r.get("metadata", {}).get("kb_id") == kb_id
                ]

                logger.info(f"搜索完成: 返回 {len(filtered_results)} 个结果")
                return filtered_results[:top_k]

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            raise

    def _classify_query(self, query: str) -> str:
        """
        简单的查询分类 - 根据问题关键词进行分类
        可以扩展为更复杂的分类逻辑（如调用 LLM）

        Returns:
            分类类型 (factual, explanation, procedural, etc.)
        """
        query_lower = query.lower()

        # 事实性问题
        if any(keyword in query_lower for keyword in ['什么是', '什么', '定义', 'what is', 'definition']):
            return "factual"

        # 解释性问题
        if any(keyword in query_lower for keyword in ['为什么', '如何', '怎样', 'why', 'how', 'explain']):
            return "explanatory"

        # 操作性问题
        if any(keyword in query_lower for keyword in ['步骤', '步骤', '教程', 'step', 'guide', 'tutorial']):
            return "procedural"

        # 对比性问题
        if any(keyword in query_lower for keyword in ['vs', '对比', '区别', 'difference', 'compare', 'vs']):
            return "comparative"

        # 默认分类
        return "general"

    def delete_knowledge_base(self, kb_id: str) -> bool:
        """
        彻底删除知识库

        完整删除流程（四层清理）:
        1. SQLite 数据库: 文本分块、文档、知识库记录
        2. 向量数据库: 删除该知识库的所有向量数据
        3. 临时文件: 删除上传的原始文档文件
        4. 分块文件: 删除处理后的分块文本文件

        Args:
            kb_id: 知识库 ID

        Returns:
            是否删除成功
        """
        try:
            import shutil

            logger.info(f"开始删除知识库: {kb_id}")

            # 步骤 1: 获取知识库中的所有文档信息（包括临时文件和分块文件路径）
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            try:
                # 获取知识库中的所有文档信息
                cursor.execute("""
                    SELECT id, temp_path FROM documents WHERE kb_id = ?
                """, (kb_id,))
                docs_info = cursor.fetchall()
                logger.info(f"知识库包含 {len(docs_info)} 个文档")
            finally:
                conn.close()

            # 步骤 2: 从 SQLite 数据库删除知识库相关的所有数据（使用事务保证一致性）
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                conn.execute("BEGIN TRANSACTION")

                # 删除文本块
                cursor.execute("DELETE FROM text_chunks WHERE kb_id = ?", (kb_id,))
                chunks_deleted = cursor.rowcount
                logger.info(f"已删除 {chunks_deleted} 个文本分块")

                # 删除文档
                cursor.execute("DELETE FROM documents WHERE kb_id = ?", (kb_id,))
                docs_deleted = cursor.rowcount
                logger.info(f"已删除 {docs_deleted} 个文档记录")

                # 删除知识库
                cursor.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))
                kb_deleted = cursor.rowcount
                logger.info(f"已删除知识库记录")

                conn.commit()
                logger.info("数据库事务提交成功")
            except Exception as e:
                conn.rollback()
                logger.error(f"数据库事务回滚: {e}")
                raise
            finally:
                conn.close()

            # 步骤 3: 从向量数据库删除知识库的所有向量数据
            vector_deleted_count = 0
            try:
                if hasattr(self, 'vector_store') and self.vector_store:
                    vector_deleted_count = self.vector_store.delete_knowledge_base_vectors(kb_id)
                    logger.info(f"向量数据库中已删除 {vector_deleted_count} 个向量")
            except Exception as e:
                logger.warning(f"删除向量数据失败（可能数据库不存在或已清空）: {e}")

            # 步骤 4: 删除临时文件（上传的原始文档）
            temp_files_deleted = 0
            try:
                for doc_id, temp_path in docs_info:
                    if temp_path and os.path.exists(temp_path):
                        os.remove(temp_path)
                        temp_files_deleted += 1
                        logger.info(f"临时文件已删除: {temp_path}")

                logger.info(f"共删除 {temp_files_deleted} 个临时文件")
            except Exception as e:
                logger.warning(f"删除临时文件失败（不影响整体删除）: {e}")

            # 步骤 5: 删除分块文件（处理后的分块文本）
            chunks_files_deleted = 0
            try:
                processed_chunks_path = settings.PROCESSED_CHUNKS_PATH
                if processed_chunks_path and os.path.exists(processed_chunks_path):
                    # 列出分块文件夹中的所有文件，查找属于该kb的分块
                    for filename in os.listdir(processed_chunks_path):
                        # 分块文件名格式: {timestamp}_{filename}_{uuid}_chunk_{index}.txt
                        # 我们需要从元数据中查找属于该知识库的分块文件
                        file_path = os.path.join(processed_chunks_path, filename)

                        # 尝试从文件元数据或内容识别属于该知识库的文件
                        # 简单方案：删除该知识库内所有文档对应的分块
                        for doc_id, _ in docs_info:
                            if doc_id in filename:
                                try:
                                    os.remove(file_path)
                                    chunks_files_deleted += 1
                                    logger.info(f"分块文件已删除: {file_path}")
                                except Exception as e:
                                    logger.warning(f"删除分块文件失败: {file_path}, 错误: {e}")
                                break

                logger.info(f"共删除 {chunks_files_deleted} 个分块文件")
            except Exception as e:
                logger.warning(f"删除分块文件失败（不影响整体删除）: {e}")

            logger.info(f"""
知识库删除完成 (ID: {kb_id})
- 数据库记录: ✓ ({chunks_deleted} 个分块 + {docs_deleted} 个文档 + 1 个知识库)
- 向量数据: ✓ ({vector_deleted_count} 个向量)
- 临时文件: ✓ ({temp_files_deleted} 个文件)
- 分块文件: ✓ ({chunks_files_deleted} 个文件)
            """)
            return True

        except Exception as e:
            logger.error(f"删除知识库失败: {e}", exc_info=True)
            return False

    def delete_document(self, doc_id: str) -> bool:
        """
        彻底删除文档

        完整删除流程（四层清理）:
        1. SQLite 数据库: 删除文档及其关联的文本分块和元数据
        2. 向量数据库: 删除该文档的所有向量数据
        3. 临时文件: 删除上传的原始文档文件
        4. 分块文件: 删除处理后的分块文本文件

        Args:
            doc_id: 文档 ID

        Returns:
            是否删除成功
        """
        try:
            logger.info(f"开始删除文档: {doc_id}")

            # 步骤 1: 检查文档是否存在并获取相关信息
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    SELECT id, kb_id, filename, temp_path FROM documents WHERE id = ?
                """, (doc_id,))
                doc_info = cursor.fetchone()
                if not doc_info:
                    logger.error(f"文档不存在: {doc_id}")
                    return False

                doc_id, kb_id, filename, temp_path = doc_info
                logger.info(f"找到文档: {filename} (kb_id: {kb_id})")
            finally:
                conn.close()

            # 步骤 2: 从 SQLite 数据库删除文档相关的所有数据（使用事务保证一致性）
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                conn.execute("BEGIN TRANSACTION")

                # 删除文本块
                cursor.execute("DELETE FROM text_chunks WHERE document_id = ?", (doc_id,))
                chunks_deleted = cursor.rowcount
                logger.info(f"已删除 {chunks_deleted} 个文本分块")

                # 删除文档本身
                cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                docs_deleted = cursor.rowcount
                logger.info(f"已删除文档记录")

                # 更新知识库统计信息
                cursor.execute("""
                    UPDATE knowledge_bases
                    SET document_count = document_count - 1,
                        total_chunks = (
                            SELECT COUNT(*) FROM text_chunks WHERE kb_id = ?
                        ),
                        updated_at = ?
                    WHERE id = ?
                """, (kb_id, datetime.now().isoformat(), kb_id))

                conn.commit()
                logger.info("数据库事务提交成功")
            except Exception as e:
                conn.rollback()
                logger.error(f"数据库事务回滚: {e}")
                raise
            finally:
                conn.close()

            # 步骤 3: 从向量数据库删除文档的所有向量数据
            vector_deleted = False
            try:
                if hasattr(self, 'vector_store') and self.vector_store:
                    self.vector_store.delete_document(doc_id)
                    vector_deleted = True
                    logger.info(f"向量数据库中已删除该文档的向量")
            except Exception as e:
                logger.warning(f"删除向量数据失败（可能数据库不存在）: {e}")

            # 步骤 4: 删除临时文件（上传的原始文档）
            temp_file_deleted = False
            try:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
                    temp_file_deleted = True
                    logger.info(f"临时文件已删除: {temp_path}")
                else:
                    logger.info(f"临时文件不存在或路径为空: {temp_path}")
            except Exception as e:
                logger.warning(f"删除临时文件失败（不影响整体删除）: {e}")

            # 步骤 5: 删除分块文件（处理后的分块文本）
            chunks_files_deleted = 0
            try:
                processed_chunks_path = settings.PROCESSED_CHUNKS_PATH
                if processed_chunks_path and os.path.exists(processed_chunks_path):
                    # 删除属于该文档的所有分块文件
                    for filename_item in os.listdir(processed_chunks_path):
                        # 分块文件名格式: {timestamp}_{original_filename}_{doc_id}_chunk_{index}.txt
                        # 我们通过 doc_id 来匹配
                        if doc_id in filename_item:
                            file_path = os.path.join(processed_chunks_path, filename_item)
                            try:
                                os.remove(file_path)
                                chunks_files_deleted += 1
                                logger.info(f"分块文件已删除: {file_path}")
                            except Exception as e:
                                logger.warning(f"删除分块文件失败: {file_path}, 错误: {e}")

                logger.info(f"共删除 {chunks_files_deleted} 个分块文件")
            except Exception as e:
                logger.warning(f"删除分块文件失败（不影响整体删除）: {e}")

            logger.info(f"""
文档删除完成 (ID: {doc_id}, 文件名: {filename})
- 数据库记录: ✓ ({chunks_deleted} 个分块 + 1 个文档)
- 向量数据: ✓ ({vector_deleted})
- 临时文件: ✓ ({temp_file_deleted})
- 分块文件: ✓ ({chunks_files_deleted} 个文件)
            """)
            return True

        except Exception as e:
            logger.error(f"删除文档失败: {e}", exc_info=True)
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
