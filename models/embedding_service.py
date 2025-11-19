"""
Embedding 服务封装 - 支持 OpenAI, Azure 等多种供应商
支持多层缓存：Embedding 缓存、批量缓存优化、重复排查
"""

from typing import Optional, Any, List
from openai import OpenAI, AzureOpenAI
import logging
from config.settings import settings
from utils.cache_manager import get_cache_manager, cache_embedding

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding 服务类
    封装对 Embedding 模型的调用，支持 OpenAI, Azure 等多种供应商
    集成多层缓存，减少 API 调用和成本
    """

    def __init__(
        self,
        provider: str = None,
        api_key: str = None,
        api_base: Optional[str] = None,
        model_name: str = None,
        enable_cache: bool = True,
    ):
        """
        初始化 Embedding 服务

        Args:
            provider: 模型供应商（openai, azure, local）
            api_key: API 密钥
            api_base: API 基础 URL（用于 Azure 或自定义服务）
            model_name: 模型名称
            enable_cache: 是否启用缓存（默认启用）
        """
        self.provider = provider or settings.EMBEDDING_PROVIDER
        self.api_key = api_key or settings.EMBEDDING_API_KEY
        self.api_base = api_base or settings.EMBEDDING_API_BASE
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self.enable_cache = enable_cache

        self.client = self._initialize_client()
        self.cache_manager = get_cache_manager() if enable_cache else None

        logger.info(
            f"Embedding 服务已初始化: provider={self.provider}, model={self.model_name}, "
            f"cache={'enabled' if enable_cache else 'disabled'}"
        )

    def _initialize_client(self) -> Any:
        """初始化 Embedding 客户端"""
        if self.provider == "openai":
            return OpenAI(
                api_key=self.api_key,
                base_url=self.api_base if self.api_base else None,
            )
        elif self.provider == "azure":
            return AzureOpenAI(
                api_key=self.api_key,
                api_version="2024-02-15-preview",
                azure_endpoint=self.api_base,
            )
        else:
            raise ValueError(f"不支持的 Embedding 供应商: {self.provider}")

    def embed_text(self, text: str) -> List[float]:
        """
        对单个文本进行嵌入（支持缓存）

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        try:
            # 检查缓存
            if self.enable_cache and self.cache_manager:
                cached = self.cache_manager.embedding_cache.get_embedding(text)
                if cached is not None:
                    logger.debug(f"Embedding 缓存命中 (text_len={len(text)})")
                    return cached

            # 调用 API
            response = self.client.embeddings.create(
                model=self.model_name,
                input=text,
            )
            embedding = response.data[0].embedding

            # 保存到缓存
            if self.enable_cache and self.cache_manager:
                self.cache_manager.embedding_cache.set_embedding(text, embedding)

            return embedding
        except Exception as e:
            logger.error(f"Embedding 生成失败: {e}")
            raise

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        对多个文本进行嵌入（批量处理，支持智能缓存）

        策略：
        1. 首先检查缓存中已有的结果
        2. 仅调用 API 获取未缓存的文本
        3. 将 API 结果与缓存结果合并
        4. 保存新结果到缓存

        Args:
            texts: 输入文本列表

        Returns:
            嵌入向量列表
        """
        try:
            # 如果禁用缓存，直接调用 API
            if not self.enable_cache or not self.cache_manager:
                logger.debug(f"缓存已禁用，直接调用 API (text_count={len(texts)})")
                return self._call_embedding_api(texts)

            # 分离缓存命中和未命中的文本
            embeddings = []
            uncached_texts = []
            uncached_indices = []

            cache = self.cache_manager.embedding_cache
            for i, text in enumerate(texts):
                cached = cache.get_embedding(text)
                if cached is not None:
                    embeddings.append(cached)
                else:
                    embeddings.append(None)
                    uncached_texts.append(text)
                    uncached_indices.append(i)

            # 如果所有文本都在缓存中，直接返回
            if not uncached_texts:
                logger.debug(f"所有文本都在缓存中 (text_count={len(texts)})")
                return embeddings

            # 仅对未缓存的文本调用 API
            logger.debug(
                f"Embedding 缓存命中率: {len(embeddings) - len(uncached_texts)}/{len(texts)} "
                f"({100 * (len(embeddings) - len(uncached_texts)) / len(texts):.1f}%), "
                f"需要调用 API (text_count={len(uncached_texts)})"
            )

            new_embeddings = self._call_embedding_api(uncached_texts)

            # 填充回完整列表并缓存
            for idx, embedding in zip(uncached_indices, new_embeddings):
                embeddings[idx] = embedding

            # 批量保存到缓存
            cache.set_batch_embeddings(uncached_texts, new_embeddings)

            return embeddings

        except Exception as e:
            logger.error(f"批量 Embedding 生成失败: {e}")
            raise

    def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        """
        调用 Embedding API（内部方法，不使用缓存）

        Args:
            texts: 输入文本列表

        Returns:
            嵌入向量列表
        """
        response = self.client.embeddings.create(
            model=self.model_name,
            input=texts,
        )
        # 按照原始顺序返回
        embeddings = [None] * len(texts)
        for item in response.data:
            embeddings[item.index] = item.embedding
        return embeddings

    def get_embedding_dimension(self) -> int:
        """
        获取嵌入向量的维度

        Returns:
            向量维度
        """
        try:
            test_embedding = self.embed_text("test")
            return len(test_embedding)
        except Exception as e:
            logger.error(f"无法获取向量维度: {e}")
            raise

    def similarity_search(
        self,
        query_text: str,
        candidates: List[str],
        top_k: int = 5,
    ) -> List[tuple]:
        """
        基于 Embedding 的相似度搜索

        Args:
            query_text: 查询文本
            candidates: 候选文本列表
            top_k: 返回前 k 个结果

        Returns:
            [(文本, 相似度分数), ...] 的列表
        """
        try:
            # 生成查询文本的嵌入
            query_embedding = self.embed_text(query_text)

            # 生成候选文本的嵌入
            candidate_embeddings = self.embed_texts(candidates)

            # 计算相似度（余弦相似度）
            import numpy as np

            scores = []
            query_vec = np.array(query_embedding)
            for i, candidate_vec in enumerate(candidate_embeddings):
                candidate_vec = np.array(candidate_vec)
                # 计算余弦相似度
                similarity = (
                    np.dot(query_vec, candidate_vec)
                    / (np.linalg.norm(query_vec) * np.linalg.norm(candidate_vec))
                )
                scores.append((candidates[i], similarity))

            # 按相似度降序排列并返回前 k 个
            scores.sort(key=lambda x: x[1], reverse=True)
            return scores[:top_k]
        except Exception as e:
            logger.error(f"相似度搜索失败: {e}")
            raise
