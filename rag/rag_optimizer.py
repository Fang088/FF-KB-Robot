"""
RAG 管道优化器 - 集成检索、过滤、生成的完整方案
设计目标：
  1. 提示词工程专业化
  2. 置信度多维度计算
  3. 相似度智能过滤
  4. 完整的质量控制
"""

from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass, field
from enum import Enum
import re

logger = logging.getLogger(__name__)


class QuestionType(Enum):
    """问题类型分类"""
    FACTUAL = "factual"          # 事实性问题："XX是什么"
    EXPLANATORY = "explanatory"  # 解释性问题："为什么..."
    PROCEDURAL = "procedural"    # 操作性问题："怎样做..."
    COMPARATIVE = "comparative"  # 对比性问题："XX vs YY"
    CREATIVE = "creative"        # 创意性问题："建议..."


def get_rag_config() -> Dict[str, Any]:
    """
    从 settings 读取 RAG 配置（避免硬编码）

    Returns:
        RAG 配置字典
    """
    from config.settings import settings

    return {
        # 检索配置
        'retrieval_top_k': settings.RETRIEVAL_TOP_K,
        'similarity_threshold': settings.RETRIEVAL_SIMILARITY_THRESHOLD,
        'dedup_threshold': settings.RETRIEVAL_DEDUP_THRESHOLD,

        # 生成配置
        'max_tokens': settings.GENERATION_MAX_TOKENS,
        'temperature': settings.GENERATION_TEMPERATURE,

        # 置信度配置
        'min_confidence': settings.MIN_CONFIDENCE,
        'confidence_weights': {
            'retrieval': settings.CONFIDENCE_W_RETRIEVAL,
            'keyword_match': settings.CONFIDENCE_W_KEYWORD_MATCH,
            'completeness': settings.CONFIDENCE_W_COMPLETENESS,
            'consistency': settings.CONFIDENCE_W_CONSISTENCY,
            'answer_quality': settings.CONFIDENCE_W_ANSWER_QUALITY,
        }
    }


class PromptTemplate:
    """专业的提示词模板 - 优化版"""

    # RAG 系统提示词 - 精简高效版
    # 移除冗余步骤，保留核心要求，加快 LLM 生成速度
    RAG_SYSTEM_PROMPT = """你是一个知识库问答助手。直接、准确地回答问题。

要求：
1. 仅基于提供的文档回答
2. 清晰简洁，避免冗余
3. 如文档信息不足，明确指出"""

    # 简洁版 RAG 提示词 - 用于所有场景
    RAG_SIMPLE_PROMPT = """【参考文档】
{context}

【问题】{question}

请直接回答："""

    @staticmethod
    def format_rag_prompt(
        question: str,
        documents: List[Dict[str, Any]],
        question_type: QuestionType = QuestionType.FACTUAL,
    ) -> Dict[str, str]:
        """
        格式化 RAG 提示词 - 统一使用简洁版本以提升生成速度

        Args:
            question: 用户问题
            documents: 检索到的文档列表
            question_type: 问题类型（保留向后兼容，但不影响输出）

        Returns:
            {system: 系统提示词, user: 用户提示词}
        """
        # 格式化上下文
        context = PromptTemplate._format_context(documents)

        # 统一使用简洁版本 - 加快生成速度
        user_prompt = PromptTemplate.RAG_SIMPLE_PROMPT.format(
            context=context,
            question=question,
        )

        return {
            "system": PromptTemplate.RAG_SYSTEM_PROMPT,
            "user": user_prompt,
        }

    @staticmethod
    def _format_context(documents: List[Dict[str, Any]]) -> str:
        """
        格式化上下文 - 精简版本，仅保留关键内容

        Args:
            documents: 文档列表

        Returns:
            格式化的上下文字符串
        """
        if not documents:
            return "【提示】未找到相关文档。"

        # 精简格式，去除冗余信息
        formatted = []
        for i, doc in enumerate(documents, 1):
            # 提取内容
            if isinstance(doc, dict):
                content = doc.get('content', '')
            else:
                content = getattr(doc, 'content', '')

            formatted.append(f"{i}. {content}")

        return "\n".join(formatted)


