"""
文档上传器组件

功能：
1. 文件拖拽上传
2. 支持多文件上传
3. 文件格式验证
4. 上传进度显示

作者: FF-KB-Robot Team
"""

import streamlit as st
from typing import List, Optional
import sys
from pathlib import Path
import tempfile
import os

# 添加 web_ui 到路径
WEB_UI_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WEB_UI_ROOT))

from services.doc_service import DocumentService


def render_doc_uploader(
    kb_id: str,
    key_prefix: str = "doc_uploader",
    allow_multiple: bool = True
) -> bool:
    """
    渲染文档上传器组件

    Args:
        kb_id: 知识库ID
        key_prefix: 组件唯一标识前缀
        allow_multiple: 是否允许多文件上传

    Returns:
        bool: 是否有文档上传成功
    """
    doc_service = DocumentService()

    st.markdown("### 📤 上传文档")

    # 显示支持的格式
    supported_formats = doc_service.get_supported_formats()
    st.caption(f"🎯 支持的格式：{', '.join(supported_formats)}")

    # 文件上传器
    uploaded_files = st.file_uploader(
        "选择文件",
        type=[fmt.replace(".", "") for fmt in supported_formats],
        accept_multiple_files=allow_multiple,
        key=f"{key_prefix}_uploader",
        help="拖拽文件到这里，或点击选择文件"
    )

    if not uploaded_files:
        return False

    # 确保 uploaded_files 是列表
    if not isinstance(uploaded_files, list):
        uploaded_files = [uploaded_files]

    # 显示上传按钮
    if st.button(
        f"✅ 上传 {len(uploaded_files)} 个文件",
        key=f"{key_prefix}_upload_btn",
        type="primary",
        use_container_width=True
    ):
        return _process_upload(kb_id, uploaded_files, doc_service)

    return False


def _process_upload(
    kb_id: str,
    uploaded_files: List,
    doc_service: DocumentService
) -> bool:
    """
    处理文件上传

    Args:
        kb_id: 知识库ID
        uploaded_files: 上传的文件列表
        doc_service: 文档服务实例

    Returns:
        bool: 是否有文档上传成功
    """
    success_count = 0
    failed_count = 0

    # 创建进度条
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, uploaded_file in enumerate(uploaded_files):
        # 更新进度
        progress = (idx + 1) / len(uploaded_files)
        progress_bar.progress(progress)
        status_text.text(f"正在处理：{uploaded_file.name} ({idx + 1}/{len(uploaded_files)})")

        try:
            # 保存到临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name

            # 上传文档
            result = doc_service.upload_document(
                kb_id=kb_id,
                file_path=tmp_file_path,
                filename=uploaded_file.name
            )

            # 清理临时文件
            try:
                os.unlink(tmp_file_path)
            except:
                pass

            if result["success"]:
                success_count += 1
                data = result["data"]
                st.success(
                    f"✅ {uploaded_file.name} - "
                    f"处理了 {data['chunk_count']} 个文本块 "
                    f"({data['processing_time_ms']}ms)"
                )
            else:
                failed_count += 1
                st.error(f"❌ {uploaded_file.name} - {result['message']}")

        except Exception as e:
            failed_count += 1
            st.error(f"❌ {uploaded_file.name} - 上传失败：{str(e)}")

    # 完成提示
    progress_bar.progress(1.0)
    status_text.empty()

    if success_count > 0:
        st.success(
            f"🎉 上传完成！成功 {success_count} 个，失败 {failed_count} 个"
        )
        return True
    else:
        st.error(f"❌ 所有文件上传失败")
        return False


def render_doc_list(
    kb_id: str,
    key_prefix: str = "doc_list",
    show_delete_button: bool = True
) -> None:
    """
    渲染文档列表组件

    Args:
        kb_id: 知识库ID
        key_prefix: 组件唯一标识前缀
        show_delete_button: 是否显示删除按钮
    """
    doc_service = DocumentService()

    st.markdown("### 📋 文档列表")

    # 获取文档列表
    result = doc_service.list_documents(kb_id)

    if not result["success"]:
        st.error(f"❌ {result['message']}")
        return

    doc_list = result["data"]

    if not doc_list:
        st.info("📭 还没有文档，快去上传吧！")
        return

    st.caption(f"📊 共 {len(doc_list)} 个文档")

    # 显示文档表格
    for idx, doc in enumerate(doc_list):
        # 防御 None 值和空字符串
        doc_id = doc.get('id') or f"unknown_{idx}"
        doc_filename = doc.get('filename') or "未命名文档"
        doc_chunk_count = doc.get('chunk_count') or 0
        doc_created_at = doc.get('created_at') or "未知时间"

        with st.expander(
            f"📄 {doc_filename} ({doc_chunk_count} 个文本块)",
            expanded=False
        ):
            col1, col2 = st.columns([3, 1])

            with col1:
                # 显示文档 ID（如果有效的话）
                if doc_id and doc_id != f"unknown_{idx}":
                    display_id = doc_id[:16] + "..." if len(doc_id) > 16 else doc_id
                    st.text(f"文档 ID: {display_id}")
                else:
                    st.text(f"文档 ID: 无效")

                st.text(f"创建时间: {doc_created_at}")
                st.text(f"文本块数量: {doc_chunk_count}")

            with col2:
                if show_delete_button:
                    # 删除按钮
                    if st.button(
                        "🗑️ 删除",
                        key=f"{key_prefix}_delete_{doc_id}",
                        type="secondary"
                    ):
                        # 点击删除，进入确��状态
                        confirm_key = f"{key_prefix}_confirm_delete_{doc_id}"
                        st.session_state[confirm_key] = True
                        st.rerun()

        # 删除确认区域（在卡片外面，避免嵌套问题）
        confirm_key = f"{key_prefix}_confirm_delete_{doc_id}"
        if st.session_state.get(confirm_key, False):
            st.markdown("---")
            st.warning(
                f"⚠️ **确认要删除这个文档吗？**\n\n"
                f"文档：**{doc_filename}**\n\n"
                f"此操作将删除文档及其所有分块和向量数据，**无法恢复**！",
                icon="⚠️"
            )

            # 确认/取消按钮
            col_confirm, col_cancel = st.columns(2)

            with col_confirm:
                if st.button(
                    "✅ 确认删除",
                    key=f"{key_prefix}_confirm_yes_{doc_id}",
                    use_container_width=True,
                    type="primary"
                ):
                    # 执行删除
                    with st.spinner("正在删除文档..."):
                        delete_result = doc_service.delete_document(kb_id, doc_id)

                    if delete_result["success"]:
                        st.success(f"✅ {delete_result['message']}")
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                    else:
                        st.error(f"❌ {delete_result['message']}")
                        st.session_state.pop(confirm_key, None)

            with col_cancel:
                if st.button(
                    "❌ 取消",
                    key=f"{key_prefix}_confirm_no_{doc_id}",
                    use_container_width=True
                ):
                    # 取消删除，重置状态
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
