"""
Neo4j 客户端工具类
提供图数据库连接和基础操作
支持重试机制和友好错误提示
"""

import os
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, RetryError

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable, AuthError, TransientError, SessionExpired

from ...config import Config
from ...utils.logger import get_logger

logger = get_logger('mirofish.neo4j_client')


@dataclass
class Neo4jConfig:
    """Neo4j 连接配置"""
    uri: str = ""
    username: str = ""
    password: str = ""
    database: str = "neo4j"
    
    @classmethod
    def from_env(cls) -> "Neo4jConfig":
        return cls(
            uri=os.environ.get('NEO4J_URI', 'bolt://localhost:7687'),
            username=os.environ.get('NEO4J_USERNAME', 'neo4j'),
            password=os.environ.get('NEO4J_PASSWORD', ''),
            database=os.environ.get('NEO4J_DATABASE', 'neo4j')
        )


@dataclass
class Neo4jNode:
    """Neo4j 节点"""
    uuid: str
    name: str
    labels: List[str] = field(default_factory=list)
    summary: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Neo4jEdge:
    """Neo4j 边（关系）"""
    uuid: str
    name: str
    fact: str
    source_node_uuid: str
    target_node_uuid: str
    source_node_name: Optional[str] = None
    target_node_name: Optional[str] = None
    created_at: Optional[str] = None
    valid_at: Optional[str] = None
    invalid_at: Optional[str] = None
    expired_at: Optional[str] = None
    
    @property
    def is_expired(self) -> bool:
        """是否已过期"""
        return self.expired_at is not None
    
    @property
    def is_invalid(self) -> bool:
        """是否已失效"""
        return self.invalid_at is not None
    
    def to_text(self, include_temporal: bool = False) -> str:
        """转换为文本格式"""
        source = self.source_node_name or self.source_node_uuid[:8]
        target = self.target_node_name or self.target_node_uuid[:8]
        base_text = f"关系: {source} --[{self.name}]--> {target}\n事实: {self.fact}"
        
        if include_temporal:
            valid_at = self.valid_at or "未知"
            invalid_at = self.invalid_at or "至今"
            base_text += f"\n时效: {valid_at} - {invalid_at}"
            if self.expired_at:
                base_text += f" (已过期: {self.expired_at})"
        
        return base_text


