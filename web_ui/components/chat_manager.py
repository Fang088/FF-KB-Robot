"""
对话管理组件

功能：
1. 新建对话
2. 历史对话列表
3. 对话切换
4. 对话删除（可选）

作者: FF-KB-Robot Team
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


def manage_conversations() -> Optional[str]:
    """
    管理对话会话（仅显示列表，不提供创建按钮）

    Returns:
        当前选中的对话ID，如果没有则为None
    """
    # 初始化对话列表
    if "conversations" not in st.session_state:
        st.session_state.conversations = []

    # 初始化当前对话ID
    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None

    # 初始化编辑标题对话ID
    if "editing_title_conv_id" not in st.session_state:
        st.session_state.editing_title_conv_id = None

    # 显示历史对话列表
    if st.session_state.conversations:
        st.markdown("#### 📜 历史对话")

        # 按时间倒序显示（最新的在前）
        for conv in reversed(st.session_state.conversations):
            with st.container():
                col1, col2 = st.columns([4, 1])

                with col1:
                    # 对话标题（显示第一条消息或时间）
                    title = conv.get("title", f"对话 {conv['id'][:8]}")
                    time_str = conv.get("created_at", "")[:16]

                    # 当前选中的对话高亮显示
                    if st.session_state.current_conversation_id == conv["id"]:
                        st.button(
                            f"🟢 {title}",
                            use_container_width=True,
                            key=f"conv_active_{conv['id']}",
                            type="primary"
                        )
                    else:
                        if st.button(
                            f"⚪ {title}",
                            use_container_width=True,
                            key=f"conv_{conv['id']}"
                        ):
                            switch_conversation(conv["id"])
                            st.rerun()

                with col2:
                    # 删除按钮
                    if st.button("🗑️", key=f"del_{conv['id']}", help="删除对话"):
                        delete_conversation(conv["id"])
                        st.rerun()

                # 显示创建时间和消息数量
                msg_count = len(conv.get("messages", []))
                kb_name = conv.get("kb_name", "未关联知识库")
                st.caption(f"{time_str} | {msg_count} 条消息 | 📚 {kb_name}")
                st.markdown("---")

    else:
        st.info("暂无历史对话，请先选择知识库并创建新对话")

    return st.session_state.current_conversation_id


def create_new_conversation(kb_id: Optional[str] = None, kb_name: Optional[str] = None):
    """
    创建新对话

    Args:
        kb_id: 知识库ID（可选）
        kb_name: 知识库名称（可选，用于显示）
    """
    conv_id = str(uuid.uuid4())

    # 创建新对话对象
    new_conv = {
        "id": conv_id,
        "title": "新对话",
        "created_at": datetime.now().isoformat(),
        "messages": [],
        "kb_id": kb_id,  # 关联的知识库ID
        "kb_name": kb_name  # 知识库名称（用于显示）
    }

    st.session_state.conversations.append(new_conv)
    st.session_state.current_conversation_id = conv_id

    # 添加欢迎消息
    welcome_msg = "你好！我是智能助手，有什么可以帮助你的吗？"
    if kb_name:
        welcome_msg = f"你好！我是智能助手，正在使用知识库【{kb_name}】为您服务"

    add_message(conv_id, "assistant", welcome_msg, is_welcome=True)


def switch_conversation(conv_id: str):
    """切换对话"""
    st.session_state.current_conversation_id = conv_id


def delete_conversation(conv_id: str):
    """删除对话"""
    st.session_state.conversations = [
        conv for conv in st.session_state.conversations
        if conv["id"] != conv_id
    ]

    # 如果删除的是当前对话，切换到第一个或清空
    if st.session_state.current_conversation_id == conv_id:
        if st.session_state.conversations:
            st.session_state.current_conversation_id = st.session_state.conversations[0]["id"]
        else:
            st.session_state.current_conversation_id = None


def get_current_conversation() -> Optional[Dict[str, Any]]:
    """获取当前对话"""
    if not st.session_state.current_conversation_id:
        return None

    for conv in st.session_state.conversations:
        if conv["id"] == st.session_state.current_conversation_id:
            return conv

    return None


def add_message(conv_id: str, role: str, content: str, **kwargs):
    """
    添加消息到对话

    Args:
        conv_id: 对话ID
        role: 角色（user/assistant）
        content: 消息内容
        **kwargs: 其他消息属性
    """
    # 查找对话
    for conv in st.session_state.conversations:
        if conv["id"] == conv_id:
            # 生成消息ID
            msg_id = str(uuid.uuid4())

            # 创建消息对象
            message = {
                "id": msg_id,
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                **kwargs
            }

            conv["messages"].append(message)

            # 如果是用户的第一条消息，用它作为对话标题
            if role == "user":
                user_messages = [m for m in conv["messages"] if m["role"] == "user"]
                if len(user_messages) == 1:  # 第一条用户消息
                    conv["title"] = content[:30] + ("..." if len(content) > 30 else "")

            break


def get_messages(conv_id: str) -> List[Dict[str, Any]]:
    """获取对话的所有消息"""
    for conv in st.session_state.conversations:
        if conv["id"] == conv_id:
            return conv.get("messages", [])

    return []


def clear_messages(conv_id: str):
    """清空对话消息"""
    for conv in st.session_state.conversations:
        if conv["id"] == conv_id:
            conv["messages"] = []
            break


def get_conversation_kb_id(conv_id: str) -> Optional[str]:
    """
    获取对话关联的知识库ID

    Args:
        conv_id: 对话ID

    Returns:
        知识库ID，如果不存在则为None
    """
    for conv in st.session_state.conversations:
        if conv["id"] == conv_id:
            return conv.get("kb_id")
    return None


def get_conversation_kb_name(conv_id: str) -> Optional[str]:
    """
    获取对话关联的知识库名称

    Args:
        conv_id: 对话ID

    Returns:
        知识库名称，如果不存在则为None
    """
    for conv in st.session_state.conversations:
        if conv["id"] == conv_id:
            return conv.get("kb_name")
    return None


def update_conversation_title(conv_id: str, new_title: str) -> bool:
    """
    修改对话标题

    Args:
        conv_id: 对话ID
        new_title: 新标题

    Returns:
        是否修改成功
    """
    for conv in st.session_state.conversations:
        if conv["id"] == conv_id:
            conv["title"] = new_title[:50] + ("..." if len(new_title) > 50 else "")  # 限制标题长度
            return True
    return False


def get_conversation_title(conv_id: str) -> Optional[str]:
    """
    获取对话标题

    Args:
        conv_id: 对话ID

    Returns:
        对话标题，如果不存在则为None
    """
    for conv in st.session_state.conversations:
        if conv["id"] == conv_id:
            return conv.get("title", "新对话")
    return None
