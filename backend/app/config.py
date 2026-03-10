"""
配置管理（增强验证版）
Enhanced Configuration Management with Comprehensive Validation

此模块扩展了原有的 config.py，添加：
1. 全面的启动时配置验证
2. 配置值类型和范围检查
3. URL 格式验证
4. 目录权限检查
5. 向后兼容的接口

用法:
    # 向后兼容方式（原有代码无需修改）
    errors = Config.validate()
    
    # 新增：全面验证
    result = Config.validate_comprehensive()
    if not result.is_valid:
        print(result.errors)
"""

import os
import re
import socket
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass, field

# 加载项目根目录的 .env 文件
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    load_dotenv(override=True)


@dataclass
class ConfigValidationResult:
    """
    配置验证结果
    
    用于收集和报告配置验证过程中的所有问题
    """
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """配置是否有效（无错误）"""
        return len(self.errors) == 0
    
    def add_error(self, message: str) -> None:
        """添加错误（阻止启动）"""
        self.errors.append(message)
    
    def add_warning(self, message: str) -> None:
        """添加警告（可以启动，但功能可能受限）"""
        self.warnings.append(message)
    
    def add_info(self, message: str) -> None:
        """添加信息"""
        self.info.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


class Config:
    """
    Flask 配置类（增强验证版）
    
    保持与原有 config.py 完全兼容，同时添加全面验证功能
    """
    
    # ============================================================
    # Flask 基础配置
    # ============================================================
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    JSON_AS_ASCII = False
    
    # ============================================================
    # LLM 配置
    # ============================================================
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    
    # LLM 加速配置（可选）
    LLM_BOOST_API_KEY = os.environ.get('LLM_BOOST_API_KEY')
    LLM_BOOST_BASE_URL = os.environ.get('LLM_BOOST_BASE_URL')
    LLM_BOOST_MODEL_NAME = os.environ.get('LLM_BOOST_MODEL_NAME')
    
    # ============================================================
    # Zep 配置
    # ============================================================
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
    # ============================================================
    # 文件上传配置
    # ============================================================
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # ============================================================
    # 文本处理配置
    # ============================================================
    DEFAULT_CHUNK_SIZE = 500
    DEFAULT_CHUNK_OVERLAP = 50
    
    # ============================================================
    # OASIS 模拟配置
    # ============================================================
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # ============================================================
    # Report Agent 配置
    # ============================================================
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))
    
    # ============================================================
    # 原有验证方法（向后兼容）
    # ============================================================
    
    @classmethod
    def validate(cls) -> List[str]:
        """
        验证必要配置（向后兼容）
        
        Returns:
            错误消息列表（空列表表示配置有效）
        """
        result = cls.validate_comprehensive()
        return result.errors
    
    # ============================================================
    # 新增：全面验证方法
    # ============================================================
    
    @classmethod
    def validate_comprehensive(cls) -> ConfigValidationResult:
        """
        全面配置验证
        
        检查项:
        1. 必需的 API Keys
        2. URL 格式
        3. 数值范围
        4. 目录权限
        5. 配置一致性
        
        Returns:
            ConfigValidationResult 包含所有验证结果
        """
        result = ConfigValidationResult()
        
        # 1. 验证 API Keys
        cls._validate_api_keys(result)
        
        # 2. 验证 URL 格式
        cls._validate_urls(result)
        
        # 3. 验证数值范围
        cls._validate_numeric_ranges(result)
        
        # 4. 验证目录权限
        cls._validate_directories(result)
        
        # 5. 验证配置一致性
        cls._validate_consistency(result)
        
        return result
    
    @classmethod
    def _validate_api_keys(cls, result: ConfigValidationResult) -> None:
        """验证 API Keys"""
        
        # LLM API Key（必需）
        if not cls.LLM_API_KEY:
            result.add_error("LLM_API_KEY 未配置 - AI 模型调用将无法工作")
        elif cls.LLM_API_KEY == 'your_api_key_here' or cls.LLM_API_KEY == 'your_api_key':
            result.add_error("LLM_API_KEY 使用的是示例值，请配置真实的 API Key")
        elif len(cls.LLM_API_KEY) < 20:
            result.add_warning(f"LLM_API_KEY 长度异常短 ({len(cls.LLM_API_KEY)} 字符)，请确认配置正确")
        else:
            # 显示脱敏后的 key
            masked = cls.LLM_API_KEY[:4] + '*' * 8 + cls.LLM_API_KEY[-4:] if len(cls.LLM_API_KEY) > 16 else '****'
            result.add_info(f"LLM_API_KEY: {masked}")
        
        # Zep API Key（必需）
        if not cls.ZEP_API_KEY:
            result.add_error("ZEP_API_KEY 未配置 - 图谱构建将无法工作")
        elif cls.ZEP_API_KEY == 'your_zep_api_key_here' or cls.ZEP_API_KEY == 'your_zep_api_key':
            result.add_error("ZEP_API_KEY 使用的是示例值，请配置真实的 API Key")
        else:
            masked = cls.ZEP_API_KEY[:4] + '*' * 8 + cls.ZEP_API_KEY[-4:] if len(cls.ZEP_API_KEY) > 16 else '****'
            result.add_info(f"ZEP_API_KEY: {masked}")
        
        # 加速 LLM 配置（可选）
        if cls.LLM_BOOST_API_KEY:
            result.add_info("LLM_BOOST 配置已启用")
            if not cls.LLM_BOOST_BASE_URL or not cls.LLM_BOOST_MODEL_NAME:
                result.add_warning("LLM_BOOST 部分配置缺失，加速功能可能无法正常工作")
    
    @classmethod
    def _validate_urls(cls, result: ConfigValidationResult) -> None:
        """验证 URL 格式"""
        
        # LLM Base URL
        if cls.LLM_BASE_URL:
            parsed = urlparse(cls.LLM_BASE_URL)
            if not parsed.scheme:
                result.add_error(f"LLM_BASE_URL 缺少协议 (http/https): {cls.LLM_BASE_URL}")
            elif parsed.scheme not in ('http', 'https'):
                result.add_error(f"LLM_BASE_URL 协议无效: {parsed.scheme}")
            elif not parsed.netloc:
                result.add_error(f"LLM_BASE_URL 缺少主机名: {cls.LLM_BASE_URL}")
            else:
                result.add_info(f"LLM_BASE_URL: {cls.LLM_BASE_URL}")
        
        # LLM Boost Base URL（如果配置了）
        if cls.LLM_BOOST_BASE_URL:
            parsed = urlparse(cls.LLM_BOOST_BASE_URL)
            if not parsed.scheme or not parsed.netloc:
                result.add_error(f"LLM_BOOST_BASE_URL 格式无效: {cls.LLM_BOOST_BASE_URL}")
    
    @classmethod
    def _validate_numeric_ranges(cls, result: ConfigValidationResult) -> None:
        """验证数值范围"""
        
        # OASIS 模拟轮数
        if cls.OASIS_DEFAULT_MAX_ROUNDS <= 0:
            result.add_error(f"OASIS_DEFAULT_MAX_ROUNDS 必须大于 0，当前值: {cls.OASIS_DEFAULT_MAX_ROUNDS}")
        elif cls.OASIS_DEFAULT_MAX_ROUNDS > 1000:
            result.add_warning(f"OASIS_DEFAULT_MAX_ROUNDS 值过大 ({cls.OASIS_DEFAULT_MAX_ROUNDS})，可能导致长时间运行")
        else:
            result.add_info(f"OASIS_DEFAULT_MAX_ROUNDS: {cls.OASIS_DEFAULT_MAX_ROUNDS}")
        
        # Report Agent 配置
        if cls.REPORT_AGENT_MAX_TOOL_CALLS <= 0:
            result.add_error(f"REPORT_AGENT_MAX_TOOL_CALLS 必须大于 0，当前值: {cls.REPORT_AGENT_MAX_TOOL_CALLS}")
        elif cls.REPORT_AGENT_MAX_TOOL_CALLS > 20:
            result.add_warning(f"REPORT_AGENT_MAX_TOOL_CALLS 较大 ({cls.REPORT_AGENT_MAX_TOOL_CALLS})，可能增加 API 成本")
        
        if cls.REPORT_AGENT_TEMPERATURE < 0 or cls.REPORT_AGENT_TEMPERATURE > 2:
            result.add_error(f"REPORT_AGENT_TEMPERATURE 必须在 0-2 之间，当前值: {cls.REPORT_AGENT_TEMPERATURE}")
        
        # 文件大小限制
        max_mb = cls.MAX_CONTENT_LENGTH / (1024 * 1024)
        if max_mb > 100:
            result.add_warning(f"MAX_CONTENT_LENGTH 较大 ({max_mb:.0f}MB)，可能影响服务器性能")
    
    @classmethod
    def _validate_directories(cls, result: ConfigValidationResult) -> None:
        """验证目录权限"""
        
        directories = [
            ("UPLOAD_FOLDER", cls.UPLOAD_FOLDER),
            ("OASIS_SIMULATION_DATA_DIR", cls.OASIS_SIMULATION_DATA_DIR),
        ]
        
        for name, path in directories:
            path_obj = Path(path)
            
            # 检查目录是否存在
            if not path_obj.exists():
                try:
                    path_obj.mkdir(parents=True, exist_ok=True)
                    result.add_info(f"{name}: 已创建目录 {path}")
                except PermissionError:
                    result.add_error(f"{name}: 无权限创建目录 {path}")
                    continue
                except Exception as e:
                    result.add_error(f"{name}: 创建目录失败 {path} - {str(e)}")
                    continue
            
            # 检查是否是目录
            if not path_obj.is_dir():
                result.add_error(f"{name}: {path} 不是目录")
                continue
            
            # 检查写权限
            if not os.access(path, os.W_OK):
                result.add_error(f"{name}: 目录不可写 {path}")
            else:
                result.add_info(f"{name}: {path} (可写)")
    
    @classmethod
    def _validate_consistency(cls, result: ConfigValidationResult) -> None:
        """验证配置一致性"""
        
        # 检查模型名称格式
        model_name = cls.LLM_MODEL_NAME
        if model_name:
            # 常见模型名称模式
            common_patterns = [
                r'^gpt-',           # OpenAI GPT models
                r'^claude-',        # Anthropic Claude
                r'^qwen',           # Alibaba Qwen
                r'^glm-',           # Zhipu GLM
                r'^deepseek',       # DeepSeek
                r'^llama',          # LLaMA
                r'^mistral',        # Mistral
                r'^[a-z]',          # 一般小写开头
            ]
            
            is_valid_pattern = any(re.match(p, model_name.lower()) for p in common_patterns)
            if not is_valid_pattern:
                result.add_warning(f"LLM_MODEL_NAME '{model_name}' 不是常见模型名称格式，请确认配置正确")
            else:
                result.add_info(f"LLM_MODEL_NAME: {model_name}")
        
        # 检查 DEBUG 模式
        if cls.DEBUG:
            result.add_warning("DEBUG 模式已启用，不建议在生产环境使用")
        
        # 检查 SECRET_KEY 强度
        if cls.SECRET_KEY == 'mirofish-secret-key':
            result.add_warning("使用默认 SECRET_KEY，建议在生产环境更换为随机字符串")
    
    @classmethod
    def get_config_summary(cls) -> Dict[str, Any]:
        """
        获取配置摘要（用于健康检查接口）
        
        注意: 不包含敏感信息如完整 API Keys
        """
        return {
            "llm": {
                "model": cls.LLM_MODEL_NAME,
                "base_url": cls.LLM_BASE_URL,
                "boost_enabled": bool(cls.LLM_BOOST_API_KEY),
            },
            "zep": {
                "configured": bool(cls.ZEP_API_KEY),
            },
            "simulation": {
                "default_max_rounds": cls.OASIS_DEFAULT_MAX_ROUNDS,
            },
            "report_agent": {
                "max_tool_calls": cls.REPORT_AGENT_MAX_TOOL_CALLS,
                "temperature": cls.REPORT_AGENT_TEMPERATURE,
            },
            "debug": cls.DEBUG,
        }


# ============================================================
# 启动时验证（可选使用）
# ============================================================

def validate_on_startup() -> bool:
    """
    启动时验证配置
    
    可以在 run.py 中调用:
        from app.config_validated import validate_on_startup
        if not validate_on_startup():
            sys.exit(1)
    
    Returns:
        bool: 配置是否有效
    """
    result = Config.validate_comprehensive()
    
    print("\n" + "=" * 60)
    print("MiroFish Configuration Validation")
    print("=" * 60)
    
    if result.info:
        print("\n[INFO]")
        for msg in result.info:
            print(f"  ✓ {msg}")
    
    if result.warnings:
        print("\n[WARNINGS]")
        for msg in result.warnings:
            print(f"  ⚠ {msg}")
    
    if result.errors:
        print("\n[ERRORS]")
        for msg in result.errors:
            print(f"  ✗ {msg}")
        print("\n❌ Configuration validation FAILED - Cannot start server")
        print("   Please fix the errors above and try again.\n")
        return False
    
    print("\n✓ Configuration validation PASSED")
    print("=" * 60 + "\n")
    return True