class Neo4jClient:
    """Neo4j 客户端 - 替代 Zep Cloud 的本地图数据库方案"""
    
    def __init__(self, config: Optional[Neo4jConfig] = None):
        self.config = config or Neo4jConfig.from_env()
        self._driver: Optional[Driver] = None
    
    @property
    def driver(self) -> Driver:
        if self._driver is None:
            if not self.config.password:
                raise ValueError("NEO4J_PASSWORD 未配置")
            self._driver = GraphDatabase.driver(
                self.config.uri,
                auth=(self.config.username, self.config.password)
            )
            logger.info(f"Neo4j 驱动已创建: {self.config.uri}")
        return self._driver
    
    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None
    
    @retry(
        stop=stop_after_attempt(Config.NEO4J_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=Config.NEO4J_RETRY_DELAY, max=5),
        retry=retry_if_exception_type((ServiceUnavailable, TransientError, SessionExpired)),
        reraise=True
    )
    def verify_connectivity(self) -> bool:
        """验证Neo4j连接（支持自动重试）"""
        try:
            with self.driver.session(database=self.config.database) as session:
                result = session.run("RETURN 1 AS n")
                result.single()
            logger.info("Neo4j 连接验证成功")
            return True
        except AuthError as e:
            logger.error(f"Neo4j 认证失败: {str(e)}")
            raise ValueError("Neo4j用户名或密码错误，请检查配置") from e
        except ServiceUnavailable as e:
            logger.warning(f"Neo4j 服务不可用: {str(e)}，将自动重试")
            raise
        except TransientError as e:
            logger.warning(f"Neo4j 临时错误: {str(e)}，将自动重试")
            raise
        except Exception as e:
            logger.error(f"Neo4j 连接未知错误: {str(e)}")
            raise
    
    def create_graph(self, graph_id: str, name: str, description: str = "") -> str:
        with self.driver.session(database=self.config.database) as session:
            session.run("""
                MERGE (g:Graph {graph_id: $graph_id})
                SET g.name = $name, g.description = $description
            """, graph_id=graph_id, name=name, description=description)
        logger.info(f"创建图谱: {graph_id}")
        return graph_id
    
    def create_node(self, graph_id: str, name: str, labels: List[str], 
                    summary: str = "", **kwargs) -> str:
        safe_labels = [l.replace(' ', '_') for l in labels]
        all_labels = ['Entity', 'Node'] + safe_labels
        label_str = ':'.join(['`{}`'.format(l) for l in all_labels])
        
        import uuid as uuid_module
        props = {'name': name, 'summary': summary, 'graph_id': graph_id, 'uuid': uuid_module.uuid4().hex}
        props.update(kwargs)
        
        with self.driver.session(database=self.config.database) as session:
            session.run(f"""
                CREATE (n:{label_str} $props)
            """, props=props)
            
            result = session.run(f"""
                MATCH (n:{label_str} {{graph_id: $graph_id, name: $name}})
                RETURN n.uuid AS uuid, elementId(n) AS element_id
            """, graph_id=graph_id, name=name)
            
            record = result.single()
            if record:
                return record['uuid'] or record['element_id']
        return ""
    
    def create_relationship(self, source_uuid: str, target_uuid: str,
                          rel_type: str, fact: str = "", **kwargs) -> str:
        safe_rel_type = rel_type.upper().replace(' ', '_')
        
        with self.driver.session(database=self.config.database) as session:
            result = session.run(f"""
                MATCH (s), (t)
                WHERE (elementId(s) = $source_id OR s.uuid = $source_uuid)
                  AND (elementId(t) = $target_id OR t.uuid = $target_uuid)
                CREATE (s)-[r:`{safe_rel_type}`]->(t)
                SET r.fact = $fact, r.created_at = datetime(), r.valid_at = datetime()
                RETURN elementId(r) AS rel_id
            """, source_id=source_uuid, target_id=target_uuid,
                source_uuid=source_uuid, target_uuid=target_uuid, fact=fact)
            
            record = result.single()
            if record:
                return record['rel_id']
        return ""
    
    def get_all_nodes(self, graph_id: str) -> List[Neo4jNode]:
        with self.driver.session(database=self.config.database) as session:
            result = session.run("""
                MATCH (n:Entity {graph_id: $graph_id})
                RETURN n, elementId(n) AS element_id
            """, graph_id=graph_id)
            
            nodes = []
            for record in result:
                node = record.get('n')
                if node:
                    props = dict(node)
                    nodes.append(Neo4jNode(
                        uuid=props.get('uuid', str(record.get('element_id'))),
                        name=props.get('name', ''),
                        labels=list(node.labels),
                        summary=props.get('summary', ''),
                        attributes={k: v for k, v in props.items() 
                                  if k not in ['uuid', 'name', 'summary', 'graph_id', 'created_at']}
                    ))
            return nodes
    
    def get_all_edges(self, graph_id: str) -> List[Neo4jEdge]:
        with self.driver.session(database=self.config.database) as session:
            result = session.run("""
                MATCH (s:Entity {graph_id: $graph_id})-[r]->(t:Entity {graph_id: $graph_id})
                RETURN s, r, t
            """, graph_id=graph_id)
            
            edges = []
            for record in result:
                source_node = dict(record.get('s'))
                target_node = dict(record.get('t'))
                rel = record.get('r')
                
                if rel:
                    props = dict(rel)
                    edges.append(Neo4jEdge(
                        uuid=str(rel.element_id),
                        name=rel.type,
                        fact=props.get('fact', ''),
                        source_node_uuid=source_node.get('uuid', ''),
                        target_node_uuid=target_node.get('uuid', ''),
                        source_node_name=source_node.get('name', ''),
                        target_node_name=target_node.get('name', ''),
                        created_at=props.get('created_at'),
                        valid_at=props.get('valid_at'),
                        invalid_at=props.get('invalid_at'),
                        expired_at=props.get('expired_at')
                    ))
            return edges
    
    def search_nodes(self, graph_id: str, query: str, limit: int = 10) -> List[Neo4jNode]:
        query_lower = query.lower()
        with self.driver.session(database=self.config.database) as session:
            result = session.run("""
                MATCH (n:Entity {graph_id: $graph_id})
                WHERE toLower(n.name) CONTAINS $query OR toLower(n.summary) CONTAINS $query
                RETURN n, elementId(n) AS element_id LIMIT $limit
            """, graph_id=graph_id, query=query_lower, limit=limit)
            
            nodes = []
            for record in result:
                node = record.get('n')
                if node:
                    props = dict(node)
                    nodes.append(Neo4jNode(
                        uuid=props.get('uuid', str(record.get('element_id'))),
                        name=props.get('name', ''),
                        labels=list(node.labels),
                        summary=props.get('summary', ''),
                        attributes={}
                    ))
            return nodes
    
    def search_edges(self, graph_id: str, query: str, limit: int = 10) -> List[Neo4jEdge]:
        query_lower = query.lower()
        with self.driver.session(database=self.config.database) as session:
            result = session.run("""
                MATCH (s:Entity {graph_id: $graph_id})-[r]->(t:Entity {graph_id: $graph_id})
                WHERE toLower(r.fact) CONTAINS $query
                RETURN s, r, t LIMIT $limit
            """, graph_id=graph_id, query=query_lower, limit=limit)
            
            edges = []
            for record in result:
                source_node = dict(record.get('s'))
                target_node = dict(record.get('t'))
                rel = record.get('r')
                
                if rel:
                    props = dict(rel)
                    edges.append(Neo4jEdge(
                        uuid=str(rel.element_id),
                        name=rel.type,
                        fact=props.get('fact', ''),
                        source_node_uuid=source_node.get('uuid', ''),
                        target_node_uuid=target_node.get('uuid', ''),
                        source_node_name=source_node.get('name', ''),
                        target_node_name=target_node.get('name', ''),
                    ))
            return edges
    
    def get_node_by_name(self, graph_id: str, name: str) -> Optional[Neo4jNode]:
        with self.driver.session(database=self.config.database) as session:
            result = session.run("""
                MATCH (n:Entity {graph_id: $graph_id, name: $name})
                RETURN n, elementId(n) AS element_id
            """, graph_id=graph_id, name=name)
            
            record = result.single()
            if record:
                node = record.get('n')
                props = dict(node)
                return Neo4jNode(
                    uuid=props.get('uuid', str(record.get('element_id'))),
                    name=props.get('name', ''),
                    labels=list(node.labels),
                    summary=props.get('summary', ''),
                    attributes={}
                )
        return None
    
    def get_node_edges(self, graph_id: str, node_uuid: str) -> List[Neo4jEdge]:
        with self.driver.session(database=self.config.database) as session:
            result = session.run("""
                MATCH (s:Entity {graph_id: $graph_id})-[r]->(t:Entity {graph_id: $graph_id})
                WHERE s.uuid = $node_uuid OR elementId(s) = $node_uuid
                   OR t.uuid = $node_uuid OR elementId(t) = $node_uuid
                RETURN s, r, t
            """, graph_id=graph_id, node_uuid=node_uuid)
            
            edges = []
            for record in result:
                source_node = dict(record.get('s'))
                target_node = dict(record.get('t'))
                rel = record.get('r')
                
                if rel:
                    props = dict(rel)
                    edges.append(Neo4jEdge(
                        uuid=str(rel.element_id),
                        name=rel.type,
                        fact=props.get('fact', ''),
                        source_node_uuid=source_node.get('uuid', ''),
                        target_node_uuid=target_node.get('uuid', ''),
                        source_node_name=source_node.get('name', ''),
                        target_node_name=target_node.get('name', ''),
                    ))
            return edges
    
    def get_entities_by_type(self, graph_id: str, entity_type: str) -> List[Neo4jNode]:
        safe_type = entity_type.replace(' ', '_')
        with self.driver.session(database=self.config.database) as session:
            result = session.run(f"""
                MATCH (n:Entity:`{safe_type}` {{graph_id: $graph_id}})
                RETURN n, elementId(n) AS element_id
            """, graph_id=graph_id)
            
            nodes = []
            for record in result:
                node = record.get('n')
                if node:
                    props = dict(node)
                    nodes.append(Neo4jNode(
                        uuid=props.get('uuid', str(record.get('element_id'))),
                        name=props.get('name', ''),
                        labels=list(node.labels),
                        summary=props.get('summary', ''),
                        attributes={}
                    ))
            return nodes
    
    def delete_graph(self, graph_id: str) -> bool:
        with self.driver.session(database=self.config.database) as session:
            session.run("""
                MATCH (n:Entity {graph_id: $graph_id})
                DETACH DELETE n
            """, graph_id=graph_id)
            session.run("""
                MATCH (g:Graph {graph_id: $graph_id})
                DELETE g
            """, graph_id=graph_id)
        logger.info(f"删除图谱: {graph_id}")
        return True
    
    def get_graph_info(self, graph_id: str) -> Dict[str, Any]:
        with self.driver.session(database=self.config.database) as session:
            result = session.run("""
                MATCH (n:Entity {graph_id: $graph_id})
                RETURN count(n) AS node_count
            """, graph_id=graph_id)
            node_count = result.single()['node_count'] if result.single() else 0
            
            result = session.run("""
                MATCH (s:Entity {graph_id: $graph_id})-[r]->(t:Entity {graph_id: $graph_id})
                RETURN count(r) AS edge_count
            """, graph_id=graph_id)
            edge_count = result.single()['edge_count'] if result.single() else 0
            
            return {"node_count": node_count, "edge_count": edge_count}
