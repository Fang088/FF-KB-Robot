"""
LangGraph 图构建 - 构建和编译 Agent 执行图
"""

from typing import Optional, Callable
from langgraph.graph import StateGraph
from .state import AgentState
from .nodes import (
    retrieve_documents,
    generate_response,
    process_tool_calls,
    decide_next_step,
    format_final_response,
)
import logging

logger = logging.getLogger(__name__)


class AgentGraph:
    """
    Agent 执行图
    使用 LangGraph 构建 RAG Agent 的工作流
    """

    def __init__(self):
        """初始化 Agent 图"""
        self.graph = None
        self.compiled_graph = None
        self._build_graph()

    def _build_graph(self):
        """构建图的节点和边"""
        logger.info("开始构建 Agent 图...")

        # 创建状态图
        self.graph = StateGraph(AgentState)

        # 添加节点
        self.graph.add_node("retrieve", retrieve_documents)
        self.graph.add_node("generate", generate_response)
        self.graph.add_node("process_tools", process_tool_calls)
        self.graph.add_node("decide", decide_next_step)
        self.graph.add_node("format", format_final_response)

        # 添加边（控制流）
        # 从 start 开始
        self.graph.set_entry_point("retrieve")

        # retrieve -> decide
        self.graph.add_edge("retrieve", "decide")

        # generate -> decide
        self.graph.add_edge("generate", "decide")

        # process_tools -> decide
        self.graph.add_edge("process_tools", "decide")

        # decide -> 条件路由
        self.graph.add_conditional_edges(
            "decide",
            self._route_decision,
            {
                "retrieve": "retrieve",
                "generate": "generate",
                "process_tools": "process_tools",
                "end": "format",
            },
        )

        # format -> end
        self.graph.set_finish_point("format")

        logger.info("Agent 图构建完成")

    def _route_decision(self, state: AgentState) -> str:
        """
        决策路由函数
        根据状态决定下一个节点

        Args:
            state: 当前状态

        Returns:
            下一个节点名称
        """
        # 如果有错误，结束
        if state.error:
            logger.warning(f"Agent 中止: {state.error}")
            return "end"

        # 如果已有满意的答案，结束
        if state.answer and state.confidence > 0.5:
            logger.info("生成了满意的答案，准备结束")
            return "end"

        # 如果超过最大迭代次数，结束
        state.increment_iteration()
        if state.iteration >= state.max_iterations:
            logger.warning(f"达到最大迭代次数: {state.max_iterations}")
            if not state.answer:
                state.answer = "经过多次尝试，无法基于提供的信息生成满意的答案。"
            return "end"

        # 如果还没有检索文档，先检索
        if not state.retrieved_docs:
            logger.info("未检索文档，进行文档检索")
            return "retrieve"

        # 如果没有生成答案，生成答案
        if not state.answer:
            logger.info("生成答案")
            return "generate"

        # 如果有待处理的工具调用，处理工具
        if len(state.tool_calls) > len(state.tool_results):
            logger.info("处理工具调用")
            return "process_tools"

        # 默认结束
        logger.info("执行流程完成")
        return "end"

    def compile(self):
        """编译图为可执行的流程"""
        if self.compiled_graph is None:
            logger.info("编译 Agent 图...")
            self.compiled_graph = self.graph.compile()
            logger.info("Agent 图编译完成")
        return self.compiled_graph

    def get_compiled_graph(self):
        """获取编译后的图"""
        return self.compile()

    async def execute(self, initial_state: AgentState):
        """
        执行 Agent 图

        Args:
            initial_state: 初始状态

        Returns:
            最终状态
        """
        compiled = self.get_compiled_graph()
        logger.info(f"开始执行 Agent: query_id={initial_state.query_id}")

        try:
            # 同步执行
            final_state = compiled.invoke(initial_state)
            logger.info(f"Agent 执行完成: query_id={initial_state.query_id}")
            return final_state
        except Exception as e:
            logger.error(f"Agent 执行失败: {e}")
            initial_state.set_error(str(e))
            return initial_state

    async def stream(self, initial_state: AgentState):
        """
        流式执行 Agent 图

        Args:
            initial_state: 初始状态

        Yields:
            中间状态
        """
        compiled = self.get_compiled_graph()
        logger.info(f"开始流式执行 Agent: query_id={initial_state.query_id}")

        try:
            # 流式执行
            for event in compiled.stream(initial_state):
                logger.debug(f"流式事件: {event}")
                yield event
            logger.info(f"Agent 流式执行完成: query_id={initial_state.query_id}")
        except Exception as e:
            logger.error(f"Agent 流式执行失败: {e}")
            initial_state.set_error(str(e))
            yield initial_state


def create_agent_graph() -> AgentGraph:
    """
    工厂函数：创建 Agent 图

    Returns:
        AgentGraph 实例
    """
    return AgentGraph()
