"""
配置常量模块 - 统一管理所有的魔法数字和常量

功能：
1. 缓存相关常量
2. 检索优化常量
3. 模型参数常量
4. 数据库常量
5. 路径相关常量
"""

from enum import Enum
from typing import Dict, Any


# ==================== 缓存相关常量 ====================

class CacheConstants:
    """缓存相关常量"""

    # 缓存TTL（秒）
    EMBEDDING_CACHE_TTL = 3600  # Embedding缓存1小时
    QUERY_RESULT_CACHE_TTL = 1800  # 查询结果缓存30分钟
    RETRIEVAL_CACHE_TTL = 900  # 检索结果缓存15分钟
    DOCUMENT_CACHE_TTL = 7200  # 文档缓存2小时

    # 缓存键前缀
    EMBEDDING_CACHE_PREFIX = "emb:"
    QUERY_CACHE_PREFIX = "qry:"
    RETRIEVAL_CACHE_PREFIX = "ret:"
    DOCUMENT_CACHE_PREFIX = "doc:"

    # 缓存大小限制
    MAX_EMBEDDING_CACHE_SIZE = 10000  # 最多缓存10000条embedding
    MAX_QUERY_CACHE_SIZE = 5000
    MAX_RETRIEVAL_CACHE_SIZE = 1000

    # 缓存清理策略
    CACHE_CLEANUP_INTERVAL = 3600  # 每1小时检查一次过期缓存
    CACHE_EVICTION_POLICY = "lru"  # 淘汰策略：lru（最近最少使用）


# ==================== 检索优化常量 ====================

class RetrievalConstants:
    """检索优化相关常量"""

    # 相似度阈值
    SIMILARITY_THRESHOLD = 10.0  # HNSW的距离阈值
    DEDUP_THRESHOLD = 0.85  # 去重相似度阈值

    # 检索数量
    DEFAULT_TOP_K = 5  # 默认返回前5个相关文档
    FETCH_MULTIPLIER = 5  # 实际获取数量 = TOP_K * FETCH_MULTIPLIER

    # 文本分块参数
    DEFAULT_CHUNK_SIZE = 1000  # 单个块的字符数
    DEFAULT_CHUNK_OVERLAP = 200  # 块之间的重叠字符数
    MAX_CHUNK_SIZE = 4000  # 最大块大小
    MIN_CHUNK_SIZE = 100  # 最小块大小

    # 批处理参数
    BATCH_SIZE_EMBEDDING = 100  # 批量embedding的批大小
    BATCH_SIZE_VECTOR_INSERT = 1000  # 向量插入批大小

    # 检索结果处理
    MAX_RETRIEVAL_RESULTS = 20  # 最多返回20个检索结果
    MIN_CONTEXT_LENGTH = 50  # 上下文最小长度


# ==================== HNSW向量库常量 ====================

class HNSWConstants:
    """HNSW向量库相关常量"""

    # 索引参数
    MAX_ELEMENTS = 1000000  # 最大元素数
    EF_CONSTRUCTION = 200  # 构建时的参数，影响索引质量
    EF_SEARCH = 100  # 搜索时的参数，影响搜索精度
    M = 16  # 每个节点的最大连接数
    DISTANCE_METRIC = "l2"  # 距离度量：l2（欧氏距离）或cosine

    # 向量参数
    DEFAULT_EMBEDDING_DIMENSION = 1536  # OpenAI embedding的默认维度

    # 索引文件
    INDEX_FILE_NAME = "hnsw.bin"
    METADATA_FILE_NAME = "metadata.json"


# ==================== 模型参数常量 ====================

class ModelConstants:
    """模型相关常量"""

    # LLM参数
    DEFAULT_LLM_TEMPERATURE = 0.7  # 温度参数，控制随机性
    DEFAULT_LLM_MAX_TOKENS = 2000  # 最大生成token数
    DEFAULT_LLM_TOP_P = 0.95  # nucleus sampling参数

    # Embedding参数
    EMBEDDING_BATCH_SIZE = 100  # 批量embedding时的批大小

    # 模型超时
    LLM_TIMEOUT_SECONDS = 120  # LLM调用超时
    EMBEDDING_TIMEOUT_SECONDS = 60  # Embedding调用超时

    # 重试参数
    MAX_RETRY_ATTEMPTS = 3  # 最大重试次数
    RETRY_DELAY_SECONDS = 1  # 初始重试延迟
    RETRY_BACKOFF_FACTOR = 2  # 退避因子


# ==================== 数据库常量 ====================

class DatabaseConstants:
    """数据库相关常量"""

    # 表名
    TABLE_KNOWLEDGE_BASES = "knowledge_bases"
    TABLE_DOCUMENTS = "documents"
    TABLE_CHUNKS = "chunks"
    TABLE_VECTORS = "vectors"

    # 数据库操作
    BATCH_INSERT_SIZE = 100  # 批量插入的批大小
    QUERY_TIMEOUT_SECONDS = 30  # 查询超时

    # 数据库编码
    DB_ENCODING = "utf-8"

    # 约束
    MAX_KB_NAME_LENGTH = 255
    MAX_FILENAME_LENGTH = 255
    MAX_CHUNK_TEXT_LENGTH = 10000


# ==================== 文件处理常量 ====================

class FileConstants:
    """文件处理相关常量"""

    # 支持的文件类���
    SUPPORTED_FILE_TYPES = {".pdf", ".txt", ".docx", ".doc", ".xlsx", ".xls"}
    DOCUMENT_FILE_TYPES = {".pdf", ".txt", ".docx", ".doc"}
    SPREADSHEET_FILE_TYPES = {".xlsx", ".xls"}

    # 文件大小限制
    MAX_FILE_SIZE_MB = 100  # 最大文件大小100MB
    MAX_TOTAL_FILES_SIZE_MB = 1000  # 单个知识库最大总大小1GB

    # 临时文件相关
    TEMP_UPLOAD_DIR = "data/temp_uploads"
    PROCESSED_CHUNKS_DIR = "data/processed_chunks"


