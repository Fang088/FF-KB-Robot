"""
模型客户端工厂 - 统一管理OpenAI/Azure客户端的初始化

功能：
1. 统一的OpenAI和Azure客户端初始化逻辑
2. 单例模式确保全局只有一个实例
3. 支持动态切换提供商
4. 统一的API版本管理
"""

from typing import Any, Optional, Union
from openai import OpenAI, AzureOpenAI
import logging

logger = logging.getLogger(__name__)


class ClientFactoryError(Exception):
    """客户端工厂异常"""
    pass


class ClientFactory:
    """
    客户端工厂 - 统一创建和管理LLM/Embedding客户端

    支持OpenAI和Azure两种提供商，提供统一的初始化接口

    Usage:
        # 创建OpenAI客户端
        client = ClientFactory.create_client(
            provider="openai",
            api_key="sk-xxx",
            api_base="https://api.openai.com/v1"
        )

        # 创建Azure客户端
        client = ClientFactory.create_client(
            provider="azure",
            api_key="xxx",
            api_base="https://xxx.openai.azure.com"
        )
    """

    # API版本常量
    AZURE_CHAT_API_VERSION = "2024-08-01-preview"
    AZURE_EMBEDDING_API_VERSION = "2024-02-15-preview"

    @staticmethod
    def validate_config(
        provider: str,
        api_key: str,
        api_base: Optional[str]
    ) -> None:
        """
        验证配置参数

        Args:
            provider: 提供商名称
            api_key: API密钥
            api_base: API基础URL

        Raises:
            ClientFactoryError: 配置无效
        """
        if provider not in ["openai", "azure"]:
            raise ClientFactoryError(f"不支持的提供商: {provider}")

        if not api_key:
            raise ClientFactoryError(f"{provider} API密钥不能为空")

        if provider == "azure" and not api_base:
            raise ClientFactoryError("Azure 需要提供 api_base (endpoint)")

    @staticmethod
    def create_client(
        provider: str,
        api_key: str,
        api_base: Optional[str] = None,
        client_type: str = "chat"
    ) -> Union[OpenAI, AzureOpenAI]:
        """
        创建客户端

        Args:
            provider: 提供商（"openai" 或 "azure"）
            api_key: API密钥
            api_base: API基础URL（Azure必需）
            client_type: 客户端类型（"chat" 或 "embedding"）

        Returns:
            OpenAI或AzureOpenAI客户端实例

        Raises:
            ClientFactoryError: 创建失败
        """
        # 验证配置
        ClientFactory.validate_config(provider, api_key, api_base)

        try:
            if provider == "openai":
                return ClientFactory._create_openai_client(api_key, api_base)
            elif provider == "azure":
                return ClientFactory._create_azure_client(
                    api_key, api_base, client_type
                )
        except Exception as e:
            raise ClientFactoryError(f"创建{provider}客户端失败: {str(e)}")

    @staticmethod
    def _create_openai_client(api_key: str, api_base: Optional[str]) -> OpenAI:
        """
        创建OpenAI客户端

        Args:
            api_key: OpenAI API密钥
            api_base: API基础URL（可选，用于兼容第三方服务）

        Returns:
            OpenAI客户端实例
        """
        return OpenAI(
            api_key=api_key,
            base_url=api_base if api_base else None
        )

    @staticmethod
    def _create_azure_client(
        api_key: str,
        api_base: str,
        client_type: str = "chat"
    ) -> AzureOpenAI:
        """
        创建Azure OpenAI客户端

        Args:
            api_key: Azure API密钥
            api_base: Azure端点URL
            client_type: 客户端类型（用于选择对应的API版本）

        Returns:
            AzureOpenAI客户端实例
        """
        api_version = (
            ClientFactory.AZURE_CHAT_API_VERSION if client_type == "chat"
            else ClientFactory.AZURE_EMBEDDING_API_VERSION
        )

        return AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=api_base
        )

    @staticmethod
    def get_api_version(provider: str, client_type: str = "chat") -> str:
        """
        获取API版本

        Args:
            provider: 提供商名称
            client_type: 客户端类型

        Returns:
            API版本字符串
        """
        if provider == "openai":
            return ""  # OpenAI不需要指定版本

        if client_type == "chat":
            return ClientFactory.AZURE_CHAT_API_VERSION
        else:
            return ClientFactory.AZURE_EMBEDDING_API_VERSION


# ==================== 单例客户端管理器 ====================

class ClientManager:
    """
    客户端管理器 - 使用单例模式管理全局的LLM/Embedding客户端

    Usage:
        manager = ClientManager.get_instance()
        llm_client = manager.get_llm_client()
        embedding_client = manager.get_embedding_client()
    """

    _instance = None
    _clients = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @staticmethod
    def get_instance() -> 'ClientManager':
        """获取单例实例"""
        if ClientManager._instance is None:
            ClientManager()
        return ClientManager._instance

    def get_llm_client(
        self,
        provider: str,
        api_key: str,
        api_base: Optional[str] = None
    ) -> Union[OpenAI, AzureOpenAI]:
        """
        获取或创建LLM客户端

        Args:
            provider: 提供商
            api_key: API密钥
            api_base: API基础URL

        Returns:
            LLM客户端实例
        """
        cache_key = f"llm_{provider}_{api_key}"

        if cache_key not in ClientManager._clients:
            ClientManager._clients[cache_key] = ClientFactory.create_client(
                provider=provider,
                api_key=api_key,
                api_base=api_base,
                client_type="chat"
            )
            logger.debug(f"创建新的LLM客户端: {cache_key}")

        return ClientManager._clients[cache_key]

    def get_embedding_client(
        self,
        provider: str,
        api_key: str,
        api_base: Optional[str] = None
    ) -> Union[OpenAI, AzureOpenAI]:
        """
        获取或创建Embedding客户端

        Args:
            provider: 提供商
            api_key: API密钥
            api_base: API基础URL

        Returns:
            Embedding客户端实例
        """
        cache_key = f"embedding_{provider}_{api_key}"

        if cache_key not in ClientManager._clients:
            ClientManager._clients[cache_key] = ClientFactory.create_client(
                provider=provider,
                api_key=api_key,
                api_base=api_base,
                client_type="embedding"
            )
            logger.debug(f"创建新的Embedding客户端: {cache_key}")

        return ClientManager._clients[cache_key]

    def clear_cache(self):
        """清空所有缓存的客户端"""
        ClientManager._clients.clear()
        logger.debug("客户端缓存已清空")

    def list_cached_clients(self):
        """列出所有缓存的客户端"""
        return list(ClientManager._clients.keys())
