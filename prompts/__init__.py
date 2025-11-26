"""
提示词模块 - 统一管理所有提示词

核心功能：
1. PromptManager - 单例提示词管理器
2. 支持多个版本的提示词（v1, v2, simple等）
3. 提示词模板格式化和验证
4. 支持提示词的导入导出

快速开始：
    from prompts import PromptManager, PromptCategory

    pm = PromptManager.get_instance()

    # 获取提示词
    prompt = pm.get_rag_system_prompt(version="v1")

    # 格式化提示词
    prompt = pm.format_prompt(
        PromptCategory.RAG, "user",
        context="文档", question="问题"
    )
"""

from .prompt_manager import (
    PromptManager,
    PromptCategory,
    PromptVersion,
    RAG_PROMPTS,
    AGENT_PROMPTS,
    RETRIEVAL_PROMPTS,
    ANALYSIS_PROMPTS,
    EVALUATION_PROMPTS,
)

# 便捷访问单例
prompt_manager = PromptManager.get_instance()

__all__ = [
    "PromptManager",
    "PromptCategory",
    "PromptVersion",
    "prompt_manager",
    "RAG_PROMPTS",
    "AGENT_PROMPTS",
    "RETRIEVAL_PROMPTS",
    "ANALYSIS_PROMPTS",
    "EVALUATION_PROMPTS",
]
