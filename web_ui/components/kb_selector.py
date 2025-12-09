"""
知识库选择器组件

功能：
1. 显示所有知识库列表
2. 支持选择知识库
3. 显示知识库详细信息
4. 支持创建新知识库

作者: FF-KB-Robot Team
"""

import streamlit as st
from typing import Optional, Dict, Any
import sys
from pathlib import Path

# 添加 web_ui 到路径
WEB_UI_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WEB_UI_ROOT))

from services.kb_service import KnowledgeBaseService


def render_kb_selector(
    key_prefix: str = "kb_selector",
    show_create_button: bool = True,
    show_stats: bool = True
) -> Optional[str]:
    """
    渲染知识库选择器组件

    Args:
        key_prefix: 组件唯一标识前缀
        show_create_button: 是否显示创建按钮
        show_stats: 是否显示统计信息

    Returns:
        Optional[str]: 选中的知识库ID，未选择返回 None
    """
    kb_service = KnowledgeBaseService()

    # 获取知识库列表
    result = kb_service.list_knowledge_bases()

    if not result["success"]:
        st.error(f"❌ {result['message']}")
        return None

    kb_list = result["data"]

    # 如果没有知识库，提示创建
    if not kb_list:
        st.warning("⚠️ 还没有知识库呢，快来创建第一个吧！")

        if show_create_button:
            if st.button("➕ 创建知识库", key=f"{key_prefix}_create_first"):
                st.session_state[f"{key_prefix}_show_create_dialog"] = True

        return None

    # 构建选择选项
    kb_options = {
        f"{kb['name']} ({kb['id'][:8]})": kb['id']
        for kb in kb_list
    }

    # 知识库选择器
    col1, col2 = st.columns([4, 1])

    with col1:
        selected_name = st.selectbox(
            "📚 选择知识库",
            options=list(kb_options.keys()),
            key=f"{key_prefix}_selectbox",
            help="选择要操作的知识库"
        )

    with col2:
        if show_create_button:
            if st.button("➕ 新建", key=f"{key_prefix}_create_btn"):
                st.session_state[f"{key_prefix}_show_create_dialog"] = True

    if not selected_name:
        return None

    selected_kb_id = kb_options[selected_name]

    # 显示知识库详细信息
    if show_stats:
        # 获取知识库信息
        kb_info_result = kb_service.get_knowledge_base_info(selected_kb_id)
        if kb_info_result["success"]:
            kb_info = kb_info_result["data"]

            # 显示统计信息
            st.markdown("---")
            cols = st.columns(4)

            with cols[0]:
                st.metric(
                    label="📄 文档数量",
                    value=kb_info.get("document_count") or 0,  # 防御 None 值
                    help="知识库中的文档总数"
                )

            with cols[1]:
                st.metric(
                    label="📝 文本块数量",
                    value=kb_info.get("total_chunks") or 0,  # 防御 None 值
                    help="文档被分割成的文本块总数"
                )

            with cols[2]:
                # 防御 None 值：使用 or 0 确保得到数字
                doc_count = kb_info.get("document_count") or 0
                chunk_count = kb_info.get("total_chunks") or 0
                avg_chunks = (
                    round(chunk_count / doc_count, 1)
                    if doc_count > 0
                    else 0
                )
                st.metric(
                    label="📊 平均分块",
                    value=avg_chunks,
                    help="每个文档的平均文本块数量"
                )

            with cols[3]:
                # 防御 None 值：估算大小
                chunk_count = kb_info.get("total_chunks") or 0
                estimated_size = round(chunk_count * 1 / 1024, 2)  # 假设每块1KB
                st.metric(
                    label="💾 估算大小",
                    value=f"{estimated_size} MB",
                    help="知识库的估算存储大小"
                )

            # 显示描述和标签
            if kb_info.get("description"):
                st.caption(f"📋 描述：{kb_info['description']}")

            if kb_info.get("tags"):
                tags_html = " ".join([f"<span style='background-color:#e0e0e0;padding:2px 8px;border-radius:10px;margin-right:5px;font-size:12px;'>🏷️ {tag}</span>" for tag in kb_info["tags"]])
                st.markdown(tags_html, unsafe_allow_html=True)

    # 创建知识库对话框
    if show_create_button and st.session_state.get(f"{key_prefix}_show_create_dialog", False):
        _render_create_kb_dialog(key_prefix)

    return selected_kb_id


def _render_create_kb_dialog(key_prefix: str):
    """
    渲染创建知识库对话框

    Args:
        key_prefix: 组件唯一标识前缀
    """
    st.markdown("---")
    st.subheader("➕ 创建新知识库")

    with st.form(key=f"{key_prefix}_create_form"):
        name = st.text_input(
            "知识库名称 *",
            placeholder="例如：技术文档库",
            help="知识库的唯一名称"
        )

        description = st.text_area(
            "描述信息",
            placeholder="简要说明这个知识库的用途...",
            help="知识库的描述（可选）"
        )

        tags_input = st.text_input(
            "标签",
            placeholder="技术, 内部, 重要（用逗号分隔）",
            help="多个标签用逗号分隔"
        )

        col1, col2 = st.columns(2)

        with col1:
            submit = st.form_submit_button(
                "✅ 创建",
                use_container_width=True,
                type="primary"
            )

        with col2:
            cancel = st.form_submit_button(
                "❌ 取消",
                use_container_width=True
            )

        if submit:
            if not name.strip():
                st.error("❌ 知识库名称不能为空")
            else:
                # 解析标签
                tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()]

                # 创建知识库
                kb_service = KnowledgeBaseService()
                result = kb_service.create_knowledge_base(
                    name=name.strip(),
                    description=description.strip(),
                    tags=tags
                )

                if result["success"]:
                    st.success(f"✅ {result['message']}")
                    st.session_state[f"{key_prefix}_show_create_dialog"] = False
                    st.rerun()
                else:
                    st.error(f"❌ {result['message']}")

        if cancel:
            st.session_state[f"{key_prefix}_show_create_dialog"] = False
            st.rerun()
