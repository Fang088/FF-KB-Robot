"""
向量数据库客户端 - 与向量数据库交互
"""

from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class VectorStoreClient:
    """
    向量数据库客户端
    支持 Chroma, Weaviate, Pinecone 等向量数据库
    """

    def __init__(
        self,
        store_type: str = "chroma",
        path_or_url: str = "./db/vector_store",
        collection_name: str = "ff_kb_documents",
    ):
        """
        初始化向量数据库客户端

        Args:
            store_type: 数据库类型（chroma, weaviate, pinecone）
            path_or_url: 数据库路径或 URL
            collection_name: 集合名称
        """
        self.store_type = store_type
        self.path_or_url = path_or_url
        self.collection_name = collection_name
        self.client = None

        self._initialize_client()
        logger.info(f"向量数据库客户端已初始化: {store_type}")

    def _initialize_client(self):
        """初始化向量数据库客户端"""
        try:
            if self.store_type == "chroma":
                import chromadb

                self.client = chromadb.PersistentClient(path=self.path_or_url)
            elif self.store_type == "weaviate":
                # TODO: 实现 Weaviate 支持
                raise NotImplementedError("Weaviate 支持即将推出")
            elif self.store_type == "pinecone":
                # TODO: 实现 Pinecone 支持
                raise NotImplementedError("Pinecone 支持即将推出")
            else:
                raise ValueError(f"不支持的向量数据库类型: {self.store_type}")
        except Exception as e:
            logger.error(f"向量数据库初始化失败: {e}")
            raise

    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        添加文档到向量数据库

        Args:
            documents: 文本列表
            embeddings: 嵌入向量列表
            metadatas: 元数据列表（可选）
            ids: 文档 ID 列表（可选）

        Returns:
            添加的文档 ID 列表
        """
        try:
            collection = self.client.get_or_create_collection(
                name=self.collection_name
            )

            # 如果没有提供 ID，生成 ID
            if ids is None:
                import uuid
                ids = [str(uuid.uuid4()) for _ in documents]

            # 添加文档
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas or [{}] * len(documents),
                ids=ids,
            )

            logger.info(f"添加 {len(documents)} 个文档到向量数据库")
            return ids
        except Exception as e:
            logger.error(f"添加文档失败: {e}")
            raise

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        搜索相似文档

        Args:
            query_embedding: 查询向量
            top_k: 返回的结果数量

        Returns:
            相似文档列表，格式为 [{"id": ..., "content": ..., "score": ..., "metadata": ...}, ...]
        """
        try:
            collection = self.client.get_collection(name=self.collection_name)

            # 搜索
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
            )

            # 格式化结果
            documents = []
            if results and results["documents"] and len(results["documents"]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    documents.append(
                        {
                            "id": results["ids"][0][i],
                            "content": doc,
                            "score": results["distances"][0][i] if "distances" in results else 0,
                            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        }
                    )

            logger.info(f"搜索完成: 返回 {len(documents)} 个结果")
            return documents
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            raise

    def delete_document(self, doc_id: str) -> bool:
        """
        删除文档

        Args:
            doc_id: 文档 ID

        Returns:
            是否删除成功
        """
        try:
            collection = self.client.get_collection(name=self.collection_name)
            collection.delete(ids=[doc_id])
            logger.info(f"文档已删除: {doc_id}")
            return True
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False

    def clear_collection(self) -> bool:
        """
        清空集合

        Returns:
            是否清空成功
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"集合已清空: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"清空集合失败: {e}")
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        获取集合统计信息

        Returns:
            统计信息
        """
        try:
            collection = self.client.get_collection(name=self.collection_name)
            return {
                "collection_name": self.collection_name,
                "count": collection.count(),
            }
        except Exception as e:
            logger.error(f"获取集合统计信息失败: {e}")
            return {}
