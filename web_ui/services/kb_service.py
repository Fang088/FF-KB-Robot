"""
知识库服务 - 封装知识库管理后端接口

功能列表：
1. 创建知识库
2. 获取知识库列表
3. 获取知识库详情
4. 删除知识库
5. 获取知识库统计信息

设计原则：
- KISS: 简单直接的接口设计
- DRY: 统一的错误处理和日志记录
- 单例模式: 确保全局只有一个实例

作者: FF-KB-Robot Team
创建时间: 2025-12-02
修复时间: 2025-12-02
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

# 添加项目根目录到 Python 路径（前后端模块解耦关键）
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from retrieval.knowledge_base_manager import KnowledgeBaseManager

logger = logging.getLogger(__name__)


class KnowledgeBaseService:
    """
    知识库服务类

    职责：封装知识库相关的所有后端操作，提供前端友好的接口

    设计模式：
    - 单例模式：全局唯一实例
    - 门面模式：简化后端复杂接口
    """

    _instance = None  # 单例实例

    def __new__(cls):
        """单例模式：确保全局只有一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化服务（仅执行一次）"""
        if self._initialized:
            return

        self.kb_manager = KnowledgeBaseManager()
        self._initialized = True
        logger.info("知识库服务已初始化")

    def create_knowledge_base(
        self,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        创建知识库

        Args:
            name: 知识库名称
            description: 描述信息
            tags: 标签列表

        Returns:
            Dict: {
                "success": bool,
                "data": {
                    "id": str,
                    "name": str,
                    "description": str,
                    "tags": List[str],
                    "created_at": str
                },
                "message": str
            }
        """
        try:
            # 调用后端创建知识库 - 返回字典
            kb_info = self.kb_manager.create_knowledge_base(
                name=name,
                description=description,
                tags=tags or []
            )

            # 格式化返回数据
            formatted_info = {
                "id": kb_info.get("id", ""),
                "name": kb_info.get("name", name),
                "description": kb_info.get("description", description),
                "tags": kb_info.get("tags", tags or []),
                "created_at": kb_info.get("created_at", datetime.now().isoformat()),
                "document_count": kb_info.get("document_count", 0),
                "total_chunks": kb_info.get("total_chunks", 0)
            }

            return {
                "success": True,
                "data": formatted_info,
                "message": f"知识库 '{name}' 创建成功"
            }
        except Exception as e:
            logger.error(f"创建知识库失败: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"创建失败：{str(e)}"
            }

    def list_knowledge_bases(self) -> Dict[str, Any]:
        """
        获取所有知识库列表

        Returns:
            Dict: {
                "success": bool,
                "data": List[{
                    "id": str,
                    "name": str,
                    "description": str,
                    "tags": List[str],
                    "document_count": int,
                    "total_chunks": int,
                    "created_at": str,
                    "updated_at": str
                }],
                "count": int,
                "message": str
            }
        """
        try:
            # 调用后端获取知识库列表 - 使用 kb_store.list_kbs()
            kb_list = self.kb_manager.kb_store.list_kbs()

            # 格式化数据（转换为前端友好格式）
            formatted_list = []
            for kb in kb_list:
                tags = kb.get("tags", "")
                # 处理标签：如果是字符串则分割，如果是列表则直接使用
                if isinstance(tags, str):
                    tags_list = tags.split(",") if tags else []
                elif isinstance(tags, list):
                    tags_list = tags
                else:
                    tags_list = []

                formatted_list.append({
                    "id": kb.get("id", ""),
                    "name": kb.get("name", "未命名"),
                    "description": kb.get("description", ""),
                    "tags": tags_list,
                    "document_count": kb.get("document_count") or 0,  # 防御 None 值
                    "total_chunks": kb.get("total_chunks") or 0,      # 防御 None 值
                    "created_at": kb.get("created_at", ""),
                    "updated_at": kb.get("updated_at", "")
                })

            return {
                "success": True,
                "data": formatted_list,
                "count": len(formatted_list),
                "message": f"成功获取 {len(formatted_list)} 个知识库"
            }
        except Exception as e:
            logger.error(f"获取知识库列表失败: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": f"获取失败：{str(e)}"
            }

    def get_knowledge_base_info(self, kb_id: str) -> Dict[str, Any]:
        """
        获取知识库详细信息

        Args:
            kb_id: 知识库ID

        Returns:
            Dict: {
                "success": bool,
                "data": {
                    "id": str,
                    "name": str,
                    "description": str,
                    "tags": List[str],
                    "document_count": int,
                    "total_chunks": int,
                    "created_at": str,
                    "updated_at": str
                },
                "message": str
            }
        """
        try:
            # 从后端获取知识库信息 - 使用 kb_store.get_kb()
            kb_info = self.kb_manager.kb_store.get_kb(kb_id)

            if not kb_info:
                return {
                    "success": False,
                    "data": None,
                    "message": f"知识库不存在"
                }

            # 处理标签
            tags = kb_info.get("tags", "")
            if isinstance(tags, str):
                tags_list = tags.split(",") if tags else []
            elif isinstance(tags, list):
                tags_list = tags
            else:
                tags_list = []

            # 格式化数据
            formatted_info = {
                "id": kb_info.get("id", ""),
                "name": kb_info.get("name", "未命名"),
                "description": kb_info.get("description", ""),
                "tags": tags_list,
                "document_count": kb_info.get("document_count") or 0,  # 防御 None 值
                "total_chunks": kb_info.get("total_chunks") or 0,      # 防御 None 值
                "created_at": kb_info.get("created_at", ""),
                "updated_at": kb_info.get("updated_at", "")
            }

            return {
                "success": True,
                "data": formatted_info,
                "message": "获取成功"
            }
        except Exception as e:
            logger.error(f"获取知识库信息失败: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"获取失败：{str(e)}"
            }

    def delete_knowledge_base(self, kb_id: str) -> Dict[str, Any]:
        """
        删除知识库（危险操作）

        Args:
            kb_id: 知识库ID

        Returns:
            Dict: {
                "success": bool,
                "message": str
            }
        """
        try:
            # 先获取知识库信息
            kb_info = self.get_knowledge_base_info(kb_id)
            if not kb_info["success"]:
                return kb_info

            kb_name = kb_info["data"]["name"]

            # 调用后端删除（四层清理）
            success = self.kb_manager.delete_knowledge_base(kb_id)

            if success:
                return {
                    "success": True,
                    "message": f"知识库 '{kb_name}' 已完全删除"
                }
            else:
                return {
                    "success": False,
                    "message": f"删除知识库 '{kb_name}' 失败"
                }
        except Exception as e:
            logger.error(f"删除知识库失败: {e}")
            return {
                "success": False,
                "message": f"删除失败：{str(e)}"
            }

    def get_knowledge_base_stats(self, kb_id: str) -> Dict[str, Any]:
        """
        获取知识库统计信息

        Args:
            kb_id: 知识库ID

        Returns:
            Dict: {
                "success": bool,
                "data": {
                    "document_count": int,
                    "total_chunks": int,
                    "avg_chunks_per_doc": float,
                    "total_size_mb": float (估算)
                },
                "message": str
            }
        """
        try:
            kb_info = self.get_knowledge_base_info(kb_id)
            if not kb_info["success"]:
                return kb_info

            data = kb_info["data"]
            # 确保值不为 None（防御性编程）
            doc_count = data.get("document_count") or 0
            chunk_count = data.get("total_chunks") or 0

            # 计算统计信息
            stats = {
                "document_count": doc_count,
                "total_chunks": chunk_count,
                "avg_chunks_per_doc": round(chunk_count / doc_count, 2) if doc_count > 0 else 0,
                "total_size_mb": round(chunk_count * 1000 * 4 / 1024 / 1024, 2)  # 估算：每个分块约1KB，向量维度1536×4字节
            }

            return {
                "success": True,
                "data": stats,
                "message": "统计成功"
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"统计失败：{str(e)}"
            }
