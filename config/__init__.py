"""
Config 模块 - 项目配置管理

核心功能：
- Settings: Pydantic 配置管理（从.env加载）

快速开始：
    from config import settings

    print(settings.LLM_MODEL_NAME)
    print(settings.RETRIEVAL_TOP_K)
"""

from .settings import settings

__all__ = [
    "settings",
]
