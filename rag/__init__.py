"""
RAG 优化模块

主要包含：
- 提示词工程 (PromptTemplate)
- 置信度计算 (ConfidenceCalculator)
- 问题分类 (classify_question)
- 配置读取 (get_rag_config)
"""

from .rag_optimizer import (
    PromptTemplate,
    ConfidenceCalculator,
    QuestionType,
    classify_question,
    get_rag_config,
)

__all__ = [
    'PromptTemplate',
    'ConfidenceCalculator',
    'QuestionType',
    'classify_question',
    'get_rag_config',
]
