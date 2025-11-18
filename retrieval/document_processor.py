"""
文档处理器 - 文档加载、分块、清洗等预处理逻辑
改进：集成新的 TextChunker 实现智能分块
"""

from typing import List, Optional, Dict, Any
import logging
from .text_chunker import TextChunker

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    文档处理器
    负责文档的加载、分块、清洗等预处理操作

    改进：使用 TextChunker 替代原始的简单分块算法
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        enable_smart_chunk: bool = True,
    ):
        """
        初始化文档处理器

        Args:
            chunk_size: 分块大小（为 None 则使用 settings 中的配置）
            chunk_overlap: 分块之间的重叠（为 None 则使用 settings 中的配置）
            enable_smart_chunk: 是否启用智能分块（推荐启用）
        """
        from config.settings import settings

        # 使用配置的默认值
        self.chunk_size = chunk_size or settings.TEXT_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.TEXT_CHUNK_OVERLAP
        self.enable_smart_chunk = enable_smart_chunk

        # 初始化智能分块器
        if enable_smart_chunk:
            self.chunker = TextChunker(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                min_chunk_size=settings.TEXT_MIN_CHUNK_SIZE,
                enable_dedup=True,
            )

        logger.info(
            f"文档处理器已初始化: "
            f"chunk_size={self.chunk_size}, overlap={self.chunk_overlap}, "
            f"smart_chunk={enable_smart_chunk}"
        )

    def load_document(self, file_path: str) -> str:
        """
        加载文档

        Args:
            file_path: 文档文件路径

        Returns:
            文档内容
        """
        logger.info(f"加载文档: {file_path}")

        try:
            if file_path.endswith(".txt"):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            elif file_path.endswith(".docx"):
                from docx import Document
                doc = Document(file_path)
                content = "\n".join([para.text for para in doc.paragraphs])
            elif file_path.endswith(".pdf"):
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                content = "\n".join([page.extract_text() for page in reader.pages])
            elif file_path.endswith((".xlsx", ".xls")):
                import pyexcel
                data = pyexcel.get_array(file_name=file_path)
                content = "\n".join(["\t".join(map(str, row)) for row in data])
            else:
                # 默认处理为文本文件
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

            logger.info(f"文档加载成功: {len(content)} 个字符")
            return content
        except Exception as e:
            logger.error(f"文档加载失败: {e}")
            raise

    def clean_text(self, text: str) -> str:
        """
        清洗文本 - 保留格式结构

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        # 注意：不再在这里移除所有空白
        # TextChunker 会处理清洗，这里只做必要的清理
        return text.strip()

    def chunk_text(self, text: str) -> List[str]:
        """
        将文本分块 - 使用智能分块器

        Args:
            text: 输入文本

        Returns:
            文本分块列表
        """
        logger.info(f"开始文本分块: 文本长度={len(text)}")

        if self.enable_smart_chunk:
            # 使用新的智能分块器
            chunks = self.chunker.chunk(text)
        else:
            # 降级到旧的简单分块（备用）
            chunks = self._simple_chunk(text)

        logger.info(f"分块完成: {len(chunks)} 个分块")
        return chunks

    def _simple_chunk(self, text: str) -> List[str]:
        """
        简单分块 - 降级方案（兼容旧版本）

        Args:
            text: 输入文本

        Returns:
            文本分块列表
        """
        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            if end < len(text):
                last_period = text.rfind("。", start, end)
                last_newline = text.rfind("\n", start, end)
                split_pos = max(last_period, last_newline)

                if split_pos > start:
                    end = split_pos + 1

            chunks.append(text[start:end])
            start = end - self.chunk_overlap

        return chunks

    def process_document(self, file_path: str, save_chunks: bool = False) -> List[str]:
        """
        处理文档（加载 -> 清洗 -> 分块）

        Args:
            file_path: 文档文件路径
            save_chunks: 是否保存处理后的分块到processed_chunks目录

        Returns:
            文本分块列表
        """
        try:
            # 加载文档
            content = self.load_document(file_path)

            # 清洗文本
            cleaned_content = self.clean_text(content)

            # 分块
            chunks = self.chunk_text(cleaned_content)

            # 保存分块
            if save_chunks:
                from config.settings import settings
                import os
                import uuid

                # 确保目录存在
                os.makedirs(settings.PROCESSED_CHUNKS_PATH, exist_ok=True)

                # 生成唯一的文件标识
                file_id = str(uuid.uuid4())
                filename = os.path.splitext(os.path.basename(file_path))[0]

                # 保存分块
                for i, chunk in enumerate(chunks):
                    chunk_filename = f"{filename}_{file_id}_chunk_{i}.txt"
                    chunk_path = os.path.join(settings.PROCESSED_CHUNKS_PATH, chunk_filename)
                    with open(chunk_path, "w", encoding="utf-8") as f:
                        f.write(chunk)

                logger.info(f"分块已保存到: {settings.PROCESSED_CHUNKS_PATH}")

            return chunks
        except Exception as e:
            logger.error(f"文档处理失败: {e}")
            raise

    def process_documents(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        批量处理文档

        Args:
            file_paths: 文档文件路径列表

        Returns:
            {文件路径: 文本分块列表} 的字典
        """
        results = {}

        for file_path in file_paths:
            try:
                chunks = self.process_document(file_path)
                results[file_path] = chunks
            except Exception as e:
                logger.error(f"处理文档 {file_path} 失败: {e}")
                results[file_path] = []

        return results
