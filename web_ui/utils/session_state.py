"""
Session State 管理器

功能：统一管理 Streamlit 的 session_state

作者: FF-KB-Robot Team
"""

import streamlit as st
from typing import Any, Optional


class SessionStateManager:
    """
    Session State 管理器

    职责：
    - 简化 session_state 的读写操作
    - 提供类型安全的接口
    - 统一命名规范
    """

    @staticmethod
    def get(key: str, default: Any = None) -> Any:
        """
        获取 session state 值

        Args:
            key: 键名
            default: 默认值

        Returns:
            Any: 对应的值，不存在则返回默认值
        """
        return st.session_state.get(key, default)

    @staticmethod
    def set(key: str, value: Any) -> None:
        """
        设置 session state 值

        Args:
            key: 键名
            value: 值
        """
        st.session_state[key] = value

    @staticmethod
    def delete(key: str) -> None:
        """
        删除 session state 值

        Args:
            key: 键名
        """
        if key in st.session_state:
            del st.session_state[key]

    @staticmethod
    def exists(key: str) -> bool:
        """
        检查 session state 是否存在

        Args:
            key: 键名

        Returns:
            bool: 是否存在
        """
        return key in st.session_state

    @staticmethod
    def initialize(key: str, default: Any) -> Any:
        """
        初始化 session state（如果不存在）

        Args:
            key: 键名
            default: 默认值

        Returns:
            Any: 当前值
        """
        if key not in st.session_state:
            st.session_state[key] = default
        return st.session_state[key]

    @staticmethod
    def clear_all() -> None:
        """清空所有 session state"""
        st.session_state.clear()

    @staticmethod
    def get_all_keys() -> list:
        """
        获取所有 session state 的键

        Returns:
            list: 所有键的列表
        """
        return list(st.session_state.keys())


# 常用的 session state 键名常量
class SessionKeys:
    """Session State 键名常量"""

    # 知识库相关
    SELECTED_KB_ID = "selected_kb_id"
    KB_LIST = "kb_list"

    # 聊天相关
    CHAT_MESSAGES = "chat_messages"
    CHAT_HISTORY = "chat_history"

    # 文档相关
    DOC_LIST = "doc_list"
    UPLOAD_STATUS = "upload_status"

    # 系统相关
    SYSTEM_CONFIG = "system_config"
    CACHE_STATS = "cache_stats"
