"""
对话管理组件

功能：
1. 新建对话
2. 历史对话列表
3. 对话切换
4. 对话删除（可选）
5. 对话持久化存储

作者: FF-KB-Robot Team
"""

import streamlit as st
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging
import time
from pathlib import Path

# 配置日志 - 只显示关键操作消息
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 导入数据库模块
from db.db_manager import DBConnection, ConversationRepository

# 初始化数据库连接
db = None
conv_repo = None

try:
    # 从统一的配置模块导入数据库路径
    try:
        from config.db_config import DB_PATH
    except ImportError:
        # 备选方案：直接计算路径（向后兼容）
        from pathlib import Path
        DB_PATH = Path(__file__).parent.parent.parent / "db" / "sql_db" / "kbrobot.db"
        logger.warning("无法导入 config.db_config，使用直接计算的路径")

    db = DBConnection(str(DB_PATH), auto_init=True)
    conv_repo = ConversationRepository(db)
    logger.info("数据库连接初始化成功")

except ImportError as e:
    logger.error(f"导入错误: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    logger.error(f"数据库初始化失败: {e}")
    import traceback
    traceback.print_exc()

# 批量保存配置
BATCH_SAVE_INTERVAL = 10  # 每 10 秒保存一次
BATCH_SAVE_THRESHOLD = 20  # 或者当消息达到 20 条时保存


class PersistenceManager:
    """后台持久化管理器 - 定期批量保存消息"""

    def __init__(self):
        self.pending_messages = []  # 待保存的消息列表
        self.dirty_conversations = set()  # 待保存的对话 ID
        self.last_save_time = time.time()

    def mark_dirty(self, conv_id: str, message: Dict = None):
        """标记对话或消息为脏数据（需要保存）"""
        self.dirty_conversations.add(conv_id)
        if message:
            self.pending_messages.append(message)

    def should_save(self) -> bool:
        """判断是否应该批量保存"""
        elapsed = time.time() - self.last_save_time
        msg_count = len(self.pending_messages)
        return elapsed >= BATCH_SAVE_INTERVAL or msg_count >= BATCH_SAVE_THRESHOLD

    def get_pending(self):
        """获取待保存数据"""
        msgs = self.pending_messages[:]
        convs = self.dirty_conversations.copy()
        return msgs, convs

    def clear_pending(self):
        """清空待保存数据"""
        self.pending_messages.clear()
        self.dirty_conversations.clear()
        self.last_save_time = time.time()


def manage_conversations() -> Optional[str]:
    """
    管理对话会话（仅显示列表，不提供创建按钮）

    Returns:
        当前选中的对话ID，如果没有则为None
    """
    # 【调试信息】显示数据库连接状态
    if conv_repo:
        st.sidebar.success("✅ 数据库已连接")
    else:
        st.sidebar.error("❌ 数据库连接失败！")

    # 初始化对话列表和持久化管理器
    if "conversations" not in st.session_state:
        try:
            # 从数据库加载所有对话（一次性加载）
            if conv_repo:
                db_convs = conv_repo.list_conversations()
                st.session_state.conversations = db_convs if db_convs else []
            else:
                logger.error("数据库连接失败")
                st.session_state.conversations = []
            st.session_state.persistence_mgr = PersistenceManager()
        except Exception as e:
            logger.error(f"从数据库加载对话失败: {e}")
            st.error(f"⚠️ 加载对话失败: {e}")
            st.session_state.conversations = []
            st.session_state.persistence_mgr = PersistenceManager()

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
        "updated_at": datetime.now().isoformat(),
        "messages": [],
        "kb_id": kb_id,  # 关联的知识库ID
        "kb_name": kb_name,  # 知识库名称（用于显示）
        "message_count": 0
    }

    # 【新增】立即保存对话到数据库（对话是主体，必须保存）
    try:
        if conv_repo:
            conv_repo.create_conversation(conv_id, kb_id, kb_name, "新对话")
        else:
            logger.warning("数据库连接不可用，对话不会被持久化")
    except Exception as e:
        logger.error(f"创建对话失败: {e}")
        st.error(f"创建对话失败: {e}")
        return

    st.session_state.conversations.append(new_conv)
    st.session_state.current_conversation_id = conv_id

    # 添加欢迎消息
    welcome_msg = "你好！我是智能助手，有什么可以帮���你的吗？"
    if kb_name:
        welcome_msg = f"你好！我是智能助手，正在使用知识库【{kb_name}】为您服务"

    add_message(conv_id, "assistant", welcome_msg, is_welcome=True)


def switch_conversation(conv_id: str):
    """切换对话"""
    st.session_state.current_conversation_id = conv_id


def delete_conversation(conv_id: str):
    """删除对话"""
    # 【新增】从数据库删除（立即执行，不延迟）
    try:
        if conv_repo:
            conv_repo.delete_conversation(conv_id)
        else:
            logger.warning("数据库连接不可用，对话不会被删除")
    except Exception as e:
        logger.error(f"删除对话失败: {e}")

    # 从 session_state 删除
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

            # 立即保存消息到数据库
            try:
                if conv_repo:
                    conv_repo.add_message(
                        msg_id,
                        conv_id,
                        role,
                        content,
                        **{k: v for k, v in kwargs.items()}
                    )
                else:
                    logger.error("conv_repo 是 None，无法保存消息到数据库！")
            except Exception as e:
                logger.error(f"保存消息失败: {e}")
                import traceback
                traceback.print_exc()

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
    # 【新增】更新数据库（立即保存）
    try:
        if conv_repo:
            conv_repo.update_conversation_title(conv_id, new_title)
        else:
            logger.warning("数据���连接不可用，标题不会被持久化")
    except Exception as e:
        logger.error(f"更新标题失败: {e}")
        return False

    # 更新 session_state
    for conv in st.session_state.conversations:
        if conv["id"] == conv_id:
            conv["title"] = new_title[:50] + ("..." if len(new_title) > 50 else "")
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


def _batch_save_to_db(persistence_mgr: PersistenceManager):
    """
    【辅助函数】批量保存待保存的消息到数据库

    Args:
        persistence_mgr: 持久化管理器实例
    """
    messages, _ = persistence_mgr.get_pending()

    if messages and conv_repo:
        try:
            for msg in messages:
                conv_id = msg.pop("conversation_id", None)
                if conv_id:
                    conv_repo.add_message(
                        msg["id"],
                        conv_id,
                        msg["role"],
                        msg["content"],
                        **{k: v for k, v in msg.items()
                           if k not in ["id", "role", "content", "conversation_id"]}
                    )
            persistence_mgr.clear_pending()
        except Exception as e:
            logger.error(f"批量保存消息失败: {e}")
    elif not conv_repo:
        logger.warning("数据库连接不可用，无法保存消息")

