"""
LangGraph 节点函数 - 定义 Agent 工作流中的各个节点
"""

from typing import Optional, Dict, Any
from .state import AgentState, RetrievedDoc
import logging

logger = logging.getLogger(__name__)


async def retrieve_documents(state: AgentState) -> Dict[str, Any]:
    """
    文档检索节点 - 优化版本
    从知识库中检索与问题相关的文档（集成检索后处理）

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

        # 检索文档（已内置后处理功能）
        retrieved_docs = kb_manager.search(
            kb_id=state.kb_id,
            query=state.question,
            top_k=5,
            use_postprocessor=True,  # 启用后处理（去重、重排等）
        )

        # 调试日志：记录检索结果
        logger.info(f"向量库返回 {len(retrieved_docs)} 个文档")
        for i, doc in enumerate(retrieved_docs):
            score = doc.get('score', 0) if isinstance(doc, dict) else getattr(doc, 'score', 0)
            content = doc.get('content', '') if isinstance(doc, dict) else getattr(doc, 'content', '')
            logger.debug(f"  文档{i+1}: score={score:.3f}, content_len={len(content)}, "
                        f"content_preview='{content[:80]}...'")

        # 将字典转换为 RetrievedDoc 对象
        # 只保留 RetrievedDoc 需要的字段，过滤掉额外的字段（如 combined_score）
        retrieved_docs = [
            RetrievedDoc(
                id=doc.get('id', ''),
                content=doc.get('content', ''),
                score=doc.get('score', 0),
                metadata=doc.get('metadata', {}),
            )
            for doc in retrieved_docs
        ]

        logger.info(f"转换后获得 {len(retrieved_docs)} 个 RetrievedDoc 对象")

        state.add_intermediate_step(
            f"检索完成，获得 {len(retrieved_docs)} 个相关文档"
        )

        return {"retrieved_docs": retrieved_docs, "current_node": "retrieve"}
    except Exception as e:
        logger.error(f"文档检索失败: {e}", exc_info=True)
        state.set_error(f"文档检索失败: {e}")
        return {"error": str(e), "current_node": "retrieve"}


async def generate_response(state: AgentState) -> Dict[str, Any]:
    """
    响应生成节点 - 优化版本
    基于检索到的文档和用户问题生成答案（集成提示词工程和多维度置信度计算）

    Args:
        state: 当前 Agent 状态

    Returns:
        更新后的状态字典
    """
    logger.info(f"执行响应生成: question={state.question}")

    try:
        state.add_intermediate_step("开始生成答案...")

        # 导入必要的模块
        from models.llm_service import LLMService
        from rag.rag_optimizer import (
            PromptTemplate,
            ConfidenceCalculator,
            classify_question,
        )

        # 步骤1：问题分类
        question_type = classify_question(state.question)
        state.add_intermediate_step(f"问题类型识别: {question_type.value}")

        # 步骤2：构建优化的提示词
        # 将 RetrievedDoc 对象转换为字典格式（便于处理）
        docs_dict = []
        for doc in state.retrieved_docs:
            if hasattr(doc, 'to_dict'):
                docs_dict.append(doc.to_dict())
            else:
                docs_dict.append(doc)

        # 调试日志：检查检索结果
        logger.info(
            f"检索结果统计: 总数={len(docs_dict)}, "
            f"问题='{state.question}', "
            f"问题类型={question_type.value}"
        )
        for i, doc in enumerate(docs_dict):
            score = doc.get('score', 0) if isinstance(doc, dict) else getattr(doc, 'score', 0)
            content_preview = doc.get('content', '')[:100] if isinstance(doc, dict) else getattr(doc, 'content', '')[:100]
            logger.debug(f"  文档{i+1}: score={score:.3f}, content_preview='{content_preview}...'")

        # 使用专业的提示词模板
        prompts = PromptTemplate.format_rag_prompt(
            question=state.question,
            documents=docs_dict,
            question_type=question_type,
        )

        # 调试日志：记录生成的提示词
        logger.debug(f"系统提示词长度: {len(prompts['system'])} 字符")
        logger.debug(f"用户提示词长度: {len(prompts['user'])} 字符")
        logger.debug(f"用户提示词内容:\n{prompts['user'][:500]}...")

        # 步骤3：调用 LLM 生成答案
        llm = LLMService()
        answer = llm.generate_text(
            prompt=prompts['user'],
            system_prompt=prompts['system'],
        )
        state.answer = answer
        state.add_intermediate_step("答案生成完成")

        # 调试日志：记录生成的答案
        logger.info(f"生成答案长度: {len(answer)} 字符")
        logger.debug(f"生成答案内容:\n{answer[:500]}...")

        # 步骤4：计算多维度置信度
        confidence_calc = ConfidenceCalculator()  # 从 settings 自动读取配置

        confidence_result = confidence_calc.calculate(
            question=state.question,
            answer=answer,
            documents=docs_dict,
        )

        state.confidence = confidence_result['overall']
        state.metadata['confidence_breakdown'] = confidence_result['breakdown']
        state.metadata['confidence_level'] = confidence_result['level']

        state.add_intermediate_step(
            f"置信度计算完成: {state.confidence:.2f} ({confidence_result['level']})"
        )

        return {
            "answer": state.answer,
            "confidence": state.confidence,
            "metadata": state.metadata,
            "current_node": "generate",
        }
    except Exception as e:
        logger.error(f"响应生成失败: {e}", exc_info=True)
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
