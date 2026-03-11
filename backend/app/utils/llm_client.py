"""
LLM客户端封装
统一使用OpenAI格式调用
支持重试机制和友好错误提示
"""

import json
import re
import time
from typing import Optional, Dict, Any, List
from openai import OpenAI, APIError, APIConnectionError, RateLimitError, AuthenticationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError

from ..config import Config
from .logger import get_logger

logger = get_logger('mirofish.llm_client')


class LLMClient:
    """LLM客户端"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model = model or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未配置")
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    @retry(
        stop=stop_after_attempt(Config.LLM_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIConnectionError, RateLimitError, APIError)),
        reraise=True
    )
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
        response_format: Optional[Dict] = None
    ) -> str:
        """
        发送聊天请求（支持自动重试）
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            response_format: 响应格式（如JSON模式）
            
        Returns:
            模型响应文本
            
        Raises:
            ConnectionError: 网络连接失败，多次重试后仍不可用
            RateLimitError: API调用频率超限
            AuthenticationError: API密钥无效
            ValueError: 模型返回格式错误
            Exception: 其他未知错误
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        if response_format:
            kwargs["response_format"] = response_format
        
        try:
            response = self.client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            # 部分模型（如MiniMax M2.5）会在content中包含<think>思考内容，需要移除
            content = re.sub(r'<think>[\s\S]*?</think>', '', content).strip()
            
            if not content:
                logger.warning("LLM返回空响应，可能是模型输出被截断或过滤")
                raise APIError("模型返回空响应，请调整提示词或减少输入长度")
                
            return content
            
        except AuthenticationError as e:
            logger.error(f"LLM API认证失败: {str(e)}")
            raise ValueError("LLM API密钥无效，请检查配置") from e
            
        except RateLimitError as e:
            logger.warning(f"LLM API调用频率超限: {str(e)}，将自动重试")
            raise  # 交给tenacity重试
            
        except APIConnectionError as e:
            logger.warning(f"LLM API连接失败: {str(e)}，将自动重试")
            raise  # 交给tenacity重试
            
        except APIError as e:
            if "500" in str(e) or "502" in str(e) or "503" in str(e) or "504" in str(e):
                logger.warning(f"LLM API服务端错误: {str(e)}，将自动重试")
                raise  # 服务端错误可以重试
            logger.error(f"LLM API调用失败: {str(e)}")
            raise ValueError(f"LLM调用失败: {str(e)}") from e
            
        except Exception as e:
            logger.error(f"LLM调用未知错误: {str(e)}")
            raise
    
    def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 4096
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
            response_format={"type": "json_object"}
        )
        # 清理markdown代码块标记
        cleaned_response = response.strip()
        cleaned_response = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_response, flags=re.IGNORECASE)
        cleaned_response = re.sub(r'\n?```\s*$', '', cleaned_response)
        cleaned_response = cleaned_response.strip()

        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            raise ValueError(f"LLM返回的JSON格式无效: {cleaned_response}")

