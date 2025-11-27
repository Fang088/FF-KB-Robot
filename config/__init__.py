"""
Config 模块 - 项目配置和数据模型

核心功能：
1. Settings - Pydantic 配置管理（从.env加载）
2. Schemas - 数据模型定义

快速开始：
    from config import settings

    print(settings.LLM_MODEL_NAME)
    print(settings.RETRIEVAL_TOP_K)
"""

from .settings import settings
from .schemas import (
    KnowledgeBaseCreate,
    KnowledgeBase,
    DocumentCreate,
    DocumentMetadata,
    Document,
    TextChunk,
    AgentQuery,
    RetrievedDocument,
    AgentResponse,
    ModelConfig,
    ErrorResponse,
)

__all__ = [
    "settings",
    "KnowledgeBaseCreate",
    "KnowledgeBase",
    "DocumentCreate",
    "DocumentMetadata",
    "Document",
    "TextChunk",
    "AgentQuery",
    "RetrievedDocument",
    "AgentResponse",
    "ModelConfig",
    "ErrorResponse",
]
