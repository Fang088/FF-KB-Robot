"""
自定义工具 - 用户定义的自定义工具
"""

from typing import Any, Dict, Callable, Optional
import logging

logger = logging.getLogger(__name__)


class CustomTool:
    """
    自定义工具基类
    用户可以继承此类创建自定义工具
    """

    def __init__(
        self,
        name: str,
        description: str,
        func: Callable,
    ):
        """
        初始化自定义工具

        Args:
            name: 工具名称
            description: 工具描述
            func: 工具函数
        """
        self.name = name
        self.description = description
        self.func = func
        logger.info(f"自定义工具已初始化: {name}")

    def execute(self, **kwargs) -> Any:
        """
        执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            执行结果
        """
        try:
            logger.info(f"执行工具: {self.name}, 参数: {kwargs}")
            result = self.func(**kwargs)
            logger.info(f"工具执行完成: {self.name}")
            return result
        except Exception as e:
            logger.error(f"工具执行失败: {e}")
            raise

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "type": "custom_tool",
        }


# 示例工具：计算工具
def calculator(expression: str) -> float:
    """
    简单的计算器工具

    Args:
        expression: 数学表达式

    Returns:
        计算结果
    """
    try:
        result = eval(expression)
        logger.info(f"计算结果: {expression} = {result}")
        return result
    except Exception as e:
        logger.error(f"计算失败: {e}")
        raise


# 创建预定义的工具实例
CALCULATOR_TOOL = CustomTool(
    name="calculator",
    description="一个简单的计算器，可以计算数学表达式",
    func=calculator,
)


# 所有可用工具的注册表
AVAILABLE_TOOLS = {
    "calculator": CALCULATOR_TOOL,
}


def register_tool(
    name: str,
    description: str,
    func: Callable,
):
    """
    注册新工具

    Args:
        name: 工具名称
        description: 工具描述
        func: 工具函数
    """
    tool = CustomTool(name, description, func)
    AVAILABLE_TOOLS[name] = tool
    logger.info(f"工具已注册: {name}")


def get_tool(name: str) -> Optional[CustomTool]:
    """
    获取工具

    Args:
        name: 工具名称

    Returns:
        工具实例
    """
    return AVAILABLE_TOOLS.get(name)


def get_all_tools() -> Dict[str, CustomTool]:
    """
    获取所有工具

    Returns:
        所有工具的字典
    """
    return AVAILABLE_TOOLS.copy()
