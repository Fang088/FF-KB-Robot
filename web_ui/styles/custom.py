"""
自定义 CSS 样式

功能：为 Streamlit 应用提供自定义样式

作者: FF-KB-Robot Team
"""

import streamlit as st


def get_custom_css() -> str:
    """
    获取自定义 CSS 样式

    Returns:
        str: CSS 样式字符串
    """
    return """
    <style>
    /* ========== 全局样式 ========== */

    /* 主容器 */
    .main {
        padding: 1rem 2rem;
    }

    /* 隐藏 Streamlit 默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ========== 标题样式 ========== */

    h1 {
        color: #1e88e5;
        font-weight: 700;
        padding-bottom: 1rem;
        border-bottom: 3px solid #1e88e5;
    }

    h2 {
        color: #43a047;
        font-weight: 600;
        padding-top: 1rem;
    }

    h3 {
        color: #5e35b1;
        font-weight: 600;
    }

    /* ========== 卡片样式 ========== */

    .css-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }

    /* ========== 按钮样式 ========== */

    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }

    /* 主要按钮 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
    }

    /* 次要按钮 */
    .stButton > button[kind="secondary"] {
        background-color: #f5f5f5;
        color: #424242;
        border: 1px solid #e0e0e0;
    }

    /* ========== 输入框样式 ========== */

    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        padding: 0.75rem;
        transition: border-color 0.3s ease;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
    }

    /* ========== 选择框样式 ========== */

    .stSelectbox > div > div {
        border-radius: 8px;
    }

    /* ========== 文件上传器样式 ========== */

    .stFileUploader {
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        transition: all 0.3s ease;
    }

    .stFileUploader:hover {
        border-color: #764ba2;
        background-color: #f8f9fa;
    }

    /* ========== 指标卡片样式 ========== */

    .css-metric-container {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        border-radius: 10px;
        padding: 1rem;
        border-left: 4px solid #667eea;
    }

    /* ========== 进度条样式 ========== */

    .stProgress > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }

    /* ========== 警告和提示样式 ========== */

    .stAlert {
        border-radius: 10px;
        padding: 1rem;
    }

    /* 成功提示 */
    .stSuccess {
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
    }

    /* 警告提示 */
    .stWarning {
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
    }

    /* 错误提示 */
    .stError {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
    }

    /* 信息提示 */
    .stInfo {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }

    /* ========== 扩展器样式 ========== */

    .streamlit-expanderHeader {
        font-weight: 600;
        background-color: #f5f5f5;
        border-radius: 8px;
        padding: 0.5rem 1rem;
    }

    .streamlit-expanderHeader:hover {
        background-color: #eeeeee;
    }

    /* ========== 分隔线样式 ========== */

    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        margin: 2rem 0;
    }

    /* ========== 表格样式 ========== */

    .dataframe {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .dataframe thead th {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        text-align: left;
        padding: 1rem;
    }

    .dataframe tbody tr:nth-child(even) {
        background-color: #f8f9fa;
    }

    .dataframe tbody tr:hover {
        background-color: #e3f2fd;
        transition: background-color 0.3s ease;
    }

    /* ========== 聊天消息样式 ========== */

    /* 聊天消息容器 */
    .stChatMessage {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        animation: slideIn 0.3s ease-out;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }

    /* 用户消息样式 */
    [data-testid="stChatMessageContent"] {
        background-color: transparent;
    }

    /* 消息滑入动画 */
    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateY(15px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    /* 聊天输入框样式优化 */
    .stChatInput {
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        transition: all 0.3s ease;
    }

    .stChatInput:focus-within {
        border-color: #667eea;
        box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.15);
    }

    /* 时间戳样式 */
    .stChatMessage .stCaption {
        opacity: 0.7;
        font-size: 0.75rem;
        margin-top: 0.25rem;
    }

    /* 旧版聊天消息样式（保留兼容性） */
    .chat-message {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        animation: fadeIn 0.3s ease-in;
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .chat-message.user {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        border-left: 4px solid #2196f3;
    }

    .chat-message.assistant {
        background: linear-gradient(135deg, #f1f8e9 0%, #dcedc8 100%);
        border-left: 4px solid #8bc34a;
    }

    .chat-message.error {
        background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
        border-left: 4px solid #f44336;
    }

    /* ========== 侧边栏样式 ========== */

    .css-1d391kg {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        color: white;
    }

    .css-1d391kg .css-1v0mbdj {
        color: white;
    }

    /* ========== 滚动条样式 ========== */

    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }

    ::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #764ba2 0%, #667eea 100%);
    }

    /* ========== 响应式设计 ========== */

    @media (max-width: 768px) {
        .main {
            padding: 0.5rem;
        }

        h1 {
            font-size: 1.5rem;
        }

        h2 {
            font-size: 1.25rem;
        }
    }

    /* ========== 动画效果 ========== */

    @keyframes pulse {
        0%, 100% {
            opacity: 1;
        }
        50% {
            opacity: 0.5;
        }
    }

    .loading {
        animation: pulse 1.5s ease-in-out infinite;
    }

    </style>
    """


def apply_custom_css() -> None:
    """
    应用自定义 CSS 样式到 Streamlit 应用

    使用方法：
        在页面开头调用此函数即可应用样式
    """
    st.markdown(get_custom_css(), unsafe_allow_html=True)
