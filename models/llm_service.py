"""
LLM 服务封装 - 支持 OpenAI, Azure 等多种 LLM 供应商
"""

from typing import Optional, Any, List, Dict
from openai import OpenAI, AzureOpenAI
import logging
from config.settings import settings

logger = logging.getLogger(__name__)


class LLMService:
    """
    LLM 服务类
    封装对 LLM 的调用，支持 OpenAI, Azure 等多种供应商
    """

    def __init__(
        self,
        provider: str = None,
        api_key: str = None,
        api_base: Optional[str] = None,
        model_name: str = None,
        temperature: float = None,
        max_tokens: int = None,
    ):
        """
        初始化 LLM 服务

        Args:
            provider: 模型供应商（openai, azure, local）
            api_key: API 密钥
            api_base: API 基础 URL（用于 Azure 或自定义服务）
            model_name: 模型名称
            temperature: 温度参数，控制随机性
            max_tokens: 最大 token 数
        """
        self.provider = provider or settings.LLM_PROVIDER
        self.api_key = api_key or settings.LLM_API_KEY
        self.api_base = api_base or settings.LLM_API_BASE
        self.model_name = model_name or settings.LLM_MODEL_NAME
        self.temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        self.max_tokens = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS

        self.client = self._initialize_client()
        logger.info(f"LLM 服务已初始化: provider={self.provider}, model={self.model_name}")

    def _initialize_client(self) -> Any:
        """初始化 LLM 客户端"""
        if self.provider == "openai":
            return OpenAI(
                api_key=self.api_key,
                base_url=self.api_base if self.api_base else None,
            )
        elif self.provider == "azure":
            return AzureOpenAI(
                api_key=self.api_key,
                api_version="2024-08-01-preview",  # 最新 API 版本
                azure_endpoint=self.api_base,
            )
        else:
            raise ValueError(f"不支持的 LLM 供应商: {self.provider}")

    def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        生成文本

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数（可选，覆盖默认值）
            max_tokens: 最大 token 数（可选，覆盖默认值）

        Returns:
            生成的文本
        """
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM 生成文本失败: {e}")
            raise

    def generate_text_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """
        流式生成文本

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数（可选，覆盖默认值）
            max_tokens: 最大 token 数（可选，覆盖默认值）

        Yields:
            生成的文本片段
        """
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM 流式生成文本失败: {e}")
            raise

    def count_tokens(self, text: str) -> int:
        """
        计算文本的 token 数

        Args:
            text: 输入文本

        Returns:
            token 数
        """
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self.model_name)
            return len(encoding.encode(text))
        except Exception as e:
            logger.warning(f"无法准确计算 token，使用近似值: {e}")
            # 粗略估计：1 token ≈ 4 个字符
            return len(text) // 4

    def set_temperature(self, temperature: float):
        """设置温度参数"""
        self.temperature = temperature

    def set_max_tokens(self, max_tokens: int):
        """设置最大 token 数"""
        self.max_tokens = max_tokens
