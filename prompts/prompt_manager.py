"""
提示词管理系统 - 统一管理所有的提示词

功能：
1. 集中管理所有提示词（系统、Agent、检索、分析等）
2. 提示词版本管理（v1, v2等）
3. 动态模板替换
4. 提示词验证和优化
5. 多语言支持框架
"""

import logging
from typing import Dict, List, Optional, Any
from enum import Enum
import json

logger = logging.getLogger(__name__)


class PromptCategory(str, Enum):
    """提��词类别"""
    RAG = "rag"  # 知识库问答
    AGENT = "agent"  # Agent决策
    RETRIEVAL = "retrieval"  # 检索优化
    ANALYSIS = "analysis"  # 数据分析
    EXTRACTION = "extraction"  # 信息抽取
    EVALUATION = "evaluation"  # 质量评估


class PromptVersion(str, Enum):
    """提示词版本"""
    V1 = "v1"  # 完整版
    V2 = "v2"  # 优化版
    SIMPLE = "simple"  # 简洁版


# ==================== RAG 提示词 ====================

RAG_PROMPTS = {
    "v1": {
        "system": """你是一个专业的知识库问答助手。
你的任务是根据提供的相关文档内容，精确、有帮助地回答用户的问题。

重要指南：
1. 仅基于提供的文档内容进行回答
2. 如果文档中没有相关信息，明确说明你无法回答
3. 在回答时引用相关文档的来源
4. 保持回答的准确性和专业性
5. 如果问题不清楚，请要求用户澄清

请以专业但友好的语气进行回答。""",
        "user": """【参考文档】
{context}

【问题】
{question}

请根据上述参考文档内容回答问题。""",
    },
    "v2": {
        "system": """你是一个知识库问答助手。直接、准确地回答问题。

要求：
1. 仅基于提供的文档回答
2. 清晰简洁，避免冗余
3. 如文档信息不足，明确指出""",
        "user": """【参考文档】{context}
【问题】{question}
请直接回答：""",
    },
    "simple": {
        "user": """【参考文档】{context}

【问题】{question}

请直接回答：""",
    },
}

# ==================== Agent 决策提示词 ====================

AGENT_PROMPTS = {
    "v1": {
        "decision": """基于当前的信息和检索结果，决定下一步应该采取的行动。
可能的行动：
1. RETRIEVE - 检索更多相关文档
2. GENERATE - 生成答案
3. REFINE - 改进答案
4. END - 结束流程

选择最合适的行动并解释原因。""",
        "tool_selection": """基于用户的问题，选择最合适的工具来获取信息。
可用工具：
1. SEARCH - 搜索知识库文档
2. ANALYZE - 分析数据
3. EXTRACT - 抽取关键信息

请选择并说明理由。""",
        "answer_evaluation": """评估当前生成的回答是否充分回答了用户的问题。
评估标准：
1. 完整性：是否覆盖了问题的所有方面
2. 准确性：信息是否准确
3. 清晰性：是否清晰易懂

返回评估结果（充分/部分充分/不充分）。""",
        "relevance_assessment": """评估检索到的文档与用户问题的相关性。
相关性等级：
1. 高度相关 - 直接回答问题
2. 中度相关 - 提供有用信息
3. 低度相关 - 信息有限
4. 不相关 - 无关文档

请给出相关性评级。""",
        "disambiguation": """用户的问题可能存在多种解释。请列出所有可能的解释。
对于每种解释：
1. 描述解释内容
2. 说明需要的澄清
3. 建议的补充问题

请帮助用户明确他们的意图。""",
    },
}

# ==================== 检索优化提示词 ====================

RETRIEVAL_PROMPTS = {
    "v1": {
        "rewrite": """请将用户的问题进行改写，以便更好地进行文档搜索。
改写应该：
1. 保留原意
2. 使用更具体的术语
3. 移除歧义
4. 生成 1-3 个改写版本

返回格式：
- 改写1：...
- 改写2：...
- 改写3：...""",
        "expand": """请为用户的问题生成相关的扩展查询，以获取更全面的信息。
扩展查询应该：
1. 覆盖相关的子主题
2. 包含相关的概念
3. 提供不同的角度
4. 生成 2-5 个扩展查询""",
    },
}

# ==================== 分析提示词 ====================

