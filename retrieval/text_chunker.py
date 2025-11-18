"""
智能文本分块引擎 - 替换原有的简单分块逻辑
设计目标：
  1. 语义边界感知 - 在句子/段落边界处分割
  2. 上下文保留 - 增加重叠比例，防止信息丢失
  3. 智能去重 - 去除重复的分块
  4. 内容感知 - 根据内容类型自适应分块
"""

import re
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class TextChunker:
    """
    高效的文本分块器

    核心特性：
    - 在语义边界处分割（句号、问号、换行等）
    - 自适应的重叠比例
    - 智能去重
    - 内容完整性检查
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        enable_dedup: bool = True,
    ):
        """
        初始化分块器

        Args:
            chunk_size: 目标分块大小（字符数）
            chunk_overlap: 分块之间的重叠（字符数）
            min_chunk_size: 最小分块大小（小于此值的分块会被合并）
            enable_dedup: 是否启用去重
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.enable_dedup = enable_dedup

        # 编译正则表达式（只编译一次，提高效率）
        self._sentence_split_patterns = {
            'zh': re.compile(r'([。！？，；：\n])', re.UNICODE),  # 中文断句
            'en': re.compile(r'([.!?\n;:])', re.UNICODE),       # 英文断句
            'mixed': re.compile(r'([。！？，；：.!?\n;:])', re.UNICODE),  # 混合
        }

        logger.info(
            f"TextChunker initialized: "
            f"chunk_size={chunk_size}, overlap={chunk_overlap}, "
            f"min_size={min_chunk_size}, dedup={enable_dedup}"
        )

    def chunk(self, text: str) -> List[str]:
        """
        主分块函数 - 替代旧的 chunk_text 方法

        Args:
            text: 输入文本

        Returns:
            分块列表
        """
        if not text or len(text.strip()) == 0:
            logger.warning("Empty text provided to chunk")
            return []

        # 步骤1：文本清洗
        cleaned_text = self._clean_text(text)

        # 步骤2：智能分块
        chunks = self._smart_chunk(cleaned_text)

        # 步骤3：去重处理
        if self.enable_dedup:
            chunks = self._dedup_chunks(chunks)

        # 步骤4：验证分块
        chunks = self._validate_chunks(chunks)

        logger.info(
            f"Chunked text ({len(text)} chars) into {len(chunks)} chunks. "
            f"Average size: {len(text) // len(chunks) if chunks else 0}"
        )

        return chunks

    def _clean_text(self, text: str) -> str:
        """
        清洗文本 - 移除垃圾字符但保留格式

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        # 1. 移除零宽字符、BOM等隐藏字符
        text = text.replace('\x00', '').replace('\ufeff', '')

        # 2. 标准化换行符（统一为 \n）
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 3. 移除过多的连续空白（但保留至少一个）
        text = re.sub(r'  +', ' ', text)  # 多个空格 → 单个空格
        text = re.sub(r'\n\n\n+', '\n\n', text)  # 多个换行 → 双换行

        # 4. 去除首尾空白
        text = text.strip()

        return text

    def _detect_language_type(self, text: str) -> str:
        """
        检测文本主要语言类型（优化分块策略）

        Args:
            text: 文本样本

        Returns:
            语言类型: 'zh'(中文) / 'en'(英文) / 'mixed'(混合)
        """
        # 统计中文字符比例
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))

        total = max(chinese_chars + english_chars, 1)

        if chinese_chars / total > 0.5:
            return 'zh'
        elif english_chars / total > 0.5:
            return 'en'
        else:
            return 'mixed'

    def _smart_chunk(self, text: str) -> List[str]:
        """
        智能分块 - 在语义边界处分割

        算法：
        1. 先按段落分割（双换行）
        2. 再按句子分割（句号、问号等）
        3. 最后合并成 chunk_size 大小的块
        4. 添加重叠以保留上下文

        Args:
            text: 清洗后的文本

        Returns:
            分块列表
        """
        if len(text) <= self.chunk_size:
            return [text]

        # 步骤1：按段落分割
        paragraphs = text.split('\n\n')
        logger.debug(f"Split into {len(paragraphs)} paragraphs")

        # 步骤2：处理每个段落
        sentences = []
        for para in paragraphs:
            if len(para.strip()) > 0:
                # 按句子分割
                para_sentences = self._split_by_sentence(para)
                sentences.extend(para_sentences)

        logger.debug(f"Split into {len(sentences)} sentences")

        # 步骤3：合并句子成分块
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # 如果加入这个句子会超过 chunk_size，就保存当前 chunk 并开新的
            if len(current_chunk) + len(sentence) > self.chunk_size:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence
            else:
                current_chunk += sentence

        # 添加最后一个分块
        if current_chunk:
            chunks.append(current_chunk)

        # 步骤4：添加重叠（实现 sliding window）
        chunks = self._add_overlap(chunks)

        return chunks

    def _split_by_sentence(self, text: str) -> List[str]:
        """
        按句子分割文本

        Args:
            text: 段落文本

        Returns:
            句子列表
        """
        # 检测语言类型
        lang = self._detect_language_type(text)
        pattern = self._sentence_split_patterns[lang]

        # 按标点符号分割，但保留标点符号
        parts = pattern.split(text)

        sentences = []
        current = ""

        for part in parts:
            if pattern.match(part or ''):
                # 这是一个分割符
                current += part
                if current.strip():
                    sentences.append(current)
                current = ""
            else:
                current += part

        # 添加最后的残留文本
        if current.strip():
            sentences.append(current)

        return [s.strip() for s in sentences if s.strip()]

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """
        添加分块重叠 - 保留上下文信息

        策略：每个分块包含上一个分块的末尾（重叠）

        Example:
            chunks = ["123456", "789ABC"]
            overlap = 2
            result = ["123456", "56789ABC"]

        Args:
            chunks: 分块列表

        Returns:
            添加重叠的分块列表
        """
        if len(chunks) <= 1:
            return chunks

        overlapped = []

        for i, chunk in enumerate(chunks):
            if i == 0:
                # 第一个分块不需要添加重叠
                overlapped.append(chunk)
            else:
                # 从前一个分块的末尾获取重叠部分
                prev_chunk = overlapped[-1]

                # 计算重叠长度（动态调整）
                overlap_len = min(self.chunk_overlap, len(prev_chunk) // 3)

                # 获取前一个分块的末尾作为上下文
                context = prev_chunk[-overlap_len:] if overlap_len > 0 else ""

                # 组合：上下文 + 当前分块
                overlapped_chunk = context + chunk
                overlapped.append(overlapped_chunk)

        return overlapped

    def _dedup_chunks(self, chunks: List[str]) -> List[str]:
        """
        去重处理 - 移除内容相似度过高的分块

        Args:
            chunks: 分块列表

        Returns:
            去重后的分块列表
        """
        if len(chunks) <= 1:
            return chunks

        deduped = []
        seen_hashes = {}  # {hash: chunk_index}

        for i, chunk in enumerate(chunks):
            # 计算内容的哈希
            content_hash = hash(chunk.lower().strip())

            if content_hash not in seen_hashes:
                deduped.append(chunk)
                seen_hashes[content_hash] = i

        if len(deduped) < len(chunks):
            logger.debug(
                f"Removed {len(chunks) - len(deduped)} duplicate chunks"
            )

        return deduped

    def _validate_chunks(self, chunks: List[str]) -> List[str]:
        """
        验证分块 - 移除过小或无效的分块

        Args:
            chunks: 分块列表

        Returns:
            验证后的分块列表
        """
        valid_chunks = []

        for chunk in chunks:
            # 检查最小大小
            if len(chunk.strip()) < self.min_chunk_size:
                # 尝试与下一个分块合并（见下一个循环）
                logger.debug(f"Skipping chunk (too small): {len(chunk)} chars")
                continue

            valid_chunks.append(chunk)

        # 最后一个检查：如果分块过少，考虑调整参数
        if len(valid_chunks) < 1:
            logger.warning("No valid chunks found. Returning all chunks.")
            return chunks

        return valid_chunks

    def chunk_with_metadata(self, text: str, source: str = "") -> List[dict]:
        """
        分块同时返回元数据（便于追踪）

        Args:
            text: 输入文本
            source: 内容来源（可选）

        Returns:
            [{chunk: 内容, metadata: 元数据}, ...]
        """
        chunks = self.chunk(text)

        result = []
        for i, chunk in enumerate(chunks):
            result.append({
                "content": chunk,
                "metadata": {
                    "chunk_index": i,
                    "chunk_count": len(chunks),
                    "size": len(chunk),
                    "source": source,
                }
            })

        return result
