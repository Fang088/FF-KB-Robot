"""
Prompts 模块 - 集中管理提示词模板
"""

from .system_prompts import *
from .agent_prompts import *

__all__ = [
    "SYSTEM_PROMPTS",
    "AGENT_PROMPTS"
]
