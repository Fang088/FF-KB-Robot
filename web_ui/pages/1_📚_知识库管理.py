"""
知识库管理页面

功能：
1. 查看所有知识库
2. 创建新知识库
3. 查看知识库详情
4. 删除知识库

作者: FF-KB-Robot Team
创建时间: 2025-12-02
"""

import streamlit as st

# 页面配置 - 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="知识库管理 - FF-KB-Robot",
    page_icon="📚",
    layout="wide"
)

import sys
from pathlib import Path

from web_ui.utils.session_state import SessionStateManager
# 添加 web_ui 到路径
WEB_UI_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WEB_UI_ROOT))

from services.kb_service import KnowledgeBaseService
from components.stats_display import render_kb_stats_card
from styles.custom import apply_custom_css

# 应用自定义样式（在 set_page_config 之后）
apply_custom_css()

# 页面标题
st.title("📚 知识库管理")
st.markdown("管理您的知识库，创建、查看和删除知识库")
st.markdown("---")


def main():
    """主函数"""
    kb_service = KnowledgeBaseService()

    # 侧边栏操作
    with st.sidebar:
        st.markdown("### ⚙️ 操作")

        if st.button("➕ 创建新知识库", use_container_width=True, type="primary"):
            SessionStateManager.set("show_create_dialog", True)

        if st.button("🔄 刷新列表", use_container_width=True):
            st.rerun()

        st.markdown("---")
        st.markdown("### 📖 使用说明")
        st.caption(
            "知识库是存储文档和知识的容器。\n\n"
            "每个知识库可以包含多个文档，"
            "系统会自动处理文档并创建向量索引"
        )

    # 获取知识库列表
    result = kb_service.list_knowledge_bases()

    if not result["success"]:
        st.error(f"❌ {result['message']}")
        return

    kb_list = result["data"]

    # 显示创建对话框
    if SessionStateManager.get("show_create_dialog", False):
        render_create_kb_dialog()

    # 显示知识库列表
    if not kb_list:
        st.info("📭 还没有知识库，请创建一个")
        return

    st.markdown(f"### 📊 知识库列表 ({len(kb_list)} 个)")

    # 列表行布局显示知识库
    for kb_info in kb_list:
        render_kb_list_row(kb_info, kb_service)


def render_kb_list_row(kb_info: dict, kb_service: KnowledgeBaseService):
    """
    渲染知识库列表行（展开式布局）

    Args:
        kb_info: 知识库信息字典
        kb_service: 知识库服务实例
    """
    kb_id = kb_info['id']

    # 构建 Expander 标题
    doc_count = kb_info.get('document_count', 0)
    chunk_count = kb_info.get('total_chunks', 0)
    expander_title = (
        f"📚 {kb_info['name']} | "
        f"ID: {kb_id[:12]}... | "
        f"📄 {doc_count} | "
        f"📝 {chunk_count}"
    )

    # 截断标题防止超长
    if len(expander_title) > 80:
        expander_title = expander_title[:77] + "..."

    # 主 Expander
    with st.expander(expander_title):
        _render_kb_expanded_content(kb_info, kb_service)

    # 行分隔
    st.markdown("")


