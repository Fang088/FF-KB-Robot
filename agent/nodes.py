"""
LangGraph 节点函数 - 定义 Agent 工作流中的各个节点（已集成性能埋点）
"""

from typing import Optional, Dict, Any
from .state import AgentState, RetrievedDoc
import logging
import time

logger = logging.getLogger(__name__)


async def retrieve_documents(state: AgentState) -> Dict[str, Any]:
    """
    文档检索节点 - 已集成性能埋点
    从知识库中检索与问题相关的文档

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态字典
    """
    retrieval_start = time.time()
    logger.info(f"[{state.query_id}] ⏳ 开始检索文档: kb_id={state.kb_id}")
    print(f"\n⏳ 【检索文档】正在搜索知识库...", end="", flush=True)

    try:
        # 调用 KnowledgeBaseManager 进行检索
        from retrieval.knowledge_base_manager import KnowledgeBaseManager

        kb_manager = KnowledgeBaseManager()

        # 执行检索
        search_start = time.time()
        retrieved_docs = kb_manager.search(
            kb_id=state.kb_id,
            query=state.question,
            top_k=5,
            use_postprocessor=True,
        )
        search_elapsed = (time.time() - search_start) * 1000

        logger.info(f"[{state.query_id}] 向量库返回 {len(retrieved_docs)} 个文档 ({search_elapsed:.2f}ms)")

        # 转换为 RetrievedDoc 对象
        retrieved_docs = [
            RetrievedDoc(
                id=doc.get('id', ''),
                content=doc.get('content', ''),
                score=doc.get('score', 0),
                metadata=doc.get('metadata', {}),
            )
            for doc in retrieved_docs
        ]

        retrieval_elapsed = (time.time() - retrieval_start) * 1000
        print(f" ✅ ({retrieval_elapsed:.0f}ms)")
        logger.info(f"[{state.query_id}] ✅ 检索完成: {len(retrieved_docs)} 个文档, 耗时 {retrieval_elapsed:.2f}ms")

        state.add_intermediate_step(f"检索完成 ({retrieval_elapsed:.0f}ms): {len(retrieved_docs)} 个文档")

        return {"retrieved_docs": retrieved_docs, "current_node": "retrieve"}
    except Exception as e:
        retrieval_elapsed = (time.time() - retrieval_start) * 1000
        print(f" ❌")
        logger.error(f"[{state.query_id}] ❌ 检索失败 ({retrieval_elapsed:.2f}ms): {e}", exc_info=True)
        state.set_error(f"文档检索失败: {e}")
        return {"error": str(e), "current_node": "retrieve"}


async def generate_response(state: AgentState) -> Dict[str, Any]:
    """
    响应生成节点 - 已集成性能埋点和流式输出
    基于检索到的文档和用户问题生成答案

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态字典
    """
    generate_start = time.time()
    logger.info(f"[{state.query_id}] ⏳ 开始生成答案")
    print(f"\n⏳ 【生成答案】", end="", flush=True)

    try:
        # 导入必要的模块
        from models.llm_service import LLMService
        from rag.rag_optimizer import (
            PromptTemplate,
            ConfidenceCalculator,
            classify_question,
        )

        # 步骤1：问题分类（快速）
        classify_start = time.time()
        question_type = classify_question(state.question)
        classify_elapsed = (time.time() - classify_start) * 1000
        logger.debug(f"[{state.query_id}] 问题分类完成 ({classify_elapsed:.2f}ms): {question_type.value}")

        # 步骤2：构建优化的提示词
        docs_dict = []
        for doc in state.retrieved_docs:
            if hasattr(doc, 'to_dict'):
                docs_dict.append(doc.to_dict())
            else:
                docs_dict.append(doc)

        prompt_start = time.time()
        prompts = PromptTemplate.format_rag_prompt(
            question=state.question,
            documents=docs_dict,
            question_type=question_type,
        )
        prompt_elapsed = (time.time() - prompt_start) * 1000
        logger.debug(f"[{state.query_id}] 提示词生成完成 ({prompt_elapsed:.2f}ms), 长度: {len(prompts['user'])} 字符")

        # 步骤3：调用 LLM 生成答案（流式）
        llm = LLMService()
        answer_chunks = []

        llm_start = time.time()

        for chunk in llm.generate_text_stream(
            prompt=prompts['user'],
            system_prompt=prompts['system'],
        ):
            answer_chunks.append(chunk)

        state.answer = "".join(answer_chunks)

        # 安全检查：如果答案为空，给出警告
        if not state.answer or state.answer.strip() == "":
            logger.warning(f"[{state.query_id}] ⚠️ LLM 生成了空答案")
            state.answer = "抱歉，无法生成有效答案。请检查 LLM API 连接和文档质量。"

        llm_elapsed = (time.time() - llm_start) * 1000

        logger.info(f"[{state.query_id}] LLM 生成完成 ({llm_elapsed:.2f}ms): {len(state.answer)} 字符")

        # 步骤4：计算多维度置信度
        confidence_start = time.time()
        confidence_calc = ConfidenceCalculator()

        confidence_result = confidence_calc.calculate(
            question=state.question,
            answer=state.answer,
            documents=docs_dict,
        )

        state.confidence = confidence_result['overall']
        state.metadata['confidence_breakdown'] = confidence_result['breakdown']
        state.metadata['confidence_level'] = confidence_result['level']

        confidence_elapsed = (time.time() - confidence_start) * 1000
        logger.debug(f"[{state.query_id}] 置信度计算完成 ({confidence_elapsed:.2f}ms)")

        generate_elapsed = (time.time() - generate_start) * 1000
        logger.info(f"[{state.query_id}] ✅ 答案生成完成, 耗时 {generate_elapsed:.2f}ms")
        print(f" ✅ 生成完成")

        state.add_intermediate_step(f"答案生成完成 ({generate_elapsed:.0f}ms), 置信度: {state.confidence:.2f}")

        return {
            "answer": state.answer,
            "confidence": state.confidence,
            "metadata": state.metadata,
            "current_node": "generate",
        }
    except Exception as e:
        generate_elapsed = (time.time() - generate_start) * 1000
        print(f" ❌")
        logger.error(f"[{state.query_id}] ❌ 答案生成失败 ({generate_elapsed:.2f}ms): {e}", exc_info=True)
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

        # 注：工具调用功能未在当前版本实现
        # 当前版本仅支持基于检索增强生成 (RAG) 的问答

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
