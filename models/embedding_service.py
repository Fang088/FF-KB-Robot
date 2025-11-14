"""
Embedding 服务封装 - 支持 OpenAI, Azure 等多种供应商
"""

from typing import Optional, Any, List
from openai import OpenAI, AzureOpenAI
import logging
from config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding 服务类
    封装对 Embedding 模型的调用，支持 OpenAI, Azure 等多种供应商
    """

    def __init__(
        self,
        provider: str = None,
        api_key: str = None,
        api_base: Optional[str] = None,
        model_name: str = None,
    ):
        """
        初始化 Embedding 服务

        Args:
            provider: 模型供应商（openai, azure, local）
            api_key: API 密钥
            api_base: API 基础 URL（用于 Azure 或自定义服务）
            model_name: 模型名称
        """
        self.provider = provider or settings.EMBEDDING_PROVIDER
        self.api_key = api_key or settings.EMBEDDING_API_KEY
        self.api_base = api_base or settings.EMBEDDING_API_BASE
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME

        self.client = self._initialize_client()
        logger.info(f"Embedding 服务已初始化: provider={self.provider}, model={self.model_name}")

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
        对单个文本进行嵌入

        Args:
            text: 输入文本

        Returns:
            嵌入向量
        """
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding 生成失败: {e}")
            raise

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        对多个文本进行嵌入（批量处理）

        Args:
            texts: 输入文本列表

        Returns:
            嵌入向量列表
        """
        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts,
            )
            # 按照原始顺序返回
            embeddings = [None] * len(texts)
            for item in response.data:
                embeddings[item.index] = item.embedding
            return embeddings
        except Exception as e:
            logger.error(f"批量 Embedding 生成失败: {e}")
            raise

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
