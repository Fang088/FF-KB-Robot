"""
精简检索模块 - 统一的检索接口
整合 HNSW 索引、多层缓存和后处理的一体化解决方案
"""

import logging
from typing import List, Dict, Any, Optional
from .knowledge_base_manager import KnowledgeBaseManager
from models.embedding_service import EmbeddingService
from config.settings import settings
from utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class SimpleRetriever:
    """
    简化检索器 - 一行代码搞定检索
    集成知识库管理、向量搜索、缓存优化
    """

    def __init__(self):
        """初始化简化检索器"""
        self.kb_manager = KnowledgeBaseManager()
        self.embedding_service = self.kb_manager.embedding_service
        self.cache_manager = get_cache_manager()
        logger.info("简化检索器已初始化")

    def search(
        self,
        kb_id: str,
        query: str,
        top_k: Optional[int] = None,
        use_cache: bool = True,
        use_postprocessor: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        执行检索（自动使用 HNSW + 缓存）

        Args:
            kb_id: 知识库 ID
            query: 查询文本
            top_k: 返回结果数量
            use_cache: 是否使用缓存
            use_postprocessor: 是否使用后处理

        Returns:
            检索结果列表
        """
        # 确定 top_k
        if top_k is None:
            top_k = settings.RETRIEVAL_TOP_K

        # 尝试从缓存获取
        if use_cache and self.cache_manager:
            try:
                cached_result = self.cache_manager.query_cache.get_result(kb_id, query)
                if cached_result:
                    logger.debug(f"缓存命中: {query}")
                    return cached_result
            except (AttributeError, KeyError):
                # 缓存可能不存在或配置不当，继续执行
                pass

        # 执行检索
        results = self.kb_manager.search(
            kb_id=kb_id,
            query=query,
            top_k=top_k,
            use_postprocessor=use_postprocessor,
            use_cache=use_cache,
        )

        # 存入缓存
        if use_cache and self.cache_manager:
            try:
                self.cache_manager.query_cache.set_result(kb_id, query, results)
            except (AttributeError, KeyError):
                # 缓存可能不可用，继续执行
                pass

        return results

    def batch_search(
        self,
        kb_id: str,
        queries: List[str],
        top_k: Optional[int] = None,
        use_cache: bool = True,
    ) -> List[List[Dict[str, Any]]]:
        """
        批量检索（更高效）

        Args:
            kb_id: 知识库 ID
            queries: 查询文本列表
            top_k: 返回结果数量
            use_cache: 是否使用缓存

        Returns:
            每个查询的检索结果列表
        """
        if top_k is None:
            top_k = settings.RETRIEVAL_TOP_K

        all_results = []
        for query in queries:
            result = self.search(
                kb_id=kb_id,
                query=query,
                top_k=top_k,
                use_cache=use_cache,
            )
            all_results.append(result)

        return all_results

    def add_documents(
        self,
        kb_id: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        添加文档到知识库

        Args:
            kb_id: 知识库 ID
            documents: 文档文本列表
            metadatas: 元数据列表

        Returns:
            添加结果
        """
        return self.kb_manager.add_documents_from_texts(
            kb_id=kb_id,
            texts=documents,
            metadatas=metadatas,
        )

    def get_retriever_stats(self) -> Dict[str, Any]:
        """获取检索器统计信息"""
        stats = {
            "vector_store_type": settings.VECTOR_STORE_TYPE,
            "vector_store_config": self.kb_manager.vector_store.get_collection_stats(),
        }

        if self.cache_manager:
            stats["cache_stats"] = {
                "embedding_cache": self.cache_manager.embedding_cache.get_stats(),
                "query_result_cache": self.cache_manager.query_result_cache.get_stats(),
            }

        return stats