# ==================== 日志相关常量 ====================

class LogConstants:
    """日志相关常量"""

    # 日志级别
    LOG_LEVEL_DEBUG = "DEBUG"
    LOG_LEVEL_INFO = "INFO"
    LOG_LEVEL_WARNING = "WARNING"
    LOG_LEVEL_ERROR = "ERROR"

    # 日志格式
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    # 日志文件
    LOG_DIR = "logs"
    LOG_FILE_NAME = "app.log"
    LOG_MAX_BYTES = 10485760  # 10MB
    LOG_BACKUP_COUNT = 5  # 保留5个备份

    # 敏感信息过滤
    SENSITIVE_KEYWORDS = {"api_key", "password", "token", "secret"}


# ==================== RAG优化常量 ====================

class RAGConstants:
    """RAG相关常量"""

    # 置信度权重
    CONFIDENCE_W_RETRIEVAL = 0.45  # 检索质量权重
    CONFIDENCE_W_COMPLETENESS = 0.25  # 完整度权重
    CONFIDENCE_W_KEYWORD_MATCH = 0.15  # 关键词匹配权重
    CONFIDENCE_W_ANSWER_QUALITY = 0.10  # 答案质量权重
    CONFIDENCE_W_CONSISTENCY = 0.05  # 一致性权重

    # 置信度阈值
    CONFIDENCE_THRESHOLD_HIGH = 0.8  # 高置信度
    CONFIDENCE_THRESHOLD_MEDIUM = 0.6  # 中置信度
    CONFIDENCE_THRESHOLD_LOW = 0.4  # 低置信度

    # RAG优化参数
    CONTEXT_WINDOW_SIZE = 4000  # 上下文窗口大小
    MAX_CONTEXT_CHUNKS = 10  # 最多使用10个检索结果
    MIN_CONTEXT_RELEVANCE = 0.3  # 最小相关性评分


# ==================== API相关常量 ====================

class APIConstants:
    """API相关常量"""

    # API供应商
    PROVIDER_OPENAI = "openai"
    PROVIDER_AZURE = "azure"
    PROVIDER_LOCAL = "local"

    # API端点
    OPENAI_API_BASE = "https://api.openai.com/v1"
    AZURE_API_VERSION_CHAT = "2024-08-01-preview"
    AZURE_API_VERSION_EMBEDDING = "2024-02-15-preview"

    # API限流
    RATE_LIMIT_REQUESTS_PER_MINUTE = 60  # 每分钟最多请求数
    RATE_LIMIT_TOKENS_PER_MINUTE = 90000  # 每分钟最多token数


# ==================== Agent相关常量 ====================

class AgentConstants:
    """Agent工作流相关常量"""

    # 工作流节点
    NODE_INPUT = "input"
    NODE_RETRIEVE = "retrieve_documents"
    NODE_GENERATE = "generate_response"
    NODE_OUTPUT = "output"

    # Agent状态
    STATE_RUNNING = "running"
    STATE_SUCCESS = "success"
    STATE_FAILED = "failed"

    # 最大重试次数
    MAX_WORKFLOW_RETRIES = 3
    WORKFLOW_TIMEOUT_SECONDS = 300


# ==================== 配置集合（供全局访问）====================

CACHE_CONFIG = {
    "embedding_ttl": CacheConstants.EMBEDDING_CACHE_TTL,
    "query_ttl": CacheConstants.QUERY_RESULT_CACHE_TTL,
    "retrieval_ttl": CacheConstants.RETRIEVAL_CACHE_TTL,
    "max_size": CacheConstants.MAX_EMBEDDING_CACHE_SIZE,
}

RETRIEVAL_CONFIG = {
    "top_k": RetrievalConstants.DEFAULT_TOP_K,
    "similarity_threshold": RetrievalConstants.SIMILARITY_THRESHOLD,
    "dedup_threshold": RetrievalConstants.DEDUP_THRESHOLD,
    "chunk_size": RetrievalConstants.DEFAULT_CHUNK_SIZE,
    "chunk_overlap": RetrievalConstants.DEFAULT_CHUNK_OVERLAP,
}

HNSW_CONFIG = {
    "max_elements": HNSWConstants.MAX_ELEMENTS,
    "ef_construction": HNSWConstants.EF_CONSTRUCTION,
    "ef_search": HNSWConstants.EF_SEARCH,
    "m": HNSWConstants.M,
    "dimension": HNSWConstants.DEFAULT_EMBEDDING_DIMENSION,
}

MODEL_CONFIG = {
    "temperature": ModelConstants.DEFAULT_LLM_TEMPERATURE,
    "max_tokens": ModelConstants.DEFAULT_LLM_MAX_TOKENS,
    "top_p": ModelConstants.DEFAULT_LLM_TOP_P,
}

RAG_CONFIDENCE_WEIGHTS = {
    "retrieval": RAGConstants.CONFIDENCE_W_RETRIEVAL,
    "completeness": RAGConstants.CONFIDENCE_W_COMPLETENESS,
    "keyword_match": RAGConstants.CONFIDENCE_W_KEYWORD_MATCH,
    "answer_quality": RAGConstants.CONFIDENCE_W_ANSWER_QUALITY,
    "consistency": RAGConstants.CONFIDENCE_W_CONSISTENCY,
}
