# coding=utf-8
"""
AI 客户端模块

基于 LiteLLM 的统一 AI 模型接口
支持 100+ AI 提供商（OpenAI、DeepSeek、Gemini、Claude、国内模型等）
"""

import os
from typing import Any, Dict, List

import requests
from litellm import completion


class AIClient:
    """统一的 AI 客户端（基于 LiteLLM）"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 AI 客户端

        Args:
            config: AI 配置字典
                - MODEL: 模型标识（格式: provider/model_name）
                - API_KEY: API 密钥
                - API_BASE: API 基础 URL（可选）
                - TEMPERATURE: 采样温度
                - MAX_TOKENS: 最大生成 token 数
                - TIMEOUT: 请求超时时间（秒）
                - NUM_RETRIES: 重试次数（可选）
                - FALLBACK_MODELS: 备用模型列表（可选）
        """
        self.model = config.get("MODEL", "deepseek/deepseek-chat")
        self.api_key = config.get("API_KEY") or os.environ.get("AI_API_KEY", "")
        self.api_base = config.get("API_BASE", "")
        self.api_mode = (config.get("API_MODE") or os.environ.get("AI_API_MODE", "chat_completions")).strip().lower()
        self.temperature = config.get("TEMPERATURE", 1.0)
        self.max_tokens = config.get("MAX_TOKENS", 5000)
        self.timeout = config.get("TIMEOUT", 120)
        self.num_retries = config.get("NUM_RETRIES", 2)
        self.fallback_models = config.get("FALLBACK_MODELS", [])

    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        调用 AI 模型进行对话

        Args:
            messages: 消息列表，格式: [{"role": "system/user/assistant", "content": "..."}]
            **kwargs: 额外参数，会覆盖默认配置

        Returns:
            str: AI 响应内容

        Raises:
            Exception: API 调用失败时抛出异常
        """
        if self.api_mode == "responses":
            return self._chat_via_responses(messages, **kwargs)

        # 构建请求参数
        params = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "timeout": kwargs.get("timeout", self.timeout),
            "num_retries": kwargs.get("num_retries", self.num_retries),
        }

        # 添加 API Key
        if self.api_key:
            params["api_key"] = self.api_key

        # 添加 API Base（如果配置了）
        if self.api_base:
            params["api_base"] = self.api_base

        # 添加 max_tokens（如果配置了且不为 0）
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        if max_tokens and max_tokens > 0:
            params["max_tokens"] = max_tokens

        # 添加 fallback 模型（如果配置了）
        if self.fallback_models:
            params["fallbacks"] = self.fallback_models

        # 合并其他额外参数
        for key, value in kwargs.items():
            if key not in params:
                params[key] = value

        # 调用 LiteLLM
        response = completion(**params)

        # 提取响应内容
        # 某些模型/提供商返回 list（内容块）而非 str，统一转为 str
        content = response.choices[0].message.content
        if isinstance(content, list):
            content = "\n".join(
                item.get("text", str(item)) if isinstance(item, dict) else str(item)
                for item in content
            )
        return content or ""

    @staticmethod
    def _resolve_model_name(model: str) -> str:
        if "/" in model:
            return model.split("/", 1)[1]
        return model

    @staticmethod
    def _to_responses_input(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        converted: List[Dict[str, Any]] = []
        for message in messages:
            role = str(message.get("role", "user"))
            content = message.get("content", "")
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        item_type = item.get("type")
                        if item_type in {"input_text", "input_image", "input_audio"}:
                            parts.append(item)
                        elif item_type == "image_url":
                            image_url = item.get("image_url")
                            url = image_url.get("url", "") if isinstance(image_url, dict) else str(image_url or "")
                            if url:
                                parts.append({"type": "input_image", "image_url": url})
                        elif item_type == "text":
                            parts.append({"type": "input_text", "text": str(item.get("text", ""))})
                        else:
                            parts.append({"type": "input_text", "text": str(item)})
                    else:
                        parts.append({"type": "input_text", "text": str(item)})
            else:
                parts = [{"type": "input_text", "text": str(content)}]
            converted.append({"role": role, "content": parts})
        return converted

    @staticmethod
    def _extract_responses_text(payload: Dict[str, Any]) -> str:
        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        chunks: List[str] = []
        for output_item in payload.get("output", []) or []:
            for content_item in output_item.get("content", []) or []:
                text = content_item.get("text") or content_item.get("output_text")
                if text:
                    chunks.append(str(text))
        return "\n".join(chunks).strip()

    def _chat_via_responses(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        if not self.api_base:
            raise ValueError("responses 模式需要配置 API_BASE")
        if not self.api_key:
            raise ValueError("responses 模式需要配置 API_KEY")

        url = self.api_base.rstrip("/") + "/responses"
        payload: Dict[str, Any] = {
            "model": self._resolve_model_name(self.model),
            "input": self._to_responses_input(messages),
            "temperature": kwargs.get("temperature", self.temperature),
        }

        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        if max_tokens and max_tokens > 0:
            payload["max_output_tokens"] = max_tokens

        response = requests.post(
            url=url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=kwargs.get("timeout", self.timeout),
        )
        response.raise_for_status()
        data = response.json()
        content = self._extract_responses_text(data)
        return content or ""

    def validate_config(self) -> tuple[bool, str]:
        """
        验证配置是否有效

        Returns:
            tuple: (是否有效, 错误信息)
        """
        if not self.model:
            return False, "未配置 AI 模型（model）"

        if not self.api_key:
            return False, "未配置 AI API Key，请在 config.yaml 或环境变量 AI_API_KEY 中设置"

        # 验证模型格式（应该包含 provider/model）
        if "/" not in self.model:
            return False, f"模型格式错误: {self.model}，应为 'provider/model' 格式（如 'deepseek/deepseek-chat'）"

        return True, ""
