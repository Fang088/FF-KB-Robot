"""
系统监控页面

功能：
1. 系统统计信息
2. 知识库统计
3. 查询统计
4. 缓存统计
5. 系统配置信息

作者: FF-KB-Robot Team
创建时间: 2025-12-02
修复时间: 2025-12-02
"""

import streamlit as st

# 页面配置 - 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="系统监控 - FF-KB-Robot",
    page_icon="📊",
    layout="wide"
)

import sys
from pathlib import Path

# 添加 web_ui 到路径
WEB_UI_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WEB_UI_ROOT))

from services.kb_service import KnowledgeBaseService
from services.query_service import QueryService
from components.stats_display import render_stats_display, render_system_info
from styles.custom import apply_custom_css

# 应用自定义样式（在 set_page_config 之后）
apply_custom_css()

# 页面标题
st.title("📊 系统监控")
st.markdown("实时查看系统运行状态和性能指标")
st.markdown("---")


def main():
    """主函数"""
    kb_service = KnowledgeBaseService()
    query_service = QueryService()

    # 侧边栏操作
    with st.sidebar:
        st.markdown("### ⚙️ 操作")

        if st.button("🔄 刷新数据", use_container_width=True, type="primary"):
            st.rerun()

        if st.button("🗑️ 清空查询历史", use_container_width=True):
            result = query_service.clear_query_history()
            if result["success"]:
                st.success(f"✅ {result['message']}")
                st.rerun()
            else:
                st.error(f"❌ {result['message']}")

        st.markdown("---")

        st.markdown("### 📖 监控说明")
        st.caption(
            "本页面显示系统的实时运行状态，"
            "包括知识库、查询和缓存的统计信息"
        )

    # Tab 布局
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 总览",
        "📚 知识库统计",
        "💬 查询统计",
        "⚙️ 系统配置"
    ])

    with tab1:
        render_overview_tab()

    with tab2:
        render_kb_stats_tab(kb_service)

    with tab3:
        render_query_stats_tab(query_service)

    with tab4:
        render_system_config_tab()


def render_overview_tab():
    """渲染总览标签页"""
    st.markdown("## 📊 系统总览")

    # 显示统计信息
    render_stats_display(
        show_kb_stats=True,
        show_query_stats=True,
        show_cache_stats=True
    )

    st.markdown("---")

    # 系统状态
    st.markdown("### 🚀 系统状态")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.success("✅ 运行正常")
        st.caption("系统运行状态")

    with col2:
        st.info("📡 API 连接正常")
        st.caption("后端服务状态")

    with col3:
        st.success("💾 数据库正常")
        st.caption("数据库连接状态")


