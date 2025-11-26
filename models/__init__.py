"""
Models 模块 - LLM 和 Embedding 模型管理

核心功能：
1. ClientFactory - 统一的客户端创建工厂
2. ClientManager - 单例客户端管理器
3. LLMService - LLM 服务封装
4. EmbeddingService - Embedding 服务封装

快速开始：
    from models import ClientManager

    manager = ClientManager.get_instance()
    llm_client = manager.get_llm_client(provider, api_key, api_base)
    embedding_client = manager.get_embedding_client(provider, api_key, api_base)
"""

from .client_factory import ClientFactory, ClientManager, ClientFactoryError
from .llm_service import LLMService
from .embedding_service import EmbeddingService

__all__ = [
    "ClientFactory",
    "ClientManager",
    "ClientFactoryError",
    "LLMService",
    "EmbeddingService",
]
