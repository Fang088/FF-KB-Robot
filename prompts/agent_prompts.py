"""
Agent 决策提示词 - 用于 Agent 在不同步骤的决策
"""

# Agent 决策提示词
AGENT_DECISION_PROMPT = """基于当前的信息和检索结果，决定下一步应该采取的行动。
可能的行动：
1. RETRIEVE - 检索更多相关文档
2. GENERATE - 生成答案
3. REFINE - 改进答案
4. END - 结束流程

选择最合适的行动并解释原因。"""

# 工具选择提示词
TOOL_SELECTION_PROMPT = """基于用户的问题，选择最合适的工具来获取信息。
可用工具：
1. SEARCH - 外部搜索工具
2. CALCULATOR - 计算工具
3. DATE_HELPER - 日期工具
4. KB_SEARCH - 知识库搜索

请说明选择理由。"""

# 回答评估提示词
ANSWER_EVALUATION_PROMPT = """评估当前生成的回答是否充分回答了用户的问题。
评估标准：
1. 是否直接回答了问题
2. 是否有足够的细节
3. 是否有误导信息
4. 是否需要进一步搜索

返回评估结果：SUFFICIENT（充分）或 INSUFFICIENT（不充分）"""

# 信息相关性评估提示词
RELEVANCE_ASSESSMENT_PROMPT = """评估检索到的文档与用户问题的相关性。
相关性等级：
1. HIGHLY_RELEVANT - 高度相关
2. RELEVANT - 相关
3. PARTIALLY_RELEVANT - 部分相关
4. IRRELEVANT - 不相关

为每个文档分配相关性等级。"""

# 歧义消除提示词
DISAMBIGUATION_PROMPT = """用户的问题可能存在多种解释。
请列出所有可能的解释，并选择最可能的一个。
如果无法确定，请要求用户澄清。"""

# Agent 所有提示词字典
AGENT_PROMPTS = {
    "decision": AGENT_DECISION_PROMPT,
    "tool_selection": TOOL_SELECTION_PROMPT,
    "answer_evaluation": ANSWER_EVALUATION_PROMPT,
    "relevance_assessment": RELEVANCE_ASSESSMENT_PROMPT,
    "disambiguation": DISAMBIGUATION_PROMPT,
}


def get_agent_prompt(prompt_type: str) -> str:
    """
    获取 Agent 提示词

    Args:
        prompt_type: 提示词类型

    Returns:
        Agent 提示词
    """
    return AGENT_PROMPTS.get(prompt_type, "")
