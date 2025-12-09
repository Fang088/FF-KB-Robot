"""
前端服务层 - 封装后端接口调用

服务层设计原则（SOLID）：
- S: 每个服务类专注单一职责（知识库/文档/查询）
- O: 通过继承扩展功能，而非修改现有代码
- L: 子类可替换父类（所有服务继承 BaseService）
- I: 接口专一，避免"胖接口"
- D: 依赖抽象（BaseService），而非具体实现

服务层职责：
1. 封装后端模块调用
2. 统一异常处理
3. 数据格式转换
4. 前端友好的接口

作者: FF-KB-Robot Team
创建时间: 2025-12-02
"""

from .kb_service import KnowledgeBaseService
from .doc_service import DocumentService
from .query_service import QueryService

__all__ = [
    "KnowledgeBaseService",
    "DocumentService",
    "QueryService",
]
