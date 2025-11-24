"""
向量数据库客户端 - 与HNSW向量数据库交互
仅支持HNSW后端实现
"""

from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class VectorStoreClient:
    """
    向量数据库客户端 - HNSW实现的薄包装层
    提供统一的向量库操作接口
    """

    def __init__(
        self,
        store_type: str = "hnsw",
        path_or_url: str = "./db/vector_store",
        collection_name: str = "ff_kb_documents",
        embedding_dim: int = 1536,
        hnsw_config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化向量数据库客户端（仅支持HNSW）

        Args:
            store_type: 数据库类型（必须为 'hnsw'）
            path_or_url: HNSW索引文件路径
            collection_name: 集合名称（向后兼容，HNSW不使用）
            embedding_dim: 向量维度
            hnsw_config: HNSW配置
        """
        if store_type != "hnsw":
            raise ValueError(f"仅支持HNSW后端，不支持: {store_type}")

        self.store_type = store_type
        self.path_or_url = path_or_url
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.hnsw_config = hnsw_config or {}
        self.client = None

        self._initialize_client()
        logger.info("HNSW向量数据库客户端已初始化")

    def _initialize_client(self):
        """初始化HNSW客户端"""
        try:
            from .hnsw_vector_store import HNSWVectorStore

            # 准备HNSW配置
            hnsw_path = self.hnsw_config.get(
                "index_path",
                str(Path(self.path_or_url) / "hnsw_index")
            )

            self.client = HNSWVectorStore(
                index_path=hnsw_path,
                embedding_dim=self.embedding_dim,
                max_elements=self.hnsw_config.get("max_elements", 1000000),
                ef_construction=self.hnsw_config.get("ef_construction", 200),
                ef_search=self.hnsw_config.get("ef_search", 50),
                m=self.hnsw_config.get("m", 16),
                distance_metric=self.hnsw_config.get("distance_metric", "l2"),
            )
        except Exception as e:
            logger.error(f"HNSW向量数据库初始化失败: {e}")
            raise

    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        添加文档到向量库

        Args:
            documents: 文本列表
            embeddings: 嵌入向量列表
            metadatas: 元数据列表（可选）
            ids: 文档ID列表（可选）

        Returns:
            添加的文档ID列表
        """
        try:
            return self.client.add_documents(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            raise

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        搜索相似文档

        Args:
            query_embedding: 查询向量
            top_k: 返回的结果数量

        Returns:
            相似文档列表，格式为 [{"id": ..., "content": ..., "score": ..., "metadata": ...}, ...]
        """
        try:
            return self.client.search(
                query_embedding=query_embedding,
                top_k=top_k,
            )
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            raise

    def delete_document(self, doc_id: str) -> bool:
        """
        删除单个文档的向量

        Args:
            doc_id: 文档ID

        Returns:
            是否删除成功
        """
        try:
            return self.client.delete_document(doc_id)
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    def delete_documents_by_metadata(self, metadata_filter: Dict[str, Any]) -> int:
        """
        根据元数据条件删除向量

        Args:
            metadata_filter: 元数据过滤条件（如 {"kb_id": "some-id"}）

        Returns:
            删除的文档数量
        """
        try:
            return self.client.delete_documents_by_metadata(metadata_filter)
        except Exception as e:
            logger.error(f"根据元数据删除文档失败: {e}")
            raise

    def delete_knowledge_base_vectors(self, kb_id: str) -> int:
        """
        删除知识库的所有向量数据

        Args:
            kb_id: 知识库ID

        Returns:
            删除的向量数量
        """
        try:
            return self.client.delete_knowledge_base_vectors(kb_id)
        except Exception as e:
            logger.error(f"删除知识库向量失败: {e}")
            raise

    def clear_collection(self) -> bool:
        """
        清空所有向量

        Returns:
            是否清空成功
        """
        try:
            return self.client.clear_all()
        except Exception as e:
            logger.error(f"清空向量库失败: {e}")
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息

        Returns:
            统计信息
        """
        try:
            return self.client.get_collection_stats()
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}
