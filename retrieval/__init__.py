"""
Retrieval 模块 - 文档检索和知识库管理

核心功能：
1. KnowledgeBaseManager - 知识库管理
2. DocumentProcessor - 文档处理
3. TextChunker - 智能文本分块
4. VectorStoreClient - 向量存储客户端
5. HNSWVectorStore - HNSW 向量索引
6. KBStore - 知识库仓储层
7. VectorManager - 向量管理器
8. RetrievalPostProcessor - 检索结果后处理

快速开始：
    from retrieval import KnowledgeBaseManager

    kb_manager = KnowledgeBaseManager()
    kb_info = kb_manager.create_knowledge_base("name")
    results = kb_manager.search(kb_id, query)
"""

from .document_processor import DocumentProcessor
from .text_chunker import TextChunker
from .vector_store_client import VectorStoreClient
from .knowledge_base_manager import KnowledgeBaseManager
from .hnsw_vector_store import HNSWVectorStore
from .kb_store import KBStore
from .vector_manager import VectorManager
from .retrieval_postprocessor import RetrievalPostProcessor

__all__ = [
    "DocumentProcessor",
    "TextChunker",
    "VectorStoreClient",
    "KnowledgeBaseManager",
    "HNSWVectorStore",
    "KBStore",
    "VectorManager",
    "RetrievalPostProcessor",
]
