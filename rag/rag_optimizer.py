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
    """专业的提示词模板"""

    # RAG 系统提示词 - 改进版
    RAG_SYSTEM_PROMPT = """你是一个专业、严谨的知识库问答助手。你需要遵循以下步骤进行回答：

【第一步：理解问题】
- 分析用户问题的核心需求
- 识别问题涉及的关键概念和实体
- 确定问题属于什么类型（定义、解释、对比等）

【第二步：查阅参考文档】
- 仔细阅读所有提供的参考文档
- 找出与问题最相关的部分
- 检查文档之间是否存在补充或矛盾信息

【第三步：组织答案】
- 直接、清晰地回答问题的核心
- 用文档中的具体证据支持你的观点
- 如果文档中有多个相关信息，要综合呈现

【第四步：质量检查】
- 检查答案是否完整回答了问题
- 确保答案基于提供的文档内容
- 如果文档信息不足，明确指出限制

【回答格式要求】

## 直接答案
[简洁、准确地直接回答问题，1-2 句]

## 详细解释
[基于参考文档的详细说明，2-3 段]

## 关键依据
- [列出支持答案的关键信息来源]

## 补充说明
[任何需要澄清的地方或相关提示]

【重要提醒】
- 只基于提供的文档进行回答
- 不要添加文档中没有的信息
- 如果无法完全回答，请说明原因
- 保持专业但友好的语气"""

    # 基础 RAG 提示词（简洁版本，用于简单问题）
    RAG_SIMPLE_PROMPT = """你是一个知识库问答助手。根据以下参考文档直接回答用户的问题。

要求：
1. 直接、清晰地回答
2. 只基于提供的文档
3. 引用具体信息来源

【参考文档】
{context}

【用户问题】
{question}

请直接给出答案："""

    @staticmethod
    def format_rag_prompt(
        question: str,
        documents: List[Dict[str, Any]],
        question_type: QuestionType = QuestionType.FACTUAL,
    ) -> Dict[str, str]:
        """
        格式化 RAG 提示词 - 根据问题类型选择合适的模板

        Args:
            question: 用户问题
            documents: 检索到的文档列表
            question_type: 问题类型

        Returns:
            {system: 系统提示词, user: 用户提示词}
        """
        # 格式化上下文
        context = PromptTemplate._format_context(documents)

        # 简单问题用简洁模板
        if question_type in [QuestionType.FACTUAL] and len(documents) <= 3:
            user_prompt = PromptTemplate.RAG_SIMPLE_PROMPT.format(
                context=context,
                question=question,
            )
            return {
                "system": PromptTemplate.RAG_SYSTEM_PROMPT,
                "user": user_prompt,
            }

        # 复杂问题用详细模板
        user_prompt = f"""【用户问题】
{question}

【参考文档】
{context}

请按照要求进行回答。"""

        return {
            "system": PromptTemplate.RAG_SYSTEM_PROMPT,
            "user": user_prompt,
        }

    @staticmethod
    def _format_context(documents: List[Dict[str, Any]]) -> str:
        """
        格式化上下文 - 将文档列表转换为易读的字符串

        Args:
            documents: 文档列表

        Returns:
            格式化的上下文字符串
        """
        if not documents:
            return """【说明】
当前知识库中未找到与您的问题相关的文档。
这可能是因为：
1. 知识库内容还不完整
2. 您的问题表述与文档的用词差异较大
3. 知识库中可能确实没有相关信息

系统将基于我的通用知识进行回答，但准确性可能有限。"""

        formatted = []
        for i, doc in enumerate(documents, 1):
            # 提取字段（支持两种格式：RetrievedDoc 和字典）
            if isinstance(doc, dict):
                content = doc.get('content', '')
                score = doc.get('score', 0)
                metadata = doc.get('metadata', {})
            else:
                # 对象格式
                content = getattr(doc, 'content', '')
                score = getattr(doc, 'score', 0)
                metadata = getattr(doc, 'metadata', {})

            filename = metadata.get('filename', 'Unknown') if isinstance(
                metadata, dict) else 'Unknown'

            formatted.append(f"""【文档 {i}】
来源: {filename}
相关度: {score:.0%}
内容:
{content}
""")

        return "\n".join(formatted)


