"""
文档服务 - 封装文档管理后端接口

功能列表：
1. 上传文档
2. 获取文档列表
3. 获取文档详情
4. 删除文档
5. 批量上传文档

设计原则：
- KISS: 简单直接的接口
- DRY: 复用上传逻辑
- 异步处理: 支持批量上传

作者: FF-KB-Robot Team
创建时间: 2025-12-02
修复时间: 2025-12-02
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, BinaryIO
import logging
from datetime import datetime

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from retrieval.knowledge_base_manager import KnowledgeBaseManager

logger = logging.getLogger(__name__)


class DocumentService:
    """
    文档服务类

    职责：封装文档相关的所有后端操作

    设计模式：单例模式
    """

    _instance = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化服务"""
        if self._initialized:
            return

        self.kb_manager = KnowledgeBaseManager()
        self._initialized = True
        logger.info("文档服务已初始化")

    def upload_document(
        self,
        kb_id: str,
        file_path: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        上传单个文档

        Args:
            kb_id: 知识库ID
            file_path: 文件路径
            filename: 自定义文件名（可选）

        Returns:
            Dict: {
                "success": bool,
                "data": {
                    "doc_id": str,
                    "filename": str,
                    "chunk_count": int,
                    "created_at": str,
                    "processing_time_ms": int
                },
                "message": str
            }
        """
        try:
            import time
            start_time = time.time()

            # 调用后端上传文档
            doc_info = self.kb_manager.upload_document(
                kb_id=kb_id,
                file_path=file_path,
                metadata={"original_filename": filename} if filename else None
            )

            processing_time = int((time.time() - start_time) * 1000)

            # 格式化返回数据
            result = {
                "doc_id": doc_info.get("id", ""),
                "filename": doc_info.get("filename", filename or Path(file_path).name),
                "chunk_count": doc_info.get("chunk_count", 0),
                "created_at": doc_info.get("created_at", datetime.now().isoformat()),
                "processing_time_ms": processing_time
            }

            return {
                "success": True,
                "data": result,
                "message": f"文档上传成功！处理了 {result['chunk_count']} 个文本块"
            }
        except Exception as e:
            logger.error(f"上传文档失败: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"上传失败：{str(e)}"
            }

    def upload_documents_batch(
        self,
        kb_id: str,
        file_paths: List[str]
    ) -> Dict[str, Any]:
        """
        批量上传文档

        Args:
            kb_id: 知识库ID
            file_paths: 文件路径列表

        Returns:
            Dict: {
                "success": bool,
                "data": {
                    "total": int,
                    "success_count": int,
                    "failed_count": int,
                    "results": List[Dict]
                },
                "message": str
            }
        """
        results = []
        success_count = 0
        failed_count = 0

        for file_path in file_paths:
            result = self.upload_document(kb_id, file_path)
            results.append({
                "file_path": file_path,
                "filename": Path(file_path).name,
                **result
            })

            if result["success"]:
                success_count += 1
            else:
                failed_count += 1

        return {
            "success": success_count > 0,
            "data": {
                "total": len(file_paths),
                "success_count": success_count,
                "failed_count": failed_count,
                "results": results
            },
            "message": f"批量上传完成：{success_count} 成功，{failed_count} 失败"
        }

    def list_documents(self, kb_id: str) -> Dict[str, Any]:
        """
        获取知识库的所有文档

        Args:
            kb_id: 知识库ID

        Returns:
            Dict: {
                "success": bool,
                "data": List[{
                    "id": str,
                    "filename": str,
                    "chunk_count": int,
                    "created_at": str
                }],
                "count": int,
                "message": str
            }
        """
        try:
            # 从数据库获取文档列表 - 使用 kb_store.doc_repo
            documents = self.kb_manager.kb_store.doc_repo.get_documents_by_kb(kb_id)

            # 格式化数据 - 使用 or 防御 None 值
            formatted_docs = []
            for doc in documents:
                formatted_docs.append({
                    "id": doc.get("id") or "",                      # 防御 None 值
                    "filename": doc.get("filename") or "未命名",     # 防御 None 值
                    "chunk_count": doc.get("chunk_count") or 0,     # 防御 None 值
                    "created_at": doc.get("created_at") or ""       # 防御 None 值
                })

            return {
                "success": True,
                "data": formatted_docs,
                "count": len(formatted_docs),
                "message": f"成功获取 {len(formatted_docs)} 个文档"
            }
        except Exception as e:
            logger.error(f"获取文档列表失败: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": f"获取失败：{str(e)}"
            }

    def get_document_info(self, kb_id: str, doc_id: str) -> Dict[str, Any]:
        """
        获取文档详细信息

        Args:
            kb_id: 知识库ID（用于验证，暂不使用）
            doc_id: 文档ID

        Returns:
            Dict: {
                "success": bool,
                "data": {
                    "id": str,
                    "filename": str,
                    "file_path": str,
                    "chunk_count": int,
                    "created_at": str
                },
                "message": str
            }
        """
        try:
            # 从数据库获取文档信息 - 使用 doc_repo.get_document_by_id()
            doc_info = self.kb_manager.kb_store.doc_repo.get_document_by_id(doc_id)

            if not doc_info:
                return {
                    "success": False,
                    "data": None,
                    "message": "文档不存在"
                }

            # 格式化数据 - 使用 or 防御 None 值
            formatted_info = {
                "id": doc_info.get("id") or "",                      # 防御 None 值
                "filename": doc_info.get("filename") or "未命名",     # 防御 None 值
                "file_path": doc_info.get("file_path") or "",        # 防御 None 值
                "chunk_count": doc_info.get("chunk_count") or 0,     # 防御 None 值
                "created_at": doc_info.get("created_at") or ""       # 防御 None 值
            }

            return {
                "success": True,
                "data": formatted_info,
                "message": "获取成功"
            }
        except Exception as e:
            logger.error(f"获取文档信息失败: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"获取失败：{str(e)}"
            }

    def delete_document(self, kb_id: str, doc_id: str) -> Dict[str, Any]:
        """
        删除文档（危险操作）

        Args:
            kb_id: 知识库ID（用于验证）
            doc_id: 文档ID

        Returns:
            Dict: {
                "success": bool,
                "message": str
            }
        """
        try:
            # 先获取文档信息
            doc_info = self.get_document_info(kb_id, doc_id)
            if not doc_info["success"]:
                return doc_info

            filename = doc_info["data"]["filename"]

            # 调用后端删除（四层清理）- 只需要 doc_id
            success = self.kb_manager.delete_document(doc_id)

            if success:
                return {
                    "success": True,
                    "message": f"文档 '{filename}' 已删除"
                }
            else:
                return {
                    "success": False,
                    "message": f"删除文档 '{filename}' 失败"
                }
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return {
                "success": False,
                "message": f"删除失败：{str(e)}"
            }

    def get_supported_formats(self) -> List[str]:
        """
        获取支持的文档格式

        Returns:
            List[str]: 支持的文件扩展名列表
        """
        return [".pdf", ".docx", ".xlsx", ".txt", ".md"]

    def validate_file_format(self, filename: str) -> Dict[str, Any]:
        """
        验证文件格式是否支持

        Args:
            filename: 文件名

        Returns:
            Dict: {
                "valid": bool,
                "extension": str,
                "message": str
            }
        """
        file_path = Path(filename)
        extension = file_path.suffix.lower()
        supported_formats = self.get_supported_formats()

        if extension in supported_formats:
            return {
                "valid": True,
                "extension": extension,
                "message": f"支持的格式 ✓"
            }
        else:
            return {
                "valid": False,
                "extension": extension,
                "message": f"不支持的格式 {extension}，仅支持：{', '.join(supported_formats)}"
            }
