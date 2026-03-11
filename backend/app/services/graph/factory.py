"""
图数据库服务工厂
根据配置自动选择使用 Zep Cloud 或 Neo4j
"""

from typing import Optional

from ...config import Config
from ...utils.logger import get_logger

logger = get_logger('mirofish.graph_factory')


class GraphServiceFactory:
    """图数据库服务工厂"""
    
    _graph_builder = None
    _graph_tools = None
    _entity_reader = None
    _memory_updater_manager = None
    
    @classmethod
    def get_graph_builder(cls):
        """获取图谱构建服务"""
        if cls._graph_builder is None:
            if Config.use_neo4j():
                from .subsystems.neo4j_graph_builder import Neo4jGraphBuilder
                cls._graph_builder = Neo4jGraphBuilder()
                logger.info("使用 Neo4j Graph Builder")
            else:
                from .subsystems.zep_graph_builder import GraphBuilderService
                cls._graph_builder = GraphBuilderService()
                logger.info("使用 Zep Graph Builder")
        
        return cls._graph_builder
    
    @classmethod
    def get_graph_tools(cls):
        """获取图谱工具服务"""
        if cls._graph_tools is None:
            if Config.use_neo4j():
                from .subsystems.neo4j_tools import Neo4jToolsService
                cls._graph_tools = Neo4jToolsService()
                logger.info("使用 Neo4j Tools Service")
            else:
                from .subsystems.zep_tools import ZepToolsService
                cls._graph_tools = ZepToolsService()
                logger.info("使用 Zep Tools Service")
        
        return cls._graph_tools
    
    @classmethod
    def get_memory_updater_manager(cls):
        """获取记忆更新管理器"""
        if cls._memory_updater_manager is None:
            if Config.use_neo4j():
                from .subsystems.neo4j_graph_memory_updater import Neo4jGraphMemoryManager
                cls._memory_updater_manager = Neo4jGraphMemoryManager
                logger.info("使用 Neo4j Memory Manager")
            else:
                from .subsystems.zep_graph_memory_updater import ZepGraphMemoryManager
                cls._memory_updater_manager = ZepGraphMemoryManager
                logger.info("使用 Zep Memory Manager")
        
        return cls._memory_updater_manager
    
    @classmethod
    def get_entity_reader(cls):
        """获取实体读取器"""
        if cls._entity_reader is None:
            if Config.use_neo4j():
                from .subsystems.neo4j_entity_reader import Neo4jEntityReader
                cls._entity_reader = Neo4jEntityReader()
                logger.info("使用 Neo4j Entity Reader")
            else:
                from .subsystems.zep_entity_reader import ZepEntityReader
                cls._entity_reader = ZepEntityReader()
                logger.info("使用 Zep Entity Reader")
        
        return cls._entity_reader
    
    @classmethod
    def reset(cls):
        """重置缓存（用于切换存储后刷新）"""
        cls._graph_builder = None
        cls._graph_tools = None
        cls._entity_reader = None
        cls._memory_updater_manager = None
        logger.info("Graph Service Factory 已重置")
