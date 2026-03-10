"""
Neo4j 图谱构建服务
使用 LLM 从文本中提取实体和关系，构建知识图谱
替代 Zep Cloud 的图谱构建功能
"""

import uuid
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from ..neo4j_client import Neo4jClient, Neo4jConfig
from ....config import Config
from ....models.task import TaskManager, TaskStatus
from ....utils.logger import get_logger
from ....utils.llm_client import LLMClient

logger = get_logger('mirofish.neo4j_graph_builder')


@dataclass
class GraphInfo:
    """图谱信息"""
    graph_id: str
    node_count: int
    edge_count: int
    entity_types: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "entity_types": self.entity_types,
        }


class Neo4jGraphBuilder:
    """
    Neo4j 图谱构建服务
    
    使用 LLM 从文本中提取实体和关系，存储到 Neo4j 图数据库
    """
    
    def __init__(self, neo4j_client: Optional[Neo4jClient] = None, 
                 llm_client: Optional[LLMClient] = None):
        self.neo4j = neo4j_client or Neo4jClient()
        self.llm = llm_client or LLMClient()
        self.task_manager = TaskManager()
    
    def _verify_neo4j(self):
        """验证 Neo4j 连接"""
        if not self.neo4j.verify_connectivity():
            raise ConnectionError("无法连接到 Neo4j，请检查配置")
    
    def build_graph_async(
        self,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str = "MiroFish Graph",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> str:
        """异步构建图谱"""
        task_id = self.task_manager.create_task(
            task_type="graph_build",
            metadata={
                "graph_name": graph_name,
                "chunk_size": chunk_size,
                "text_length": len(text),
            }
        )
        
        thread = threading.Thread(
            target=self._build_graph_worker,
            args=(task_id, text, ontology, graph_name, chunk_size, chunk_overlap)
        )
        thread.daemon = True
        thread.start()
        
        return task_id
    
    def _build_graph_worker(
        self,
        task_id: str,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str,
        chunk_size: int,
        chunk_overlap: int
    ):
        """图谱构建工作线程"""
        try:
            self._verify_neo4j()
            
            self.task_manager.update_task(
                task_id, status=TaskStatus.PROCESSING,
                progress=5, message="开始构建图谱..."
            )
            
            # 1. 创建图谱
            graph_id = f"mirofish_{uuid.uuid4().hex[:16]}"
            self.neo4j.create_graph(graph_id, graph_name)
            self.task_manager.update_task(
                task_id, progress=10,
                message=f"图谱已创建: {graph_id}"
            )
            
            # 2. 文本分块
            chunks = self._split_text(text, chunk_size, chunk_overlap)
            total_chunks = len(chunks)
            self.task_manager.update_task(
                task_id, progress=20,
                message=f"文本已分割为 {total_chunks} 个块"
            )
            
            # 3. 提取实体和关系
            all_entities = []
            all_relations = []
            
            for i, chunk in enumerate(chunks):
                entities, relations = self._extract_entities_relations(
                    chunk, ontology
                )
                all_entities.extend(entities)
                all_relations.extend(relations)
                
                progress = 20 + int((i + 1) / total_chunks * 50)
                self.task_manager.update_task(
                    task_id, progress=progress,
                    message=f"处理块 {i+1}/{total_chunks}..."
                )
            
            # 4. 去重
            unique_entities = self._deduplicate_entities(all_entities)
            unique_relations = self._deduplicate_relations(all_relations, unique_entities)
            
            # 5. 写入 Neo4j
            entity_uuids = {}
            for entity in unique_entities:
                uuid_str = self.neo4j.create_node(
                    graph_id=graph_id,
                    name=entity['name'],
                    labels=entity['type'],
                    summary=entity.get('summary', '')
                )
                entity_uuids[entity['name']] = uuid_str
            
            for relation in unique_relations:
                source_uuid = entity_uuids.get(relation['source'])
                target_uuid = entity_uuids.get(relation['target'])
                if source_uuid and target_uuid:
                    self.neo4j.create_relationship(
                        source_uuid, target_uuid,
                        relation['type'], relation.get('fact', '')
                    )
            
            self.task_manager.update_task(
                task_id, progress=90,
                message="写入图数据库..."
            )
            
            # 6. 获取图谱信息
            graph_info = self._get_graph_info(graph_id)
            
            self.task_manager.complete_task(task_id, {
                "graph_id": graph_id,
                "graph_info": graph_info.to_dict(),
                "chunks_processed": total_chunks,
            })
            
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.task_manager.fail_task(task_id, error_msg)
    
    def _split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """文本分块"""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap
        return chunks
    
    def _extract_entities_relations(
        self, 
        text: str, 
        ontology: Dict[str, Any]
    ) -> tuple:
        """使用 LLM 从文本中提取实体和关系"""
        
        # 构建本体约束
        entity_types = ontology.get('entity_types', [])
        edge_types = ontology.get('edge_types', [])
        
        entity_types_str = ", ".join([e['name'] for e in entity_types])
        edge_types_str = ", ".join([e['name'] for e in edge_types])
        
        system_prompt = f"""你是一个知识图谱提取专家。从给定文本中提取实体和关系。

可用实体类型: {entity_types_str}
可用关系类型: {edge_types_str}

返回JSON格式:
{{
    "entities": [
        {{"name": "实体名", "type": "实体类型", "summary": "实体描述"}}
    ],
    "relations": [
        {{"source": "源实体", "target": "目标实体", "type": "关系类型", "fact": "关系描述"}}
    ]
}}

要求:
1. 只提取文本中明确提到的实体和关系
2. 实体 summary 应简洁描述实体
3. 关系 fact 应描述这个关系的具体内容
4. 返回有效的 JSON"""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text[:2000]}
                ],
                temperature=0.1
            )
            
            entities = response.get('entities', [])
            relations = response.get('relations', [])
            
            return entities, relations
            
        except Exception as e:
            logger.warning(f"LLM 提取失败: {e}")
            return [], []
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """实体去重"""
        seen = {}
        for e in entities:
            key = (e['name'], e['type'])
            if key not in seen:
                seen[key] = e
        return list(seen.values())
    
    def _deduplicate_relations(self, relations: List[Dict], entities: List[Dict]) -> List[Dict]:
        """关系去重"""
        entity_names = {e['name'] for e in entities}
        seen = set()
        unique = []
        
        for r in relations:
            key = (r['source'], r['target'], r['type'])
            if key not in seen and r['source'] in entity_names and r['target'] in entity_names:
                seen.add(key)
                unique.append(r)
        return unique
    
    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        """获取图谱信息"""
        info = self.neo4j.get_graph_info(graph_id)
        
        nodes = self.neo4j.get_all_nodes(graph_id)
        entity_types = set()
        for node in nodes:
            for label in node.labels:
                if label not in ['Entity', 'Node']:
                    entity_types.add(label)
        
        return GraphInfo(
            graph_id=graph_id,
            node_count=info['node_count'],
            edge_count=info['edge_count'],
            entity_types=list(entity_types)
        )
    
    def create_graph(self, name: str) -> str:
        """创建图谱"""
        graph_id = f"mirofish_{uuid.uuid4().hex[:16]}"
        self.neo4j.create_graph(graph_id, name)
        return graph_id
    
    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        """设置图谱本体（Neo4j 为无模式数据库，此方法为空实现）"""
        # Neo4j 是无模式数据库，不需要预先定义实体和边的类型
        # 实体和边的类型会在创建节点和关系时自动创建
        pass
    
    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """分批添加文本到图谱（Neo4j 版本）"""
        # 对于 Neo4j，直接处理所有 chunks 并返回 chunk 数量作为 ID
        # Neo4j 是同步处理的，不需要等待异步处理
        all_entities = []
        all_relations = []
        
        # 需要获取 ontology 信息，可以从 graph 存储中获取
        # 这里简化处理，假设直接添加
        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(f"处理块 {i+1}/{len(chunks)}...", i / len(chunks))
            
            # 使用空的 ontology 提取实体和关系
            entities, relations = self._extract_entities_relations(chunk, {
                'entity_types': [],
                'edge_types': []
            })
            all_entities.extend(entities)
            all_relations.extend(relations)
        
        # 去重并写入 Neo4j
        unique_entities = self._deduplicate_entities(all_entities)
        unique_relations = self._deduplicate_relations(all_relations, unique_entities)
        
        entity_uuids = {}
        for entity in unique_entities:
            uuid_str = self.neo4j.create_node(
                graph_id=graph_id,
                name=entity['name'],
                labels=entity['type'],
                summary=entity.get('summary', '')
            )
            entity_uuids[entity['name']] = uuid_str
        
        for relation in unique_relations:
            source_uuid = entity_uuids.get(relation['source'])
            target_uuid = entity_uuids.get(relation['target'])
            if source_uuid and target_uuid:
                self.neo4j.create_relationship(
                    source_uuid, target_uuid,
                    relation['type'], relation.get('fact', '')
                )
        
        # 返回 chunk 索引列表作为 pseudo-episode IDs
        return [str(i) for i in range(len(chunks))]
    
    def _wait_for_episodes(
        self,
        episode_uuids: List[str],
        progress_callback: Optional[Callable] = None,
        timeout: int = 600
    ):
        """等待所有 episode 处理完成（Neo4j 版本）"""
        # Neo4j 是同步处理的，无需等待
        if progress_callback:
            progress_callback("图谱构建完成", 1.0)
    
    # 同步版本
    def build_graph(
        self,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str = "MiroFish Graph",
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ) -> str:
        """同步构建图谱"""
        self._verify_neo4j()
        
        graph_id = f"mirofish_{uuid.uuid4().hex[:16]}"
        self.neo4j.create_graph(graph_id, graph_name)
        
        chunks = self._split_text(text, chunk_size, chunk_overlap)
        
        all_entities = []
        all_relations = []
        
        for chunk in chunks:
            entities, relations = self._extract_entities_relations(chunk, ontology)
            all_entities.extend(entities)
            all_relations.extend(relations)
        
        unique_entities = self._deduplicate_entities(all_entities)
        unique_relations = self._deduplicate_relations(all_relations, unique_entities)
        
        entity_uuids = {}
        for entity in unique_entities:
            uuid_str = self.neo4j.create_node(
                graph_id=graph_id,
                name=entity['name'],
                labels=entity['type'],
                summary=entity.get('summary', '')
            )
            entity_uuids[entity['name']] = uuid_str
        
        for relation in unique_relations:
            source_uuid = entity_uuids.get(relation['source'])
            target_uuid = entity_uuids.get(relation['target'])
            if source_uuid and target_uuid:
                self.neo4j.create_relationship(
                    source_uuid, target_uuid,
                    relation['type'], relation.get('fact', '')
                )
        
        return graph_id
    
    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """
        获取完整图谱数据（包含详细信息）
        
        Args:
            graph_id: 图谱ID
            
        Returns:
            包含nodes和edges的字典
        """
        nodes = self.neo4j.get_all_nodes(graph_id)
        edges = self.neo4j.get_all_edges(graph_id)

        nodes_data = []
        for node in nodes:
            nodes_data.append({
                "uuid": node.uuid,
                "name": node.name,
                "labels": node.labels or [],
                "summary": node.summary or "",
                "attributes": node.attributes or {},
            })
        
        edges_data = []
        for edge in edges:
            edges_data.append({
                "uuid": edge.uuid,
                "source_uuid": edge.source_uuid,
                "target_uuid": edge.target_uuid,
                "type": edge.type or "",
                "fact": edge.fact or "",
            })
        
        return {
            "nodes": nodes_data,
            "edges": edges_data
        }
    
    def delete_graph(self, graph_id: str) -> bool:
        """删除图谱"""
        return self.neo4j.delete_graph(graph_id)
