"""
Neo4j 图谱记忆更新服务
将模拟中的 Agent 活动动态更新到 Neo4j 图数据库中
替代 Zep Cloud 的图谱记忆更新功能
"""

import os
import json
import threading
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

from ..neo4j_client import Neo4jClient
from ....config import Config
from ....utils.logger import get_logger

logger = get_logger('mirofish.neo4j_graph_memory_updater')


@dataclass
class Activity:
    """活动数据"""
    agent_name: str
    action_type: str
    content: str
    platform: str
    timestamp: str
    metadata: Dict[str, Any]


class Neo4jGraphMemoryUpdater:
    """
    Neo4j 图谱记忆更新器
    
    监控模拟的 actions 日志文件，将新的 agent 活动实时更新到 Neo4j 图数据库
    """
    
    BATCH_SIZE = 10
    POLL_INTERVAL = 2.0
    
    def __init__(self, graph_id: str, neo4j_client: Optional[Neo4jClient] = None):
        self.graph_id = graph_id
        self.neo4j = neo4j_client or Neo4jClient()
        self._queue: List[Activity] = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._processed_files: Dict[str, int] = {}  # platform -> last position
    
    def start(self):
        """启动更新器"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()
        logger.info(f"Neo4jGraphMemoryUpdater 已启动: graph_id={self.graph_id}")
    
    def stop(self):
        """停止更新器"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info(f"Neo4jGraphMemoryUpdater 已停止: graph_id={self.graph_id}")
    
    def add_activity(self, agent_name: str, action_type: str, content: str,
                    platform: str, metadata: Optional[Dict] = None):
        """添加活动到队列"""
        activity = Activity(
            agent_name=agent_name,
            action_type=action_type,
            content=content,
            platform=platform,
            timestamp=datetime.now().isoformat(),
            metadata=metadata or {}
        )
        
        with self._lock:
            self._queue.append(activity)
        
        logger.debug(f"添加活动到队列: {agent_name} - {action_type}")
    
    def add_activity_from_dict(self, data: Dict[str, Any], platform: str):
        """
        从字典数据添加活动
        
        Args:
            data: 从actions.jsonl解析的字典数据
            platform: 平台名称 (twitter/reddit)
        """
        # 跳过事件类型的条目
        if "event_type" in data:
            return
        
        # 从字典中提取活动数据
        agent_name = data.get("agent_name", "Unknown")
        action_type = data.get("action_type", "Unknown")
        # 尝试从 action_args 构建内容
        action_args = data.get("action_args", {})
        content = action_args.get("content", "") or action_args.get("text", "") or str(action_args)
        
        self.add_activity(
            agent_name=agent_name,
            action_type=action_type,
            content=content,
            platform=platform,
            metadata=data
        )
    
    def _worker_loop(self):
        """后台工作循环"""
        while self._running:
            try:
                self._process_queue()
            except Exception as e:
                logger.error(f"处理队列出错: {e}")
            
            time.sleep(self.POLL_INTERVAL)
    
    def _process_queue(self):
        """处理队列中的活动"""
        with self._lock:
            if not self._queue:
                return
            
            batch = self._queue[:self.BATCH_SIZE]
            self._queue = self._queue[self.BATCH_SIZE:]
        
        if batch:
            self._save_to_neo4j(batch)
    
    def _save_to_neo4j(self, activities: List[Activity]):
        """保存活动到 Neo4j"""
        try:
            # 按平台分组
            platform_activities: Dict[str, List[Activity]] = {}
            for activity in activities:
                if activity.platform not in platform_activities:
                    platform_activities[activity.platform] = []
                platform_activities[activity.platform].append(activity)
            
            # 为每个平台创建/更新 Agent 节点
            for platform, platform_activities in platform_activities.items():
                # 创建平台节点
                self.neo4j.create_node(
                    graph_id=self.graph_id,
                    name=platform,
                    labels=["Platform", "Node"],
                    summary=f"{platform} 平台的活动"
                )
                
                # 为每个活动创建节点和关系
                for activity in platform_activities:
                    # 创建 Agent 节点（如果不存在）
                    self.neo4j.create_node(
                        graph_id=self.graph_id,
                        name=activity.agent_name,
                        labels=["Agent", "Node"],
                        summary=f"执行 {activity.action_type} 的代理"
                    )
                    
                    # 创建活动节点
                    activity_id = self.neo4j.create_node(
                        graph_id=self.graph_id,
                        name=f"{activity.action_type}_{activity.timestamp}",
                        labels=["Activity", "Node"],
                        summary=activity.content[:200]
                    )
                    
                    # 创建关系: Agent -> Platform
                    self.neo4j.create_relationship(
                        source_uuid=self._get_node_uuid(activity.agent_name),
                        target_uuid=self._get_node_uuid(platform),
                        rel_type="BELONGS_TO",
                        fact=f"{activity.agent_name} 属于 {platform} 平台"
                    )
                    
                    # 创建关系: Agent -> Activity
                    self.neo4j.create_relationship(
                        source_uuid=self._get_node_uuid(activity.agent_name),
                        target_uuid=activity_id,
                        rel_type=activity.action_type,
                        fact=activity.content
                    )
            
            logger.info(f"批量保存 {len(activities)} 条活动到 Neo4j")
            
        except Exception as e:
            logger.error(f"保存到 Neo4j 失败: {e}")
    
    def _get_node_uuid(self, name: str) -> str:
        """获取节点 UUID"""
        node = self.neo4j.get_node_by_name(self.graph_id, name)
        return node.uuid if node else ""


class Neo4jGraphMemoryManager:
    """管理多个模拟的图谱记忆更新器"""
    
    _updaters: Dict[str, Neo4jGraphMemoryUpdater] = {}
    
    @classmethod
    def create_updater(cls, simulation_id: str, graph_id: str) -> Neo4jGraphMemoryUpdater:
        """创建更新器"""
        if simulation_id in cls._updaters:
            return cls._updaters[simulation_id]
        
        updater = Neo4jGraphMemoryUpdater(graph_id)
        cls._updaters[simulation_id] = updater
        return updater
    
    @classmethod
    def get_updater(cls, simulation_id: str) -> Optional[Neo4jGraphMemoryUpdater]:
        """获取更新器"""
        return cls._updaters.get(simulation_id)
    
    @classmethod
    def remove_updater(cls, simulation_id: str):
        """移除更新器"""
        if simulation_id in cls._updaters:
            updater = cls._updaters[simulation_id]
            updater.stop()
            del cls._updaters[simulation_id]
