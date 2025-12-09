"""
文档管理页面

功能：
1. 查看知识库文档列表
2. 上传新文档
3. 删除文档
4. 查看文档详情

作者: FF-KB-Robot Team
创建时间: 2025-12-02
修复时间: 2025-12-02
"""

import streamlit as st

# 页面配置 - 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="文档管理 - FF-KB-Robot",
    page_icon="📝",
    layout="wide"
)

import sys
from pathlib import Path

from web_ui.utils.session_state import SessionStateManager, SessionKeys

# 添加 web_ui 到路径
WEB_UI_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WEB_UI_ROOT))

from services.doc_service import DocumentService
from components.kb_selector import render_kb_selector
from components.doc_uploader import render_doc_uploader, render_doc_list
from styles.custom import apply_custom_css

# 应用自定义样式（在 set_page_config 之后）
apply_custom_css()

# 页面标题
st.title("📝 文档管理")
st.markdown("上传、管理和查看知识库中的文档")
st.markdown("---")


def main():
    """主函数"""
    doc_service = DocumentService()

    # 侧边栏说明
    with st.sidebar:
        st.markdown("### 📖 使用说明")
        st.caption(
            "**支持的文档格式：**\n"
            "- PDF (.pdf)\n"
            "- Word (.docx)\n"
            "- Excel (.xlsx)\n"
            "- 纯文本 (.txt, .md)\n\n"
            "**处理流程：**\n"
            "1. 上传文档\n"
            "2. 自动解析和分块\n"
            "3. 生成向量索引\n"
            "4. 完成！可以开始问答"
        )

        st.markdown("---")

        # 显示支持的格式
        formats = doc_service.get_supported_formats()
        st.markdown("**📋 支持格式**")
        for fmt in formats:
            st.caption(f"✓ {fmt}")

    # 步骤 1：选择知识库

    selected_kb_id = render_kb_selector(
        key_prefix="doc_page_kb",
        show_create_button=False,
        show_stats=True
    )

    if not selected_kb_id:
        st.info("⬆️ 请先选择一个知识库")
        return

    # 保存到 session state
    SessionStateManager.set(SessionKeys.SELECTED_KB_ID, selected_kb_id)

    st.markdown("---")

    # 使用两列布局
    col1, col2 = st.columns([1, 1])

    with col1:
        # 步骤 2：上传文档

        uploaded = render_doc_uploader(
            kb_id=selected_kb_id,
            key_prefix="doc_page_upload",
            allow_multiple=True
        )

        if uploaded:
            # 上传成功后刷新文档列表
            st.rerun()

    with col2:
        # 步骤 3：查看文档列表

        render_doc_list(
            kb_id=selected_kb_id,
            key_prefix="doc_page_list",
            show_delete_button=True
        )


if __name__ == "__main__":
    main()