class ConfidenceCalculator:
    """多维度置信度计算器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化置信度计算器

        Args:
            config: RAG 配置字典（如果为 None，从 settings 读取）
        """
        if config is None:
            config = get_rag_config()

        self.config = config
        self.weights = config['confidence_weights']

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

        # 各维度计算
        retrieval_score = self._calculate_retrieval_score(documents)
        keyword_score = self._calculate_keyword_match(question, answer)
        completeness_score = self._calculate_completeness(answer)
        consistency_score = self._calculate_consistency(answer, documents)
        quality_score = self._calculate_answer_quality(answer)

        # 加权综合
        overall = (
            retrieval_score * self.weights['retrieval'] +
            keyword_score * self.weights['keyword_match'] +
            completeness_score * self.weights['completeness'] +
            consistency_score * self.weights['consistency'] +
            quality_score * self.weights['answer_quality']
        )

        # 确保在 0-0.95 范围内
        overall = min(max(overall, 0.0), 0.95)

        # 判断置信度等级
        if overall >= 0.7:
            level = 'high'
        elif overall >= 0.5:
            level = 'medium'
        else:
            level = 'low'

        breakdown = {
            'retrieval': retrieval_score,
            'keyword_match': keyword_score,
            'completeness': completeness_score,
            'consistency': consistency_score,
            'answer_quality': quality_score,
        }

        logger.debug(
            f"Confidence calculation: overall={overall:.2f}, level={level}, "
            f"breakdown={breakdown}"
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
        计算检索质量分数

        Args:
            documents: 文档列表

        Returns:
            检索分数 (0-1)
        """
        if not documents:
            return 0.0

        # 提取所有文档的相似度分数
        scores = []
        for doc in documents:
            if isinstance(doc, dict):
                score = doc.get('score', 0)
            else:
                score = getattr(doc, 'score', 0)
            scores.append(score)

        if not scores:
            return 0.0

        # 策略：
        # - 最高分 80% 权重（最相关文档）
        # - 平均分 20% 权重（整体质量）
        best_score = max(scores)
        avg_score = sum(scores) / len(scores)

        retrieval_score = best_score * 0.8 + avg_score * 0.2

        return min(retrieval_score, 1.0)

    def _calculate_keyword_match(self, question: str, answer: str) -> float:
        """
        计算关键词匹配度

        Args:
            question: 问题
            answer: 答案

        Returns:
            匹配分数 (0-1)
        """
        # 提取问题关键词（移除停用词）
        keywords = self._extract_keywords(question)

        if not keywords:
            return 0.5

        # 计算有多少关键词出现在答案中
        answer_lower = answer.lower()
        matched = sum(1 for kw in keywords if kw in answer_lower)

        keyword_match = matched / len(keywords)

        return min(keyword_match, 1.0)

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            '的', '是', '了', '在', '和', '这', '个', '有', '什么', '哪',
            '怎样', '怎么', '如何', '请', '帮',
        }

        keywords = [
            word.lower() for word in text.split()
            if len(word) > 1 and word.lower() not in stopwords
        ]

        return keywords

    def _calculate_completeness(self, answer: str) -> float:
        """
        计算答案完整度

        Args:
            answer: 答案

        Returns:
            完整度分数 (0-1)
        """
        # 策略：
        # - 长度足够（> 100 字符）：80% 分
        # - 有多个段落（> 1 段）：20% 分
        answer_len = len(answer.strip())
        paragraph_count = len([p for p in answer.split('\n') if p.strip()])

        length_score = min(answer_len / 200, 1.0)  # 200 字符为目标
        paragraph_score = min(paragraph_count / 3, 1.0)  # 3 段为目标

        completeness = length_score * 0.8 + paragraph_score * 0.2

        return completeness

    def _calculate_consistency(
        self, answer: str, documents: List[Dict[str, Any]]
    ) -> float:
        """
        计算答案一致性

        检查答案是否与文档内容一致

        Args:
            answer: 答案
            documents: 文档列表

        Returns:
            一致性分数 (0-1)
        """
        if not documents:
            return 0.5

        # 简单的一致性检查：
        # 检查答案中是否包含文档中的关键数字、人名等
        doc_texts = []
        for doc in documents:
            if isinstance(doc, dict):
                content = doc.get('content', '')
            else:
                content = getattr(doc, 'content', '')
            doc_texts.append(content.lower())

        combined_docs = ' '.join(doc_texts)

        # 提取答案中的数字、名词等
        numbers = re.findall(r'\d+', answer)
        answer_entities = re.findall(r'[A-Z][a-z]+', answer)

        # 检查是否在文档中出现
        consistency_score = 0.7  # 基础分

        for number in numbers:
            if number in combined_docs:
                consistency_score += 0.1
                break  # 只加一次

        for entity in answer_entities[:2]:  # 最多检查 2 个实体
            if entity.lower() in combined_docs:
                consistency_score += 0.1
                break

        return min(consistency_score, 1.0)

    def _calculate_answer_quality(self, answer: str) -> float:
        """
        计算答案质量

        检查答案的表达质量

        Args:
            answer: 答案

        Returns:
            质量分数 (0-1)
        """
        quality = 0.5  # 基础分

        # 有适当的标点符号
        if answer.count('。') >= 1 or answer.count('.') >= 1:
            quality += 0.2

        # 没有过多的重复字词
        words = answer.split()
        if len(words) > 0 and len(set(words)) / len(words) > 0.6:
            quality += 0.1

        # 包含具体信息而不是模糊的表述
        vague_phrases = [
            '可能', '也许', '感觉', '似乎', '不太确定',
            'might', 'maybe', 'probably', 'seems'
        ]
        vague_count = sum(1 for phrase in vague_phrases if phrase in answer.lower())

        if vague_count == 0:
            quality += 0.2
        elif vague_count <= 1:
            quality += 0.1

        return min(quality, 1.0)


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
