"""
查询服务 - 封装智能问答后端接口

功能列表：
1. 同步问答
2. 流式问答（生成器）
3. 获取查询历史
4. 查询统计

设计原则：
- KISS: 简单清晰的接口
- 性能优化: 支持流式输出
- 缓存友好: 自动利用后端缓存

作者: FF-KB-Robot Team
创建时间: 2025-12-02
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Generator
import logging
import asyncio

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.agent_core import AgentCore
from utils.cache_manager import QueryResultCache

logger = logging.getLogger(__name__)


class QueryService:
    """
    查询服务类

    职责：封装智能问答相关的所有后端操作

    设计模式：
    - 单例模式
    - 代理模式：封装 AgentCore 复杂性
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

        self.agent_core = AgentCore()
        self.query_cache = QueryResultCache()
        self._query_history = []  # 简单的查询历史（内存存储）
        self._initialized = True
        logger.info("查询服务已初始化")

    async def execute_query_async(
        self,
        kb_id: str,
        question: str,
        top_k: int = 5,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        执行查询（异步）

        Args:
            kb_id: 知识库ID
            question: 用户问题
            top_k: 返回的文档数量
            use_cache: 是否使用缓存

        Returns:
            Dict: {
                "success": bool,
                "data": {
                    "query_id": str,
                    "question": str,
                    "answer": str,
                    "confidence": float,
                    "confidence_level": str,
                    "retrieved_docs": List[Dict],
                    "response_time_ms": int,
                    "from_cache": bool,
                    "metadata": Dict
                },
                "message": str
            }
        """
        try:
            import time
            start_time = time.time()

            # 调用 Agent 核心执行查询
            result = await self.agent_core.execute_query(
                kb_id=kb_id,
                question=question,
                top_k=top_k,
                use_cache=use_cache
            )

            response_time = int((time.time() - start_time) * 1000)

            # 计算置信度等级
            confidence = result.get("confidence", 0.0)
            confidence_level = self._get_confidence_level(confidence)

            # 格式化检索文档
            retrieved_docs = []
            for doc in result.get("retrieved_docs", []):
                retrieved_docs.append({
                    "id": doc.get("id", ""),
                    "content": doc.get("content", ""),
                    "score": round(doc.get("score", 0.0), 4),
                    "source": doc.get("metadata", {}).get("source", "未知")
                })

            # 构建返回数据
            query_data = {
                "query_id": result.get("query_id", ""),
                "question": question,
                "answer": result.get("answer", ""),
                "confidence": round(confidence, 3),
                "confidence_level": confidence_level,
                "retrieved_docs": retrieved_docs,
                "response_time_ms": response_time,
                "from_cache": result.get("from_cache", False),
                "metadata": {
                    "kb_id": kb_id,
                    "top_k": top_k,
                    "iteration": result.get("iteration", 1),
                    "confidence_breakdown": result.get("metadata", {}).get("confidence_breakdown", {})
                }
            }

            # 保存到查询历史
            self._add_to_history(query_data)

            return {
                "success": True,
                "data": query_data,
                "message": "查询成功"
            }
        except Exception as e:
            logger.error(f"查询失败: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"查询失败：{str(e)}"
            }

    def execute_query(
        self,
        kb_id: str,
        question: str,
        top_k: int = 5,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        执行查询（同步封装）

        适用于 Streamlit 等同步环境
        修复了 Streamlit 的 ScriptRunner 线程中没有事件循环的问题

        Args:
            kb_id: 知识库ID
            question: 用户问题
            top_k: 返回的文档数量
            use_cache: 是否使用缓存

        Returns:
            同 execute_query_async
        """
        try:
            import nest_asyncio

            # 应用 nest_asyncio，允许在运行的事件循环中运行新的异步代码
            nest_asyncio.apply()

            try:
                # 尝试获取当前事件循环
                loop = asyncio.get_running_loop()
                # 如果有运行中的循环，使用 run_until_complete
                return loop.run_until_complete(
                    self.execute_query_async(kb_id, question, top_k, use_cache)
                )
            except RuntimeError:
                # 如果没有运行中的事件循环（Streamlit ScriptRunner 线程）
                # 创建新的事件循环并运行
                return asyncio.run(
                    self.execute_query_async(kb_id, question, top_k, use_cache)
                )

        except Exception as e:
            logger.error(f"同步查询失败: {e}", exc_info=True)
            return {
                "success": False,
                "data": None,
                "message": f"查询失败：{str(e)}"
            }

    def get_query_history(self, limit: int = 10) -> Dict[str, Any]:
        """
        获取查询历史

        Args:
            limit: 返回的最大数量

        Returns:
            Dict: {
                "success": bool,
                "data": List[Dict],
                "count": int,
                "message": str
            }
        """
        try:
            # 返回最近的查询记录
            history = self._query_history[-limit:][::-1]  # 逆序，最新的在前面

            return {
                "success": True,
                "data": history,
                "count": len(history),
                "message": f"成功获取 {len(history)} 条历史记录"
            }
        except Exception as e:
            logger.error(f"获取查询历史失败: {e}")
            return {
                "success": False,
                "data": [],
                "count": 0,
                "message": f"获取失败：{str(e)}"
            }

    def clear_query_history(self) -> Dict[str, Any]:
        """
        清空查询历史

        Returns:
            Dict: {
                "success": bool,
                "message": str
            }
        """
        try:
            count = len(self._query_history)
            self._query_history.clear()

            return {
                "success": True,
                "message": f"已清空 {count} 条历史记录"
            }
        except Exception as e:
            logger.error(f"清空查询历史失败: {e}")
            return {
                "success": False,
                "message": f"清空失败：{str(e)}"
            }

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            Dict: {
                "success": bool,
                "data": {
                    "hit_rate": str,
                    "total_requests": int,
                    "cache_hits": int,
                    "cache_misses": int
                },
                "message": str
            }
        """
        try:
            stats = self.query_cache.get_stats()
            stats_dict = stats.to_dict()  # 转换 CacheStats 对象为字典

            return {
                "success": True,
                "data": {
                    "hit_rate": stats_dict.get("hit_rate", "0.0%"),
                    "total_requests": stats_dict.get("total_requests", 0),
                    "cache_hits": stats_dict.get("cache_hits", 0),
                    "cache_misses": stats_dict.get("cache_misses", 0)
                },
                "message": "获取缓存统计成功"
            }
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"获取失败：{str(e)}"
            }

    def _get_confidence_level(self, confidence: float) -> str:
        """
        根据置信度分数获取置信度等级

        Args:
            confidence: 置信度分数 (0.0-1.0)

        Returns:
            str: 置信度等级
        """
        if confidence >= 0.8:
            return "非常高 ⭐⭐⭐⭐⭐"
        elif confidence >= 0.6:
            return "高 ⭐⭐⭐⭐"
        elif confidence >= 0.4:
            return "中等 ⭐⭐⭐"
        elif confidence >= 0.2:
            return "低 ⭐⭐"
        else:
            return "非常低 ⭐"

    def _add_to_history(self, query_data: Dict[str, Any]) -> None:
        """
        添加查询到历史记录

        Args:
            query_data: 查询数据
        """
        # 限制历史记录数量（最多保留100条）
        if len(self._query_history) >= 100:
            self._query_history.pop(0)

        # 添加时间戳
        from datetime import datetime
        query_data["timestamp"] = datetime.now().isoformat()

        self._query_history.append(query_data)

    def get_query_statistics(self) -> Dict[str, Any]:
        """
        获取查询统计信息

        Returns:
            Dict: {
                "success": bool,
                "data": {
                    "total_queries": int,
                    "avg_confidence": float,
                    "avg_response_time_ms": float,
                    "cache_hit_rate": str
                },
                "message": str
            }
        """
        try:
            if not self._query_history:
                return {
                    "success": True,
                    "data": {
                        "total_queries": 0,
                        "avg_confidence": 0.0,
                        "avg_response_time_ms": 0,
                        "cache_hit_rate": "0.0%"
                    },
                    "message": "暂无查询记录"
                }

            # 计算统计信息
            total = len(self._query_history)
            avg_confidence = sum(q["confidence"] for q in self._query_history) / total
            avg_response_time = sum(q["response_time_ms"] for q in self._query_history) / total
            cache_hits = sum(1 for q in self._query_history if q["from_cache"])
            cache_hit_rate = f"{(cache_hits / total * 100):.1f}%"

            return {
                "success": True,
                "data": {
                    "total_queries": total,
                    "avg_confidence": round(avg_confidence, 3),
                    "avg_response_time_ms": int(avg_response_time),
                    "cache_hit_rate": cache_hit_rate
                },
                "message": "统计成功"
            }
        except Exception as e:
            logger.error(f"获取查询统计失败: {e}")
            return {
                "success": False,
                "data": None,
                "message": f"统计失败：{str(e)}"
            }
