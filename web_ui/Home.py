"""
FF-KB-Robot Web UI 主应用

这是 Streamlit 多页面应用的主页面

功能：
1. 欢迎页面
2. 系统介绍
3. 快速导航
4. 使用指南

作者: FF-KB-Robot Team
创建时间: 2025-12-02
"""

import streamlit as st

# 页面配置 - 必须是第一个 Streamlit 命令
st.set_page_config(
    page_title="FF-KB-Robot - 智能知识库问答系统",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from web_ui.components.stats_display import render_stats_display
from web_ui.styles.custom import apply_custom_css

# 应用自定义样式（在 set_page_config 之后）
apply_custom_css()


def main():
    """主函数"""

    # 侧边栏
    with st.sidebar:

        st.markdown("### 📋 功能导航")
        st.caption(
            "👈 请从上方选择功能页面：\n\n"
            "• 📚 知识库管理\n"
            "• 📝 文档管理\n"
            "• 💬 智能问答\n"
            "• 📊 系统监控"
        )

        st.markdown("---")

        st.markdown("### 💡 温馨提示")
        st.caption(
            "**首次使用：**\n"
            "1. 创建知识库\n"
            "2. 上传文档\n"
            "3. 开始问答\n\n"
            "**性能优化：**\n"
            "• 启用缓存加速查询\n"
            "• 合理设置检索数量\n"
            "• 定期清理无用数据"
        )

        st.markdown("---")

        st.caption("🎨 界面设计: 简洁优雅")
        st.caption("⚡ 性能优化: 极致体验")
        st.caption("🔒 数据安全: 本地存储")

    # 欢迎页面
    st.markdown(
        """
        <div style="text-align: center; padding: 2rem 0;">
            <h1 style="color: #667eea; font-size: 3rem; margin-bottom: 0;">
                🤖 FF-KB-Robot
            </h1>
            <p style="color: #666; font-size: 1.2rem; margin-top: 0.5rem;">
                企业级智能知识库 RAG 问答系统
            </p>
            <p style="color: #999; font-size: 1rem;">
                高性能检索·智能缓存·精准问答
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    # 系统介绍
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
                        border-radius: 10px; padding: 1.5rem; height: 200px;
                        border-left: 4px solid #667eea;">
                <h3 style="color: #667eea; margin-top: 0;">⚡ 高性能检索</h3>
                <p style="color: #666; font-size: 0.9rem;">
                    • HNSW 向量数据库<br>
                    • 毫秒级检索 (<100ms)<br>
                    • 支持百万级向量<br>
                    • 智能文本分块
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #43a04715 0%, #66bb6a15 100%);
                        border-radius: 10px; padding: 1.5rem; height: 200px;
                        border-left: 4px solid #43a047;">
                <h3 style="color: #43a047; margin-top: 0;">🚀 智能缓存</h3>
                <p style="color: #666; font-size: 0.9rem;">
                    • 4层缓存架构<br>
                    • 语义化缓存匹配<br>
                    • API成本降低50-70%<br>
                    • 重复查询<200ms响应
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:
        st.markdown(
            """
            <div style="background: linear-gradient(135deg, #5e35b115 0%, #7e57c215 100%);
                        border-radius: 10px; padding: 1.5rem; height: 200px;
                        border-left: 4px solid #5e35b1;">
                <h3 style="color: #5e35b1; margin-top: 0;">🎯 精准问答</h3>
                <p style="color: #666; font-size: 0.9rem;">
                    • LangGraph 工作流<br>
                    • 多维度置信度评分<br>
                    • RAG优化提示词<br>
                    • 智能检索后处理
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("---")

    # 快速导航
    st.markdown("## 🚀 快速开始")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("📚 知识库管理", use_container_width=True, type="primary"):
            st.info("👈 请从侧边栏选择 '📚 知识库管理' 页面")

    with col2:
        if st.button("📝 文档管理", use_container_width=True, type="primary"):
            st.info("👈 请从侧边栏选择 '📝 文档管理' 页面")

    with col3:
        if st.button("💬 智能问答", use_container_width=True, type="primary"):
            st.info("👈 请从侧边栏选择 '💬 智能问答' 页面")

    with col4:
        if st.button("📊 系统监控", use_container_width=True, type="primary"):
            st.info("👈 请从侧边栏选择 '📊 系统监控' 页面")

    st.markdown("---")

    # 使用指南
    st.markdown("## 📖 使用指南")

    with st.expander("1️⃣ 创建知识库", expanded=False):
        st.markdown(
            """
            **步骤：**
            1. 进入 '📚 知识库管理' 页面
            2. 点击 '➕ 创建新知识库' 按钮
            3. 填写知识库名称、描述和标签
            4. 点击 '✅ 创建' 完成创建

            **提示：** 知识库是存储文档的容器，建议按主题或用途创建不同的知识库
            """
        )

    with st.expander("2️⃣ 上传文档", expanded=False):
        st.markdown(
            """
            **步骤：**
            1. 进入 '📝 文档管理' 页面
            2. 选择目标知识库
            3. 点击或拖拽上传文档
            4. 系统自动处理和向量化

            **支持格式：** PDF, DOCX, XLSX, TXT, MD

            **处理流程：**
            - 文档解析 → 文本分块 → 向量化 → 索引构建

            **提示：** 每个文档会被智能分块（默认1000字符/块，重叠200字符）
            """
        )

    with st.expander("3️⃣ 开始问答", expanded=False):
        st.markdown(
            """
            **步骤：**
            1. 进入 '💬 智能问答' 页面
            2. 选择包含相关信息的知识库
            3. 输入您的问题
            4. 查看答案和置信度

            **查询流程：**
            ```
            问题输入 → 向量检索 → 文档排序 → LLM生成 → 置信度计算
            ```

            **高级功能：**
            - 📊 多维度置信度评分（5个维度）
            - 📚 检索文档详情查看
            - 🚀 智能缓存加速
            - 📜 查询历史记录

            **提示：** 启用缓存后，相同问题秒级响应 (<200ms)
            """
        )

    with st.expander("4️⃣ 监控系统", expanded=False):
        st.markdown(
            """
            **监控内容：**
            - 📚 知识库统计（数量、文档、分块）
            - 💬 查询统计（次数、置信度、响应时间）
            - 🚀 缓存统计（命中率、请求数）
            - ⚙️ 系统配置（模型、参数）

            **性能指标：**
            - 向量检索：<100ms
            - 完整查询：3-4秒（无缓存）
            - 缓存命中：<200ms
            - API成本：降低50-70%

            **提示：** 定期查看缓存命中率，优化系统性能
            """
        )

    st.markdown("---")

    # 系统统计
    st.markdown("## 📊 系统概览")

    render_stats_display(
        show_kb_stats=True,
        show_query_stats=True,
        show_cache_stats=True
    )

    st.markdown("---")

    # 技术架构
    st.markdown("## 🏗️ 技术架构")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 前端技术栈")
        st.markdown(
            """
            - **框架**: Streamlit
            - **架构**: 多页面应用 (MPA)
            - **设计模式**: 服务层分离
            - **组件化**: 可复用 UI 组件
            - **样式**: 自定义 CSS
            """
        )

    with col2:
        st.markdown("### 后端技术栈")
        st.markdown(
            """
            - **工作流**: LangGraph
            - **向量库**: HNSW
            - **LLM**: OpenAI API (302.ai)
            - **缓存**: 4层缓存系统
            - **数据库**: SQLite + HNSW
            """
        )

    st.markdown("---")

    # 页脚
    st.markdown(
        """
        <div style="text-align: center; color: #999; padding: 2rem 0;">
            <p>
                🤖 FF-KB-Robot v1.0 |
                基于 LangGraph + HNSW + Streamlit |
                Enterprise-Grade Knowledge Base RAG System
            </p>
            <p style="font-size: 0.8rem;">
                © 2025 FF-KB-Robot. All rights reserved.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )


# 直接调用 main() 函数（无论是直接运行还是作为模块导入）
main()

