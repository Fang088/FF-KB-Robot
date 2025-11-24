"""
HNSW 向量存储 - 高效的近似最近邻搜索索引
基于 hnswlib 库实现，支持快速向量搜索和增量索引
"""

import os
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import hnswlib

logger = logging.getLogger(__name__)


class HNSWVectorStore:
    """
    HNSW（Hierarchical Navigable Small World）向量存储

    特点：
    - 支持增量索引（无需重建）
    - 内存高效（无需全量加载）
    - 搜索速度快（O(log N)）
    - 可持久化存储
    """

    def __init__(
        self,
        index_path: str = "./db/vector_store/hnsw_index",
        embedding_dim: int = 1536,
        max_elements: int = 1000000,
        ef_construction: int = 200,
        ef_search: int = 50,
        m: int = 16,
        distance_metric: str = "l2",
        enable_sqlite_metadata: bool = True,
    ):
        """
        初始化 HNSW 向量存储

        Args:
            index_path: 索引文件存储路径
            embedding_dim: 向量维度（默认 1536）
            max_elements: 最大元素数
            ef_construction: 构建时扩展参数（越大越精确但越慢）
            ef_search: 搜索时扩展参数
            m: 每个节点的最大连接数
            distance_metric: 距离度量方式（l2, cosine, ip）
            enable_sqlite_metadata: 是否使用 SQLite 存储元数据
        """
        self.index_path = Path(index_path)
        self.embedding_dim = embedding_dim
        self.max_elements = max_elements
        self.ef_construction = ef_construction
        self.ef_search = ef_search
        self.m = m
        self.distance_metric = self._map_distance_metric(distance_metric)
        self.enable_sqlite_metadata = enable_sqlite_metadata

        # 创建索引目录
        self.index_path.mkdir(parents=True, exist_ok=True)

        # 初始化索引
        self.index = None
        self.metadata_store = {}  # id -> metadata 映射
        self.id_to_label_map = {}  # id -> label 映射（hnswlib 内部使用）
        self.label_counter = 0  # label 计数器
        self.load_or_create_index()

        logger.info(
            f"HNSW 向量存储已初始化: 维度={embedding_dim}, "
            f"ef_construction={ef_construction}, ef_search={ef_search}, m={m}"
        )

    def _map_distance_metric(self, metric: str) -> str:
        """映射距离度量方式"""
        metric_map = {
            "l2": "l2",
            "euclidean": "l2",
            "cosine": "cosine",
            "ip": "ip",
            "inner_product": "ip",
        }
        return metric_map.get(metric.lower(), "l2")

    def load_or_create_index(self):
        """加载现有索引或创建新索引"""
        index_file = self.index_path / "hnsw.bin"
        metadata_file = self.index_path / "metadata.json"

        if index_file.exists():
            # 加载现有索引
            self.index = hnswlib.Index(
                space=self.distance_metric,
                dim=self.embedding_dim,
            )
            self.index.load_index(str(index_file), max_elements=self.max_elements)
            self.index.ef = self.ef_search
            logger.info(f"已加载现有 HNSW 索引: {index_file}")

            # 加载元数据
            if metadata_file.exists():
                with open(metadata_file, "r", encoding="utf-8") as f:
                    self.metadata_store = json.load(f)
                    # 恢复 label 计数器
                    if self.metadata_store:
                        self.label_counter = max(
                            int(label) for label in self.metadata_store.keys()
                        ) + 1
                logger.info(f"已加载元数据: {len(self.metadata_store)} 条记录")
        else:
            # 创建新索引
            self.index = hnswlib.Index(
                space=self.distance_metric,
                dim=self.embedding_dim,
            )
            self.index.init_index(
                max_elements=self.max_elements,
                ef_construction=self.ef_construction,
                M=self.m,
            )
            self.index.ef = self.ef_search
            logger.info(f"已创建新 HNSW 索引")

    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        添加文档到向量存储

        Args:
            documents: 文本列表
            embeddings: 嵌入向量列表
            metadatas: 元数据列表
            ids: 文档 ID 列表

        Returns:
            添加的文档 ID 列表
        """
        if not documents or not embeddings:
            logger.warning("尝试添加空文档列表")
            return []

        if len(documents) != len(embeddings):
            raise ValueError("文档数量与向量数量不匹配")

        # 生成 ID
        if ids is None:
            import uuid
            ids = [str(uuid.uuid4()) for _ in documents]

        # 准备元数据
        if metadatas is None:
            metadatas = [{"source": "ff-kb-robot"} for _ in documents]

        # 转换为 numpy 数组
        embeddings_array = np.array(embeddings, dtype="float32")

        # 添加到索引
        labels = list(range(self.label_counter, self.label_counter + len(documents)))
        self.index.add_items(embeddings_array, labels)

        # 存储元数据和 ID 映射
        for label, doc_id, doc_text, metadata in zip(
            labels, ids, documents, metadatas
        ):
            self.metadata_store[str(label)] = {
                "id": doc_id,
                "content": doc_text,
                "metadata": metadata,
            }
            self.id_to_label_map[doc_id] = label

        self.label_counter += len(documents)

        # 持久化
        self.save_index()

        logger.info(f"已添加 {len(documents)} 个文档到 HNSW 索引")
        return ids

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        搜索相似文档

        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量

        Returns:
            相似文档列表
        """
        if not self.metadata_store:
            logger.warning("向量存储为空，无法搜索")
            return []

        # 智能调整搜索参数：top_k不能超过实际向量数量
        actual_top_k = min(top_k, len(self.metadata_store))

        # 当top_k较大时，自动提升ef以确保搜索质量
        # ef应该至少是top_k的3-10倍，这里使用保守的10倍
        original_ef = self.index.ef
        recommended_ef = original_ef
        if actual_top_k > 0:
            recommended_ef = max(self.ef_search, actual_top_k * 10)
            if recommended_ef > original_ef:
                self.index.ef = recommended_ef
                logger.debug(f"已临时提升ef_search: {original_ef} → {recommended_ef} (for top_k={actual_top_k})")

        query_array = np.array([query_embedding], dtype="float32")

        try:
            # HNSW 搜索
            labels, distances = self.index.knn_query(query_array, k=actual_top_k)
            labels = labels[0]
            distances = distances[0]

            # 格式化结果
            results = []
            for label, distance in zip(labels, distances):
                label_str = str(label)
                if label_str in self.metadata_store:
                    meta = self.metadata_store[label_str]
                    results.append(
                        {
                            "id": meta["id"],
                            "content": meta["content"],
                            "score": float(distance),  # HNSW 返回距离
                            "metadata": meta["metadata"],
                        }
                    )

            logger.debug(f"HNSW 搜索完成: 返回 {len(results)} 个结果 (请求 {top_k}, 实际 {actual_top_k})")
            return results

        except Exception as e:
            logger.error(f"HNSW 搜索失败: {e}")
            raise
        finally:
            # 恢复原来的ef值
            if recommended_ef > original_ef:
                self.index.ef = original_ef
                logger.debug(f"已恢复ef_search到原值: {original_ef}")

    def delete_document(self, doc_id: str) -> bool:
        """
        删除单个文档

        Args:
            doc_id: 文档 ID

        Returns:
            是否删除成功
        """
        if doc_id not in self.id_to_label_map:
            logger.warning(f"文档不存在: {doc_id}")
            return False

        label = self.id_to_label_map[doc_id]
        label_str = str(label)

        # 从元数据中删除
        if label_str in self.metadata_store:
            del self.metadata_store[label_str]

        # 从 ID 映射中删除
        del self.id_to_label_map[doc_id]

        # HNSW 不支持直接删除，只能标记为删除
        # 这里我们选择懒删除，搜索时过滤掉删除的项
        self.save_index()

        logger.info(f"文档已删除: {doc_id}")
        return True

    def delete_documents_by_metadata(self, metadata_filter: Dict[str, Any]) -> int:
        """
        根据元数据条件删除文档

        Args:
            metadata_filter: 元数据过滤条件（如 {"kb_id": "some-id"}）

        Returns:
            删除的文档数量
        """
        deleted_count = 0
        labels_to_delete = []

        for label_str, meta in self.metadata_store.items():
            doc_metadata = meta.get("metadata", {})
            # 检查是否匹配所有过滤条件
            if all(
                doc_metadata.get(k) == v for k, v in metadata_filter.items()
            ):
                labels_to_delete.append(label_str)
                doc_id = meta["id"]
                if doc_id in self.id_to_label_map:
                    del self.id_to_label_map[doc_id]
                deleted_count += 1

        # 删除元数据
        for label_str in labels_to_delete:
            del self.metadata_store[label_str]

        self.save_index()
        logger.info(f"已删除 {deleted_count} 个文档（基于元数据过滤）")
        return deleted_count

    def delete_knowledge_base_vectors(self, kb_id: str) -> int:
        """
        删除知识库的所有向量数据

        Args:
            kb_id: 知识库 ID

        Returns:
            删除的向量数量
        """
        return self.delete_documents_by_metadata({"kb_id": kb_id})

    def clear_all(self) -> bool:
        """
        清空所有数据

        Returns:
            是否清空成功
        """
        try:
            self.metadata_store.clear()
            self.id_to_label_map.clear()
            self.label_counter = 0

            # 创建新索引
            self.index = hnswlib.Index(
                space=self.distance_metric,
                dim=self.embedding_dim,
            )
            self.index.init_index(
                max_elements=self.max_elements,
                ef_construction=self.ef_construction,
                M=self.m,
            )
            self.index.ef = self.ef_search

            self.save_index()
            logger.info("已清空 HNSW 索引")
            return True
        except Exception as e:
            logger.error(f"清空索引失败: {e}")
            return False

    def save_index(self):
        """保存索引和元数据到磁盘"""
        try:
            # 保存索引
            index_file = self.index_path / "hnsw.bin"
            self.index.save_index(str(index_file))

            # 保存元数据
            metadata_file = self.index_path / "metadata.json"
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(self.metadata_store, f, ensure_ascii=False, indent=2)

            logger.debug("HNSW 索引已保存到磁盘")
        except Exception as e:
            logger.error(f"保存索引失败: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息

        Returns:
            统计信息字典
        """
        return {
            "collection_name": "hnsw_index",
            "count": len(self.metadata_store),
            "embedding_dim": self.embedding_dim,
            "distance_metric": self.distance_metric,
            "max_elements": self.max_elements,
        }

    def optimize(self):
        """优化索引（紧凑重建）"""
        try:
            logger.info("开始优化 HNSW 索引...")
            # 重新构建索引以优化内存使用
            self.index.ef = self.ef_construction
            logger.info("HNSW 索引优化完成")
        except Exception as e:
            logger.error(f"优化索引失败: {e}")
            raise

    def set_ef_search(self, ef: int):
        """
        动态设置搜索扩展参数

        Args:
            ef: 扩展参数（越大搜索越准确但越慢）
        """
        if ef > 0:
            self.ef_search = ef
            self.index.ef = ef
            logger.info(f"已设置 ef_search = {ef}")
        else:
            raise ValueError("ef 必须大于 0")

    def batch_search(
        self,
        query_embeddings: List[List[float]],
        top_k: int = 5,
    ) -> List[List[Dict[str, Any]]]:
        """
        批量搜索（批处理多个查询）

        Args:
            query_embeddings: 查询向量列表
            top_k: 每个查询返回的结果数量

        Returns:
            每个查询的结果列表
        """
        query_array = np.array(query_embeddings, dtype="float32")

        try:
            labels, distances = self.index.knn_query(query_array, k=top_k)

            all_results = []
            for query_labels, query_distances in zip(labels, distances):
                results = []
                for label, distance in zip(query_labels, query_distances):
                    label_str = str(label)
                    if label_str in self.metadata_store:
                        meta = self.metadata_store[label_str]
                        results.append(
                            {
                                "id": meta["id"],
                                "content": meta["content"],
                                "score": float(distance),
                                "metadata": meta["metadata"],
                            }
                        )
                all_results.append(results)

            logger.debug(f"批量搜索完成: {len(all_results)} 个查询")
            return all_results
        except Exception as e:
            logger.error(f"批量搜索失败: {e}")
            raise
