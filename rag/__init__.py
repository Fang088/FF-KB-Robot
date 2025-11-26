"""
RAG 优化模块 - 提示词工程和置信度计算

核心功能：
1. PromptTemplate - RAG提示词模板
2. ConfidenceCalculator - 置信度计算器
3. QuestionType - 问题分类枚举
4. classify_question - 问题分类函数

快速开始：
    from rag import PromptTemplate, ConfidenceCalculator

    prompt = PromptTemplate.RAG_SYSTEM_PROMPT
    calc = ConfidenceCalculator()
    confidence = calc.calculate(retrieval_score, ...)
"""

from .rag_optimizer import (
    PromptTemplate,
    ConfidenceCalculator,
    QuestionType,
    classify_question,
    get_rag_config,
)

__all__ = [
    "PromptTemplate",
    "ConfidenceCalculator",
    "QuestionType",
    "classify_question",
    "get_rag_config",
]
