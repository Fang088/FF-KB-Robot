"""
检索结果后处理器 - 提升检索质量
功能：
  1. 相似度过滤 + 去重
  2. 多维度重排
  3. 结果合并
  4. 上下文补充
"""

from typing import List, Dict, Any, Optional, Set
import logging
import hashlib
from collections import defaultdict

logger = logging.getLogger(__name__)


class RetrievalPostProcessor:
    """
    检索结果后处理器 - 让检索结果更精准

    工作流：
    1. 过滤：按 kb_id + 相似度过滤
    2. 去重：按内容哈希去重，保留相关度最高的
    3. 重排：多维度评分后重排
    4. 合并：将高度相似的结果合并
    """

    def __init__(
        self,
        similarity_threshold: float = 0.3,
        dedup_threshold: float = 0.85,
        top_k: int = 5,
    ):
        """
        初始化后处理器

        Args:
            similarity_threshold: 相似度过滤阈值
                                 (< 此值的结果会被过滤)
            dedup_threshold: 去重阈值
                            (相似度 > 此值认为是重复内容)
            top_k: 最多返回多少个结果
        """
        self.similarity_threshold = similarity_threshold
        self.dedup_threshold = dedup_threshold
        self.top_k = top_k

        logger.info(
            f"RetrievalPostProcessor initialized: "
            f"sim_threshold={similarity_threshold}, "
            f"dedup_threshold={dedup_threshold}, "
            f"top_k={top_k}"
        )

    def process(
        self,
        results: List[Dict[str, Any]],
        kb_id: str,
        query: str = "",
    ) -> List[Dict[str, Any]]:
        """
        处理检索结果 - 完整流程

        Args:
            results: 原始检索结果
            kb_id: 知识库 ID（用于过滤）
            query: 用户查询（可选，用于重排）

        Returns:
            处理后的检索结果（按质量排序）
        """
        if not results:
            return []

        logger.debug(f"Processing {len(results)} raw results")

        # 步骤1：按 kb_id + 相似度过滤
        filtered = self._filter_by_kb_and_score(results, kb_id)
        logger.debug(f"After filtering: {len(filtered)} results")

        if not filtered:
            logger.warning(f"No results after filtering for kb_id={kb_id}")
            return []

        # 步骤2：去重处理
        deduped = self._dedup_results(filtered)
        logger.debug(f"After dedup: {len(deduped)} results")

        # 步骤3：重排
        if query:
            reranked = self._rerank_by_query(deduped, query)
        else:
            # 如果没有查询，就按原始相似度排序（距离越小越好，升序排列）
            reranked = sorted(
                deduped, key=lambda x: x['score'], reverse=False
            )

        # 步骤4：返回前 top_k 个
        final_results = reranked[: self.top_k]

        logger.debug(f"Final results: {len(final_results)}")
        return final_results

    def _filter_by_kb_and_score(
        self,
        results: List[Dict[str, Any]],
        kb_id: str,
    ) -> List[Dict[str, Any]]:
        """
        过滤结果：只保留指定 kb_id 且相似度足够的结果

        注意：score 是距离值（越小越相似）
        对于 L2 距离：
        - 距离=0: 完全相同
        - 距离<1: 很相似
        - 距离1-3: 相似
        - 距离>3: 不相似

        Args:
            results: 原始结果
            kb_id: 知识库 ID

        Returns:
            过滤后的结果
        """
        filtered = []
        kb_mismatch_count = 0
        score_filtered_count = 0

        for result in results:
            # 检查 kb_id 匹配
            result_kb_id = result.get('metadata', {}).get('kb_id')
            if result_kb_id != kb_id:
                kb_mismatch_count += 1
                continue

            # 检查距离（score 是距离，越小越相似）
            # 过滤掉距离太大的结果（距离 > threshold 表示不相似）
            score = result.get('score', float('inf'))
            if score > self.similarity_threshold:
                score_filtered_count += 1
                logger.debug(
                    f"Filtering out result with large distance: {score:.3f} "
                    f"(threshold: {self.similarity_threshold})"
                )
                continue

            filtered.append(result)

        if kb_mismatch_count > 0:
            logger.debug(f"Filtered {kb_mismatch_count} results due to kb_id mismatch")
        if score_filtered_count > 0:
            logger.debug(f"Filtered {score_filtered_count} results due to distance threshold")

        return filtered

    def _dedup_results(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        去重：移除高度相似的结果

        策略：
        1. 按内容哈希分组
        2. 每组只保留相关度最高的

        Args:
            results: 过滤后的结果

        Returns:
            去重后的结果
        """
        # 步骤1：计算内容哈希
        content_groups = defaultdict(list)

        for result in results:
            content = result.get('content', '')
            # 标准化内容（转小写，去空白）
            normalized = content.lower().strip()
            # 计算哈希
            content_hash = hashlib.md5(normalized.encode()).hexdigest()
            # 分组
            content_groups[content_hash].append(result)

        # 步骤2：每组保留最高分
        deduped = []
        duplicate_count = 0

        for content_hash, group in content_groups.items():
            if len(group) > 1:
                # 这组有重复
                # 按距离排序，保留最小距离的（最相似的）
                best = min(group, key=lambda x: x.get('score', float('inf')))
                deduped.append(best)
                duplicate_count += len(group) - 1
            else:
                deduped.append(group[0])

        if duplicate_count > 0:
            logger.debug(f"Removed {duplicate_count} duplicate results")

        return deduped

    def _rerank_by_query(
        self,
        results: List[Dict[str, Any]],
        query: str,
    ) -> List[Dict[str, Any]]:
        """
        按查询重排 - 多维度评分

        维度：
        1. 向量相似度 (50%) - 原始向量匹配分数
        2. 关键词匹配度 (30%) - 查询关键词在文本中的匹配度
        3. 内容完整度 (20%) - 文本长度（太短可能不完整）

        Args:
            results: 结果
            query: 查询文本

        Returns:
            重排后的结果（带新的综合分数）
        """
        # 提取查询关键词
        query_keywords = self._extract_keywords(query)

        scored_results = []

        # 先计算距离的统计信息，用于标准化
        distances = [r.get('score', float('inf')) for r in results]
        min_distance = min(distances) if distances else 0
        max_distance = max(distances) if distances else 1.0
        distance_range = max_distance - min_distance if max_distance > min_distance else 1.0

        for result in results:
            content = result.get('content', '')

            # 维度1：向量相似度（距离转相似度标准化）
            # 注意：score 是距离值，越小越相似
            distance = result.get('score', float('inf'))
            if distance == float('inf'):
                vector_score = 0.0
            else:
                # 标准化距离到 0-1 范围（越小越好，反向转换）
                normalized_distance = (distance - min_distance) / distance_range if distance_range > 0 else 0
                vector_score = 1.0 - normalized_distance  # 反向：距离越小，分数越高

            # 维度2：关键词匹配度
            keyword_score = self._compute_keyword_match_score(
                query_keywords, content
            )

            # 维度3：内容完整度
            completeness_score = self._compute_completeness_score(content)

            # 综合评分
            combined_score = (
                vector_score * 0.5 +
                keyword_score * 0.3 +
                completeness_score * 0.2
            )

            # 添加综合分数到结果
            result_copy = result.copy()
            result_copy['combined_score'] = combined_score
            result_copy['breakdown'] = {
                'vector': vector_score,
                'keyword': keyword_score,
                'completeness': completeness_score,
            }

            scored_results.append(result_copy)

        # 按综合分数排序
        scored_results.sort(
            key=lambda x: x['combined_score'], reverse=True
        )

        return scored_results

    def _extract_keywords(self, query: str) -> List[str]:
        """
        提取查询关键词

        简单实现：按空格分割，过滤掉停用词

        Args:
            query: 查询文本

        Returns:
            关键词列表
        """
        # 简单的停用词集合（可扩展）
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            '的', '是', '了', '在', '和', '这', '个', '有', '什么', '哪',
            '怎样', '怎么', '如何', '请', '帮', '我',
        }

        # 分割并过滤
        keywords = [
            word.lower() for word in query.split()
            if len(word) > 1 and word.lower() not in stopwords
        ]

        return keywords

    def _compute_keyword_match_score(
        self,
        keywords: List[str],
        content: str,
    ) -> float:
        """
        计算关键词匹配分数

        Args:
            keywords: 查询关键词
            content: 文本内容

        Returns:
            匹配分数 (0-1)
        """
        if not keywords:
            return 0.5  # 默认分数

        content_lower = content.lower()

        # 计算有多少个关键词在文本中出现
        matched = sum(1 for kw in keywords if kw in content_lower)

        # 匹配分数 = 匹配关键词数 / 总关键词数
        match_score = matched / len(keywords)

        return min(match_score, 1.0)

    def _compute_completeness_score(self, content: str) -> float:
        """
        计算内容完整度分数

        假设：文本越长，内容越完整

        Args:
            content: 文本内容

        Returns:
            完整度分数 (0-1)
        """
        # 目标长度：200 字符（认为是合理长度）
        target_length = 200

        content_length = len(content.strip())

        # 长度与目标长度的比例
        ratio = content_length / target_length

        # 过长也不好（太多噪音），最多 1.0
        completeness = min(ratio, 1.0)

        return completeness

    def merge_similar_results(
        self,
        results: List[Dict[str, Any]],
        similarity_threshold: float = 0.9,
    ) -> List[Dict[str, Any]]:
        """
        合并高度相似的结果 - 可选的高级处理

        Args:
            results: 结果列表
            similarity_threshold: 相似度阈值（> 此值认为相似）

        Returns:
            合并后的结果
        """
        if len(results) <= 1:
            return results

        # TODO: 实现基于向量的相似度计算和合并
        # 现在简单返回原结果
        return results
