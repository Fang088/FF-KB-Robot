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
        on_chunk: Optional[callable] = None,
        images: Optional[List[Dict[str, Any]]] = None,  # 【新增】支持图片数据
    ):
        """
        流式生成文本 - 支持回调和性能追踪 + 多模态vision

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数（可选，覆盖默认值）
            max_tokens: 最大 token 数（可选，覆盖默认值）
            on_chunk: 回调函数，接收每个文本片段
            images: 【新增】图片数据列表 [{"format": "PNG", "base64": "..."}, ...]

        Yields:
            生成的文本片段
        """
        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # 【新增】构建支持vision的消息格式
        if images and len(images) > 0:
            # 多模态消息：文本 + 图片
            content_parts = [{"type": "text", "text": prompt}]

            for img_data in images:
                # 构建image_url格式
                img_format = img_data.get("format", "PNG").lower()
                base64_str = img_data.get("base64", "")

                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/{img_format};base64,{base64_str}"
                    }
                })

            messages.append({"role": "user", "content": content_parts})
        else:
            # 纯文本消息
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
                # 安全检查: choices 列表可能为空
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    if on_chunk:
                        on_chunk(content)
                    yield content
        except Exception as e:
            logger.error(f"LLM 流式生成文本失败: {e}")
            raise

    async def generate_text_stream_async(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        on_chunk: Optional[callable] = None,
    ):
        """
        异步流式生成文本

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大 token 数
            on_chunk: 回调函数

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
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                # 安全检查: choices 列表可能为空
                if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    if on_chunk:
                        on_chunk(content)
                    yield content
        except Exception as e:
            logger.error(f"LLM 异步流式生成文本失败: {e}")
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
