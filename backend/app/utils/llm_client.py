"""
LLM client package
Unified use of OpenAI format calls
"""

import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI, APIStatusError, RateLimitError

from ..config import Config


OPENROUTER_FALLBACK_MODELS = [
    "google/gemma-3-12b-it:free",
    "google/gemma-3-4b-it:free",
    "openai/gpt-oss-20b:free",
]


class LLMClient:
    """LLM client"""

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
            raise ValueError("LLM_API_KEY not configured")

        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def _model_candidates(self) -> List[str]:
        candidates = [self.model]
        if self.base_url and "openrouter.ai" in self.base_url:
            candidates.extend(OPENROUTER_FALLBACK_MODELS)

        unique = []
        for model in candidates:
            if model and model not in unique:
                unique.append(model)
        return unique

    @staticmethod
    def _should_fallback(exc: Exception) -> bool:
        if isinstance(exc, RateLimitError):
            return True
        if isinstance(exc, APIStatusError):
            return exc.status_code in {402, 429}

        message = str(exc).lower()
        return "insufficient credits" in message or "rate-limited upstream" in message

    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None,
    ) -> str:
        """
        Send chat request

        Args:
        messages: message list
        temperature: temperature parameter
        max_tokens: maximum number of tokens
        response_format: response format (such as JSON mode)

        Returns:
        Model response text
        """
        last_error = None

        for model in self._model_candidates():
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if response_format:
                kwargs["response_format"] = response_format

            try:
                response = self.client.chat.completions.create(**kwargs)
                message = response.choices[0].message
                content = message.content or getattr(message, "reasoning", None) or ""
                content = re.sub(r"<think>[\s\S]*?</think>", "", content).strip()
                if content:
                    self.model = model
                    return content
                last_error = ValueError(f"LLM returned empty content for model {model}")
            except Exception as exc:
                last_error = exc
                if not self._should_fallback(exc):
                    raise

        if last_error is not None:
            raise last_error
        raise RuntimeError("No LLM response was generated")

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """
        Send chat request and return JSON

        Args:
        messages: message list
        temperature: temperature parameter
        max_tokens: maximum number of tokens

        Returns:
        Parsed JSON object
        """
        response = self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        # Clean up markdown code block tags
        cleaned_response = response.strip()
        cleaned_response = re.sub(
            r"^```(?:json)?\s*\n?", "", cleaned_response, flags=re.IGNORECASE
        )
        cleaned_response = re.sub(r"\n?```\s*$", "", cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(
                f"The JSON format returned by LLM is invalid: {cleaned_response}"
            )
