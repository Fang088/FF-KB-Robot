"""
项目配置文件 - 使用 Pydantic Settings 最新版本
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """
    项目全局配置
    从环境变量或 .env 文件加载配置
    """

    # 项目基本信息
    PROJECT_NAME: str = "FF-KB-Robot"
    PROJECT_VERSION: str = "0.1.0"
    PROJECT_ROOT: Path = Path(__file__).parent.parent

    # 数据库配置
    DATABASE_URL: str = "sqlite:///./db/sql_db/kbrobot.db"
    VECTOR_STORE_PATH: str = "./db/vector_store"

    # LLM 配置（使用 302.ai API - OpenAI 兼容接口）
    LLM_PROVIDER: str = "openai"  # 302.ai 使用 OpenAI 兼容接口
    LLM_API_KEY: str = ""  # 从 .env 读取
    LLM_API_BASE: str = "https://api.302.ai/v1"  # 302.ai API 地址
    LLM_MODEL_NAME: str = "gpt-5-nano"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000

    # Embedding 配置（使用 302.ai API - OpenAI 兼容接口）
    EMBEDDING_PROVIDER: str = "openai"  # 302.ai 使用 OpenAI 兼容接口
    EMBEDDING_API_KEY: str = ""  # 从 .env 读取
    EMBEDDING_API_BASE: str = "https://api.302.ai/v1"  # 302.ai API 地址
    EMBEDDING_MODEL_NAME: str = "text-embedding-ada-002"
    EMBEDDING_DIMENSION: int = 1536

    # Vector Store 配置（仅支持HNSW）
    VECTOR_STORE_TYPE: str = "hnsw"  # 仅支持 hnsw
    VECTOR_STORE_COLLECTION_NAME: str = "ff_kb_documents"

    # HNSW 索引配置
    HNSW_INDEX_PATH: str = "./db/vector_store/hnsw_index"  # HNSW 索引文件路径
    HNSW_MAX_ELEMENTS: int = 1000000  # 最大元素数
    HNSW_EF_CONSTRUCTION: int = 200  # 构建时搜索扩展参数（越大精度越高，速度越慢）
    HNSW_EF_SEARCH: int = 100  # 搜索时扩展参数（越大精度越高，速度越慢） - 已提升以支持更好的搜索质量
    HNSW_M: int = 16  # 每个节点的最大连接数（越大索引更紧凑，搜索更快）
    HNSW_DISTANCE_METRIC: str = "l2"  # 距离度量：l2（欧几里得）, cosine, ip

    # 文档处理配置（已移至下方统一管理，保留这些为向后兼容）
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_UPLOAD_SIZE_MB: int = 100

    # LangGraph 配置
    LANGGRAPH_TIMEOUT: int = 60  # 秒
    LANGGRAPH_MAX_ITERATIONS: int = 10

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/ff_kb_robot.log"

    # 临时文件配置
    TEMP_UPLOAD_PATH: str = "D:\\VsCodePyProject\\LLMAPP\\FF-KB-Robot\\data\\temp_uploads"
    PROCESSED_CHUNKS_PATH: str = "D:\\VsCodePyProject\\LLMAPP\\FF-KB-Robot\\data\\temp_uploads"

    # ==================== 检索优化配置 ====================
    # 相似度过滤阈值（< 此值的结果会被过滤）
    # HNSW使用L2距离度量：
    #   - 距离=0: 完全相同
    #   - 距离<1: 很相似
    #   - 距离1-3: 相似
    #   - 距离>3: 不相似
    # 推荐值: 10.0 (允许距离在0-10之间的结果)
    # 原值0.1太严格，会过滤掉所有结果
    RETRIEVAL_SIMILARITY_THRESHOLD: float = 10.0
    # 去重阈值（相似度 > 此值认为是重复）
    RETRIEVAL_DEDUP_THRESHOLD: float = 0.85
    # 检索返回数量
    RETRIEVAL_TOP_K: int = 5
    # 向量库获取数量倍数（top_k * 倍数）
    # 获取更多候选结果，然后通过后处理器精选
    RETRIEVAL_FETCH_MULTIPLIER: int = 5
    # 是否启用检索后处理
    RETRIEVAL_ENABLE_POSTPROCESSOR: bool = True

    # ==================== 文本分块配置 ====================
    # 分块大小
    TEXT_CHUNK_SIZE: int = 1000
    # 分块重叠
    TEXT_CHUNK_OVERLAP: int = 200
    # 最小分块大小
    TEXT_MIN_CHUNK_SIZE: int = 100
    # 是否启用智能分块
    ENABLE_SMART_CHUNK: bool = True

    # ==================== 置信度计算配置 ====================
    # 最低置信度阈值
    MIN_CONFIDENCE: float = 0.3
    # 置信度权重（各维度）- 优化后的权重分配
    # 优先级：检索质量(45%) > 完整度(25%) > 关键词(15%) > 质量(10%) > 一致性(5%)
    CONFIDENCE_W_RETRIEVAL: float = 0.45      # 检索质量 - 最关键的维度
    CONFIDENCE_W_COMPLETENESS: float = 0.25   # 内容完整度 - 重要维度
    CONFIDENCE_W_KEYWORD_MATCH: float = 0.15  # 关键词匹配
    CONFIDENCE_W_ANSWER_QUALITY: float = 0.10 # 答案质量
    CONFIDENCE_W_CONSISTENCY: float = 0.05    # 答案一致性

    # ==================== LLM 生成配置 ====================
    # 生成最大 tokens
    GENERATION_MAX_TOKENS: int = 2000
    # 生成温度
    GENERATION_TEMPERATURE: float = 0.7

    # Pydantic v2 配置方式（新版本推荐）
    # 明确配置读取项目根目录下的 .env 文件
    # 使用绝对路径确保无论从哪里运行脚本都能正确找到.env文件
    model_config = ConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),  # 绝对路径指向项目根目录下的.env
        env_file_encoding="utf-8",  # 配置文件编码：UTF-8
        case_sensitive=True,  # 配置项区分大小写
        extra="ignore"  # 忽略配置文件中未定义的配置项
    )

    def get_project_root(self) -> Path:
        """获取项目根目录"""
        return self.PROJECT_ROOT

    def get_db_path(self) -> str:
        """获取数据库路径"""
        return str(self.PROJECT_ROOT / self.DATABASE_URL.replace("sqlite:///./", ""))

# 创建全局配置实例
settings = Settings()