class ConfidenceCalculator:
    """
    多维度置信度计算器 - 改进版

    置信度反映答案的可信度，综合考虑：
    1. 检索质量（最重要）- 文档与问题的匹配程度
    2. 答案完整度 - 答案长度和段落数
    3. 关键词覆盖 - 问题的关键词是否在答案中
    4. 答案质量 - 表达的专业性和清晰度
    5. 答案一致性 - 答案与文档内容的一致程度
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化置信度计算器

        Args:
            config: RAG 配置字典（如果为 None，从 settings 读取）
        """
        if config is None:
            config = get_rag_config()

        self.config = config
        # 新的权重分配（优先级：检索 > 完整度 > 关键词 > 质量 > 一致性）
        self.weights = {
            'retrieval': 0.45,           # 检索质量（最重要）
            'completeness': 0.25,        # 答案完整度
            'keyword_match': 0.15,       # 关键词匹配
            'answer_quality': 0.10,      # 答案质量
            'consistency': 0.05,         # 答案一致性
        }

    def calculate(
        self,
        question: str,
        answer: str,
        documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        计算多维度置信度

        Args:
            question: 用户问题
            answer: 生成的答案
            documents: 检索到的文档

        Returns:
            {
                'overall': 总体置信度 (0-1),
                'breakdown': 各维度分数,
                'level': 置信度等级 (low/medium/high),
            }
        """
        if not documents or not answer:
            return {
                'overall': 0.0,
                'breakdown': {},
                'level': 'low',
            }

        # 各维度计算（按优先级）
        retrieval_score = self._calculate_retrieval_score(documents)      # 45% 权重
        completeness_score = self._calculate_completeness(answer)         # 25% 权重
        keyword_score = self._calculate_keyword_match(question, answer)   # 15% 权重
        quality_score = self._calculate_answer_quality(answer)            # 10% 权重
        consistency_score = self._calculate_consistency(answer, documents) # 5% 权重

        # 加权综合
        overall = (
            retrieval_score * self.weights['retrieval'] +
            completeness_score * self.weights['completeness'] +
            keyword_score * self.weights['keyword_match'] +
            quality_score * self.weights['answer_quality'] +
            consistency_score * self.weights['consistency']
        )

        # 确保在 0-1 范围内
        overall = min(max(overall, 0.0), 1.0)

        # 判断置信度等级
        if overall >= 0.75:
            level = 'high'
        elif overall >= 0.5:
            level = 'medium'
        else:
            level = 'low'

        breakdown = {
            'retrieval': round(retrieval_score, 2),
            'completeness': round(completeness_score, 2),
            'keyword_match': round(keyword_score, 2),
            'answer_quality': round(quality_score, 2),
            'consistency': round(consistency_score, 2),
        }

        # 详细的日志输出，包括计算过程
        print(f"\n[置信度详细计算]")
        print(f"  检索质量: {retrieval_score:.3f} × 0.45 = {retrieval_score * 0.45:.3f}")
        print(f"  答案完整度: {completeness_score:.3f} × 0.25 = {completeness_score * 0.25:.3f}")
        print(f"  关键词匹配: {keyword_score:.3f} × 0.15 = {keyword_score * 0.15:.3f}")
        print(f"  答案质量: {quality_score:.3f} × 0.10 = {quality_score * 0.1:.3f}")
        print(f"  答案一致性: {consistency_score:.3f} × 0.05 = {consistency_score * 0.05:.3f}")
        print(f"  ────────────────────────")
        print(f"  总置信度: {overall:.3f}")

        logger.info(
            f"置信度计算: overall={overall:.2f}, level={level}, "
            f"retrieval={retrieval_score:.2f}, completeness={completeness_score:.2f}, "
            f"keyword={keyword_score:.2f}, quality={quality_score:.2f}, consistency={consistency_score:.2f}"
        )

        return {
            'overall': overall,
            'breakdown': breakdown,
            'level': level,
        }

    def _calculate_retrieval_score(
        self, documents: List[Dict[str, Any]]
    ) -> float:
        """
        计算检索质量分数 - 最关键的维度！

        说明：
        - HNSW 返回的 score 是**距离值**，不是相似度
        - 距离越小，说明向量越接近（越相似）
        - 距离 0: 完全相同
        - 距离 < 1: 非常相似
        - 距离 1-3: 比较相似
        - 距离 > 3: 相关度一般

        策略：
        - 最佳文档相似度：80% 权重
        - 其他文档平均相似度：20% 权重

        Args:
            documents: 文档列表

        Returns:
            检索分数 (0-1)，越接近 1 越好
        """
        if not documents:
            return 0.0

        # 提取所有文档的距离分数
        distances = []
        for doc in documents:
            if isinstance(doc, dict):
                distance = doc.get('score', 0)
            else:
                distance = getattr(doc, 'score', 0)
            distances.append(distance)

        if not distances:
            return 0.0

        # 关键：将距离转换为相似度
        # 使用公式: similarity = 1 / (1 + distance)
        # 这样距离 0 → 相似度 1, 距离 1 → 相似度 0.5, 距离 3 → 相似度 0.25
        similarities = [1.0 / (1.0 + distance) for distance in distances]

        # 最佳文档（距离最小）的相似度，80% 权重
        best_similarity = max(similarities)

        # 其他文档的平均相似度，20% 权重
        avg_similarity = sum(similarities) / len(similarities)

        # 综合评分
        retrieval_score = best_similarity * 0.8 + avg_similarity * 0.2

        logger.debug(
            f"检索得分: distances={[f'{d:.3f}' for d in distances]}, "
            f"similarities={[f'{s:.3f}' for s in similarities]}, "
            f"best={best_similarity:.3f}, avg={avg_similarity:.3f}, "
            f"final={retrieval_score:.3f}"
        )

        return min(retrieval_score, 1.0)

    def _calculate_keyword_match(self, question: str, answer: str) -> float:
        """
        计算关键词匹配度

        策略：
        - 提取问题中的关键词（去除停用词）
        - 检查这些关键词是否出现在答案中
        - 匹配比例越高，分数越高

        Args:
            question: 问题
            answer: 答案

        Returns:
            匹配分数 (0-1)
        """
        # 提取问题关键词（移除停用词）
        keywords = self._extract_keywords(question)

        if not keywords:
            # 没有提取到关键词，返回中等分数
            return 0.6

        # 计算有多少关键词出现在答案中
        answer_lower = answer.lower()
        matched = sum(1 for kw in keywords if kw in answer_lower)

        keyword_match = matched / len(keywords)

        logger.debug(
            f"关键词匹配: 总数={len(keywords)}, 匹配={matched}, "
            f"关键词={keywords}, 匹配度={keyword_match:.3f}"
        )

        return min(keyword_match, 1.0)

    def _calculate_completeness(self, answer: str) -> float:
        """
        计算答案完整度

        策略：
        - 答案长度：目标 150-400 字符（考虑到 LLM 的实际输出）
        - 段落数：LLM 通常不会产生明显的多段落，所以权重降低
        - 句子数：检查是否有多个句子（比段落数更实际）

        Args:
            answer: 答案

        Returns:
            完整度分数 (0-1)
        """
        answer_len = len(answer.strip())
        # 更好的段落计数方式：按句号、逗号等分割
        sentences = [s.strip() for s in answer.replace('，', '。').replace(',', '.').split('。') if s.strip()]
        sentence_count = len(sentences)

        # 长度评分：150 字符为基准
        # LLM 一般输出 100-600 字符为正常范围
        if answer_len < 50:
            length_score = min(answer_len / 100, 0.3)  # 最多 0.3
        elif answer_len < 150:
            length_score = 0.3 + (answer_len - 50) / 333  # 0.3-0.6
        elif answer_len < 300:
            length_score = 0.6 + (answer_len - 150) / 300  # 0.6-0.8
        elif answer_len < 600:
            length_score = 0.8 + (answer_len - 300) / 600  # 0.8-1.0
        else:
            length_score = 1.0

        # 句子评分：更符合 LLM 输出的实际情况
        if sentence_count == 0:
            sentence_score = 0.3
        elif sentence_count == 1:
            sentence_score = 0.6
        elif sentence_count < 3:
            sentence_score = 0.75
        else:
            sentence_score = 1.0

        # 综合：长度 60%，句子数 40%（降低了对多段落的依赖）
        completeness = length_score * 0.6 + sentence_score * 0.4

        logger.debug(
            f"完整度评分: 长度={answer_len}字符({length_score:.2f}), "
            f"句子={sentence_count}个({sentence_score:.2f}), "
            f"综合={completeness:.3f}"
        )

        return min(completeness, 1.0)

    def _calculate_consistency(
        self, answer: str, documents: List[Dict[str, Any]]
    ) -> float:
        """
        计算答案一致性

        策略：
        - 提取答案中的关键词和实体
        - 检查这些是否出现在源文档中
        - 出现得越多，说明答案基于文档的内容

        Args:
            answer: 答案
            documents: 文档列表

        Returns:
            一致性分数 (0-1)
        """
        if not documents:
            return 0.6

        # 合并所有文档内容
        doc_texts = []
        for doc in documents:
            if isinstance(doc, dict):
                content = doc.get('content', '')
            else:
                content = getattr(doc, 'content', '')
            doc_texts.append(content.lower())

        combined_docs = ' '.join(doc_texts)

        # 策略：检查答案中的关键信息是否在文档中出现
        # 1. 检查数字是否出现
        numbers = re.findall(r'\d+', answer)
        if numbers:
            numbers_in_docs = sum(1 for num in numbers if num in combined_docs)
            number_match_ratio = numbers_in_docs / len(numbers)
        else:
            # 如果没有数字，不处罚，设为 1.0
            numbers_in_docs = 0
            number_match_ratio = 1.0

        # 2. 检查关键词是否出现
        keywords = self._extract_keywords(answer)
        if keywords:
            keywords_in_docs = sum(1 for kw in keywords if kw in combined_docs)
            keyword_match_ratio = keywords_in_docs / len(keywords)
        else:
            keywords_in_docs = 0
            keyword_match_ratio = 1.0

        # 综合评分：数字 20%, 关键词 80%
        # 降低了对数字的依赖，因为并非所有答案都包含数字
        consistency = number_match_ratio * 0.2 + keyword_match_ratio * 0.8

        logger.debug(
            f"一致性评分: 数字{numbers_in_docs}/{len(numbers) if numbers else 0}({number_match_ratio:.2f}), "
            f"关键词{keywords_in_docs}/{len(keywords) if keywords else 0}({keyword_match_ratio:.2f}), "
            f"综合={consistency:.3f}"
        )

        return min(consistency, 1.0)

    def _calculate_answer_quality(self, answer: str) -> float:
        """
        计算答案质量

        策略：
        - 表达清晰度：有适当的标点符号
        - 词汇多样性：不要重复过多相同的词
        - 信息明确性：避免使用模糊表述（可能、也许等）
        - 长度适宜性：太短说明不够完整，太长说明冗余

        Args:
            answer: 答案

        Returns:
            质量分数 (0-1)
        """
        quality = 0.5  # 基础分

        # 1. 标点符号检查（2 分）
        if answer.count('。') >= 1 or answer.count('.') >= 1:
            quality += 0.1
        if answer.count('，') >= 2 or answer.count(',') >= 2:
            quality += 0.1

        # 2. 词汇多样性检查（2 分）
        words = answer.split()
        if len(words) > 0:
            unique_ratio = len(set(words)) / len(words)
            if unique_ratio > 0.7:
                quality += 0.1
            if unique_ratio > 0.8:
                quality += 0.1

        # 3. 避免模糊表述（2 分）
        vague_phrases = [
            '可能', '也许', '感觉', '似乎', '不太确定',
            'might', 'maybe', 'probably', 'seems', 'unclear'
        ]
        vague_count = sum(1 for phrase in vague_phrases if phrase in answer.lower())

        if vague_count == 0:
            quality += 0.2
        elif vague_count == 1:
            quality += 0.1

        # 4. 长度适宜性（2 分）
        answer_len = len(answer.strip())
        if 100 < answer_len < 1000:
            quality += 0.15
        if 200 < answer_len < 800:
            quality += 0.05

        logger.debug(
            f"答案质量评分: 长度={answer_len}, 标点=✓, "
            f"词汇多样性={len(set(words))}/{len(words) if words else 0}, "
            f"模糊词={vague_count}, 综合={min(quality, 1.0):.3f}"
        )

        return min(quality, 1.0)

    def _extract_keywords(self, text: str) -> List[str]:
        """
        提取关键词（去除停用词）

        Args:
            text: 输入文本

        Returns:
            关键词列表
        """
        stopwords = {
            # 英文
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'is', 'are', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            # 中文
            '的', '是', '了', '在', '和', '这', '个', '有', '什么', '哪',
            '怎样', '怎么', '如何', '请', '帮', '我', '他', '她', '它',
            '都', '还', '也', '只', '就', '很', '太', '才', '去', '来',
        }

        keywords = [
            word.lower() for word in text.split()
            if len(word) > 1 and word.lower() not in stopwords
        ]

        return keywords


def classify_question(question: str) -> QuestionType:
    """
    分类问题类型

    Args:
        question: 问题文本

    Returns:
        问题类型
    """
    question_lower = question.lower()

    # 操作性问题
    if any(word in question_lower for word in [
        '怎样', '怎么', '如何', '怎样做', '步骤', 'how to', 'how do'
    ]):
        return QuestionType.PROCEDURAL

    # 对比性问题
    if any(word in question_lower for word in [
        '对比', '差异', 'vs', 'versus', '区别', '相比'
    ]):
        return QuestionType.COMPARATIVE

    # 创意性问题
    if any(word in question_lower for word in [
        '建议', '推荐', '想法', '想象', '创意', 'suggest', 'recommend'
    ]):
        return QuestionType.CREATIVE

    # 解释性问题
    if any(word in question_lower for word in [
        '为什么', '原因', '因为', 'why', 'reason'
    ]):
        return QuestionType.EXPLANATORY

    # 默认：事实性问题
    return QuestionType.FACTUAL
