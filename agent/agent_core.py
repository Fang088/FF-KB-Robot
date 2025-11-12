"""
Agent 核心逻辑 - 协调 LLM、Embedding 和检索模块
"""

from typing import Optional, Dict, Any, AsyncGenerator
from datetime import datetime
import uuid
import logging
from .state import AgentState
from .graph import create_agent_graph
from config.settings import settings
import time

logger = logging.getLogger(__name__)


class AgentCore:
    """
    Agent 核心类
    协调 LLM、Embedding、检索等模块，提供统一的 Agent 接口
    """

    def __init__(self):
        """初始化 Agent 核心"""
        self.agent_graph = create_agent_graph()
        logger.info("Agent 核心已初始化")

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
    ) -> Dict[str, Any]:
        """
        执行查询

        Args:
            kb_id: 知识库 ID
            question: 用户问题
            top_k: 检索结果数量
            use_tools: 是否使用工具

        Returns:
            查询结果
        """
        logger.info(
            f"执行查询: kb_id={kb_id}, question={question}, top_k={top_k}"
        )

        start_time = time.time()

        try:
            # 创建初始状态
            initial_state = self._create_initial_state(kb_id, question, top_k)

            # 执行 Agent 图
            final_state = await self.agent_graph.execute(initial_state)

            # 计算响应时间
            response_time_ms = (time.time() - start_time) * 1000

            # 格式化响应
            response = {
                "query_id": final_state.query_id,
                "kb_id": final_state.kb_id,
                "question": final_state.question,
                "answer": final_state.answer or "无法生成答案",
                "retrieved_docs": [
                    {
                        "id": doc.id,
                        "content": doc.content,
                        "score": doc.score,
                        "metadata": doc.metadata,
                    }
                    for doc in final_state.retrieved_docs
                ],
                "sources": final_state.sources,
                "confidence": final_state.confidence,
                "response_time_ms": response_time_ms,
                "metadata": {
                    "iterations": final_state.iteration,
                    "intermediate_steps": final_state.intermediate_steps,
                    "error": final_state.error,
                },
            }

            logger.info(
                f"查询完成: query_id={final_state.query_id}, "
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
            "chunk_size": settings.CHUNK_SIZE,
            "max_iterations": settings.LANGGRAPH_MAX_ITERATIONS,
            "timeout": settings.LANGGRAPH_TIMEOUT,
        }
