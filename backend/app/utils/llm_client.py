"""
LLM客户端封装
统一使用OpenAI格式调用
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from ..config import Config


class LLMClient:
    """LLM客户端"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME

        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> str:
        """
        发送聊天请求

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）

        Returns:
            模型响应文本
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
        content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
        return content

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        发送聊天请求并返回JSON

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数

        Returns:
            解析后的JSON对象
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # 清理markdown代码块标记
        cleaned_response = response.strip()
        # 移除思考标签 (MiniMax等模型)
        cleaned_response = re.sub(
            r"<think>[\s\S]*?</think>", "", cleaned_response, flags=re.IGNORECASE
        )
        cleaned_response = re.sub(
            r"^```(?:json)?\s*\n?", "", cleaned_response, flags=re.IGNORECASE
        )
        cleaned_response = re.sub(r"\n?```\s*$", "", cleaned_response)
        cleaned_response = cleaned_response.strip()

        # 如果响应为空
        if not cleaned_response:
            raise ValueError("LLM返回了空响应")

        # 尝试解析JSON，如果失败则尝试修复
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            # 尝试修复常见的LLM JSON错误
            repaired = self._repair_json(cleaned_response)
            try:
                return json.loads(repaired)
            except json.JSONDecodeError:
                # 修复失败，返回原始错误
                raise ValueError(f"LLM返回的JSON格式无效: {cleaned_response}")

    def _repair_json(self, text: str) -> str:
        """
        尝试修复常见的LLM JSON错误

        修复的问题：
        1. 重复的attributes数组（先字符串数组，后对象数组）
        2. 多余的逗号
        3. 缺少的引号
        4. 尾随的逗号
        """

        # 修复1: 处理attributes字段的重复数组问题
        # 模式: "attributes": ["a", "b"],\n[\n {...}, {...}\n]
        # 应该变成: "attributes": [\n {...}, {...}\n]
        def fix_duplicate_attributes(match):
            # 保留第二个数组（对象数组），丢弃第一个（字符串数组）
            return '"attributes":' + match.group(2)

        # 匹配 "attributes": [...],\n[...] 模式（两个连续的数组）
        pattern = r'"attributes"\s*:\s*(\[[^\]]*\])\s*,?\s*(\[[\s\S]*?\])'
        text = re.sub(pattern, fix_duplicate_attributes, text)

        # 修复2: 移除对象/数组中最后一个元素后的多余逗号
        text = re.sub(r",(\s*[}\]])", r"\1", text)

        # 修复3: 修复单引号（替换为双引号）
        text = re.sub(r"'([^']*)'(?=\s*:)", r'"\1"', text)  # 键名
        text = re.sub(r":\s*'([^']*)'", r': "\1"', text)  # 字符串值

        # 修复4: 修复缺失的逗号（在新行开始的键前添加逗号）
        text = re.sub(r'(\S)\s*\n\s*"', r'\1,\n"', text)

        return text
