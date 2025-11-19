"""
Agent 核心逻辑 - 协调 LLM、Embedding 和检索模块
支持多层缓存：查询结果缓存、检索分类缓存、Embedding 缓存、语义化缓存
"""

from typing import Optional, Dict, Any, AsyncGenerator, List
from datetime import datetime
import uuid
import logging
from .state import AgentState
from .graph import create_agent_graph
from config.settings import settings
import time
from utils.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class AgentCore:
    """
    Agent 核心类
    协调 LLM、Embedding、检索等模块，提供统一的 Agent 接口
    支持多层缓存优化查询性能
    """

    def __init__(self, enable_cache: bool = True):
        """
        初始化 Agent 核心

        Args:
            enable_cache: 是否启用缓存（包括语义化缓存）
        """
        self.agent_graph = create_agent_graph()
        self.enable_cache = enable_cache
        self.cache_manager = get_cache_manager() if enable_cache else None

        logger.info(
            f"Agent 核心已初始化 (cache={'enabled' if enable_cache else 'disabled'})"
        )

    def _create_initial_state(
        self,
        kb_id: str,
        question: str,
        top_k: int = 5,
    ) -> AgentState:
        """
        创建初始状态

        Args:
            kb_id: 知识库 ID
            question: 用户问题
            top_k: 检索结果数量

        Returns:
            初始 AgentState
        """
        query_id = str(uuid.uuid4())
        state = AgentState(
            query_id=query_id,
            kb_id=kb_id,
            question=question,
            max_iterations=settings.LANGGRAPH_MAX_ITERATIONS,
        )
        state.add_message("user", question)
        return state

    async def execute_query(
        self,
        kb_id: str,
        question: str,
        top_k: int = 5,
        use_tools: bool = False,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        执行查询（支持多层缓存）

        缓存策略：
        1. 首先检查查询结果缓存（L2）- 完整查询结果
        2. 如果缓存命中，直接返回
        3. 否则执行完整的 Agent 工作流
        4. Embedding 和分类会自动使用 L1 和 L3 缓存

        Args:
            kb_id: 知识库 ID
            question: 用户问题
            top_k: 检索结果数量
            use_tools: 是否使用工具
            use_cache: 是否使用缓存

        Returns:
            查询结果
        """
        logger.info(
            f"执行查询: kb_id={kb_id}, question={question}, top_k={top_k}, "
            f"cache={'enabled' if (use_cache and self.enable_cache) else 'disabled'}"
        )

        start_time = time.time()

        try:
            # 检查查询结果缓存（支持语义匹配）
            if use_cache and self.enable_cache and self.cache_manager:
                try:
                    # 查询缓存（自动支持语义匹配）
                    cached_result = self.cache_manager.query_cache.get_result(kb_id, question)
                    if cached_result is not None:
                        response_time_ms = (time.time() - start_time) * 1000
                        cached_result["response_time_ms"] = response_time_ms
                        cached_result["from_cache"] = True
                        logger.info(
                            f"缓存命中 (query_id={cached_result.get('query_id')}, "
                            f"time={response_time_ms:.2f}ms)"
                        )
                        return cached_result

                except Exception as e:
                    logger.warning(f"缓存查询失败（继续执行）: {e}")

            # 创建初始状态
            initial_state = self._create_initial_state(kb_id, question, top_k)

            # 执行 Agent 图
            final_state = await self.agent_graph.execute(initial_state)

            # 计算响应时间
            response_time_ms = (time.time() - start_time) * 1000

            # 格式化响应
            response = {
                "query_id": initial_state.query_id,
                "kb_id": initial_state.kb_id,
                "question": initial_state.question,
                "answer": "无法生成答案",
                "retrieved_docs": [],
                "sources": [],
                "confidence": 0.0,
                "response_time_ms": response_time_ms,
                "from_cache": False,
                "metadata": {
                    "iterations": 0,
                    "intermediate_steps": [],
                    "error": None,
                },
            }

            # 尝试从 final_state 中提取其他信息
            try:
                # 处理两种情况：final_state 是字典或 AgentState 对象
                if isinstance(final_state, dict):
                    # 如果 final_state 是字典

                    response["query_id"] = final_state.get("query_id", initial_state.query_id)
                    response["kb_id"] = final_state.get("kb_id", initial_state.kb_id)
                    response["question"] = final_state.get("question", initial_state.question)
                    response["answer"] = final_state.get("answer", "无法生成答案")

                    # 处理 retrieved_docs
                    retrieved_docs = final_state.get("retrieved_docs", [])
                    if retrieved_docs:
                        docs_list = []
                        for doc in retrieved_docs:
                            if hasattr(doc, 'id'):
                                # 如果是对象
                                docs_list.append({
                                    "id": doc.id,
                                    "content": doc.content,
                                    "score": doc.score,
                                    "metadata": doc.metadata,
                                })
                            elif isinstance(doc, dict):
                                # 如果是字典
                                docs_list.append(doc.copy())

                        response["retrieved_docs"] = docs_list

                    response["sources"] = final_state.get("sources", [])
                    response["confidence"] = final_state.get("confidence", 0.0)

                    # 处理 metadata
                    response["metadata"]["iterations"] = final_state.get("iteration", 0)
                    response["metadata"]["intermediate_steps"] = final_state.get("intermediate_steps", [])
                    response["metadata"]["error"] = final_state.get("error", None)

                elif hasattr(final_state, '__dict__'):

                    if hasattr(final_state, 'answer') and final_state.answer:
                        response["answer"] = final_state.answer
                    if hasattr(final_state, 'retrieved_docs'):
                        response["retrieved_docs"] = [
                            {
                                "id": doc.id,
                                "content": doc.content,
                                "score": doc.score,
                                "metadata": doc.metadata,
                            }
                            for doc in final_state.retrieved_docs
                        ]
                    if hasattr(final_state, 'sources'):
                        response["sources"] = final_state.sources
                    if hasattr(final_state, 'confidence'):
                        response["confidence"] = final_state.confidence
                    if hasattr(final_state, 'iteration'):
                        response["metadata"]["iterations"] = final_state.iteration
                    if hasattr(final_state, 'intermediate_steps'):
                        response["metadata"]["intermediate_steps"] = final_state.intermediate_steps
                    if hasattr(final_state, 'error'):
                        response["metadata"]["error"] = final_state.error

            except Exception as e:
                logger.error(f"从 final_state 提取信息失败: {e}")

            # 缓存查询结果（支持语义匹配）
            if use_cache and self.enable_cache and self.cache_manager:
                try:
                    cache_result = response.copy()
                    # 保存到缓存（自动支持语义匹配）
                    self.cache_manager.query_cache.set_result(kb_id, question, cache_result)
                except Exception as e:
                    logger.warning(f"缓存保存失败（不影响主流程）: {e}")

            logger.info(
                f"查询完成: query_id={initial_state.query_id}, "
                f"time={response_time_ms:.2f}ms"
            )

            return response

        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            return {
                "query_id": str(uuid.uuid4()),
                "kb_id": kb_id,
                "question": question,
                "answer": f"查询执行失败: {e}",
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000,
                "from_cache": False,
            }

    async def stream_query(
        self,
        kb_id: str,
        question: str,
        top_k: int = 5,
        use_tools: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式执行查询

        Args:
            kb_id: 知识库 ID
            question: 用户问题
            top_k: 检索结果数量
            use_tools: 是否使用工具

        Yields:
            流式结果
        """
        logger.info(
            f"开始流式查询: kb_id={kb_id}, question={question}"
        )

        start_time = time.time()

        try:
            # 创建初始状态
            initial_state = self._create_initial_state(kb_id, question, top_k)

            # 流式执行 Agent 图
            async for event in self.agent_graph.stream(initial_state):
                response_time_ms = (time.time() - start_time) * 1000
                yield {
                    "query_id": initial_state.query_id,
                    "event": event,
                    "response_time_ms": response_time_ms,
                }

            logger.info(f"流式查询完成: query_id={initial_state.query_id}")

        except Exception as e:
            logger.error(f"流式查询执行失败: {e}")
            yield {
                "error": str(e),
                "response_time_ms": (time.time() - start_time) * 1000,
            }

    def get_agent_info(self) -> Dict[str, Any]:
        """
        获取 Agent 信息

        Returns:
            Agent 配置信息
        """
        return {
            "project": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION,
            "llm_model": settings.LLM_MODEL_NAME,
            "embedding_model": settings.EMBEDDING_MODEL_NAME,
            "vector_store": settings.VECTOR_STORE_TYPE,
            "chunk_size": settings.TEXT_CHUNK_SIZE,
            "max_iterations": settings.LANGGRAPH_MAX_ITERATIONS,
            "timeout": settings.LANGGRAPH_TIMEOUT,
        }
