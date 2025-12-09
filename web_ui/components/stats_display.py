"""
统计信息展示组件

功能：
1. 系统统计卡片
2. 查询统计图表
3. 缓存统计展示

作者: FF-KB-Robot Team
"""

import streamlit as st
from typing import Dict, Any
import sys
from pathlib import Path

# 添加 web_ui 到路径
WEB_UI_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WEB_UI_ROOT))

from services.kb_service import KnowledgeBaseService
from services.query_service import QueryService


def render_stats_display(
    show_kb_stats: bool = True,
    show_query_stats: bool = True,
    show_cache_stats: bool = True
) -> None:
    """
    渲染统计信息展示组件

    Args:
        show_kb_stats: 是否显示知识库统计
        show_query_stats: 是否显示查询统计
        show_cache_stats: 是否显示缓存统计
    """
    kb_service = KnowledgeBaseService()
    query_service = QueryService()

    # 知识库统计
    if show_kb_stats:
        st.markdown("### 📚 知识库统计")

        # 获取所有知识库
        result = kb_service.list_knowledge_bases()

        if result["success"]:
            kb_list = result["data"]

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    label="知识库数量",
                    value=len(kb_list),
                    help="系统中的知识库总数"
                )

            with col2:
                # 防止 None 值导致求和失败
                total_docs = sum(kb.get("document_count") or 0 for kb in kb_list)
                st.metric(
                    label="文档总数",
                    value=total_docs,
                    help="所有知识库的文档总数"
                )

            with col3:
                # 防止 None 值导致求和失败
                total_chunks = sum(kb.get("total_chunks") or 0 for kb in kb_list)
                st.metric(
                    label="文本块总数",
                    value=total_chunks,
                    help="所有知识库的文本块总数"
                )

        st.markdown("---")

    # 查询统计
    if show_query_stats:
        st.markdown("### 💬 查询统计")

        # 获取查询统计
        stats_result = query_service.get_query_statistics()

        if stats_result["success"]:
            stats = stats_result["data"]

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    label="总查询次数",
                    value=stats["total_queries"],
                    help="系统启动后的查询总次数"
                )

            with col2:
                st.metric(
                    label="平均置信度",
                    value=f"{stats['avg_confidence']:.1%}",
                    help="所有查询的平均置信度"
                )

            with col3:
                st.metric(
                    label="平均响应时间",
                    value=f"{stats['avg_response_time_ms']}ms",
                    help="平均查询响应时间"
                )

            with col4:
                st.metric(
                    label="缓存命中率",
                    value=stats['cache_hit_rate'],
                    help="查询缓存的命中率"
                )

        st.markdown("---")

    # 缓存统计
    if show_cache_stats:
        st.markdown("### 🚀 缓存统计")

        # 获取缓存统计
        cache_result = query_service.get_cache_stats()

        if cache_result["success"]:
            cache_data = cache_result["data"]

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    label="总请求数",
                    value=cache_data["total_requests"],
                    help="缓存系统处理的总请求数"
                )

            with col2:
                st.metric(
                    label="缓存命中",
                    value=cache_data["cache_hits"],
                    help="缓存命中的请求数"
                )

            with col3:
                st.metric(
                    label="命中率",
                    value=cache_data["hit_rate"],
                    help="缓存命中率（越高越好）"
                )

            # 显示缓存效果说明
            st.info(
                "💡 **缓存优势**: 缓存命中的查询响应时间 <200ms，"
                "而未命中的完整查询约需 3-4秒。启用缓存可显著提升用户体验"
            )


def render_kb_stats_card(kb_id: str) -> None:
    """
    渲染单个知识库的统计卡片

    Args:
        kb_id: 知识库ID
    """
    kb_service = KnowledgeBaseService()

    # 获取知识库统计
    result = kb_service.get_knowledge_base_stats(kb_id)

    if not result["success"]:
        st.error(f"❌ {result['message']}")
        return

    stats = result["data"]

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            label="📄 文档数量",
            value=stats["document_count"]
        )

        st.metric(
            label="📊 平均分块数",
            value=stats["avg_chunks_per_doc"]
        )

    with col2:
        st.metric(
            label="📝 文本块总数",
            value=stats["total_chunks"]
        )

        st.metric(
            label="💾 估算大小",
            value=f"{stats['total_size_mb']} MB"
        )


def render_system_info() -> None:
    """
    渲染系统信息卡片
    """
    import sys
    from pathlib import Path

    # 添加项目根目录到路径
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(PROJECT_ROOT))

    from config.settings import settings

    st.markdown("### ⚙️ 系统配置")

    col1, col2 = st.columns(2)

    with col1:
        st.text(f"🤖 LLM 模型: {settings.LLM_MODEL_NAME}")
        st.text(f"📊 向量维度: {settings.EMBEDDING_DIMENSION}")
        st.text(f"🔍 检索精度: EF={settings.HNSW_EF_SEARCH}")

    with col2:
        st.text(f"📝 分块大小: {settings.TEXT_CHUNK_SIZE}")
        st.text(f"🔄 分块重叠: {settings.TEXT_CHUNK_OVERLAP}")

    st.caption(f"📍 项目路径: {PROJECT_ROOT}")
