"""
多层缓存管理系统 - 支持语义化智能匹配的高效缓存体系

核心功能：
1. 基础缓存: Embedding (L1) / QueryResult (L2) / RetrievalClassifier (L3)
2. 智能语义匹配: 问题规范化 + 关键词提取 + 相似度匹配
3. LRU淘汰 + TTL过期 + 命中率统计

使用示例：
  # Embedding 缓存（自动）
  embedding = embedding_service.embed_text("什么是AI？")  # 100ms
  embedding = embedding_service.embed_text("什么是AI？")  # <1ms (缓存命中)

  # 查询结果缓存（支持语义匹配）
  result1 = await agent.execute_query(kb_id, "Python是什么？")
  result2 = await agent.execute_query(kb_id, "Python是啥？")  # 缓存命中！
"""

import hashlib
import time
import logging
import threading
import re
from typing import Any, Dict, List, Optional, Callable, TypeVar
from functools import wraps
from enum import Enum
from dataclasses import dataclass
from collections import OrderedDict

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CacheLevel(str, Enum):
    """缓存层级 - 统一定义"""
    EMBEDDING = "embedding"
    QUERY_RESULT = "query_result"
    RETRIEVAL_CLASS = "retrieval_class"
    RETRIEVAL = "retrieval"
    DOCUMENT = "document"


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    timestamp: float
    ttl: int
    hits: int = 0
    level: CacheLevel = CacheLevel.EMBEDDING

    def is_expired(self) -> bool:
        """检查是否过期"""
        return time.time() - self.timestamp > self.ttl

    def update_hit(self) -> None:
        """更新命中次数"""
        self.hits += 1


@dataclass
class CacheStats:
    """缓存统计信息"""
    level: CacheLevel
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    evictions: int = 0
    current_size: int = 0
    max_size: int = 0

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.cache_hits / self.total_requests

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": f"{self.hit_rate:.2%}",
            "evictions": self.evictions,
            "current_size": self.current_size,
            "max_size": self.max_size,
        }


class QuestionNormalizer:
    """轻量级问题规范化器 - 智能关键词提取和分类"""

    # 停用词
    STOPWORDS = {'什么', '是', '啥', '呢', '吗', '的', '了', '哦', '呃', 'is', 'are', 'what', 'the'}

    # 同义词
    SYNONYMS = {'啥': '什么', '怎样': '怎么', '为何': '为什么', '如何': '怎么'}

    @staticmethod
    def normalize(question: str) -> tuple[str, List[str], str]:
        """
        规范化问题

        Returns:
            (规范化文本, 关键词列表, 缓存键)
        """
        # 转小写并替换同义词
        text = question.lower().strip()
        for syn, canonical in QuestionNormalizer.SYNONYMS.items():
            text = text.replace(syn, canonical)

        # 移除标点符号
        text = re.sub(r'[？?！!，,。.；;：:\'""''【】\[\]（）()\s]+', ' ', text)

        # 提取关键词（移除停用词）
        words = text.split()
        keywords = sorted(set(w for w in words if w and w not in QuestionNormalizer.STOPWORDS and len(w) > 1))

        # 生成缓存键
        cache_key = hashlib.md5(':'.join(keywords).encode()).hexdigest()

        return text.strip(), keywords, cache_key


class BaseCache:
    """基础缓存类 - 支持 LRU 淘汰和 TTL 过期"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600, level: CacheLevel = CacheLevel.EMBEDDING):
        self.max_size = max_size
        self.ttl = ttl
        self.level = level
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.stats = CacheStats(level=level, max_size=max_size)
        self.lock = threading.RLock()

    def _clean_expired(self) -> None:
        """清理已过期的条目"""
        with self.lock:
            expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]
            for key in expired_keys:
                del self.cache[key]

    def _evict_lru(self) -> None:
        """LRU 淘汰"""
        with self.lock:
            if len(self.cache) >= self.max_size:
                least_used_key = min(
                    self.cache.keys(),
                    key=lambda k: (self.cache[k].hits, self.cache[k].timestamp)
                )
                del self.cache[least_used_key]
                self.stats.evictions += 1

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self.lock:
            self._clean_expired()
            self.stats.total_requests += 1

            if key in self.cache:
                entry = self.cache[key]
                if not entry.is_expired():
                    entry.update_hit()
                    self.stats.cache_hits += 1
                    self.cache.move_to_end(key)
                    return entry.value
                else:
                    del self.cache[key]

            self.stats.cache_misses += 1
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存"""
        with self.lock:
            self._clean_expired()
            self._evict_lru()

            ttl = ttl or self.ttl
            entry = CacheEntry(
                key=key,
                value=value,
                timestamp=time.time(),
                ttl=ttl,
                level=self.level,
            )
            self.cache[key] = entry
            self.cache.move_to_end(key)
            self.stats.current_size = len(self.cache)

    def delete(self, key: str) -> bool:
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.stats.current_size = len(self.cache)
                return True
            return False

    def clear(self) -> None:
        with self.lock:
            size = len(self.cache)
            self.cache.clear()
            self.stats.current_size = 0
            logger.info(f"已清空 {self.level.value} 缓存 ({size} 条目)")

    def get_stats(self) -> CacheStats:
        with self.lock:
            return self.stats