ANALYSIS_PROMPTS = {
    "v1": {
        "report_analysis": """你是一个专业的数据报告分析师。
你的任务是分析和解释提供的报告数据，提供有洞察力的分析和建议。

分析框架：
1. 数据概览 - 总结主要数据点
2. 趋势分析 - 识别关键趋势
3. 对比分析 - 与历史数据或预期进行对比
4. 结论建议 - 提供可操作的建议

请用清晰的结构化格式呈现你的分析。""",
        "summary": """请对以下内容生成一个简洁的摘要。
摘要应该：
1. 保留关键信息
2. 长度不超过原文的 30%
3. 使用清晰的语言
4. 突出重点和结论""",
        "extraction": """从以下文本中抽取以下信息：
- 主要实体（人名、地名、组织等）
- 关键数字和统计
- 重要日期和时间
- 主要事件或观点

请以结构化的格式返回抽取的信息。""",
    },
}

# ==================== 评估提示词 ====================

EVALUATION_PROMPTS = {
    "v1": {
        "quality_assessment": """请评估以下回答的质量：
评估维度：
1. 准确性：回答是否准确
2. 完整性：是否覆盖了问题的所有方面
3. 相关性：回答是否与问题相关
4. 可读性：回答是否易于理解

请给出 1-5 分的评分。""",
    },
}


