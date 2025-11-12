"""
知识库管理器 - 知识库的创建、管理、文档上传、检索等功能
"""

from typing import List, Dict, Any, Optional
import uuid
import logging
from datetime import datetime
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
            kb_id = str(uuid.uuid4())
            kb_info = {
                "id": kb_id,
                "name": name,
                "description": description,
                "tags": tags or [],
                "created_at": datetime.now().isoformat(),
                "document_count": 0,
                "total_chunks": 0,
            }
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
    ) -> Dict[str, Any]:
        """
        上传文档到知识库

        Args:
            kb_id: 知识库 ID
            file_path: 文档文件路径
            metadata: 文档元数据

        Returns:
            文档信息
        """
        try:
            logger.info(f"开始上传文档: kb_id={kb_id}, file_path={file_path}")

            # 处理文档
            chunks = self.doc_processor.process_document(file_path)

            # 生成嵌入
            embeddings = self.embedding_service.embed_texts(chunks)

            # 准备元数据
            doc_id = str(uuid.uuid4())
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

            doc_info = {
                "id": doc_id,
                "kb_id": kb_id,
                "filename": file_path.split("/")[-1],
                "chunk_count": len(chunks),
                "chunk_ids": chunk_ids,
                "created_at": datetime.now().isoformat(),
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
            # TODO: 实现真正的删除逻辑（包括数据库操作）
            logger.info(f"知识库已删除: {kb_id}")
            return True
        except Exception as e:
            logger.error(f"删除知识库失败: {e}")
            return False
