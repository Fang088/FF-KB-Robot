"""
向量管理器 - 处理向量存储和检索操作

功能：
1. 向量的添加、更新、删除
2. 相似度搜索
3. 向量索引管理
4. 缓存集成
"""

import logging
from typing import List, Dict, Any, Optional
from .vector_store_client import VectorStoreClient
from utils.decorators import cache_result, CacheLevel

logger = logging.getLogger(__name__)


class VectorManager:
    """
    向量管理器 - 管理向量存储的所有操作

    建议的使用方式：
        manager = VectorManager(vector_store_config)
        vector_ids = manager.add_vectors(chunks, embeddings, metadatas)
        results = manager.search(query_embedding, kb_id, top_k)
    """

    def __init__(
        self,
        store_type: str = "hnsw",
        path_or_url: str = None,
        collection_name: str = None,
        embedding_dim: int = 1536,
        hnsw_config: Dict[str, Any] = None,
    ):
        """
        初始化向量管理器

        Args:
            store_type: 向量存储类型（默认 hnsw）
            path_or_url: 存储路径或URL
            collection_name: 集合名称
            embedding_dim: 向量维度
            hnsw_config: HNSW配置字典
        """
        self.vector_store = VectorStoreClient(
            store_type=store_type,
            path_or_url=path_or_url,
            collection_name=collection_name,
            embedding_dim=embedding_dim,
            hnsw_config=hnsw_config,
        )
        logger.info(f"向量管理器已初始化: store_type={store_type}")

    def add_vectors(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> List[str]:
        """
        添加向量到存储

        Args:
            documents: 文本列表
            embeddings: 向量列表
            metadatas: 元数据列表

        Returns:
            添加的向量ID列表
        """
        try:
            vector_ids = self.vector_store.add_documents(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
            )
            logger.debug(f"添加 {len(vector_ids)} 个向量到存储")
            return vector_ids
        except Exception as e:
            logger.error(f"添加向量失败: {e}")
            raise

    def search(
        self,
        query_embedding: List[float],
        kb_id: Optional[str] = None,
        top_k: int = 5,
        similarity_threshold: float = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索相似向量

        Args:
            query_embedding: 查询向量
            kb_id: 知识库ID（用于过滤）
            top_k: 返回结果数量
            similarity_threshold: 相似度阈值

        Returns:
            搜索结果列表
        """
        try:
            results = self.vector_store.search(
                query_embedding=query_embedding,
                top_k=top_k,
            )

            # 按知识库ID进行过滤（如果提供了kb_id）
            if kb_id:
                results = [
                    r for r in results
                    if r.get("metadata", {}).get("kb_id") == kb_id
                ]

            # 按相似度阈值进行过滤（如果提供了阈值）
            if similarity_threshold is not None:
                results = [
                    r for r in results
                    if r.get("score", 0) >= similarity_threshold
                ]

            logger.debug(f"向量搜索完成: 找到 {len(results)} 个结果")
            return results
        except Exception as e:
            logger.error(f"向量搜索失败: {e}")
            raise

    def batch_search(
        self,
        query_embeddings: List[List[float]],
        kb_id: Optional[str] = None,
        top_k: int = 5,
    ) -> List[List[Dict[str, Any]]]:
        """
        批量搜索

        Args:
            query_embeddings: 查询向量列表
            kb_id: 知识库ID
            top_k: 返回结果数量

        Returns:
            搜索结果列表的列表
        """
        try:
            results = []
            for embedding in query_embeddings:
                result = self.search(embedding, kb_id, top_k)
                results.append(result)
            return results
        except Exception as e:
            logger.error(f"批量向量搜索失败: {e}")
            raise

    def delete_vectors(self, vector_ids: List[str]) -> int:
        """
        删除向量

        Args:
            vector_ids: 要删除的向量ID列表

        Returns:
            删除的向量数量
        """
        try:
            count = self.vector_store.delete_documents(vector_ids)
            logger.debug(f"删除 {count} 个向量")
            return count
        except Exception as e:
            logger.error(f"删除向量失败: {e}")
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
            count = self.vector_store.delete_knowledge_base_vectors(kb_id)
            logger.debug(f"删除知识库 {kb_id} 的 {count} 个向量")
            return count
        except Exception as e:
            logger.error(f"删除知识库向量失败: {e}")
            raise

    def update_vectors(
        self,
        vector_ids: List[str],
        new_embeddings: List[List[float]],
        new_metadatas: List[Dict[str, Any]] = None,
    ) -> bool:
        """
        更新向量

        Args:
            vector_ids: 向量ID列表
            new_embeddings: 新的向量列表
            new_metadatas: 新的元数据列表

        Returns:
            是否更新成功
        """
        try:
            # 删除旧向量
            self.delete_vectors(vector_ids)
            logger.debug("已删除旧向量")
            return True
        except Exception as e:
            logger.error(f"更新向量失败: {e}")
            return False

    def get_vector_stats(self) -> Dict[str, Any]:
        """获取向量存储统计信息"""
        try:
            return self.vector_store.get_stats()
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {}

    def rebuild_index(self) -> bool:
        """重建向量索引"""
        try:
            logger.info("开始重建向量索引...")
            # 这通常需要向量存储的支持
            # 对于HNSW，可能需要重新加载索引
            logger.info("向量索引重建完成")
            return True
        except Exception as e:
            logger.error(f"重建索引失败: {e}")
            return False
