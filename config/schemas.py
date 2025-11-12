"""
数据模型定义 - 用于数据库记录和内部数据传输
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ======================== 知识库相关 ========================

class KnowledgeBaseCreate(BaseModel):
    """创建知识库的请求模型"""
    name: str = Field(..., description="知识库名称")
    description: Optional[str] = Field(None, description="知识库描述")
    tags: Optional[List[str]] = Field([], description="知识库标签")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "财务报告",
                "description": "公司财务报告汇总",
                "tags": ["财务", "2024"]
            }
        }
    )


class KnowledgeBase(KnowledgeBaseCreate):
    """知识库数据模型"""
    id: str = Field(..., description="知识库 ID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    document_count: int = Field(0, description="包含的文档数")
    total_chunks: int = Field(0, description="总分块数")

    model_config = ConfigDict(from_attributes=True)


# ======================== 文档相关 ========================

class DocumentCreate(BaseModel):
    """创建文档的请求模型"""
    kb_id: str = Field(..., description="知识库 ID")
    filename: str = Field(..., description="文档文件名")
    content: str = Field(..., description="文档内容（可选，如果不提供则从文件读取）")
    metadata: Optional[Dict[str, Any]] = Field({}, description="文档元数据")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kb_id": "kb_001",
                "filename": "report_2024.pdf",
                "content": "...",
                "metadata": {"source": "finance_dept", "year": 2024}
            }
        }
    )


class DocumentMetadata(BaseModel):
    """文档元数据"""
    source: Optional[str] = Field(None, description="文档来源")
    author: Optional[str] = Field(None, description="作者")
    created_date: Optional[datetime] = Field(None, description="文档创建日期")
    category: Optional[str] = Field(None, description="文档分类")
    tags: Optional[List[str]] = Field([], description="标签")
    extra: Optional[Dict[str, Any]] = Field({}, description="其他元数据")


class Document(DocumentCreate):
    """文档数据模型"""
    id: str = Field(..., description="文档 ID")
    chunk_count: int = Field(0, description="分块数")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    model_config = ConfigDict(from_attributes=True)


# ======================== 文本分块相关 ========================

class TextChunk(BaseModel):
    """文本分块模型"""
    id: str = Field(..., description="分块 ID")
    document_id: str = Field(..., description="所属文档 ID")
    kb_id: str = Field(..., description="所属知识库 ID")
    content: str = Field(..., description="分块内容")
    chunk_index: int = Field(..., description="分块在文档中的位置")
    metadata: Optional[Dict[str, Any]] = Field({}, description="分块元数据")
    vector: Optional[List[float]] = Field(None, description="向量表示")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    model_config = ConfigDict(from_attributes=True)


# ======================== Agent 相关 ========================

class AgentQuery(BaseModel):
    """Agent 查询请求"""
    kb_id: str = Field(..., description="知识库 ID")
    question: str = Field(..., description="问题")
    top_k: int = Field(5, description="检索的文档数量")
    use_tools: bool = Field(False, description="是否使用外部工具")
    stream: bool = Field(False, description="是否流式返回")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kb_id": "kb_001",
                "question": "2024年的营收是多少？",
                "top_k": 5,
                "use_tools": False,
                "stream": False
            }
        }
    )


class RetrievedDocument(BaseModel):
    """检索结果中的文档"""
    id: str = Field(..., description="分块 ID")
    content: str = Field(..., description="分块内容")
    score: float = Field(..., description="相似度分数")
    metadata: Optional[Dict[str, Any]] = Field({}, description="元数据")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "chunk_001",
                "content": "2024年营收达到1000万元...",
                "score": 0.95,
                "metadata": {"source": "report_2024.pdf", "page": 1}
            }
        }
    )


class AgentResponse(BaseModel):
    """Agent 响应"""
    query_id: str = Field(..., description="查询 ID")
    kb_id: str = Field(..., description="知识库 ID")
    question: str = Field(..., description="原始问题")
    answer: str = Field(..., description="生成的答案")
    retrieved_docs: List[RetrievedDocument] = Field([], description="检索到的相关文档")
    sources: List[str] = Field([], description="答案的信息来源")
    confidence: float = Field(..., description="答案的置信度")
    response_time_ms: float = Field(..., description="响应耗时（毫秒）")
    metadata: Optional[Dict[str, Any]] = Field({}, description="其他元数据")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query_id": "query_001",
                "kb_id": "kb_001",
                "question": "2024年的营收是多少？",
                "answer": "根据财务报告，2024年营收达到1000万元。",
                "retrieved_docs": [
                    {
                        "id": "chunk_001",
                        "content": "2024年营收达到1000万元...",
                        "score": 0.95,
                        "metadata": {}
                    }
                ],
                "sources": ["report_2024.pdf"],
                "confidence": 0.92,
                "response_time_ms": 1234.5
            }
        }
    )


# ======================== 模型配置相关 ========================

class ModelConfig(BaseModel):
    """模型配置模型"""
    id: str = Field(..., description="配置 ID")
    provider: str = Field(..., description="模型供应商（openai, azure, local）")
    model_name: str = Field(..., description="模型名称")
    api_key: Optional[str] = Field(None, description="API 密钥")
    api_base: Optional[str] = Field(None, description="API 基础 URL")
    temperature: float = Field(0.7, description="温度参数")
    max_tokens: int = Field(2000, description="最大 token 数")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    model_config = ConfigDict(from_attributes=True)


# ======================== 错误响应 ========================

class ErrorResponse(BaseModel):
    """错误响应"""
    error: str = Field(..., description="错误信息")
    error_code: str = Field(..., description="错误代码")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.now, description="错误时间")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "Knowledge base not found",
                "error_code": "KB_NOT_FOUND",
                "details": {"kb_id": "kb_001"},
                "timestamp": "2024-11-10T12:34:56"
            }
        }
    )