class PromptManager:
    """
    提示词管理器 - 单例模式

    统一管理所有提示词，支持版本管理、模板替换、验证等

    Usage:
        manager = PromptManager.get_instance()

        # 获取RAG提示词
        system_prompt = manager.get_prompt(PromptCategory.RAG, "system", version="v1")

        # 动态替换模板
        user_prompt = manager.format_prompt(
            PromptCategory.RAG,
            "user",
            context="...",
            question="..."
        )

        # 列出所有提示词
        all_prompts = manager.list_prompts(PromptCategory.RAG)
    """

    _instance = None
    _prompts = {
        PromptCategory.RAG: RAG_PROMPTS,
        PromptCategory.AGENT: AGENT_PROMPTS,
        PromptCategory.RETRIEVAL: RETRIEVAL_PROMPTS,
        PromptCategory.ANALYSIS: ANALYSIS_PROMPTS,
        PromptCategory.EVALUATION: EVALUATION_PROMPTS,
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            logger.info("PromptManager 单例已初始化")
        return cls._instance

    @staticmethod
    def get_instance() -> 'PromptManager':
        """获取单例实例"""
        if PromptManager._instance is None:
            PromptManager()
        return PromptManager._instance

    def get_prompt(
        self,
        category: PromptCategory,
        prompt_name: str,
        version: str = "v1"
    ) -> Optional[str]:
        """
        获取单个提示词

        Args:
            category: 提示词类别
            prompt_name: 提示词名称
            version: 版本（默认v1）

        Returns:
            提示词内容，如果不存在则返回None
        """
        try:
            if category not in self._prompts:
                logger.warning(f"提示词类别不存在: {category}")
                return None

            category_prompts = self._prompts[category]
            if version not in category_prompts:
                logger.warning(f"提示词版本不存在: {category}/{version}")
                return None

            version_prompts = category_prompts[version]
            if prompt_name not in version_prompts:
                logger.warning(f"提示词不存在: {category}/{version}/{prompt_name}")
                return None

            return version_prompts[prompt_name]
        except Exception as e:
            logger.error(f"获取提示词失败: {str(e)}")
            return None

    def format_prompt(
        self,
        category: PromptCategory,
        prompt_name: str,
        version: str = "v1",
        **kwargs
    ) -> Optional[str]:
        """
        获取并格式化提示词

        使用kwargs中的参数替换提示词中的占位符

        Args:
            category: 提示词类别
            prompt_name: 提示词名称
            version: 版本
            **kwargs: 模板变量

        Returns:
            格式化后的提示词

        Usage:
            prompt = manager.format_prompt(
                PromptCategory.RAG,
                "user",
                context="文档内容",
                question="用户问题"
            )
        """
        try:
            prompt = self.get_prompt(category, prompt_name, version)
            if prompt is None:
                return None

            # 替换模板变量
            for key, value in kwargs.items():
                placeholder = "{" + key + "}"
                prompt = prompt.replace(placeholder, str(value))

            return prompt
        except Exception as e:
            logger.error(f"格式化提示词失败: {str(e)}")
            return None

    def get_rag_system_prompt(self, version: str = "v1") -> Optional[str]:
        """获取RAG系统提示词（快捷方法）"""
        return self.get_prompt(PromptCategory.RAG, "system", version)

    def get_rag_user_prompt(
        self,
        context: str,
        question: str,
        version: str = "v1"
    ) -> Optional[str]:
        """获取并格式化RAG用户提示词（快捷方法）"""
        return self.format_prompt(
            PromptCategory.RAG,
            "user",
            version=version,
            context=context,
            question=question
        )

    def get_agent_prompt(
        self,
        prompt_type: str,
        version: str = "v1"
    ) -> Optional[str]:
        """获取Agent决策提示词（快捷方法）"""
        return self.get_prompt(PromptCategory.AGENT, prompt_type, version)

    def list_prompts(self, category: PromptCategory) -> Dict[str, List[str]]:
        """
        列出某类别的所有提示词

        Args:
            category: 提示词类别

        Returns:
            {版本: [提示词名列表]}

        Usage:
            prompts = manager.list_prompts(PromptCategory.RAG)
            # 返回: {"v1": ["system", "user"], "v2": ["system", "user"], ...}
        """
        try:
            if category not in self._prompts:
                logger.warning(f"提示词类别不存在: {category}")
                return {}

            result = {}
            category_prompts = self._prompts[category]
            for version, prompts in category_prompts.items():
                result[version] = list(prompts.keys())

            return result
        except Exception as e:
            logger.error(f"列出提示词失败: {str(e)}")
            return {}

    def list_categories(self) -> List[str]:
        """列出所有提示词类别"""
        return [cat.value for cat in PromptCategory]

    def validate_prompt(self, prompt: str) -> bool:
        """
        验证提示词格式

        检查提示词是否包含非法字符或格式错误

        Args:
            prompt: 提示词文本

        Returns:
            是否有效
        """
        if not prompt:
            return False

        # 基本验证
        if len(prompt) < 10:  # 提示词至少10个字符
            return False

        if len(prompt) > 10000:  # 提示词不超过10000字符
            return False

        return True

    def get_all_prompts(self) -> Dict[str, Any]:
        """获取所有提示词（用于调试）"""
        return self._prompts

    def register_custom_prompt(
        self,
        category: PromptCategory,
        version: str,
        prompt_name: str,
        prompt_content: str
    ) -> bool:
        """
        注册自定义提示词

        Args:
            category: 提示词类别
            version: 版本
            prompt_name: 提示词名称
            prompt_content: 提示词内容

        Returns:
            是否注册成功
        """
        try:
            if category not in self._prompts:
                self._prompts[category] = {}

            if version not in self._prompts[category]:
                self._prompts[category][version] = {}

            if not self.validate_prompt(prompt_content):
                logger.warning(f"提示词格式无效: {category}/{version}/{prompt_name}")
                return False

            self._prompts[category][version][prompt_name] = prompt_content
            logger.info(f"自定义提示词已注册: {category}/{version}/{prompt_name}")
            return True
        except Exception as e:
            logger.error(f"注册自定义提示词失败: {str(e)}")
            return False

    def export_prompts(self, filepath: str) -> bool:
        """
        导出所有提示词到JSON文件（用于备份和版本管理）

        Args:
            filepath: 导出文件路径

        Returns:
            是否导出成功
        """
        try:
            # 将Enum转换为字符串
            export_data = {}
            for category, versions in self._prompts.items():
                export_data[category.value] = versions

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            logger.info(f"提示词已导出: {filepath}")
            return True
        except Exception as e:
            logger.error(f"导出提示词失败: {str(e)}")
            return False

    def import_prompts(self, filepath: str) -> bool:
        """
        从JSON文件导入提示词

        Args:
            filepath: 导入文件路径

        Returns:
            是否导入成功
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                import_data = json.load(f)

            for category_str, versions in import_data.items():
                try:
                    category = PromptCategory(category_str)
                    self._prompts[category] = versions
                except ValueError:
                    logger.warning(f"未知的提示词类别: {category_str}")

            logger.info(f"提示词已导入: {filepath}")
            return True
        except Exception as e:
            logger.error(f"导入提示词失败: {str(e)}")
            return False
