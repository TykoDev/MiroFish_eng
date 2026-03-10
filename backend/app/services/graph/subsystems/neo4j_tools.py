"""
Neo4j 图谱检索工具服务
封装图谱搜索、节点读取、边查询等工具，供 Report Agent 使用
替代 Zep Cloud 的检索功能
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from ..neo4j_client import Neo4jClient, Neo4jNode, Neo4jEdge
from ....utils.logger import get_logger
from ....utils.llm_client import LLMClient

logger = get_logger('mirofish.neo4j_tools')


@dataclass
class AgentInterview:
    """单个Agent的采访结果"""
    agent_name: str
    agent_role: str
    agent_bio: str
    question: str
    response: str
    key_quotes: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "agent_bio": self.agent_bio,
            "question": self.question,
            "response": self.response,
            "key_quotes": self.key_quotes
        }
    
    def to_text(self) -> str:
        text = f"**{self.agent_name}** ({self.agent_role})\n"
        text += f"_简介: {self.agent_bio}_\n\n"
        text += f"**Q:** {self.question}\n\n"
        text += f"**A:** {self.response}\n"
        return text


@dataclass
class InterviewResult:
    """采访结果"""
    interview_topic: str
    interview_questions: List[str]
    selected_agents: List[Dict[str, Any]] = field(default_factory=list)
    interviews: List[AgentInterview] = field(default_factory=list)
    selection_reasoning: str = ""
    summary: str = ""
    total_agents: int = 0
    interviewed_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "interview_topic": self.interview_topic,
            "interview_questions": self.interview_questions,
            "selected_agents": self.selected_agents,
            "interviews": [i.to_dict() for i in self.interviews],
            "selection_reasoning": self.selection_reasoning,
            "summary": self.summary,
            "total_agents": self.total_agents,
            "interviewed_count": self.interviewed_count
        }
    
    def to_text(self) -> str:
        text_parts = [
            "## 深度采访报告",
            f"**采访主题:** {self.interview_topic}",
            f"**采访人数:** {self.interviewed_count} / {self.total_agents} 位模拟Agent",
            f"\n摘要: {self.summary or '无'}"
        ]
        return "\n".join(text_parts)


@dataclass
class SearchResult:
    """搜索结果"""
    facts: List[str]
    edges: List[Dict[str, Any]]
    nodes: List[Dict[str, Any]]
    query: str
    total_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "facts": self.facts,
            "edges": self.edges,
            "nodes": self.nodes,
            "query": self.query,
            "total_count": self.total_count
        }
    
    def to_text(self) -> str:
        text_parts = [f"搜索查询: {self.query}", f"找到 {self.total_count} 条相关信息"]
        if self.facts:
            text_parts.append("\n### 相关事实:")
            for i, fact in enumerate(self.facts, 1):
                text_parts.append(f"{i}. {fact}")
        return "\n".join(text_parts)


@dataclass
class InsightForgeResult:
    """深度洞察检索结果"""
    query: str
    simulation_requirement: str
    sub_queries: List[str]
    semantic_facts: List[str] = field(default_factory=list)
    entity_insights: List[Dict[str, Any]] = field(default_factory=list)
    relationship_chains: List[str] = field(default_factory=list)
    total_facts: int = 0
    total_entities: int = 0
    total_relationships: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "simulation_requirement": self.simulation_requirement,
            "sub_queries": self.sub_queries,
            "semantic_facts": self.semantic_facts,
            "entity_insights": self.entity_insights,
            "relationship_chains": self.relationship_chains,
            "total_facts": self.total_facts,
            "total_entities": self.total_entities,
            "total_relationships": self.total_relationships
        }
    
    def to_text(self) -> str:
        text_parts = [
            f"## 未来预测深度分析",
            f"分析问题: {self.query}",
            f"预测场景: {self.simulation_requirement}",
            f"\n### 预测数据统计",
            f"- 相关预测事实: {self.total_facts}条",
            f"- 涉及实体: {self.total_entities}个",
            f"- 关系链: {self.total_relationships}条"
        ]
        
        if self.sub_queries:
            text_parts.append(f"\n### 分析的子问题")
            for i, sq in enumerate(self.sub_queries, 1):
                text_parts.append(f"{i}. {sq}")
        
        if self.semantic_facts:
            text_parts.append(f"\n### 【关键事实】")
            for i, fact in enumerate(self.semantic_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")
        
        if self.entity_insights:
            text_parts.append(f"\n### 【核心实体】")
            for entity in self.entity_insights:
                text_parts.append(f"- **{entity.get('name', '未知')}** ({entity.get('type', '实体')})")
                if entity.get('summary'):
                    text_parts.append(f"  摘要: \"{entity.get('summary')}\"")
        
        if self.relationship_chains:
            text_parts.append(f"\n### 【关系链】")
            for chain in self.relationship_chains:
                text_parts.append(f"- {chain}")
        
        return "\n".join(text_parts)


@dataclass
class PanoramaResult:
    """广度搜索结果"""
    query: str
    all_nodes: List[Any] = field(default_factory=list)
    all_edges: List[Any] = field(default_factory=list)
    active_facts: List[str] = field(default_factory=list)
    historical_facts: List[str] = field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0
    active_count: int = 0
    historical_count: int = 0
    
    def to_text(self) -> str:
        text_parts = [
            f"## 广度搜索结果（未来全景视图）",
            f"查询: {self.query}",
            f"\n### 统计信息",
            f"- 总节点数: {self.total_nodes}",
            f"- 总边数: {self.total_edges}",
            f"- 当前有效事实: {self.active_count}条",
            f"- 历史/过期事实: {self.historical_count}条"
        ]
        
        if self.active_facts:
            text_parts.append(f"\n### 【当前有效事实】")
            for i, fact in enumerate(self.active_facts, 1):
                text_parts.append(f"{i}. \"{fact}\"")
        
        if self.all_nodes:
            text_parts.append(f"\n### 【涉及实体】")
            for node in self.all_nodes:
                text_parts.append(f"- **{node.name}**")
        
        return "\n".join(text_parts)


class Neo4jToolsService:
    """
    Neo4j 图谱检索工具服务
    
    替代 Zep Tools Service 的本地版本
    """
    
    def __init__(self, neo4j_client: Optional[Neo4jClient] = None,
                 llm_client: Optional[LLMClient] = None):
        self.neo4j = neo4j_client or Neo4jClient()
        self._llm_client = llm_client
        logger.info("Neo4jToolsService 初始化完成")
    
    @property
    def llm(self) -> LLMClient:
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client
    
    def search_graph(self, graph_id: str, query: str, 
                    limit: int = 10, scope: str = "edges") -> SearchResult:
        """图谱语义搜索"""
        logger.info(f"图谱搜索: graph_id={graph_id}, query={query[:50]}...")
        
        facts = []
        edges_result = []
        nodes_result = []
        
        # 搜索边
        if scope in ["edges", "both"]:
            edges = self.neo4j.search_edges(graph_id, query, limit)
            for edge in edges:
                if edge.fact:
                    facts.append(edge.fact)
                edges_result.append({
                    "uuid": edge.uuid,
                    "name": edge.name,
                    "fact": edge.fact,
                    "source_node_uuid": edge.source_node_uuid,
                    "target_node_uuid": edge.target_node_uuid,
                })
        
        # 搜索节点
        if scope in ["nodes", "both"]:
            nodes = self.neo4j.search_nodes(graph_id, query, limit)
            for node in nodes:
                nodes_result.append({
                    "uuid": node.uuid,
                    "name": node.name,
                    "labels": node.labels,
                    "summary": node.summary,
                })
                if node.summary:
                    facts.append(f"[{node.name}]: {node.summary}")
        
        logger.info(f"搜索完成: 找到 {len(facts)} 条相关事实")
        
        return SearchResult(
            facts=facts,
            edges=edges_result,
            nodes=nodes_result,
            query=query,
            total_count=len(facts)
        )
    
    def get_all_nodes(self, graph_id: str) -> List[Neo4jNode]:
        """获取图谱所有节点"""
        return self.neo4j.get_all_nodes(graph_id)
    
    def get_node_detail(self, graph_id: str, node_uuid: str) -> Optional[Neo4jNode]:
        """
        获取单个节点的详细信息
        
        Args:
            graph_id: 图谱ID
            node_uuid: 节点UUID
            
        Returns:
            节点信息或None
        """
        logger.info(f"获取节点详情: {node_uuid[:8]}...")
        
        try:
            all_nodes = self.get_all_nodes(graph_id)
            for node in all_nodes:
                if node.uuid == node_uuid:
                    return node
            logger.warning(f"未找到节点: {node_uuid}")
            return None
        except Exception as e:
            logger.error(f"获取节点详情失败: {str(e)}")
            return None
    
    def get_all_edges(self, graph_id: str, include_temporal: bool = True) -> List[Neo4jEdge]:
        """获取图谱所有边"""
        return self.neo4j.get_all_edges(graph_id)
    
    def get_node_edges(self, graph_id: str, node_uuid: str) -> List[Neo4jEdge]:
        """获取节点相关的边"""
        return self.neo4j.get_node_edges(graph_id, node_uuid)
    
    def get_entities_by_type(self, graph_id: str, entity_type: str) -> List[Neo4jNode]:
        """按类型获取实体"""
        return self.neo4j.get_entities_by_type(graph_id, entity_type)
    
    def get_entity_summary(self, graph_id: str, entity_name: str) -> Dict[str, Any]:
        """获取实体的关系摘要"""
        search_result = self.search_graph(graph_id, entity_name, limit=20)
        
        entity_node = self.neo4j.get_node_by_name(graph_id, entity_name)
        related_edges = self.get_node_edges(graph_id, entity_node.uuid) if entity_node else []
        
        return {
            "entity_name": entity_name,
            "entity_info": {"name": entity_node.name, "labels": entity_node.labels, 
                          "summary": entity_node.summary} if entity_node else None,
            "related_facts": search_result.facts,
            "related_edges": [{"name": e.name, "fact": e.fact} for e in related_edges],
            "total_relations": len(related_edges)
        }
    
    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        """获取图谱统计信息"""
        nodes = self.get_all_nodes(graph_id)
        edges = self.get_all_edges(graph_id)
        
        entity_types = {}
        for node in nodes:
            for label in node.labels:
                if label not in ["Entity", "Node"]:
                    entity_types[label] = entity_types.get(label, 0) + 1
        
        relation_types = {}
        for edge in edges:
            relation_types[edge.name] = relation_types.get(edge.name, 0) + 1
        
        return {
            "graph_id": graph_id,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "entity_types": entity_types,
            "relation_types": relation_types
        }
    
    def get_simulation_context(
        self, 
        graph_id: str,
        simulation_requirement: str,
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        获取模拟相关的上下文信息
        
        综合搜索与模拟需求相关的所有信息
        
        Args:
            graph_id: 图谱ID
            simulation_requirement: 模拟需求描述
            limit: 每类信息的数量限制
            
        Returns:
            模拟上下文信息
        """
        logger.info(f"获取模拟上下文: {simulation_requirement[:50]}...")
        
        # 搜索与模拟需求相关的信息
        search_result = self.search_graph(
            graph_id=graph_id,
            query=simulation_requirement,
            limit=limit
        )
        
        # 获取图谱统计
        stats = self.get_graph_statistics(graph_id)
        
        # 获取所有实体节点
        all_nodes = self.get_all_nodes(graph_id)
        
        # 筛选有实际类型的实体（非纯Entity节点）
        entities = []
        for node in all_nodes:
            custom_labels = [l for l in node.labels if l not in ["Entity", "Node"]]
            if custom_labels:
                entities.append({
                    "name": node.name,
                    "type": custom_labels[0],
                    "summary": node.summary
                })
        
        return {
            "simulation_requirement": simulation_requirement,
            "related_facts": search_result.facts,
            "graph_statistics": stats,
            "entities": entities[:limit],  # 限制数量
            "total_entities": len(entities)
        }
    
    def insight_forge(self, graph_id: str, query: str,
                     simulation_requirement: str, report_context: str = "",
                     max_sub_queries: int = 5) -> InsightForgeResult:
        """深度洞察检索"""
        logger.info(f"InsightForge 深度洞察检索: {query[:50]}...")
        
        result = InsightForgeResult(
            query=query,
            simulation_requirement=simulation_requirement,
            sub_queries=[]
        )
        
        # 使用 LLM 生成子问题
        sub_queries = self._generate_sub_queries(
            query, simulation_requirement, report_context, max_sub_queries
        )
        result.sub_queries = sub_queries
        logger.info(f"生成 {len(sub_queries)} 个子问题")
        
        # 搜索各子问题
        all_facts = []
        all_edges = []
        seen_facts = set()
        
        for sub_query in sub_queries:
            search_result = self.search_graph(graph_id, sub_query, limit=15, scope="edges")
            for fact in search_result.facts:
                if fact not in seen_facts:
                    all_facts.append(fact)
                    seen_facts.add(fact)
            all_edges.extend(search_result.edges)
        
        # 原始问题搜索
        main_search = self.search_graph(graph_id, query, limit=20, scope="edges")
        for fact in main_search.facts:
            if fact not in seen_facts:
                all_facts.append(fact)
                seen_facts.add(fact)
        
        result.semantic_facts = all_facts
        result.total_facts = len(all_facts)
        
        # 提取实体
        entity_uuids = set()
        for edge_data in all_edges:
            if isinstance(edge_data, dict):
                entity_uuids.add(edge_data.get('source_node_uuid', ''))
                entity_uuids.add(edge_data.get('target_node_uuid', ''))
        
        entity_insights = []
        node_map = {}
        
        for uuid in list(entity_uuids):
            if not uuid:
                continue
            # 获取节点信息
            all_nodes = self.get_all_nodes(graph_id)
            for node in all_nodes:
                if node.uuid == uuid:
                    node_map[uuid] = node
                    entity_type = next((l for l in node.labels if l not in ["Entity", "Node"]), "实体")
                    related_facts = [f for f in all_facts if node.name.lower() in f.lower()]
                    entity_insights.append({
                        "uuid": node.uuid,
                        "name": node.name,
                        "type": entity_type,
                        "summary": node.summary,
                        "related_facts": related_facts
                    })
        
        result.entity_insights = entity_insights
        result.total_entities = len(entity_insights)
        
        # 构建关系链
        relationship_chains = []
        for edge_data in all_edges:
            if isinstance(edge_data, dict):
                source_name = edge_data.get('source_node_name', edge_data.get('source_node_uuid', '')[:8])
                target_name = edge_data.get('target_node_name', edge_data.get('target_node_uuid', '')[:8])
                relation_name = edge_data.get('name', '')
                chain = f"{source_name} --[{relation_name}]--> {target_name}"
                if chain not in relationship_chains:
                    relationship_chains.append(chain)
        
        result.relationship_chains = relationship_chains
        result.total_relationships = len(relationship_chains)
        
        logger.info(f"InsightForge完成: {result.total_facts}条事实, {result.total_entities}个实体")
        return result
    
    def _generate_sub_queries(self, query: str, simulation_requirement: str,
                             report_context: str, max_queries: int) -> List[str]:
        """使用 LLM 生成子问题"""
        system_prompt = """你是一个专业的问题分析专家。你的任务是将一个复杂问题分解为多个可以在模拟世界中独立观察的子问题。

要求：
1. 每个子问题应该足够具体，可以在模拟世界中找到相关的Agent行为或事件
2. 子问题应该覆盖原问题的不同维度（如：谁、什么、为什么、怎么样、何时、何地）
3. 子问题应该与模拟场景相关
4. 返回JSON格式：{"sub_queries": ["子问题1", "子问题2", ...]}"""

        user_prompt = f"""模拟需求背景：
{simulation_requirement}

{f"报告上下文：{report_context[:500]}" if report_context else ""}

请将以下问题分解为{max_queries}个子问题：
{query}

返回JSON格式的子问题列表。"""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            return response.get("sub_queries", [])[:max_queries]
        except Exception as e:
            logger.warning(f"生成子问题失败: {str(e)}，使用默认子问题")
            return [
                query,
                f"{query} 的主要参与者",
                f"{query} 的原因和影响",
                f"{query} 的发展过程"
            ][:max_queries]
    
    def panorama_search(self, graph_id: str, query: str,
                      include_expired: bool = True, limit: int = 50) -> PanoramaResult:
        """广度搜索"""
        logger.info(f"PanoramaSearch 广度搜索: {query[:50]}...")
        
        result = PanoramaResult(query=query)
        
        all_nodes = self.get_all_nodes(graph_id)
        node_map = {n.uuid: n for n in all_nodes}
        result.all_nodes = all_nodes
        result.total_nodes = len(all_nodes)
        
        # 获取所有边（包含时间信息）
        all_edges = self.get_all_edges(graph_id, include_temporal=True)
        result.all_edges = all_edges
        result.total_edges = len(all_edges)
        
        # 分类事实
        active_facts = []
        historical_facts = []
        
        for edge in all_edges:
            if not edge.fact:
                continue
            
            # 判断是否过期/失效
            is_historical = edge.expired_at is not None or edge.invalid_at is not None
            
            if is_historical:
                # 历史/过期事实，添加时间标记
                valid_at = edge.valid_at or "未知"
                invalid_at = edge.invalid_at or edge.expired_at or "未知"
                fact_with_time = f"[{valid_at} - {invalid_at}] {edge.fact}"
                historical_facts.append(fact_with_time)
            else:
                # 当前有效事实
                active_facts.append(edge.fact)
        
        # 基于查询进行相关性排序
        query_lower = query.lower()
        keywords = [w.strip() for w in query_lower.replace(',', ' ').replace('，', ' ').split() if len(w.strip()) > 1]
        
        def relevance_score(fact: str) -> int:
            fact_lower = fact.lower()
            score = 0
            if query_lower in fact_lower:
                score += 100
            for kw in keywords:
                if kw in fact_lower:
                    score += 10
            return score
        
        # 排序并限制数量
        active_facts.sort(key=relevance_score, reverse=True)
        historical_facts.sort(key=relevance_score, reverse=True)
        
        result.active_facts = active_facts[:limit]
        result.historical_facts = historical_facts[:limit] if include_expired else []
        result.active_count = len(active_facts)
        result.historical_count = len(historical_facts)
        
        logger.info(f"PanoramaSearch完成: {result.active_count}条有效, {result.historical_count}条历史")
        return result
    
    def quick_search(self, graph_id: str, query: str, limit: int = 10) -> SearchResult:
        """简单搜索"""
        logger.info(f"QuickSearch 简单搜索: {query[:50]}...")
        return self.search_graph(graph_id, query, limit, scope="edges")

    def interview_agents(
        self,
        simulation_id: str,
        interview_requirement: str,
        simulation_requirement: str = "",
        max_agents: int = 5,
        custom_questions: List[str] = None
    ) -> InterviewResult:
        """
        【InterviewAgents - 深度采访】
        
        调用真实的OASIS采访API，采访模拟中正在运行的Agent：
        1. 自动读取人设文件，了解所有模拟Agent
        2. 使用LLM分析采访需求，智能选择最相关的Agent
        3. 使用LLM生成采访问题
        4. 调用 /api/simulation/interview/batch 接口进行真实采访（双平台同时采访）
        5. 整合所有采访结果，生成采访报告
        
        【重要】此功能需要模拟环境处于运行状态（OASIS环境未关闭）
        """
        from ...simulation.runner import SimulationRunner
        
        logger.info(f"InterviewAgents 深度采访（真实API）: {interview_requirement[:50]}...")
        
        result = InterviewResult(
            interview_topic=interview_requirement,
            interview_questions=custom_questions or []
        )
        
        # Step 1: 读取人设文件
        profiles = self._load_agent_profiles(simulation_id)
        
        if not profiles:
            logger.warning(f"未找到模拟 {simulation_id} 的人设文件")
            result.summary = "未找到可采访的Agent人设文件"
            return result
        
        result.total_agents = len(profiles)
        logger.info(f"加载到 {len(profiles)} 个Agent人设")
        
        # Step 2: 使用LLM选择要采访的Agent（返回agent_id列表）
        selected_agents, selected_indices, selection_reasoning = self._select_agents_for_interview(
            profiles=profiles,
            interview_requirement=interview_requirement,
            simulation_requirement=simulation_requirement,
            max_agents=max_agents
        )
        
        result.selected_agents = selected_agents
        result.selection_reasoning = selection_reasoning
        logger.info(f"选择了 {len(selected_agents)} 个Agent进行采访: {selected_indices}")
        
        # Step 3: 生成采访问题（如果没有提供）
        if not result.interview_questions:
            result.interview_questions = self._generate_interview_questions(
                interview_requirement=interview_requirement,
                simulation_requirement=simulation_requirement,
                selected_agents=selected_agents
            )
            logger.info(f"生成了 {len(result.interview_questions)} 个采访问题")
        
        # 将问题合并为一个采访prompt
        combined_prompt = "\n".join([f"{i+1}. {q}" for i, q in enumerate(result.interview_questions)])
        
        # 添加优化前缀，约束Agent回复格式
        INTERVIEW_PROMPT_PREFIX = (
            "你正在接受一次采访。请结合你的人设、所有的过往记忆与行动，"
            "以纯文本方式直接回答以下问题。\n"
            "回复要求：\n"
            "1. 直接用自然语言回答，不要调用任何工具\n"
            "2. 不要返回JSON格式或工具调用格式\n"
            "3. 不要使用Markdown标题（如#、##、###）\n"
            "4. 按问题编号逐一回答，每个回答以「问题X：」开头（X为问题编号）\n"
            "5. 每个问题的回答之间用空行分隔\n"
            "6. 回答要有实质内容，每个问题至少回答2-3句话\n\n"
        )
        optimized_prompt = f"{INTERVIEW_PROMPT_PREFIX}{combined_prompt}"
        
        # Step 4: 调用真实的采访API（不指定platform，默认双平台同时采访）
        try:
            # 构建批量采访列表（不指定platform，双平台采访）
            interviews_request = []
            for agent_idx in selected_indices:
                interviews_request.append({
                    "agent_id": agent_idx,
                    "prompt": optimized_prompt  # 使用优化后的prompt
                })
            
            logger.info(f"调用批量采访API（双平台）: {len(interviews_request)} 个Agent")
            
            # 调用 SimulationRunner 的批量采访方法（不传platform，双平台采访）
            api_result = SimulationRunner.interview_agents_batch(
                simulation_id=simulation_id,
                interviews=interviews_request,
                platform=None,  # 不指定platform，双平台采访
                timeout=180.0   # 双平台需要更长超时
            )
            
            logger.info(f"采访API返回: {api_result.get('interviews_count', 0)} 个结果, success={api_result.get('success')}")
            
            # 检查API调用是否成功
            if not api_result.get("success", False):
                error_msg = api_result.get("error", "未知错误")
                logger.warning(f"采访API返回失败: {error_msg}")
                result.summary = f"采访API调用失败：{error_msg}。请检查OASIS模拟环境状态。"
                return result
            
            # Step 5: 解析API返回结果，构建AgentInterview对象
            api_data = api_result.get("result", {})
            results_dict = api_data.get("results", {}) if isinstance(api_data, dict) else {}
            
            for i, agent_idx in enumerate(selected_indices):
                agent = selected_agents[i]
                agent_name = agent.get("realname", agent.get("username", f"Agent_{agent_idx}"))
                agent_role = agent.get("profession", "未知")
                agent_bio = agent.get("bio", "")
                
                twitter_result = results_dict.get(f"twitter_{agent_idx}", {})
                reddit_result = results_dict.get(f"reddit_{agent_idx}", {})
                
                twitter_response = twitter_result.get("response", "")
                reddit_response = reddit_result.get("response", "")

                twitter_response = self._clean_tool_call_response(twitter_response)
                reddit_response = self._clean_tool_call_response(reddit_response)

                twitter_text = twitter_response if twitter_response else "（该平台未获得回复）"
                reddit_text = reddit_response if reddit_response else "（该平台未获得回复）"
                response_text = f"【Twitter平台回答】\n{twitter_text}\n\n【Reddit平台回答】\n{reddit_text}"

                import re
                combined_responses = f"{twitter_response} {reddit_response}"

                clean_text = re.sub(r'#{1,6}\s+', '', combined_responses)
                clean_text = re.sub(r'\{[^}]*tool_name[^}]*\}', '', clean_text)
                clean_text = re.sub(r'[*_`|>~\-]{2,}', '', clean_text)
                clean_text = re.sub(r'问题\d+[：:]\s*', '', clean_text)
                clean_text = re.sub(r'【[^】]+】', '', clean_text)

                sentences = re.split(r'[。！？]', clean_text)
                meaningful = [
                    s.strip() for s in sentences
                    if 20 <= len(s.strip()) <= 150
                    and not re.match(r'^[\s\W，,；;：:、]+', s.strip())
                    and not s.strip().startswith(('{', '问题'))
                ]
                meaningful.sort(key=len, reverse=True)
                key_quotes = [s + "。" for s in meaningful[:3]]

                if not key_quotes:
                    paired = re.findall(r'\u201c([^\u201c\u201d]{15,100})\u201d', clean_text)
                    paired += re.findall(r'\u300c([^\u300c\u300d]{15,100})\u300d', clean_text)
                    key_quotes = [q for q in paired if not re.match(r'^[，,；;：:、]', q)][:3]
                
                interview = AgentInterview(
                    agent_name=agent_name,
                    agent_role=agent_role,
                    agent_bio=agent_bio[:1000],
                    question=combined_prompt,
                    response=response_text,
                    key_quotes=key_quotes[:5]
                )
                result.interviews.append(interview)
            
            result.interviewed_count = len(result.interviews)
            
        except ValueError as e:
            logger.warning(f"采访API调用失败（环境未运行？）: {e}")
            result.summary = f"采访失败：{str(e)}。模拟环境可能已关闭，请确保OASIS环境正在运行。"
            return result
        except Exception as e:
            logger.error(f"采访API调用异常: {e}")
            import traceback
            logger.error(traceback.format_exc())
            result.summary = f"采访过程发生错误：{str(e)}"
            return result
        
        # Step 6: 生成采访摘要
        if result.interviews:
            result.summary = self._generate_interview_summary(
                interviews=result.interviews,
                interview_requirement=interview_requirement
            )
        
        logger.info(f"InterviewAgents完成: 采访了 {result.interviewed_count} 个Agent（双平台）")
        return result

    @staticmethod
    def _clean_tool_call_response(response: str) -> str:
        """清理 Agent 回复中的 JSON 工具调用包裹，提取实际内容"""
        if not response or not response.strip().startswith('{'):
            return response
        text = response.strip()
        if 'tool_name' not in text[:80]:
            return response
        import re as _re
        try:
            data = json.loads(text)
            if isinstance(data, dict) and 'arguments' in data:
                for key in ('content', 'text', 'body', 'message', 'reply'):
                    if key in data['arguments']:
                        return str(data['arguments'][key])
        except (json.JSONDecodeError, KeyError, TypeError):
            match = _re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
            if match:
                return match.group(1).replace('\\n', '\n').replace('\\"', '"')
        return response

    def _load_agent_profiles(self, simulation_id: str) -> List[Dict[str, Any]]:
        """加载模拟的Agent人设文件"""
        import os
        import csv
        
        sim_dir = os.path.join(
            os.path.dirname(__file__), 
            f'../../uploads/simulations/{simulation_id}'
        )
        
        profiles = []
        
        reddit_profile_path = os.path.join(sim_dir, "reddit_profiles.json")
        if os.path.exists(reddit_profile_path):
            try:
                with open(reddit_profile_path, 'r', encoding='utf-8') as f:
                    profiles = json.load(f)
                logger.info(f"从 reddit_profiles.json 加载了 {len(profiles)} 个人设")
                return profiles
            except Exception as e:
                logger.warning(f"读取 reddit_profiles.json 失败: {e}")
        
        twitter_profile_path = os.path.join(sim_dir, "twitter_profiles.csv")
        if os.path.exists(twitter_profile_path):
            try:
                with open(twitter_profile_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        profiles.append({
                            "realname": row.get("name", ""),
                            "username": row.get("username", ""),
                            "bio": row.get("description", ""),
                            "persona": row.get("user_char", ""),
                            "profession": "未知"
                        })
                logger.info(f"从 twitter_profiles.csv 加载了 {len(profiles)} 个人设")
                return profiles
            except Exception as e:
                logger.warning(f"读取 twitter_profiles.csv 失败: {e}")
        
        return profiles
    
    def _select_agents_for_interview(
        self,
        profiles: List[Dict[str, Any]],
        interview_requirement: str,
        simulation_requirement: str,
        max_agents: int
    ) -> tuple:
        """
        使用LLM选择要采访的Agent
        """
        agent_summaries = []
        for i, profile in enumerate(profiles):
            summary = {
                "index": i,
                "name": profile.get("realname", profile.get("username", f"Agent_{i}")),
                "profession": profile.get("profession", "未知"),
                "bio": profile.get("bio", "")[:200],
                "interested_topics": profile.get("interested_topics", [])
            }
            agent_summaries.append(summary)
        
        system_prompt = """你是一个专业的采访策划专家。你的任务是根据采访需求，从模拟Agent列表中选择最适合采访的对象。

选择标准：
1. Agent的身份/职业与采访主题相关
2. Agent可能持有独特或有价值的观点
3. 选择多样化的视角（如：支持方、反对方、中立方、专业人士等）
4. 优先选择与事件直接相关的角色

返回JSON格式：
{
    "selected_indices": [选中Agent的索引列表],
    "reasoning": "选择理由说明"
}"""

        user_prompt = f"""采访需求：
{interview_requirement}

模拟背景：
{simulation_requirement if simulation_requirement else "未提供"}

可选择的Agent列表（共{len(agent_summaries)}个）：
{json.dumps(agent_summaries, ensure_ascii=False, indent=2)}

请选择最多{max_agents}个最适合采访的Agent，并说明选择理由。"""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            
            selected_indices = response.get("selected_indices", [])[:max_agents]
            reasoning = response.get("reasoning", "基于相关性自动选择")
            
            selected_agents = []
            valid_indices = []
            for idx in selected_indices:
                if 0 <= idx < len(profiles):
                    selected_agents.append(profiles[idx])
                    valid_indices.append(idx)
            
            return selected_agents, valid_indices, reasoning
            
        except Exception as e:
            logger.warning(f"LLM选择Agent失败，使用默认选择: {e}")
            selected = profiles[:max_agents]
            indices = list(range(min(max_agents, len(profiles))))
            return selected, indices, "使用默认选择策略"
    
    def _generate_interview_questions(
        self,
        interview_requirement: str,
        simulation_requirement: str,
        selected_agents: List[Dict[str, Any]]
    ) -> List[str]:
        """使用LLM生成采访问题"""
        
        agent_roles = [a.get("profession", "未知") for a in selected_agents]
        
        system_prompt = """你是一个专业的记者/采访者。根据采访需求，生成3-5个深度采访问题。

问题要求：
1. 开放性问题，鼓励详细回答
2. 针对不同角色可能有不同答案
3. 涵盖事实、观点、感受等多个维度
4. 语言自然，像真实采访一样
5. 每个问题控制在50字以内，简洁明了
6. 直接提问，不要包含背景说明或前缀

返回JSON格式：{"questions": ["问题1", "问题2", ...]}"""

        user_prompt = f"""采访需求：{interview_requirement}

模拟背景：{simulation_requirement if simulation_requirement else "未提供"}

采访对象角色：{', '.join(agent_roles)}

请生成3-5个采访问题。"""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.5
            )
            
            return response.get("questions", [f"关于{interview_requirement}，您有什么看法？"])
            
        except Exception as e:
            logger.warning(f"生成采访问题失败: {e}")
            return [
                f"关于{interview_requirement}，您的观点是什么？",
                "这件事对您或您所代表的群体有什么影响？",
                "您认为应该如何解决或改进这个问题？"
            ]
    
    def _generate_interview_summary(
        self,
        interviews: List[AgentInterview],
        interview_requirement: str
    ) -> str:
        """生成采访摘要"""
        
        if not interviews:
            return "未完成任何采访"
        
        interview_texts = []
        for interview in interviews:
            interview_texts.append(f"【{interview.agent_name}（{interview.agent_role}）】\n{interview.response[:500]}")
        
        system_prompt = """你是一个专业的新闻编辑。请根据多位受访者的回答，生成一份采访摘要。

摘要要求：
1. 提炼各方主要观点
2. 指出观点的共识和分歧
3. 突出有价值的引言
4. 客观中立，不偏袒任何一方
5. 控制在1000字内

格式约束（必须遵守）：
- 使用纯文本段落，用空行分隔不同部分
- 不要使用Markdown标题（如#、##、###）
- 不要使用分割线（如---、***）
- 引用受访者原话时使用中文引号「」
- 可以使用**加粗**标记关键词，但不要使用其他Markdown语法"""

        user_prompt = f"""采访主题：{interview_requirement}

采访内容：
{"".join(interview_texts)}

请生成采访摘要。"""

        try:
            summary = self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            return summary
            
        except Exception as e:
            logger.warning(f"生成采访摘要失败: {e}")
            return f"共采访了{len(interviews)}位受访者，包括：" + "、".join([i.agent_name for i in interviews])
