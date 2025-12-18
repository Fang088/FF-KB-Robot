"""
对话文件上传组件 - Streamlit 组件

功能：
1. 提供文件上传按钮（集成到输入框旁）
2. 显示已上传文件的预览窗口
3. 提供文件删除功能
4. 文件大小和格式验证

作者: FF-KB-Robot Team
"""

import streamlit as st
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def render_file_upload_button(
    conversation_id: str,
    key_prefix: str = "chat_file_upload",
    max_files: int = 10,
    max_file_size_mb: int = 100,
    supported_formats: List[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    渲染简单的文件上传按钮（仅图标，无文字）

    Args:
        conversation_id: 对话 ID
        key_prefix: 组件 key 前缀
        max_files: 最多上传的文件数
        max_file_size_mb: 单个文件最大大小（MB）
        supported_formats: 支持的文件格式（后缀名列表）

    Returns:
        List[Dict]: 上传的文件信息列表，或 None
    """

    # 如果不在 session_state 中初始化，就初始化
    session_key = f"uploaded_files_{conversation_id}"
    if session_key not in st.session_state:
        st.session_state[session_key] = []

    # 支持的格式配置
    if supported_formats is None:
        supported_formats = [
            "jpg", "jpeg", "png", "gif", "bmp", "webp",
            "pdf", "doc", "docx", "xls", "xlsx", "txt", "md", "csv"
        ]

    # ========== 纯按钮式文件上传器 ==========
    uploaded_files = st.file_uploader(
        label="",  # 无标签
        accept_multiple_files=True,
        key=f"{key_prefix}_{conversation_id}",
        type=supported_formats,
        label_visibility="collapsed"
    )

    # ========== 处理上传的文件 ==========
    if uploaded_files:
        try:
            # 导入必要的工具
            from web_ui.services.conversation_file_manager import ConversationFileManager
            from config.settings import settings
            from utils.file_utils import is_supported_format

            file_manager = ConversationFileManager(settings.TEMP_UPLOAD_PATH)

            new_files = []
            for uploaded_file in uploaded_files:
                try:
                    # 获取文件信息
                    filename = uploaded_file.name
                    file_content = uploaded_file.read()
                    file_size = len(file_content)

                    # 验证文件格式
                    if not is_supported_format(filename, "all"):
                        st.warning(f"❌ 不支持的文件格式: {filename}")
                        continue

                    # 验证文件大小
                    if file_size > max_file_size_mb * 1024 * 1024:
                        st.warning(
                            f"❌ 文件太大: {filename} "
                            f"({file_size / (1024 * 1024):.1f}MB > {max_file_size_mb}MB)"
                        )
                        continue

                    # 保存文件并获取文件信息
                    file_info = file_manager.save_uploaded_file(
                        conversation_id,
                        file_content,
                        filename
                    )

                    new_files.append(file_info.to_dict())

                except Exception as e:
                    logger.error(f"处理文件失败 ({filename}): {e}")
                    st.error(f"❌ 处理文件失败: {filename}")

            # 更新 session state
            if new_files:
                st.session_state[session_key].extend(new_files)

        except Exception as e:
            logger.error(f"文件上传处理失败: {e}")

    # 返回上传的文件列表
    uploaded_file_list = st.session_state.get(session_key, [])
    return uploaded_file_list if uploaded_file_list else None


def render_file_preview_window(
    conversation_id: str,
    uploaded_files: Optional[List[Dict[str, Any]]] = None
) -> None:
    """
    渲染文件预览窗口（显示在输入框下方）

    Args:
        conversation_id: 对话 ID
        uploaded_files: 上传的文件列表
    """
    # 获取 session 中的上传文件
    session_key = f"uploaded_files_{conversation_id}"
    file_list = uploaded_files or st.session_state.get(session_key, [])

    if not file_list:
        return

    # ========== 文件预览窗口 ==========
    with st.container():
        st.markdown("")  # 添加一些空白

        # 显示已上传的文件列表（小窗口风格）
        with st.expander(f"📎 已附加 {len(file_list)} 个文件", expanded=True):
            for idx, file_info in enumerate(file_list):
                col1, col2, col3 = st.columns([4, 2, 1])

                with col1:
                    # 显示文件名和大小
                    file_size_kb = file_info.get("file_size", 0) / 1024
                    file_type = file_info.get("file_type", "unknown").upper()
                    st.caption(
                        f"📄 **{file_info.get('filename', 'unknown')}** "
                        f"({file_type}, {file_size_kb:.1f}KB)"
                    )

                with col2:
                    # 显示上传时间
                    upload_time = file_info.get("upload_time", "")
                    if upload_time:
                        from datetime import datetime
                        try:
                            dt = datetime.fromisoformat(upload_time)
                            time_str = dt.strftime("%H:%M:%S")
                            st.caption(f"🕐 {time_str}")
                        except:
                            pass

                with col3:
                    # 删除按钮
                    if st.button(
                        "❌",
                        key=f"remove_file_{conversation_id}_{idx}",
                        help="删除文件"
                    ):
                        st.session_state[session_key].pop(idx)
                        st.rerun()

                st.markdown("---")


def display_file_info_compact(file_info: Dict[str, Any]) -> None:
    """
    在消息中显示文件信息（紧凑版本）

    Args:
        file_info: 文件信息字典
    """
    filename = file_info.get("filename", "unknown")
    file_type = file_info.get("file_type", "unknown")
    file_size_kb = file_info.get("file_size", 0) / 1024

    st.caption(f"📎 {filename} ({file_type.upper()}, {file_size_kb:.1f}KB)")


def display_uploaded_files_summary(uploaded_files: List[Dict[str, Any]]) -> None:
    """
    显示上传文件的总结（用于消息展示）

    Args:
        uploaded_files: 上传文件列表
    """
    if not uploaded_files:
        return

    with st.expander(f"📎 上传的文件 ({len(uploaded_files)})"):
        for file_info in uploaded_files:
            display_file_info_compact(file_info)
