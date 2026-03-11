"""
配置管理
统一从项目根目录的 .env 文件加载配置
"""

import os
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
# 路径: MiroFish/.env (相对于 backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # 如果根目录没有 .env，尝试加载环境变量（用于生产环境）
    load_dotenv(override=True)


class Config:
    """Flask配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JSON配置 - 禁用ASCII转义，让中文直接显示（而不是 \uXXXX 格式）
    JSON_AS_ASCII = False
    
    # LLM配置（统一使用OpenAI格式）
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    LLM_MAX_RETRIES = int(os.environ.get('LLM_MAX_RETRIES', '3'))  # LLM调用最大重试次数
    
    # 数据库配置
    NEO4J_MAX_RETRIES = int(os.environ.get('NEO4J_MAX_RETRIES', '3'))  # Neo4j操作最大重试次数
    NEO4J_RETRY_DELAY = int(os.environ.get('NEO4J_RETRY_DELAY', '1'))  # Neo4j重试间隔（秒）
    ZEP_MAX_RETRIES = int(os.environ.get('ZEP_MAX_RETRIES', '3'))  # Zep API调用最大重试次数
    
    # ===== 图数据库配置 =====
    # 选择使用的数据存储方式: "zep" 或 "neo4j"
    GRAPH_STORAGE = os.environ.get('GRAPH_STORAGE', 'zep')
    
    # Zep配置（云服务）
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
    # Neo4j配置（本地自建）
    NEO4J_URI = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USERNAME = os.environ.get('NEO4J_USERNAME', 'neo4j')
    NEO4J_PASSWORD = os.environ.get('NEO4J_PASSWORD', '')
    NEO4J_DATABASE = os.environ.get('NEO4J_DATABASE', 'neo4j')
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小
    
    # OASIS模拟配置
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')
    
    # OASIS平台可用动作配置
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent配置
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))
    
    @classmethod
    def validate(cls):
        """验证必要配置"""
        errors = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY 未配置")
        
        # 根据图数据库选择验证
        if cls.GRAPH_STORAGE == 'zep':
            if not cls.ZEP_API_KEY:
                errors.append("ZEP_API_KEY 未配置（当前使用 Zep Cloud）")
        elif cls.GRAPH_STORAGE == 'neo4j':
            if not cls.NEO4J_PASSWORD:
                errors.append("NEO4J_PASSWORD 未配置（当前使用 Neo4j）")
        else:
            errors.append(f"GRAPH_STORAGE 配置错误: {cls.GRAPH_STORAGE}，应为 'zep' 或 'neo4j'")
        
        return errors
    
    @classmethod
    def use_neo4j(cls) -> bool:
        """是否使用 Neo4j"""
        return cls.GRAPH_STORAGE == 'neo4j'
    
    @classmethod
    def use_zep(cls) -> bool:
        """是否使用 Zep"""
        return cls.GRAPH_STORAGE == 'zep'

