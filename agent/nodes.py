"""
LangGraph 节点函数 - 定义 Agent 工作流中的各个节点
"""

from typing import Optional, Dict, Any
from .state import AgentState, RetrievedDoc
import logging

logger = logging.getLogger(__name__)


async def retrieve_documents(state: AgentState) -> Dict[str, Any]:
    """
    文档检索节点
    从知识库中检索与问题相关的文档

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态字典
    """
    logger.info(f"执行文档检索: kb_id={state.kb_id}, question={state.question}")

    try:
        state.add_intermediate_step("开始文档检索...")

        # 调用 KnowledgeBaseManager 进行检索
        from retrieval.knowledge_base_manager import KnowledgeBaseManager
        from .state import RetrievedDoc

        kb_manager = KnowledgeBaseManager()
        retrieved_docs = kb_manager.search(state.kb_id, state.question, top_k=5)

        # 将字典转换为 RetrievedDoc 对象
        retrieved_docs = [RetrievedDoc(**doc) for doc in retrieved_docs]

        state.add_intermediate_step(f"检索完成，获得 {len(retrieved_docs)} 个相关文档")

        return {"retrieved_docs": retrieved_docs, "current_node": "retrieve"}
    except Exception as e:
        logger.error(f"文档检索失败: {e}")
        state.set_error(f"文档检索失败: {e}")
        return {"error": str(e), "current_node": "retrieve"}


async def generate_response(state: AgentState) -> Dict[str, Any]:
    """
    响应生成节点
    基于检索到的文档和用户问题生成答案

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态字典
    """
    logger.info(f"执行响应生成: question={state.question}")

    try:
        state.add_intermediate_step("开始生成答案...")

        # 使用 LLMService 生成答案
        from models.llm_service import LLMService
        from config.settings import settings
        from prompts.system_prompts import get_system_prompt

        llm = LLMService()
        context = state.get_context_for_generation()
        system_prompt = get_system_prompt("rag")
        user_prompt = f"问题: {state.question}\n\n{context}"
        answer = llm.generate_text(user_prompt, system_prompt=system_prompt)
        state.answer = answer

        # 计算置信度（基于检索文档数量和相关度）
        if state.retrieved_docs:
            # 同时支持 RetrievedDoc 对象和字典
            scores = []
            for doc in state.retrieved_docs:
                if hasattr(doc, 'score'):
                    scores.append(doc.score)
                elif isinstance(doc, dict):
                    scores.append(doc.get('score', 0.0))

            if scores:
                avg_score = sum(scores) / len(scores)
                state.confidence = min(avg_score, 0.95)
            else:
                state.confidence = 0.5
        else:
            state.confidence = 0.5

        state.add_intermediate_step(
            f"答案已生成，置信度: {state.confidence:.2f}"
        )

        return {
            "answer": state.answer,
            "confidence": state.confidence,
            "current_node": "generate",
        }
    except Exception as e:
        logger.error(f"响应生成失败: {e}")
        state.set_error(f"响应生成失败: {e}")
        return {"error": str(e), "current_node": "generate"}


async def process_tool_calls(state: AgentState) -> Dict[str, Any]:
    """
    工具调用处理节点
    执行 LLM 请求的工具调用（例如搜索、计算等）

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态字典
    """
    logger.info(f"处理工具调用: {len(state.tool_calls)} 个待处理")

    try:
        state.add_intermediate_step("开始处理工具调用...")

        # TODO: 实现工具调用的执行逻辑
        # 支持的工具：
        # - search_tool: 外部搜索
        # - custom_tool: 自定义工具

        state.add_intermediate_step(f"完成 {len(state.tool_calls)} 个工具调用")

        return {
            "tool_results": state.tool_results,
            "current_node": "process_tools",
        }
    except Exception as e:
        logger.error(f"工具调用处理失败: {e}")
        state.set_error(f"工具调用处理失败: {e}")
        return {"error": str(e), "current_node": "process_tools"}


async def decide_next_step(state: AgentState) -> Dict[str, Any]:
    """
    决策节点
    根据当前状态决定下一步应该执行的节点

    Args:
        state: 当前 Agent 状态

    Returns:
        空字典，因为路由决策由 graph.py 中的 _route_decision 函数完成
    """
    logger.info(f"执行决策: iteration={state.iteration}, current_node={state.current_node}")

    # 该节点仅作为条件路由的占位符，实际路由决策由 _route_decision 函数完成
    return {}


async def format_final_response(state: AgentState) -> Dict[str, Any]:
    """
    格式化最终响应节点
    返回整个状态的字典表示
    """
    # 同时支持 AgentState 对象和字典
    if hasattr(state, 'query_id'):
        logger.info(f"执行最终响应格式化: query_id={state.query_id}")
    elif isinstance(state, dict):
        logger.info(f"执行最终响应格式化: query_id={state.get('query_id', 'unknown')}")

    # 同时支持 AgentState 对象和字典
    if hasattr(state, 'to_dict'):
        # 如果是 AgentState 对象
        return state.to_dict()
    elif isinstance(state, dict):
        # 如果是字典
        return state.copy()
    else:
        # 其他类型
        logger.error(f"不支持的状态类型: {type(state)}")
        return {}
