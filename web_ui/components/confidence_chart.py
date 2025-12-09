"""
置信度图表组件

功能：
1. 显示置信度进度条
2. 显示多维度置信度雷达图
3. 显示置信度分布

作者: FF-KB-Robot Team
"""

import streamlit as st
from typing import Dict, Any
import sys
from pathlib import Path

# 添加 web_ui 到路径
WEB_UI_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WEB_UI_ROOT))


def render_confidence_chart(
    confidence: float,
    confidence_breakdown: Dict[str, float] = None,
    show_breakdown: bool = True
) -> None:
    """
    渲染置信度图表组件

    Args:
        confidence: 总体置信度 (0.0-1.0)
        confidence_breakdown: 置信度分解 (可选)
        show_breakdown: 是否显示详细分解
    """
    # 总体置信度进度条
    st.markdown("### 🎯 答案置信度")

    # 根据置信度选择颜色
    if confidence >= 0.8:
        color = "green"
        level = "非常高"
        emoji = "⭐⭐⭐⭐⭐"
    elif confidence >= 0.6:
        color = "blue"
        level = "高"
        emoji = "⭐⭐⭐⭐"
    elif confidence >= 0.4:
        color = "orange"
        level = "中等"
        emoji = "⭐⭐⭐"
    elif confidence >= 0.2:
        color = "red"
        level = "低"
        emoji = "⭐⭐"
    else:
        color = "red"
        level = "非常低"
        emoji = "⭐"

    # 显示进度条
    st.progress(confidence, text=f"{level} - {confidence:.1%} {emoji}")

    # 显示详细分解
    if show_breakdown and confidence_breakdown:
        st.markdown("---")
        st.markdown("### 📊 多维度评分")

        # 维度映射（中文显示）
        dimension_mapping = {
            "retrieval": "🔍 检索质量",
            "completeness": "✅ 答案完整度",
            "keyword_match": "🔑 关键词匹配",
            "answer_quality": "💎 答案质量",
            "consistency": "🔗 答案一致性"
        }

        # 权重映射
        weight_mapping = {
            "retrieval": 0.45,
            "completeness": 0.25,
            "keyword_match": 0.15,
            "answer_quality": 0.10,
            "consistency": 0.05
        }

        # 显示每个维度
        for key, label in dimension_mapping.items():
            value = confidence_breakdown.get(key, 0.0)
            weight = weight_mapping.get(key, 0.0)

            col1, col2, col3 = st.columns([2, 3, 1])

            with col1:
                st.text(label)

            with col2:
                st.progress(value, text=f"{value:.1%}")

            with col3:
                st.caption(f"权重: {weight:.0%}")


def render_confidence_breakdown_table(
    confidence_breakdown: Dict[str, float]
) -> None:
    """
    渲染置信度分解表格

    Args:
        confidence_breakdown: 置信度分解数据
    """
    import pandas as pd

    # 维度映射
    dimension_mapping = {
        "retrieval": "检索质量",
        "completeness": "答案完整度",
        "keyword_match": "关键词匹配",
        "answer_quality": "答案质量",
        "consistency": "答案一致性"
    }

    # 权重映射
    weight_mapping = {
        "retrieval": 0.45,
        "completeness": 0.25,
        "keyword_match": 0.15,
        "answer_quality": 0.10,
        "consistency": 0.05
    }

    # 构建数据
    data = []
    for key, label in dimension_mapping.items():
        score = confidence_breakdown.get(key, 0.0)
        weight = weight_mapping.get(key, 0.0)
        weighted_score = score * weight

        data.append({
            "维度": label,
            "得分": f"{score:.1%}",
            "权重": f"{weight:.0%}",
            "加权得分": f"{weighted_score:.3f}"
        })

    # 显示表格
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 显示总分
    total_score = sum(
        confidence_breakdown.get(key, 0.0) * weight_mapping.get(key, 0.0)
        for key in dimension_mapping.keys()
    )
    st.metric(label="📈 综合得分", value=f"{total_score:.1%}")
