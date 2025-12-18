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
    文档检索节点 - 已集成性能埋点 + 文件内容融合
    从知识库中检索与问题相关的文档，并融合上传文件的内容

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
        from config.settings import settings

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

        # 【新增】如果有上传的文件，融合文件内容到检索结果
        if state.file_contents:
            try:
                logger.info(f"[{state.query_id}] 【新增】融合 {len(state.file_contents)} 个文件内容到检索结果")

                # 从文件内容中创建虚拟文档
                file_docs = []
                for filename, content in state.file_contents.items():
                    if content.strip():  # 只处理有实际内容的文件
                        # 构建文件文档
                        file_doc = {
                            'id': f"file_{filename}",
                            'content': content,
                            'score': 0.9,  # 文件内容给予高权重
                            'metadata': {
                                'source': 'uploaded_file',
                                'filename': filename,
                                'type': 'file_content'
                            }
                        }
                        file_docs.append(file_doc)

                # 【新增】融合策略：文件内容 + 知识库内容
                # 优先级：文件内容 > 知识库内容
                all_docs = file_docs + retrieved_docs

                # 【新增】按相关性重排序（文件内容已有较高分数）
                # 应用权重倍数
                for doc in all_docs:
                    if doc.get('metadata', {}).get('source') == 'uploaded_file':
                        # 文件内容加权
                        doc['score'] = doc.get('score', 0.9) * settings.FILE_CONTENT_CONTEXT_WEIGHT
                    else:
                        # 知识库内容基础权重
                        doc['score'] = doc.get('score', 0) * settings.KNOWLEDGE_BASE_CONTEXT_WEIGHT

                # 按分数排序（高到低）
                all_docs.sort(key=lambda x: x.get('score', 0), reverse=True)

                # 截断到 top_k
                retrieved_docs = all_docs[:5]

                logger.info(f"[{state.query_id}] 【新增】融合后共 {len(retrieved_docs)} 个文档（包含文件内容）")

            except Exception as e:
                logger.warning(f"[{state.query_id}] 融合文件内容失败: {e}，继续使用知识库检索结果")

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
    响应生成节点 - 已集成性能埋点和流式输出 + 多模态vision支持
    基于检索到的文档和用户问题生成答案
    【新增】支持图片分析（如果上传了图片文件）

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
        import json
        import re

        # 【新增】提取图片数据（如果存在）
        images_data = []
        if state.file_contents:
            for filename, content in state.file_contents.items():
                # 检测是否为图片数据（带特殊标记）
                if content.startswith("__IMAGE_DATA__") and content.endswith("__IMAGE_DATA_END__"):
                    try:
                        # 提取JSON数据
                        json_str = content.replace("__IMAGE_DATA__", "").replace("__IMAGE_DATA_END__", "")
                        image_info = json.loads(json_str)

                        # 添加到图片列表
                        images_data.append({
                            "format": image_info.get("format", "PNG"),
                            "base64": image_info.get("base64", ""),
                            "filename": filename
                        })

                        logger.info(f"[{state.query_id}] 检测到图片文件: {filename}, 格式: {image_info.get('format')}")
                    except Exception as e:
                        logger.warning(f"解析图片数据失败 ({filename}): {e}")

        # 步骤1：问题分类（快速）
        classify_start = time.time()
        question_type = classify_question(state.question)
        classify_elapsed = (time.time() - classify_start) * 1000
        logger.debug(f"[{state.query_id}] 问题分类完成 ({classify_elapsed:.2f}ms): {question_type.value}")

        # 步骤2：构建优化的提示词
        docs_dict = []
        for doc in state.retrieved_docs:
            if hasattr(doc, 'to_dict'):
                doc_dict = doc.to_dict()
            else:
                doc_dict = doc

            # 【新增】过滤掉图片数据文档（避免base64干扰Prompt）
            content = doc_dict.get('content', '')
            if not (content.startswith("__IMAGE_DATA__") and content.endswith("__IMAGE_DATA_END__")):
                docs_dict.append(doc_dict)

        prompt_start = time.time()
        prompts = PromptTemplate.format_rag_prompt(
            question=state.question,
            documents=docs_dict,
            question_type=question_type,
        )

        # 【新增】如果有图片，在Prompt中添加提示
        if images_data:
            prompts['user'] += f"\n\n【附加信息】用户上传了 {len(images_data)} 张图片，请结合图片内容回答问题。"

        prompt_elapsed = (time.time() - prompt_start) * 1000
        logger.debug(f"[{state.query_id}] 提示词生成完成 ({prompt_elapsed:.2f}ms), 长度: {len(prompts['user'])} 字符")

        # 步骤3：调用 LLM 生成答案（流式 + vision支持）
        llm = LLMService()
        answer_chunks = []

        llm_start = time.time()

        # 【新增】传递图片数据（如果存在）
        for chunk in llm.generate_text_stream(
            prompt=prompts['user'],
            system_prompt=prompts['system'],
            images=images_data if images_data else None  # 传递图片
        ):
            answer_chunks.append(chunk)

        state.answer = "".join(answer_chunks)

        # 安全检查：如果答案为空，给出警告
        if not state.answer or state.answer.strip() == "":
            logger.warning(f"[{state.query_id}] ⚠️ LLM 生成了空答案")
            state.answer = "抱歉，无法生成有效答案。请检查 LLM API 连接和文档质量。"

        llm_elapsed = (time.time() - llm_start) * 1000

        logger.info(f"[{state.query_id}] LLM 生成完成 ({llm_elapsed:.2f}ms): {len(state.answer)} 字符")
        if images_data:
            logger.info(f"[{state.query_id}] ✅ 使用了多模态vision分析 {len(images_data)} 张图片")

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
