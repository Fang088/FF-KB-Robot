"""
智能问答页面（核心功能）

功能：
1. 对话管理（新建/切换/删除）
2. 知识库选择
3. 参数调节
4. 简约聊天界面
5. 历史记录

作者: FF-KB-Robot Team
创建时间: 2025-12-02
优化时间: 2025-12-08
"""

import streamlit as st

# 页面配置 - 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="智能问答 - FF-KB-Robot",
    page_icon="💬",
    layout="wide"
)

import sys
import logging
from pathlib import Path

# 添加 web_ui 到路径
WEB_UI_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WEB_UI_ROOT))

from services.kb_service import KnowledgeBaseService
from services.query_service import QueryService
from components.kb_selector import render_kb_selector
from components.chat_manager import (
    manage_conversations,
    get_messages,
    add_message,
    create_new_conversation,
    get_conversation_kb_id,
    get_conversation_kb_name,
    update_conversation_title,
    get_conversation_title
)
from styles.custom import apply_custom_css

# 初始化日志记录器
logger = logging.getLogger(__name__)


def render_chat_messages(messages, show_confidence=True, show_retrieved_docs=True):
    """
    渲染聊天消息（自适应样式）

    Args:
        messages: 消息列表
        show_confidence: 是否显示置信度
        show_retrieved_docs: 是否显示检索文档
    """
    from datetime import datetime

    for message in messages:
        # 格式化时间戳
        timestamp = message.get("timestamp", "")
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp)
                time_str = dt.strftime("%H:%M:%S")
            except:
                time_str = ""
        else:
            time_str = ""

        if message["role"] == "user":
            # 用户消息 - 右侧显示
            with st.chat_message("user"):
                st.markdown(message["content"])

                # 【改进】显示用户消息中的文件信息
                uploaded_files = message.get("uploaded_files", [])
                if uploaded_files:
                    with st.expander(f"📎 附加文件 ({len(uploaded_files)}) ", expanded=False):
                        for file_info in uploaded_files:
                            file_size_kb = file_info.get("file_size", 0) / 1024
                            file_type = file_info.get("file_type", "unknown").upper()
                            st.caption(
                                f"📄 **{file_info.get('filename', 'unknown')}** "
                                f"({file_type}, {file_size_kb:.1f}KB)"
                            )

                if time_str:
                    st.caption(f"🕐 {time_str}")
        else:
            # 助手消息 - 左侧显示
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(message["content"])

                # 欢迎消息只显示内容，不显示额外信息
                is_welcome = message.get("is_welcome", False)

                if not is_welcome:
                    # 显示时间戳
                    if time_str and not message.get("error", False):
                        st.caption(f"🕐 {time_str}")

                    # 显示置信度和元信息（仅显示查询结果，不显示欢迎或错误消息）
                    if not message.get("error", False) and show_confidence:
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            st.caption(f"🎯 置信度: {message.get('confidence', 0):.2f}")

                        with col2:
                            st.caption(f"⭐ 等级: {message.get('confidence_level', '未知')}")

                        with col3:
                            response_time = message.get('response_time_ms', 0)
                            st.caption(f"⏱️ 响应: {response_time}ms")

                        with col4:
                            from_cache = message.get('from_cache', False)
                            cache_icon = "✅" if from_cache else "❌"
                            st.caption(f"{cache_icon} 缓存: {'是' if from_cache else '否'}")

                    # 显示检索文档
                    if not message.get("error", False) and show_retrieved_docs and message.get("retrieved_docs"):
                        with st.expander("📚 查看检索文档", expanded=False):
                            for idx, doc in enumerate(message["retrieved_docs"], 1):
                                st.markdown(f"**文档 {idx}** (相似度: {doc['score']:.4f})")
                                st.text(doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"])
                                st.markdown("---")


def main():
    """主函数"""
    # 应用自定义样式
    apply_custom_css()

    # 基础样式：给底部留出空间，避免内容被输入框遮挡
    st.markdown("""
        <style>
        .main .block-container {
            padding-bottom: 120px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # 初始化查询服务和知识库服务
    query_service = QueryService()
    kb_service = KnowledgeBaseService()

    # Sidebar 侧边栏
    with st.sidebar:

        # 知识库选择器
        selected_kb_id = render_kb_selector(
            key_prefix="chat_page_kb",
            show_create_button=False,
            show_stats=False
        )

        if not selected_kb_id:
            st.warning("⬆️ 请先选择一个知识库")
        else:
            # 获取知识库名称
            kb_result = kb_service.get_knowledge_base_info(selected_kb_id)
            kb_name = kb_result["data"]["name"] if kb_result["success"] else "未知知识库"

            st.success(f"✅ 已选择: {kb_name}")

            # 创建新对话按钮
            if st.button("➕ 创建新对话", key="create_new_conv_with_kb", use_container_width=True, type="primary"):
                create_new_conversation(kb_id=selected_kb_id, kb_name=kb_name)
                st.rerun()

        st.markdown("---")

        # 对话管理
        st.markdown("### 💬 对话管理")
        manage_conversations()

        # 参数调节（只有在有当前对话时显示）
        if st.session_state.get("current_conversation_id"):
            st.markdown("### ⚙️ 参数设置")

            top_k = st.slider(
                "检索数量",
                min_value=1,
                max_value=10,
                value=5,
                key="top_k_slider",
                help="检索多少个相关文档"
            )

            use_cache = st.checkbox(
                "缓存加速",
                value=True,
                key="use_cache_checkbox",
                help="启用缓存可以加快重复查询速度"
            )

            st.markdown("---")
        else:
            top_k = 5
            use_cache = True

        # 系统说明
        st.markdown("### 💡 使用技巧")
        st.caption(
            "1. 先选择知识库\n\n"
            "2. 创建新对话（一个对话对应一个知识库）\n\n"
            "3. 问题具体清晰描述\n\n"
            "4. 关注置信度和检索文档"
        )

    # 主区域
    if not st.session_state.get("current_conversation_id"):
        st.markdown("### 💬 智能问答")
        st.info("💬 请先选择知识库，然后在左侧边栏创建新对话")
        return

    # 获取当前对话的知识库
    current_conv_id = st.session_state.current_conversation_id
    conv_kb_id = get_conversation_kb_id(current_conv_id)
    conv_kb_name = get_conversation_kb_name(current_conv_id)

    if not conv_kb_id:
        st.warning("⚠️ 当前对话未关联知识库，请创建新对话")
        return

    # 获取当前对话标题
    conv_title = get_conversation_title(current_conv_id)

    # 对话框顶部 - 标题和编辑功能
    col_title, col_edit = st.columns([5, 1])

    with col_title:
        # 检查是否正在编辑标题
        if st.session_state.get("editing_title_conv_id") == current_conv_id:
            # 编辑模式
            new_title = st.text_input(
                "修改话题标题：",
                value=conv_title or "",
                key=f"title_edit_{current_conv_id}",
                placeholder="输入新的话题标题..."
            )
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("✅ 保存", key=f"save_title_{current_conv_id}", use_container_width=True):
                    if new_title.strip():
                        update_conversation_title(current_conv_id, new_title.strip())
                        st.session_state.editing_title_conv_id = None
                        st.rerun()
            with col_cancel:
                if st.button("❌ 取消", key=f"cancel_title_{current_conv_id}", use_container_width=True):
                    st.session_state.editing_title_conv_id = None
                    st.rerun()
        else:
            # 显示模式 - 显示标题
            st.markdown(f"## 💬 {conv_title}")

    with col_edit:
        # 编辑标题按钮
        if st.button("✏️", key=f"edit_title_{current_conv_id}", help="编辑标题"):
            st.session_state.editing_title_conv_id = current_conv_id
            st.rerun()

    # 显示当前对话信息（知识库）
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
                    border-radius: 10px; padding: 1rem; margin-bottom: 1rem;
                    border-left: 4px solid #667eea;">
            <p style="color: #666; font-size: 0.9rem; margin: 0;">
                📚 当前知识库: <strong>{conv_kb_name}</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    messages = get_messages(current_conv_id)

    # 聊天容器
    chat_container = st.container()

    with chat_container:
        if messages:
            render_chat_messages(
                messages,
                show_confidence=True,
                show_retrieved_docs=True
            )
        else:
            st.info("🎉 对话已创建！开始提问吧")

    # ========================================
    # 使用 chat_input 内置的文件上传功能
    # ========================================

    # 渲染聊天输入框（支持文件上传）
    user_input = st.chat_input(
        placeholder="💬 输入您的问题，按回车发送（可点击📎上传附件）...",
        key=f"chat_input_{current_conv_id}",
        accept_file=True
    )

    # ========================================
    # 处理用户输入和文件上传
    # ========================================

    if user_input:
        # chat_input 返回字典：{"text": str, "files": List[UploadedFile]}
        question_text = user_input.get("text", "").strip()
        uploaded_files = user_input.get("files", [])

        if question_text:
            # 处理上传的文件
            processed_files = []
            if uploaded_files:
                try:
                    from web_ui.services.conversation_file_manager import ConversationFileManager
                    from config.settings import settings
                    from utils.file_utils import is_supported_format
                    import time

                    file_manager = ConversationFileManager(settings.TEMP_UPLOAD_PATH)
                    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

                    for uploaded_file in uploaded_files:
                        try:
                            filename = uploaded_file.name
                            file_content = uploaded_file.read()
                            file_size = len(file_content)

                            # 检查文件大小
                            if file_size > MAX_FILE_SIZE:
                                st.warning(f"⚠️ 文件 {filename} 过大 ({file_size / (1024 * 1024):.1f}MB > 50MB)，已跳过")
                                continue

                            # 检查文件格式
                            if not is_supported_format(filename, "all"):
                                st.warning(f"⚠️ 文件 {filename} 格式不支持，已跳过")
                                continue

                            # 保存文件
                            file_info = file_manager.save_uploaded_file(
                                current_conv_id,
                                file_content,
                                filename
                            )
                            processed_files.append(file_info.to_dict())
                            logger.info(f"成功处理附件: {filename}")

                        except Exception as e:
                            logger.error(f"处理附件 {uploaded_file.name} 失败: {e}")
                            st.warning(f"⚠️ 处理文件 {uploaded_file.name} 失败")

                except Exception as e:
                    logger.error(f"文件处理失败: {e}")
                    st.error(f"❌ 文件处理失败: {str(e)}")

            # 添加用户消息
            add_message(
                current_conv_id,
                "user",
                question_text,
                uploaded_files=processed_files
            )

            # 设置待处理查询
            st.session_state.pending_query = {
                "kb_id": conv_kb_id,
                "question": question_text,
                "top_k": top_k,
                "use_cache": use_cache,
                "uploaded_files": processed_files
            }

            st.rerun()

    # 【新流程】第二步：处理待处理的查询（显示答案）
    if st.session_state.get("pending_query"):
        query_info = st.session_state.pending_query

        # 显示加载状态并执行查询
        with st.spinner("正在思考中..."):
            result = query_service.execute_query(
                kb_id=query_info["kb_id"],
                question=query_info["question"],
                top_k=query_info["top_k"],
                use_cache=query_info["use_cache"],
                uploaded_files=query_info.get("uploaded_files", [])  # 【新增】传递上传的文件
            )

        # 处理查询结果
        if result["success"]:
            data = result["data"]
            add_message(
                current_conv_id,
                "assistant",
                data["answer"],
                confidence=data["confidence"],
                confidence_level=data["confidence_level"],
                retrieved_docs=data["retrieved_docs"],
                response_time_ms=data["response_time_ms"],
                from_cache=data["from_cache"],
                metadata=data["metadata"]
            )
        else:
            add_message(
                current_conv_id,
                "assistant",
                f"抱歉，查询失败了... {result['message']}",
                error=True
            )

        # 清除待处理查询标志
        del st.session_state.pending_query

        # 重新运行以显示答案
        st.rerun()


if __name__ == "__main__":
    main()
