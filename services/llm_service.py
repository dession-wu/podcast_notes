"""LLM 服务封装 — 支持多种大语言模型提供商.

支持的提供商：
- OpenAI (GPT-4o, GPT-4o-mini)
- Anthropic (Claude 3.5 Sonnet)
- Ollama (本地模型，如 Qwen2.5, DeepSeek)
"""

from __future__ import annotations

from typing import Any

import requests

from config import settings
from config.settings import LLMProvider
from utils import get_logger, with_retry

logger = get_logger(__name__)


class LLMServiceError(Exception):
    """LLM 服务相关错误."""

    pass


class LLMService:
    """大语言模型服务封装.

    统一封装多种 LLM 提供商的调用接口，支持自动切换和降级。
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        """初始化 LLM 服务.

        Args:
            provider: LLM 提供商，默认使用配置中的设置
        """
        self.provider = provider or settings.default_llm_provider

        # 验证配置
        self._validate_config()

        logger.info("LLM 服务初始化完成", provider=self.provider.value)

    def _validate_config(self) -> None:
        """验证当前提供商的配置是否完整."""
        match self.provider:
            case LLMProvider.OPENAI:
                if not settings.is_openai_configured:
                    raise LLMServiceError(
                        "OpenAI API 密钥未配置，请在 .env 中设置 OPENAI_API_KEY"
                    )
            case LLMProvider.ANTHROPIC:
                if not settings.is_anthropic_configured:
                    raise LLMServiceError(
                        "Anthropic API 密钥未配置，请在 .env 中设置 ANTHROPIC_API_KEY"
                    )
            case LLMProvider.OLLAMA:
                # 检查 Ollama 服务是否可达
                try:
                    response = requests.get(
                        f"{settings.ollama_host}/api/tags",
                        timeout=5,
                    )
                    if response.status_code != 200:
                        raise LLMServiceError(
                            f"Ollama 服务不可达: {settings.ollama_host}"
                        )
                except requests.RequestException as e:
                    raise LLMServiceError(
                        f"Ollama 服务连接失败: {e}\n"
                        "请确保 Ollama 已安装并运行: https://ollama.com"
                    ) from e

    @with_retry(max_attempts=3)
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """生成文本.

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词
            temperature: 温度参数（创造性 vs 确定性）
            max_tokens: 最大生成 token 数

        Returns:
            生成的文本

        Raises:
            LLMServiceError: 生成失败
        """
        match self.provider:
            case LLMProvider.OPENAI:
                return self._generate_openai(prompt, system_prompt, temperature, max_tokens)
            case LLMProvider.ANTHROPIC:
                return self._generate_anthropic(prompt, system_prompt, temperature, max_tokens)
            case LLMProvider.OLLAMA:
                return self._generate_ollama(prompt, system_prompt, temperature, max_tokens)
            case _:
                raise LLMServiceError(f"不支持的 LLM 提供商: {self.provider}")

    def _generate_openai(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        """使用 OpenAI API 生成文本."""
        try:
            from openai import OpenAI
        except ImportError:
            raise LLMServiceError("未安装 openai，请运行: pip install openai")

        client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )

        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        params: dict[str, Any] = {
            "model": settings.openai_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens:
            params["max_tokens"] = max_tokens

        try:
            response = client.chat.completions.create(**params)
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMServiceError(f"OpenAI API 调用失败: {e}") from e

    def _generate_anthropic(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        """使用 Anthropic Claude API 生成文本."""
        try:
            from anthropic import Anthropic
        except ImportError:
            raise LLMServiceError("未安装 anthropic，请运行: pip install anthropic")

        client = Anthropic(api_key=settings.anthropic_api_key)

        params: dict[str, Any] = {
            "model": settings.anthropic_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens or 4096,
        }
        if system_prompt:
            params["system"] = system_prompt

        try:
            response = client.messages.create(**params)
            return response.content[0].text if response.content else ""
        except Exception as e:
            raise LLMServiceError(f"Anthropic API 调用失败: {e}") from e

    def _generate_ollama(
        self,
        prompt: str,
        system_prompt: str | None,
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        """使用 Ollama 本地服务生成文本."""
        url = f"{settings.ollama_host}/api/generate"

        payload: dict[str, Any] = {
            "model": settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if system_prompt:
            payload["system"] = system_prompt
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.RequestException as e:
            raise LLMServiceError(f"Ollama 调用失败: {e}") from e

    def generate_with_template(
        self,
        template_name: str,
        variables: dict[str, Any],
        **kwargs,
    ) -> str:
        """使用 Jinja2 模板生成文本.

        Args:
            template_name: 模板文件名（相对于 prompts/ 目录）
            variables: 模板变量字典
            **kwargs: 其他生成参数

        Returns:
            生成的文本
        """
        from jinja2 import Environment, FileSystemLoader

        # 加载模板
        env = Environment(loader=FileSystemLoader("prompts"))
        template = env.get_template(f"{template_name}.md")

        # 渲染模板
        prompt = template.render(**variables)

        # 调用生成
        return self.generate(prompt, **kwargs)
