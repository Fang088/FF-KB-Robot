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

    # Vector Store 配置
    VECTOR_STORE_TYPE: str = "chroma"  # chroma, weaviate, pinecone
    VECTOR_STORE_COLLECTION_NAME: str = "ff_kb_documents"

    # 文档处理配置
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
    TEMP_UPLOAD_PATH: str = "./data/temp_uploads"
    PROCESSED_CHUNKS_PATH: str = "./data/processed_chunks"

    # 检索配置
    TOP_K_RETRIEVAL: int = 5  # 检索 Top K 相关文档
    SIMILARITY_THRESHOLD: float = 0.5

    # Pydantic v2 配置方式（新版本推荐）
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    def get_project_root(self) -> Path:
        """获取项目根目录"""
        return self.PROJECT_ROOT

    def get_db_path(self) -> str:
        """获取数据库路径"""
        return str(self.PROJECT_ROOT / self.DATABASE_URL.replace("sqlite:///./", ""))


# 创建全局配置实例
settings = Settings()
