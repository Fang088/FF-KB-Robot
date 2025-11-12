"""
模型工厂 - 根据配置动态创建 LLM 和 Embedding 客户端
"""

from typing import Optional, Any
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


class ModelFactory:
    """
    模型工厂类
    负责根据配置信息动态创建 LLM 和 Embedding 客户端实例
    """

    @staticmethod
    def create_llm_client(
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Any:
        """
        创建 LLM 客户端

        Args:
            provider: 模型供应商（openai, azure, local）
            api_key: API 密钥
            api_base: API 基础 URL
            model_name: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            LLM 客户端实例
        """
        from .llm_service import LLMService

        provider = provider or settings.LLM_PROVIDER
        api_key = api_key or settings.LLM_API_KEY
        api_base = api_base or settings.LLM_API_BASE
        model_name = model_name or settings.LLM_MODEL_NAME
        temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        max_tokens = max_tokens or settings.LLM_MAX_TOKENS

        logger.info(f"创建 {provider} LLM 客户端: {model_name}")

        return LLMService(
            provider=provider,
            api_key=api_key,
            api_base=api_base,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    @staticmethod
    def create_embedding_client(
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> Any:
        """
        创建 Embedding 客户端

        Args:
            provider: 模型供应商（openai, azure, local）
            api_key: API 密钥
            api_base: API 基础 URL
            model_name: 模型名称

        Returns:
            Embedding 客户端实例
        """
        from .embedding_service import EmbeddingService

        provider = provider or settings.EMBEDDING_PROVIDER
        api_key = api_key or settings.EMBEDDING_API_KEY
        api_base = api_base or settings.EMBEDDING_API_BASE
        model_name = model_name or settings.EMBEDDING_MODEL_NAME

        logger.info(f"创建 {provider} Embedding 客户端: {model_name}")

        return EmbeddingService(
            provider=provider,
            api_key=api_key,
            api_base=api_base,
            model_name=model_name,
        )
