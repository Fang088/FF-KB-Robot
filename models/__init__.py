"""
Models 模块 - LLM 和 Embedding 模型管理

核心功能：
1. LLMService - LLM 服务封装
2. EmbeddingService - Embedding 服务封装

快速开始：
    from models import LLMService, EmbeddingService

    llm = LLMService()
    embedding = EmbeddingService()
"""

from .llm_service import LLMService
from .embedding_service import EmbeddingService

__all__ = [
    "LLMService",
    "EmbeddingService",
]
