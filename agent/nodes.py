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
        # 这里将在后续实现与 KnowledgeBaseManager 的集成
        # 暂时返回空的检索结果
        state.add_intermediate_step("开始文档检索...")

        # TODO: 调用 KnowledgeBaseManager 进行检索
        # from retrieval.knowledge_base_manager import KnowledgeBaseManager
        # kb_manager = KnowledgeBaseManager()
        # retrieved_docs = kb_manager.search(state.kb_id, state.question, top_k=5)

        state.add_intermediate_step(f"检索完成，获得 {len(state.retrieved_docs)} 个相关文档")

        return {"retrieved_docs": state.retrieved_docs, "current_node": "retrieve"}
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

        # TODO: 使用 LLMService 生成答案
        # from models.llm_service import LLMService
        # from config.settings import settings
        # from prompts.system_prompts import get_rag_system_prompt

        # llm = LLMService()
        # context = state.get_context_for_generation()
        # system_prompt = get_rag_system_prompt()
        # user_prompt = f"问题: {state.question}\n\n{context}"
        # answer = llm.generate_text(user_prompt, system_prompt=system_prompt)

        # 暂时返回示例答案
        answer = f"关于'{state.question}'的答案。"
        state.answer = answer

        # 计算置信度（基于检索文档数量和相关度）
        if state.retrieved_docs:
            avg_score = sum(doc.score for doc in state.retrieved_docs) / len(
                state.retrieved_docs
            )
            state.confidence = min(avg_score, 0.95)
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


async def decide_next_step(state: AgentState) -> str:
    """
    决策节点
    根据当前状态决定下一步应该执行的节点

    Args:
        state: 当前 Agent 状态

    Returns:
        下一个节点的名称
    """
    logger.info(f"执行决策: iteration={state.iteration}, current_node={state.current_node}")

    # 如果有错误，结束
    if state.error:
        return "end"

    # 如果已有答案，结束
    if state.answer and state.confidence > 0.5:
        return "end"

    # 如果超过最大迭代次数，结束
    if state.iteration >= state.max_iterations:
        logger.warning(f"达到最大迭代次数: {state.max_iterations}")
        if not state.answer:
            state.answer = "无法基于提供的信息生成答案。"
        return "end"

    # 如果还没有检索文档，先检索
    if not state.retrieved_docs:
        return "retrieve"

    # 如果没有生成答案，生成答案
    if not state.answer:
        return "generate"

    # 如果有待处理的工具调用，处理工具
    if len(state.tool_calls) > len(state.tool_results):
        return "process_tools"

    # 默认结束
    return "end"


def format_final_response(state: AgentState) -> Dict[str, Any]:
    """
    格式化最终响应

    Args:
        state: 最终的 Agent 状态

    Returns:
        格式化的响应字典
    """
    return {
        "query_id": state.query_id,
        "kb_id": state.kb_id,
        "question": state.question,
        "answer": state.answer or "无法生成答案",
        "retrieved_docs": [
            {
                "id": doc.id,
                "content": doc.content,
                "score": doc.score,
                "metadata": doc.metadata,
            }
            for doc in state.retrieved_docs
        ],
        "sources": state.sources,
        "confidence": state.confidence,
        "response_time_ms": 0,  # 由调用者计算
        "metadata": {
            "iterations": state.iteration,
            "intermediate_steps": state.intermediate_steps,
            "error": state.error,
        },
    }