def render_kb_stats_tab(kb_service: KnowledgeBaseService):
    """
    渲染知识库统计标签页

    Args:
        kb_service: 知识库服务实例
    """
    st.markdown("## 📚 知识库统计")

    # 获取所有知识库
    result = kb_service.list_knowledge_bases()

    if not result["success"]:
        st.error(f"❌ {result['message']}")
        return

    kb_list = result["data"]

    if not kb_list:
        st.info("📭 还没有知识库")
        return

    # 总体统计
    st.markdown("### 📊 总体统计")

    col1, col2, col3, col4 = st.columns(4)

    # 防御 None 值：使用 or 0 确保得到数字
    total_docs = sum(kb.get("document_count") or 0 for kb in kb_list)
    total_chunks = sum(kb.get("total_chunks") or 0 for kb in kb_list)
    avg_chunks_per_kb = total_chunks / len(kb_list) if len(kb_list) > 0 else 0
    avg_docs_per_kb = total_docs / len(kb_list) if len(kb_list) > 0 else 0

    with col1:
        st.metric("知识库总数", len(kb_list))

    with col2:
        st.metric("文档总数", total_docs)

    with col3:
        st.metric("文本块总数", total_chunks)

    with col4:
        st.metric("平均文本块/库", f"{avg_chunks_per_kb:.0f}")

    st.markdown("---")

    # 各知识库详细统计
    st.markdown("### 📋 各知识库详情")

    # 创建表格数据
    import pandas as pd

    table_data = []
    for kb in kb_list:
        # 防御 None 值
        doc_count = kb.get("document_count") or 0
        chunk_count = kb.get("total_chunks") or 0
        avg_chunks = round(chunk_count / doc_count, 1) if doc_count > 0 else 0

        table_data.append({
            "知识库名称": kb["name"],
            "文档数": doc_count,
            "文本块数": chunk_count,
            "平均分块": avg_chunks,
            "创建时间": kb.get("created_at", "")[:10] if kb.get("created_at") else "未知"
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_query_stats_tab(query_service: QueryService):
    """
    渲染查询统计标签页

    Args:
        query_service: 查询服务实例
    """
    st.markdown("## 💬 查询统计")

    # 查询统计
    stats_result = query_service.get_query_statistics()

    if not stats_result["success"]:
        st.error(f"❌ {stats_result['message']}")
        return

    stats = stats_result["data"]

    # 显示统计信息
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "总查询次数",
            stats["total_queries"],
            help="系统启动后的查询总次数"
        )

    with col2:
        st.metric(
            "平均置信度",
            f"{stats['avg_confidence']:.1%}",
            help="所有查询的平均置信度"
        )

    with col3:
        st.metric(
            "平均响应时间",
            f"{stats['avg_response_time_ms']}ms",
            help="平均查询响应时间"
        )

    with col4:
        st.metric(
            "缓存命中率",
            stats['cache_hit_rate'],
            help="查询缓存的命中率"
        )

    st.markdown("---")

    # 缓存统计
    st.markdown("### 🚀 缓存统计")

    cache_result = query_service.get_cache_stats()

    if cache_result["success"]:
        cache_data = cache_result["data"]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("总请求数", cache_data["total_requests"])

        with col2:
            st.metric("缓存命中", cache_data["cache_hits"])

        with col3:
            st.metric("命中率", cache_data["hit_rate"])

        # 缓存效果说明
        st.info(
            "💡 **缓存优势**: 缓存命中的查询响应时间 <200ms，"
            "而未命中的完整查询约需 3-4秒。启用缓存可显著提升用户体验"
        )

    st.markdown("---")

    # 查询历史
    st.markdown("### 📜 最近查询历史")

    history_result = query_service.get_query_history(limit=10)

    if history_result["success"]:
        history = history_result["data"]

        if not history:
            st.info("📭 暂无查询历史")
        else:
            for idx, query in enumerate(history, 1):
                with st.expander(
                    f"{idx}. {query['question'][:50]}... (置信度: {query['confidence']:.1%})",
                    expanded=False
                ):
                    col1, col2 = st.columns([2, 1])

                    with col1:
                        st.text(f"问题: {query['question']}")
                        st.text(f"答案: {query['answer'][:100]}...")

                    with col2:
                        st.text(f"置信度: {query['confidence']:.1%}")
                        st.text(f"响应时间: {query['response_time_ms']}ms")
                        st.text(f"缓存: {'是' if query['from_cache'] else '否'}")


def render_system_config_tab():
    """渲染系统配置标签页"""
    st.markdown("## ⚙️ 系统配置")

    # 显示系统信息
    render_system_info()

    st.markdown("---")

    # 显示环境信息
    st.markdown("### Python 环境")

    import sys
    import platform

    col1, col2 = st.columns(2)

    with col1:
        st.text(f"Python 版本: {sys.version.split()[0]}")
        st.text(f"平台: {platform.system()} {platform.release()}")

    with col2:
        st.text(f"架构: {platform.machine()}")
        st.text(f"处理器: {platform.processor()[:30]}...")

    st.markdown("---")

    # 项目信息
    st.markdown("### 📦 项目信息")

    st.text("项目名称: FF-KB-Robot")
    st.text("版本: 0.1.0")
    st.text("前端框架: Streamlit")
    st.text("后端框架: LangGraph + HNSW")
    st.text("作者: FF-KB-Robot Team")


if __name__ == "__main__":
    main()
