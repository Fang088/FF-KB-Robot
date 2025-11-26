"""
知识库管理器 - 知识库的创建、管理、文档上传、检索等功能
"""

import os
from typing import List, Dict, Any, Optional
import uuid
import logging
from datetime import datetime
from pathlib import Path
from .document_processor import DocumentProcessor
from .vector_manager import VectorManager
from .retrieval_postprocessor import RetrievalPostProcessor
from .kb_store import KBStore
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
        # 准备向量存储配置
        hnsw_config = {}
        if settings.VECTOR_STORE_TYPE == "hnsw":
            hnsw_config = {
                # HNSW 索引路径应与 VECTOR_STORE_PATH 相同
                # 索引文件 (hnsw.bin, metadata.json) 直接存储在该目录下
                "index_path": settings.HNSW_INDEX_PATH,
                "max_elements": settings.HNSW_MAX_ELEMENTS,
                "ef_construction": settings.HNSW_EF_CONSTRUCTION,
                "ef_search": settings.HNSW_EF_SEARCH,
                "m": settings.HNSW_M,
                "distance_metric": settings.HNSW_DISTANCE_METRIC,
            }

        # 使用 VectorManager 而不是直接使用 VectorStoreClient
        self.vector_manager = VectorManager(
            store_type=settings.VECTOR_STORE_TYPE,
            path_or_url=settings.VECTOR_STORE_PATH,
            collection_name=settings.VECTOR_STORE_COLLECTION_NAME,
            embedding_dim=settings.EMBEDDING_DIMENSION,
            hnsw_config=hnsw_config,
        )

        # 初始化 KB 仓储 - 用于数据库操作
        self.db_path = str(settings.PROJECT_ROOT / settings.DATABASE_URL.replace("sqlite:///./", ""))
        self.kb_store = KBStore(self.db_path)

        # 初始化后处理器
        self.postprocessor = RetrievalPostProcessor()

        logger.info("知识库管理器已初始化")

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
            # 使用 KBStore 创建知识库
            kb_info = self.kb_store.create_kb(
                name=name,
                description=description,
                tags=tags,
            )
            logger.info(f"知识库已创建: {kb_info['id']} - {name}")
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
            chunk_ids = self.vector_manager.add_vectors(
                documents=chunks,
                embeddings=embeddings,
                metadatas=metadatas,
            )

            # 更新数据库记录
            self.kb_store.add_document(
                kb_id=kb_id,
                doc_id=doc_id,
                filename=file_path.split("/")[-1],
                file_path=temp_file_path or file_path,
                chunk_count=len(chunks),
            )

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

            results = self.vector_manager.search(
                query_embedding=query_embedding,
                kb_id=kb_id,
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
            kb_info = self.kb_store.get_kb(kb_id)
            if not kb_info:
                logger.error(f"知识库不存在: {kb_id}")
                return False

            # 获取知识库中的所有文档
            docs_info = self.kb_store.db.doc_repo.get_documents_by_kb(kb_id)
            logger.info(f"知识库包含 {len(docs_info)} 个文档")

            # 步骤 2: 从数据库删除知识库（KBStore 会级联删除关联数据）
            if self.kb_store.delete_kb(kb_id):
                logger.info("数据库中的知识库已删除")
                chunks_deleted = len([d for d in docs_info])  # 估计删除数量
                docs_deleted = len(docs_info)
            else:
                logger.error("数据库删除失败")
                return False

            # 步骤 3: 从向量数据库删除知识库的所有向量数据
            vector_deleted_count = 0
            try:
                if hasattr(self, 'vector_manager') and self.vector_manager:
                    vector_deleted_count = self.vector_manager.delete_knowledge_base_vectors(kb_id)
                    logger.info(f"向量数据库中已删除 {vector_deleted_count} 个向量")
            except Exception as e:
                logger.warning(f"删除向量数据失败（可能数据库不存在或已清空）: {e}")

            # 步骤 4: 删除临时文件（上传的原始文档）
            temp_files_deleted = 0
            try:
                for doc_info in docs_info:
                    temp_path = doc_info.get('temp_path') or doc_info.get('path')
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
                        for doc in docs_info:
                            doc_id = doc.get('id')
                            if doc_id and doc_id in filename:
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
            docs = self.kb_store.db.doc_repo.get_documents_by_id(doc_id)
            if not docs or len(docs) == 0:
                logger.error(f"文档不存在: {doc_id}")
                return False

            doc_info = docs[0]
            kb_id = doc_info.get('kb_id')
            filename = doc_info.get('filename')
            temp_path = doc_info.get('temp_path') or doc_info.get('path')
            logger.info(f"找到文档: {filename} (kb_id: {kb_id})")

            # 步骤 2: 从数据库删除文档及其关联数据
            # 首先获取分块数量用于统计
            chunks_info = self.kb_store.db.chunk_repo.get_chunks_by_doc(doc_id) if hasattr(self.kb_store.db, 'chunk_repo') else []
            chunks_deleted = len(chunks_info)

            # 删除文档（KBStore 会级联删除关联的分块）
            # TODO: 需要实现 delete_document 方法在 DocumentRepository
            # 暂时使用直接 SQL 删除
            try:
                with self.kb_store.db.session() as conn:
                    cursor = conn.cursor()
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
                logger.error(f"数据库删除失败: {e}")
                raise

            # 步骤 3: 从向量数据库删除文档的所有向量数据
            vector_deleted = False
            try:
                if hasattr(self, 'vector_manager') and self.vector_manager:
                    self.vector_manager.delete_vectors([doc_id])
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
            kb_info = self.kb_store.get_kb(kb_id)
            return kb_info is not None
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
            return self.kb_store.list_kbs()
        except Exception as e:
            logger.error(f"获取知识库列表失败: {e}")
            return []

    def get_kb_documents(self, kb_id: str) -> List[Dict[str, Any]]:
        """
        获取知识库中的所有文档列表

        Args:
            kb_id: 知识库 ID

        Returns:
            文档列表，每个文档包含 id, filename, chunk_count, created_at, temp_path 等信息
        """
        try:
            # 使用数据库连接直接查询文档信息
            with self.kb_store.db.session() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, filename, chunk_count, created_at FROM documents WHERE kb_id = ? ORDER BY created_at DESC",
                    (kb_id,)
                )
                rows = cursor.fetchall()

                documents = []
                for row in rows:
                    documents.append({
                        "id": row[0],
                        "filename": row[1],
                        "chunk_count": row[2],
                        "created_at": row[3],
                    })
                return documents
        except Exception as e:
            logger.error(f"获取文档列表失败: {e}")
            return []