def _render_kb_expanded_content(kb_info: dict, kb_service: KnowledgeBaseService):
    """
    渲染展开器内容

    分为4个区块：
    1. 基本信息：ID、名称、描述、创建/更新时间、标签
    2. 详细统计：调用 render_kb_stats_card
    3. 操作按钮：查看、编辑、删除
    4. 删除确认：条件显示删除确认面板

    Args:
        kb_info: 知识库信息字典
        kb_service: 知识库服务实例
    """
    kb_id = kb_info['id']

    # ===== 区块1：基本信息 =====
    st.markdown("#### 📋 基本信息")
    col1, col2 = st.columns(2)

    with col1:
        st.text(f"ID: {kb_id}")
        st.text(f"名称: {kb_info['name']}")
        if kb_info.get("description"):
            st.text(f"描述: {kb_info['description']}")

    with col2:
        st.text(f"创建时间: {kb_info.get('created_at', '未知')}")
        st.text(f"更新时间: {kb_info.get('updated_at', '未知')}")
        if kb_info.get("tags"):
            st.text(f"标签: {', '.join(kb_info['tags'])}")

    st.markdown("---")

    st.markdown("#### 📊 统计信息")
    render_kb_stats_card(kb_id)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "📝 编辑",
            key=f"edit_{kb_id}",
            use_container_width=True,
            disabled=True
        ):
            st.info("编辑功能开发中")

    with col2:
        if st.button(
            "🗑️ 删除",
            key=f"delete_{kb_id}",
            use_container_width=True,
            type="secondary"
        ):
            confirm_key = f"kb_delete_confirm_{kb_id}"
            SessionStateManager.set(confirm_key, True)
            st.rerun()

    # ===== 区块4：删除确认 =====
    confirm_key = f"kb_delete_confirm_{kb_id}"
    if SessionStateManager.get(confirm_key, False):
        st.warning(
            f"⚠️ **确认要删除这个知识库吗？**\n\n"
            f"知识库：**{kb_info['name']}**\n\n"
            "此操作将删除知识库及其所有文档和向量数据，无法恢复",
            icon="⚠️"
        )

        col_confirm, col_cancel = st.columns(2)

        with col_confirm:
            if st.button(
                "✅ 确认删除",
                key=f"confirm_yes_{kb_id}",
                use_container_width=True,
                type="primary"
            ):
                # 执行删除
                with st.spinner("正在删除中..."):
                    delete_result = kb_service.delete_knowledge_base(kb_id)

                if delete_result["success"]:
                    st.success(f"✅ {delete_result['message']}")
                    SessionStateManager.delete(confirm_key)
                    st.rerun()
                else:
                    st.error(f"❌ {delete_result['message']}")
                    SessionStateManager.delete(confirm_key)

        with col_cancel:
            if st.button(
                "❌ 取消",
                key=f"confirm_no_{kb_id}",
                use_container_width=True
            ):
                # 取消删除，重置状态
                SessionStateManager.delete(confirm_key)
                st.rerun()


def render_create_kb_dialog():
    """渲染创建知识库对话框"""
    st.markdown("---")
    st.markdown("## ➕ 创建新知识库")

    with st.form(key="create_kb_form"):
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

                with st.spinner("正在创建知识库..."):
                    result = kb_service.create_knowledge_base(
                        name=name.strip(),
                        description=description.strip(),
                        tags=tags
                    )

                if result["success"]:
                    st.success(f"✅ {result['message']}")
                    SessionStateManager.delete("show_create_dialog")
                    st.rerun()
                else:
                    st.error(f"❌ {result['message']}")

        if cancel:
            SessionStateManager.delete("show_create_dialog")
            st.rerun()


def render_detail_dialog(kb_info: dict, kb_service: KnowledgeBaseService):
    """
    渲染详情对话框

    Args:
        kb_info: 知识库信息
        kb_service: 知识库服务实例
    """
    st.markdown("---")
    st.markdown(f"## 📖 知识库详情：{kb_info['name']}")

    # 基本信息
    col1, col2 = st.columns(2)

    with col1:
        st.text(f"ID: {kb_info['id']}")
        st.text(f"名称: {kb_info['name']}")
        st.text(f"描述: {kb_info.get('description', '无')}")

    with col2:
        st.text(f"创建时间: {kb_info.get('created_at', '未知')}")
        st.text(f"更新时间: {kb_info.get('updated_at', '未知')}")

        if kb_info.get("tags"):
            st.text(f"标签: {', '.join(kb_info['tags'])}")

    st.markdown("---")

    # 显示详细统计
    render_kb_stats_card(kb_info['id'])

    st.markdown("---")

    if st.button("关闭", key=f"close_detail_dialog_{kb_info['id']}"):
        SessionStateManager.delete("show_detail_dialog")
        SessionStateManager.delete("selected_kb_id")
        st.rerun()


if __name__ == "__main__":
    main()
