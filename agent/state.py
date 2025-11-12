"""
LangGraph 状态定义 - 定义 Agent 的状态结构
"""

from typing import Optional, List, Dict, Any, Annotated
from dataclasses import dataclass, field
from datetime import datetime
import operator


@dataclass
class RetrievedDoc:
    """检索到的文档"""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
        }


@dataclass
class Message:
    """消息数据结构"""
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AgentState:
    """
    LangGraph Agent 状态
    定义 Agent 在执行过程中的状态信息
    """

    # 基本信息
    query_id: str
    kb_id: str
    question: str

    # 检索相关
    retrieved_docs: Annotated[List[RetrievedDoc], operator.add] = field(
        default_factory=list
    )
    retrieval_query: Optional[str] = None

    # 生成相关
    answer: Optional[str] = None
    intermediate_steps: Annotated[List[str], operator.add] = field(default_factory=list)

    # Tool 调用相关
    tool_calls: Annotated[List[Dict[str, Any]], operator.add] = field(
        default_factory=list
    )
    tool_results: Annotated[List[Dict[str, Any]], operator.add] = field(
        default_factory=list
    )

    # 消息历史
    messages: Annotated[List[Message], operator.add] = field(default_factory=list)

    # 元数据
    sources: Annotated[List[str], operator.add] = field(default_factory=list)
    confidence: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 流程控制
    current_node: str = "start"
    iteration: int = 0
    max_iterations: int = 10

    def add_message(self, role: str, content: str):
        """添加消息到历史"""
        self.messages.append(Message(role=role, content=content))

    def add_retrieved_doc(self, doc: RetrievedDoc):
        """添加检索到的文档"""
        self.retrieved_docs.append(doc)

    def add_intermediate_step(self, step: str):
        """添加中间步骤"""
        self.intermediate_steps.append(step)

    def add_tool_call(self, tool_name: str, tool_input: Dict[str, Any]):
        """添加工具调用"""
        self.tool_calls.append(
            {
                "tool_name": tool_name,
                "tool_input": tool_input,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def add_tool_result(self, tool_name: str, result: Any):
        """添加工具调用结果"""
        self.tool_results.append(
            {
                "tool_name": tool_name,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def add_source(self, source: str):
        """添加信息源"""
        if source not in self.sources:
            self.sources.append(source)

    def set_error(self, error: str):
        """设置错误信息"""
        self.error = error
        self.add_intermediate_step(f"[ERROR] {error}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "query_id": self.query_id,
            "kb_id": self.kb_id,
            "question": self.question,
            "answer": self.answer,
            "retrieved_docs": [doc.to_dict() for doc in self.retrieved_docs],
            "sources": self.sources,
            "confidence": self.confidence,
            "intermediate_steps": self.intermediate_steps,
            "tool_calls": self.tool_calls,
            "tool_results": self.tool_results,
            "messages": [msg.to_dict() for msg in self.messages],
            "error": self.error,
            "current_node": self.current_node,
            "iteration": self.iteration,
            "metadata": self.metadata,
        }

    def get_context_for_generation(self) -> str:
        """
        获取用于生成答案的上下文

        Returns:
            格式化的上下文文本
        """
        context_parts = []

        if self.retrieved_docs:
            context_parts.append("检索到的相关文档：\n")
            for i, doc in enumerate(self.retrieved_docs, 1):
                context_parts.append(
                    f"{i}. 相关度: {doc.score:.2f}\n内容: {doc.content}\n"
                )

        if self.tool_results:
            context_parts.append("\n工具调用结果：\n")
            for result in self.tool_results:
                context_parts.append(
                    f"- {result['tool_name']}: {result['result']}\n"
                )

        return "".join(context_parts)

    def is_complete(self) -> bool:
        """检查 Agent 是否完成"""
        return self.answer is not None and not self.error

    def should_continue(self) -> bool:
        """检查是否应该继续迭代"""
        return (
            self.iteration < self.max_iterations
            and not self.is_complete()
            and not self.error
        )

    def increment_iteration(self):
        """增加迭代计数"""
        self.iteration += 1
