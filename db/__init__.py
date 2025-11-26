"""
DB 模块 - 数据库访问层和仓储

核心功能：
1. DBConnection - 数据库连接管理
2. DocumentRepository - 文档仓储
3. KBRepository - 知识库仓储

快速开始：
    from db import DBConnection, KBRepository

    db = DBConnection(db_path)
    kb_repo = KBRepository(db)

    kb_info = kb_repo.get_knowledge_base(kb_id)
"""

from .db_manager import (
    DBConnection,
    DocumentRepository,
    KBRepository,
    DatabaseError,
)

__all__ = [
    "DBConnection",
    "DocumentRepository",
    "KBRepository",
    "DatabaseError",
]
