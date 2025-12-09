"""
UI 组件库 - 可复用的 Streamlit 组件

组件设计原则：
- S: 单一职责 - 每个组件只负责一个特定的UI功能
- O: 开放扩展 - 通过参数自定义组件行为
- I: 接口隔离 - 简单清晰的函数签名
- D: 依赖倒置 - 组件依赖服务层接口，而非具体实现

作者: FF-KB-Robot Team
创建时间: 2025-12-02
更新: 2025-12-08 - 移除 chat_interface（已重构为 chat_manager）
"""

from .kb_selector import render_kb_selector
from .doc_uploader import render_doc_uploader
from .chat_manager import manage_conversations, get_messages, add_message
from .confidence_chart import render_confidence_chart
from .stats_display import render_stats_display

__all__ = [
    "render_kb_selector",
    "render_doc_uploader",
    "manage_conversations",
    "get_messages",
    "add_message",
    "render_confidence_chart",
    "render_stats_display",
]