class EmbeddingCache(BaseCache):
    """Embedding 缓存 - L1"""

    def __init__(self, max_size: int = 10000, ttl: int = 86400):
        super().__init__(max_size, ttl, CacheLevel.EMBEDDING)

    @staticmethod
    def get_key(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def get_embedding(self, text: str) -> Optional[List[float]]:
        key = self.get_key(text)
        return self.get(key)

    def set_embedding(self, text: str, embedding: List[float]) -> None:
        key = self.get_key(text)
        self.set(key, embedding)

    def get_batch_embeddings(self, texts: List[str]) -> tuple[List[Optional[List[float]]], List[str], List[int]]:
        """批量获取 embeddings，返回缓存结果和未缓存的文本"""
        embeddings = []
        uncached_texts = []
        uncached_indices = []

        for i, text in enumerate(texts):
            cached = self.get_embedding(text)
            if cached is not None:
                embeddings.append(cached)
            else:
                embeddings.append(None)
                uncached_texts.append(text)
                uncached_indices.append(i)

        return embeddings, uncached_texts, uncached_indices

    def set_batch_embeddings(self, texts: List[str], embeddings: List[List[float]]) -> None:
        for text, embedding in zip(texts, embeddings):
            self.set_embedding(text, embedding)


class QueryResultCache(BaseCache):
    """查询结果缓存 - L2（支持语义匹配）"""

    def __init__(self, max_size: int = 5000, ttl: int = 3600):
        super().__init__(max_size, ttl, CacheLevel.QUERY_RESULT)
        # 优化：使用倒排索引，语义键 -> 精确键的直接映射
        # 这样查找从 O(n²) 优化为 O(1)
        self.semantic_index: Dict[str, str] = {}  # 语义键 -> 精确缓存键的倒排索引

    def get_key(self, kb_id: str, question: str) -> str:
        """生成缓存键"""
        combined = f"{kb_id}:{question}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get_semantic_key(self, kb_id: str, question: str) -> str:
        """生成语义缓存键（智能匹配）"""
        normalized_text, keywords, semantic_hash = QuestionNormalizer.normalize(question)
        return f"{kb_id}:{semantic_hash}"

    def get_result(self, kb_id: str, question: str) -> Optional[Dict[str, Any]]:
        """
        获取查询结果（支持语义匹配）

        优化说明：
        - 使用倒排索引实现 O(1) 语义匹配查找
        - 避免了原来的 O(n²) 双重循环
        """
        # 步骤 1: 尝试精确匹配
        exact_key = self.get_key(kb_id, question)
        result = self.get(exact_key)
        if result is not None:
            logger.debug(f"精确缓存命中: {exact_key[:16]}...")
            return result

        # 步骤 2: 尝试语义匹配（优化为 O(1) 查找）
        semantic_key = self.get_semantic_key(kb_id, question)

        # 直接从倒排索引中查找，O(1) 复杂度
        if semantic_key in self.semantic_index:
            stored_key = self.semantic_index[semantic_key]

            # 检查缓存是否仍然有效
            if stored_key in self.cache:
                entry = self.cache[stored_key]
                if not entry.is_expired():
                    entry.update_hit()
                    self.stats.cache_hits += 1
                    self.cache.move_to_end(stored_key)
                    logger.debug(f"语义缓存命中: {semantic_key[:16]}...")
                    return entry.value
                else:
                    # 过期则清理
                    del self.cache[stored_key]
                    del self.semantic_index[semantic_key]
            else:
                # 索引不一致，清理
                del self.semantic_index[semantic_key]

        self.stats.cache_misses += 1
        return None

    def set_result(self, kb_id: str, question: str, result: Dict[str, Any]) -> None:
        """
        设置查询结果

        优化说明：
        - 同时更新倒排索引，保持语义���到精确键的映射
        """
        exact_key = self.get_key(kb_id, question)
        semantic_key = self.get_semantic_key(kb_id, question)

        # 保存到基础缓存
        self.set(exact_key, result)

        # 更新倒排索引：语义键 -> 精确键
        self.semantic_index[semantic_key] = exact_key
        logger.debug(f"缓存已设置: semantic_key={semantic_key[:16]}... -> exact_key={exact_key[:16]}...")

    def clear_kb(self, kb_id: str) -> int:
        """清空知识库的缓存"""
        with self.lock:
            prefix = f"{kb_id}:"
            keys_to_delete = [
                key for key in self.cache.keys()
                if key.startswith(hashlib.md5(prefix.encode()).hexdigest()[:10])
            ]
            for key in keys_to_delete:
                del self.cache[key]
                # 清理倒排索引
                for sem_key, stored_key in list(self.semantic_index.items()):
                    if stored_key == key:
                        del self.semantic_index[sem_key]

            self.stats.current_size = len(self.cache)
            logger.info(f"已清空 KB {kb_id} 的查询缓存 ({len(keys_to_delete)} 条目)")
            return len(keys_to_delete)

    def clear(self) -> None:
        """清空所有缓存（重写以同时清理倒排索引）"""
        with self.lock:
            size = len(self.cache)
            self.cache.clear()
            self.semantic_index.clear()  # 清理倒排索引
            self.stats.current_size = 0
            logger.info(f"已清空 {self.level.value} 缓存 ({size} 条目)")

    def _clean_expired(self) -> None:
        """清理已过期的条目（重写以同时清理倒排索引）"""
        with self.lock:
            expired_keys = [key for key, entry in self.cache.items() if entry.is_expired()]
            for key in expired_keys:
                del self.cache[key]
                # 清理对应的倒排索引
                for sem_key, stored_key in list(self.semantic_index.items()):
                    if stored_key == key:
                        del self.semantic_index[sem_key]


class RetrievalClassifierCache(BaseCache):
    """检索分类缓存 - L3（低频更新）"""

    def __init__(self, max_size: int = 2000, ttl: int = 604800):
        super().__init__(max_size, ttl, CacheLevel.RETRIEVAL_CLASS)

    @staticmethod
    def get_key(question: str) -> str:
        return hashlib.md5(question.encode()).hexdigest()

    def get_classification(self, question: str) -> Optional[Dict[str, Any]]:
        key = self.get_key(question)
        return self.get(key)

    def set_classification(self, question: str, classification: Dict[str, Any]) -> None:
        key = self.get_key(question)
        self.set(key, classification)


class CacheManager:
    """统一缓存管理器"""

    def __init__(
        self,
        embedding_cache_size: int = 10000,
        query_cache_size: int = 5000,
        classifier_cache_size: int = 2000,
    ):
        self.embedding_cache = EmbeddingCache(max_size=embedding_cache_size)
        self.query_cache = QueryResultCache(max_size=query_cache_size)
        self.classifier_cache = RetrievalClassifierCache(max_size=classifier_cache_size)

        logger.info(
            f"缓存管理器已初始化: "
            f"embedding={embedding_cache_size}, "
            f"query={query_cache_size}, "
            f"classifier={classifier_cache_size}"
        )

    def clear_all(self) -> None:
        """清空所有缓存"""
        self.embedding_cache.clear()
        self.query_cache.clear()
        self.classifier_cache.clear()
        logger.info("已清空所有缓存")

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓存统计"""
        return {
            "embedding": self.embedding_cache.get_stats().to_dict(),
            "query_result": self.query_cache.get_stats().to_dict(),
            "retrieval_classifier": self.classifier_cache.get_stats().to_dict(),
        }

    def print_stats(self) -> None:
        """打印缓存统计"""
        stats = self.get_stats()
        logger.info("=" * 60)
        logger.info("缓存统计信息")
        logger.info("=" * 60)
        for level, data in stats.items():
            logger.info(f"\n{level}:")
            for key, value in data.items():
                logger.info(f"  {key}: {value}")
        logger.info("=" * 60)


# 全局缓存管理器实例
_cache_manager_instance: Optional[CacheManager] = None


def get_cache_manager(
    embedding_cache_size: int = 10000,
    query_cache_size: int = 5000,
    classifier_cache_size: int = 2000,
) -> CacheManager:
    """获取或创建全局缓存管理器（单例模式）"""
    global _cache_manager_instance
    if _cache_manager_instance is None:
        _cache_manager_instance = CacheManager(
            embedding_cache_size=embedding_cache_size,
            query_cache_size=query_cache_size,
            classifier_cache_size=classifier_cache_size,
        )
    return _cache_manager_instance


def cache_embedding(cache_manager: Optional[CacheManager] = None):
    """Embedding 缓存装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, text_or_texts: Any) -> Any:
            manager = cache_manager or get_cache_manager()
            cache = manager.embedding_cache

            if isinstance(text_or_texts, str):
                cached = cache.get_embedding(text_or_texts)
                if cached is not None:
                    return cached
                result = func(self, text_or_texts)
                cache.set_embedding(text_or_texts, result)
                return result
            else:
                embeddings, uncached_texts, uncached_indices = cache.get_batch_embeddings(text_or_texts)
                if uncached_texts:
                    new_embeddings = func(self, uncached_texts)
                    for idx, embedding in zip(uncached_indices, new_embeddings):
                        embeddings[idx] = embedding
                    cache.set_batch_embeddings(uncached_texts, new_embeddings)
                return embeddings

        return wrapper
    return decorator
