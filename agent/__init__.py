"""
Agent 模块 - LangGraph 智能体框架

核心功能：
1. AgentCore - Agent 核心执行引擎
2. AgentState - Agent 状态定义
3. Graph - LangGraph 工作流构建
4. Nodes - 工作流节点定义

快速开始：
    from agent import AgentCore

    agent = AgentCore()
    response = await agent.execute_query(kb_id, query)
"""

from .state import AgentState
from .nodes import retrieve_documents, generate_response, process_tool_calls
from .graph import create_agent_graph
from .agent_core import AgentCore

__all__ = [
    "AgentCore",
    "AgentState",
    "create_agent_graph",
    "retrieve_documents",
    "generate_response",
    "process_tool_calls",
]
