"""
Graph search tool service using LightRAG.

Replaces ZepToolsService — provides graph search, node reading, edge query
and other tools for use by Report Agent. Uses LightRAG for semantic search
and direct PostgreSQL queries for data access.

Core search tools:
1. InsightForge (deep insight search) - generates sub-questions, multi-dimensional search
2. PanoramaSearch - get the full picture, including all content
3. QuickSearch - quick search
4. InterviewAgents - in-depth interviews with simulated agents
"""

import time
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from lightrag import QueryParam

from ..config import Config
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient
from ..utils.async_bridge import run_async
from .lightrag_manager import LightRAGManager

logger = get_logger("mirofish.graph_tools")


@dataclass
class SearchResult:
    """Search results"""

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
            "total_count": self.total_count,
        }

    def to_text(self) -> str:
        """Convert to text format for LLM to understand"""
        text_parts = [
            f"Search query: {self.query}",
            f"{self.total_count} related information found",
        ]
        if self.facts:
            text_parts.append("\n### Relevant facts:")
            for i, fact in enumerate(self.facts, 1):
                text_parts.append(f"{i}. {fact}")
        return "\n".join(text_parts)


@dataclass
class NodeInfo:
    """Node information"""

    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
        }

    def to_text(self) -> str:
        entity_type = next(
            (l for l in self.labels if l not in ["Entity", "Node"]), "Unknown type"
        )
        return f"Entity: {self.name} (Type: {entity_type})\nSummary: {self.summary}"


@dataclass
class EdgeInfo:
    """Edge information"""

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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "fact": self.fact,
            "source_node_uuid": self.source_node_uuid,
            "target_node_uuid": self.target_node_uuid,
            "source_node_name": self.source_node_name,
            "target_node_name": self.target_node_name,
            "created_at": self.created_at,
            "valid_at": self.valid_at,
            "invalid_at": self.invalid_at,
            "expired_at": self.expired_at,
        }

    def to_text(self, include_temporal: bool = False) -> str:
        source = self.source_node_name or self.source_node_uuid[:8]
        target = self.target_node_name or self.target_node_uuid[:8]
        base_text = (
            f"Relationship: {source} --[{self.name}]--> {target}\nFact: {self.fact}"
        )
        if include_temporal:
            valid_at = self.valid_at or "unknown"
            invalid_at = self.invalid_at or "Right now"
            base_text += f"\nAge: {valid_at} - {invalid_at}"
            if self.expired_at:
                base_text += f" (Expired: {self.expired_at})"
        return base_text

    @property
    def is_expired(self) -> bool:
        return self.expired_at is not None

    @property
    def is_invalid(self) -> bool:
        return self.invalid_at is not None


@dataclass
class InsightForgeResult:
    """Deep Insight Search Results"""

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
            "total_relationships": self.total_relationships,
        }

    def to_text(self) -> str:
        text_parts = [
            f"## In-depth analysis of future forecasts",
            f"Analysis question: {self.query}",
            f"Prediction scenario: {self.simulation_requirement}",
            f"\n### Forecast data statistics",
            f"-Related prediction facts: {self.total_facts}",
            f"-Involved entities: {self.total_entities}",
            f"-Relationship chain: {self.total_relationships}",
        ]
        if self.sub_queries:
            text_parts.append(f"\n### Analysis sub-problems")
            for i, sq in enumerate(self.sub_queries, 1):
                text_parts.append(f"{i}. {sq}")
        if self.semantic_facts:
            text_parts.append(
                f"\n### [Key Facts] (Please cite these original texts in your report)"
            )
            for i, fact in enumerate(self.semantic_facts, 1):
                text_parts.append(f'{i}. "{fact}"')
        if self.entity_insights:
            text_parts.append(f"\n### [Core Entity]")
            for entity in self.entity_insights:
                text_parts.append(
                    f"- **{entity.get('name', 'unknown')}** ({entity.get('type', 'entity')})"
                )
                if entity.get("summary"):
                    text_parts.append(f'  Summary: "{entity.get("summary")}"')
                if entity.get("related_facts"):
                    text_parts.append(
                        f"  Related facts: {len(entity.get('related_facts', []))}"
                    )
        if self.relationship_chains:
            text_parts.append(f"\n### [Relationship chain]")
            for chain in self.relationship_chains:
                text_parts.append(f"- {chain}")
        return "\n".join(text_parts)


@dataclass
class PanoramaResult:
    """Breadth search results"""

    query: str
    all_nodes: List[NodeInfo] = field(default_factory=list)
    all_edges: List[EdgeInfo] = field(default_factory=list)
    active_facts: List[str] = field(default_factory=list)
    historical_facts: List[str] = field(default_factory=list)
    total_nodes: int = 0
    total_edges: int = 0
    active_count: int = 0
    historical_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "all_nodes": [n.to_dict() for n in self.all_nodes],
            "all_edges": [e.to_dict() for e in self.all_edges],
            "active_facts": self.active_facts,
            "historical_facts": self.historical_facts,
            "total_nodes": self.total_nodes,
            "total_edges": self.total_edges,
            "active_count": self.active_count,
            "historical_count": self.historical_count,
        }

    def to_text(self) -> str:
        text_parts = [
            f"## Panorama Search Results",
            f"Search query: {self.query}",
            f"\n### Statistics",
            f"- Total entities: {self.total_nodes}",
            f"- Total relationships: {self.total_edges}",
            f"- Currently valid facts: {self.active_count}",
            f"- Historical facts: {self.historical_count}",
        ]
        if self.active_facts:
            text_parts.append(f"\n### Currently valid facts")
            for i, fact in enumerate(self.active_facts[:30], 1):
                text_parts.append(f"{i}. {fact}")
        if self.historical_facts:
            text_parts.append(f"\n### Historical facts")
            for i, fact in enumerate(self.historical_facts[:20], 1):
                text_parts.append(f"{i}. {fact}")
        return "\n".join(text_parts)


@dataclass
class AgentInterview:
    """Single Agent interview result"""

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
            "key_quotes": self.key_quotes,
        }

    def to_text(self) -> str:
        text = f"**{self.agent_name}** ({self.agent_role})\n"
        text += f"_Introduction: {self.agent_bio}_\n\n"
        text += f"**Q:** {self.question}\n\n"
        text += f"**A:** {self.response}\n"
        if self.key_quotes:
            text += "\n**Key Quote:**\n"
            for quote in self.key_quotes:
                clean_quote = (
                    quote.replace("\u201c", "").replace("\u201d", "").replace('"', "")
                )
                clean_quote = clean_quote.replace("\u300c", "").replace("\u300d", "")
                clean_quote = clean_quote.strip()
                while clean_quote and clean_quote[0] in ",;:\n\r\t ":
                    clean_quote = clean_quote[1:]
                if clean_quote and len(clean_quote) >= 10:
                    text += f'> "{clean_quote}"\n'
        return text


@dataclass
class InterviewResult:
    """Interview results from multiple agents"""

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
            "interviewed_count": self.interviewed_count,
        }

    def to_text(self) -> str:
        text_parts = [
            "## In-depth interview report",
            f"**Interview topic:** {self.interview_topic}",
            f"**Number of people interviewed:** {self.interviewed_count} / {self.total_agents} simulated Agents",
            "\n### Reasons for selecting interviewees",
            self.selection_reasoning or "(auto-select)",
            "\n---",
        ]
        if self.interviews:
            for i, interview in enumerate(self.interviews, 1):
                text_parts.append(f"\n### Interviewee {i}: {interview.agent_name}")
                text_parts.append(interview.to_text())
                text_parts.append("\n---")
        else:
            text_parts.append("(No interview record)\n\n---")
        text_parts.append("\n### Interview summary and core points")
        text_parts.append(self.summary or "(No abstract)")
        return "\n".join(text_parts)


class GraphToolsService:
    """
    Graph search tool service using LightRAG.

    Core search tools:
    1. insight_forge - deep insight search
    2. panorama_search - breadth search
    3. quick_search - simple search
    4. interview_agents - in-depth interviews

    Basic tools:
    - search_graph, get_all_nodes, get_all_edges, get_node_detail,
      get_node_edges, get_entities_by_type, get_entity_summary
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self._llm_client = llm_client
        self._nodes_cache: Dict[str, List[NodeInfo]] = {}
        self._edges_cache: Dict[str, List[EdgeInfo]] = {}
        logger.info("GraphToolsService initialization completed")

    @staticmethod
    def _graph_schema_name(graph_id: str) -> str:
        return f"{graph_id}_chunk_entity_relation"

    def _load_nodes_from_sql(self, graph_id: str) -> List[NodeInfo]:
        schema = self._graph_schema_name(graph_id)
        conn = LightRAGManager.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f'''
                    SELECT
                        ag_catalog.agtype_access_operator(v.properties, '"entity_id"'::ag_catalog.agtype)::text,
                        ag_catalog.agtype_access_operator(v.properties, '"entity_type"'::ag_catalog.agtype)::text,
                        ag_catalog.agtype_access_operator(v.properties, '"description"'::ag_catalog.agtype)::text,
                        ag_catalog.agtype_access_operator(v.properties, '"source_id"'::ag_catalog.agtype)::text,
                        ag_catalog.agtype_access_operator(v.properties, '"content"'::ag_catalog.agtype)::text
                    FROM "{schema}"."base" v
                    '''
                )
                rows = cur.fetchall()
        finally:
            LightRAGManager.put_connection(conn)

        nodes: List[NodeInfo] = []
        for entity_name, entity_type, description, source_id, content in rows:
            name = entity_name or ""
            kind = entity_type or ""
            labels = ["Entity"]
            if kind and kind not in ["Entity", "Node"]:
                labels.insert(0, kind)
            nodes.append(
                NodeInfo(
                    uuid=name,
                    name=name,
                    labels=labels,
                    summary=description or content or "",
                    attributes={"source_id": source_id or "", "entity_type": kind},
                )
            )
        return nodes

    def _load_edges_from_sql(self, graph_id: str) -> List[EdgeInfo]:
        schema = self._graph_schema_name(graph_id)
        conn = LightRAGManager.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f'''
                    SELECT
                        e.id::text,
                        ag_catalog.agtype_access_operator(e.properties, '"keywords"'::ag_catalog.agtype)::text,
                        ag_catalog.agtype_access_operator(e.properties, '"description"'::ag_catalog.agtype)::text,
                        ag_catalog.agtype_access_operator(e.properties, '"content"'::ag_catalog.agtype)::text,
                        ag_catalog.agtype_access_operator(e.properties, '"created_at"'::ag_catalog.agtype)::text,
                        ag_catalog.agtype_access_operator(src.properties, '"entity_id"'::ag_catalog.agtype)::text,
                        ag_catalog.agtype_access_operator(tgt.properties, '"entity_id"'::ag_catalog.agtype)::text
                    FROM "{schema}"."DIRECTED" e
                    LEFT JOIN "{schema}"."base" src ON src.id::text = e.start_id::text
                    LEFT JOIN "{schema}"."base" tgt ON tgt.id::text = e.end_id::text
                    '''
                )
                rows = cur.fetchall()
        finally:
            LightRAGManager.put_connection(conn)

        edges: List[EdgeInfo] = []
        for (
            edge_id,
            keywords,
            description,
            content,
            created_at,
            source_name,
            target_name,
        ) in rows:
            edges.append(
                EdgeInfo(
                    uuid=edge_id or f"edge_{graph_id}_{len(edges)}",
                    name=keywords or "",
                    fact=description or content or "",
                    source_node_uuid=source_name or "",
                    target_node_uuid=target_name or "",
                    source_node_name=source_name or None,
                    target_node_name=target_name or None,
                    created_at=created_at or None,
                )
            )
        return edges

    @property
    def llm(self) -> LLMClient:
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client

    def search_graph(
        self, graph_id: str, query: str, limit: int = 10, scope: str = "edges"
    ) -> SearchResult:
        """Graph search using local cached graph data."""
        logger.info(f"Graph search: graph_id={graph_id}, query={query[:50]}...")
        return self._local_search(graph_id, query, limit, scope)

    def _local_search(
        self, graph_id: str, query: str, limit: int = 10, scope: str = "edges"
    ) -> SearchResult:
        """Local keyword matching search as fallback."""
        logger.info(f"Using local search: query={query[:30]}...")

        facts = []
        edges_result = []
        nodes_result = []

        query_lower = query.lower()
        keywords = [
            w.strip()
            for w in query_lower.replace(",", " ").split()
            if len(w.strip()) > 1
        ]

        def match_score(text: str) -> int:
            if not text:
                return 0
            text_lower = text.lower()
            if query_lower in text_lower:
                return 100
            score = 0
            for keyword in keywords:
                if keyword in text_lower:
                    score += 10
            return score

        try:
            if scope in ["edges", "both"]:
                all_edges = self.get_all_edges(graph_id)
                scored_edges = []
                for edge in all_edges:
                    score = match_score(edge.fact) + match_score(edge.name)
                    if score > 0:
                        scored_edges.append((score, edge))
                scored_edges.sort(key=lambda x: x[0], reverse=True)
                for score, edge in scored_edges[:limit]:
                    if edge.fact:
                        facts.append(edge.fact)
                    edges_result.append(edge.to_dict())

            if scope in ["nodes", "both"]:
                all_nodes = self.get_all_nodes(graph_id)
                scored_nodes = []
                for node in all_nodes:
                    score = match_score(node.name) + match_score(node.summary)
                    if score > 0:
                        scored_nodes.append((score, node))
                scored_nodes.sort(key=lambda x: x[0], reverse=True)
                for score, node in scored_nodes[:limit]:
                    nodes_result.append(node.to_dict())
                    if node.summary:
                        facts.append(f"[{node.name}]: {node.summary}")

        except Exception as e:
            logger.error(f"Local search failed: {e}")

        return SearchResult(
            facts=facts,
            edges=edges_result,
            nodes=nodes_result,
            query=query,
            total_count=len(facts),
        )

    def get_all_nodes(self, graph_id: str) -> List[NodeInfo]:
        """Get all nodes of the graph."""
        logger.info(f"Get all nodes of graph {graph_id}...")

        if graph_id not in self._nodes_cache:
            self._nodes_cache[graph_id] = self._load_nodes_from_sql(graph_id)

        result = self._nodes_cache[graph_id]
        logger.info(f"Obtained {len(result)} nodes")
        return result

    def get_all_edges(
        self, graph_id: str, include_temporal: bool = True
    ) -> List[EdgeInfo]:
        """Get all edges of the graph."""
        logger.info(f"Get all edges of graph {graph_id}...")

        if graph_id not in self._edges_cache:
            self._edges_cache[graph_id] = self._load_edges_from_sql(graph_id)

        result = self._edges_cache[graph_id]
        logger.info(f"Obtained {len(result)} edges")
        return result

    def get_node_detail(
        self, node_uuid: str, graph_id: str = None
    ) -> Optional[NodeInfo]:
        """Get details of a single node by name."""
        if not graph_id:
            logger.warning("get_node_detail called without graph_id")
            return None

        try:
            for node in self.get_all_nodes(graph_id):
                if node.uuid == node_uuid or node.name == node_uuid:
                    return node
            return None
        except Exception as e:
            logger.error(f"Failed to get node detail: {e}")
            return None

    def get_node_edges(self, graph_id: str, node_uuid: str) -> List[EdgeInfo]:
        """Get all edges related to a node."""
        try:
            return [
                edge
                for edge in self.get_all_edges(graph_id)
                if edge.source_node_uuid == node_uuid
                or edge.target_node_uuid == node_uuid
            ]
        except Exception as e:
            logger.warning(f"Failed to get node edges: {e}")
            return []

    def get_entities_by_type(self, graph_id: str, entity_type: str) -> List[NodeInfo]:
        """Get entities by type."""
        all_nodes = self.get_all_nodes(graph_id)
        return [n for n in all_nodes if entity_type in n.labels]

    def get_entity_summary(self, graph_id: str, entity_name: str) -> Dict[str, Any]:
        """Get the relationship summary for an entity."""
        search_result = self.search_graph(
            graph_id=graph_id, query=entity_name, limit=20
        )

        all_nodes = self.get_all_nodes(graph_id)
        entity_node = None
        for node in all_nodes:
            if node.name.lower() == entity_name.lower():
                entity_node = node
                break

        related_edges = []
        if entity_node:
            related_edges = self.get_node_edges(graph_id, entity_node.uuid)

        return {
            "entity_name": entity_name,
            "entity_info": entity_node.to_dict() if entity_node else None,
            "related_facts": search_result.facts,
            "related_edges": [e.to_dict() for e in related_edges],
            "total_relations": len(related_edges),
        }

    def get_graph_statistics(self, graph_id: str) -> Dict[str, Any]:
        """Get graph statistics."""
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
            "relation_types": relation_types,
        }

    def get_simulation_context(
        self, graph_id: str, simulation_requirement: str, limit: int = 30
    ) -> Dict[str, Any]:
        """Get simulation-related contextual information."""
        search_result = self.search_graph(
            graph_id=graph_id, query=simulation_requirement, limit=limit
        )
        stats = self.get_graph_statistics(graph_id)
        all_nodes = self.get_all_nodes(graph_id)

        entities = []
        for node in all_nodes:
            custom_labels = [l for l in node.labels if l not in ["Entity", "Node"]]
            if custom_labels:
                entities.append(
                    {
                        "name": node.name,
                        "type": custom_labels[0],
                        "summary": node.summary,
                    }
                )

        return {
            "simulation_requirement": simulation_requirement,
            "related_facts": search_result.facts,
            "graph_statistics": stats,
            "entities": entities[:limit],
            "total_entities": len(entities),
        }

    # ========== Core search tools ==========

    def insight_forge(
        self,
        graph_id: str,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_sub_queries: int = 5,
    ) -> InsightForgeResult:
        """InsightForge - Deep Insight Search."""
        logger.info(f"InsightForge deep insight retrieval: {query[:50]}...")

        result = InsightForgeResult(
            query=query, simulation_requirement=simulation_requirement, sub_queries=[]
        )

        sub_queries = self._generate_sub_queries(
            query=query,
            simulation_requirement=simulation_requirement,
            report_context=report_context,
            max_queries=max_sub_queries,
        )
        result.sub_queries = sub_queries

        all_facts = []
        all_edges = []
        seen_facts = set()

        for sub_query in sub_queries:
            search_result = self.search_graph(
                graph_id=graph_id, query=sub_query, limit=15, scope="edges"
            )
            for fact in search_result.facts:
                if fact not in seen_facts:
                    all_facts.append(fact)
                    seen_facts.add(fact)
            all_edges.extend(search_result.edges)

        main_search = self.search_graph(
            graph_id=graph_id, query=query, limit=20, scope="edges"
        )
        for fact in main_search.facts:
            if fact not in seen_facts:
                all_facts.append(fact)
                seen_facts.add(fact)

        result.semantic_facts = all_facts
        result.total_facts = len(all_facts)

        # Extract entity names from edges and look them up
        entity_names = set()
        for edge_data in all_edges:
            if isinstance(edge_data, dict):
                src = edge_data.get("source_node_uuid", "")
                tgt = edge_data.get("target_node_uuid", "")
                if src:
                    entity_names.add(src)
                if tgt:
                    entity_names.add(tgt)

        entity_insights = []
        node_map = {}

        for name in entity_names:
            if not name:
                continue
            node = self.get_node_detail(name, graph_id=graph_id)
            if node:
                node_map[name] = node
                entity_type = next(
                    (l for l in node.labels if l not in ["Entity", "Node"]), "entity"
                )
                related_facts = [f for f in all_facts if node.name.lower() in f.lower()]
                entity_insights.append(
                    {
                        "uuid": node.uuid,
                        "name": node.name,
                        "type": entity_type,
                        "summary": node.summary,
                        "related_facts": related_facts,
                    }
                )

        result.entity_insights = entity_insights
        result.total_entities = len(entity_insights)

        relationship_chains = []
        for edge_data in all_edges:
            if isinstance(edge_data, dict):
                src = edge_data.get("source_node_uuid", "")
                tgt = edge_data.get("target_node_uuid", "")
                rel = edge_data.get("name", "")
                source_name = (
                    node_map.get(src, NodeInfo("", "", [], "", {})).name or src[:8]
                    if src
                    else ""
                )
                target_name = (
                    node_map.get(tgt, NodeInfo("", "", [], "", {})).name or tgt[:8]
                    if tgt
                    else ""
                )
                chain = f"{source_name} --[{rel}]--> {target_name}"
                if chain not in relationship_chains:
                    relationship_chains.append(chain)

        result.relationship_chains = relationship_chains
        result.total_relationships = len(relationship_chains)

        logger.info(
            f"InsightForge completed: {result.total_facts} facts, {result.total_entities} entities, {result.total_relationships} relationships"
        )
        return result

    def _generate_sub_queries(
        self,
        query: str,
        simulation_requirement: str,
        report_context: str = "",
        max_queries: int = 5,
    ) -> List[str]:
        """Use LLM to generate sub-queries."""
        system_prompt = """You are a professional problem analyzer. Your task is to decompose a complex problem into multiple sub-problems that can be independently observed in the simulated world.

Requirements:
1. Each sub-problem should be specific enough that relevant Agent behaviors or events can be found in the simulated world
2. Sub-questions should cover different dimensions of the original question (such as: who, what, why, how, when, where)
3. Sub-problems should be relevant to the simulation scenario
4. Return JSON format: {"sub_queries": ["Sub-question 1", "Sub-question 2", ...]}"""

        user_prompt = f"""Simulation requirement background:
{simulation_requirement}

{f"Report context: {report_context[:500]}" if report_context else ""}

Please break the following question into {max_queries} sub-questions:
{query}

Returns a list of subquestions in JSON format."""

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            sub_queries = response.get("sub_queries", [])
            return [str(sq) for sq in sub_queries[:max_queries]]
        except Exception as e:
            logger.warning(f"Failed to generate sub-queries: {e}")
            return [
                query,
                f"Key players in {query}",
                f"The causes and effects of {query}",
                f"The development process of {query}",
            ][:max_queries]

    def panorama_search(
        self, graph_id: str, query: str, include_expired: bool = True, limit: int = 50
    ) -> PanoramaResult:
        """PanoramaSearch - Breadth Search."""
        logger.info(f"PanoramaSearch breadth search: {query[:50]}...")

        result = PanoramaResult(query=query)

        all_nodes = self.get_all_nodes(graph_id)
        node_map = {n.uuid: n for n in all_nodes}
        result.all_nodes = all_nodes
        result.total_nodes = len(all_nodes)

        all_edges = self.get_all_edges(graph_id, include_temporal=True)
        result.all_edges = all_edges
        result.total_edges = len(all_edges)

        active_facts = []
        for edge in all_edges:
            if not edge.fact:
                continue
            active_facts.append(edge.fact)

        query_lower = query.lower()
        keywords = [
            w.strip()
            for w in query_lower.replace(",", " ").split()
            if len(w.strip()) > 1
        ]

        def relevance_score(fact: str) -> int:
            fact_lower = fact.lower()
            score = 0
            if query_lower in fact_lower:
                score += 100
            for kw in keywords:
                if kw in fact_lower:
                    score += 10
            return score

        active_facts.sort(key=relevance_score, reverse=True)
        result.active_facts = active_facts[:limit]
        result.historical_facts = []
        result.active_count = len(active_facts)
        result.historical_count = 0

        logger.info(f"PanoramaSearch completed: {result.active_count} facts found")
        return result

    def quick_search(self, graph_id: str, query: str, limit: int = 10) -> SearchResult:
        """QuickSearch - Simple search."""
        logger.info(f"QuickSearch simple search: {query[:50]}...")
        result = self.search_graph(
            graph_id=graph_id, query=query, limit=limit, scope="edges"
        )
        logger.info(f"QuickSearch completed: {result.total_count} results")
        return result

    def interview_agents(
        self,
        simulation_id: str,
        interview_requirement: str,
        simulation_requirement: str = "",
        max_agents: int = 5,
        custom_questions: List[str] = None,
    ) -> InterviewResult:
        """InterviewAgents - In-depth interview using real OASIS API."""
        from .simulation_runner import SimulationRunner

        logger.info(f"InterviewAgents: {interview_requirement[:50]}...")

        result = InterviewResult(
            interview_topic=interview_requirement,
            interview_questions=custom_questions or [],
        )

        profiles = self._load_agent_profiles(simulation_id)
        if not profiles:
            result.summary = "No interviewable Agent profile found"
            return result

        result.total_agents = len(profiles)

        selected_agents, selected_indices, selection_reasoning = (
            self._select_agents_for_interview(
                profiles=profiles,
                interview_requirement=interview_requirement,
                simulation_requirement=simulation_requirement,
                max_agents=max_agents,
            )
        )

        result.selected_agents = selected_agents
        result.selection_reasoning = selection_reasoning

        if not result.interview_questions:
            result.interview_questions = self._generate_interview_questions(
                interview_requirement=interview_requirement,
                simulation_requirement=simulation_requirement,
                selected_agents=selected_agents,
            )

        combined_prompt = "\n".join(
            [f"{i + 1}. {q}" for i, q in enumerate(result.interview_questions)]
        )

        INTERVIEW_PROMPT_PREFIX = (
            "You are being interviewed. Please incorporate your persona, all past memories and actions, "
            "Answer the following questions directly in plain text.\n"
            "Reply request:\n"
            "1. Answer directly in natural language, do not use any tools\n"
            "2. Do not return JSON format or tool call format\n"
            "3. Do not use Markdown titles (such as #, ##, ###)\n"
            "4. Answer one by one according to the question number. Each answer starts with 'Question X:' (X is the question number)\n"
            "5. Separate the answers to each question with a blank line\n"
            "6. Answers must be substantive and answer at least 2-3 sentences for each question\n\n"
        )
        optimized_prompt = f"{INTERVIEW_PROMPT_PREFIX}{combined_prompt}"

        try:
            interviews_request = []
            for agent_idx in selected_indices:
                interviews_request.append(
                    {"agent_id": agent_idx, "prompt": optimized_prompt}
                )

            api_result = SimulationRunner.interview_agents_batch(
                simulation_id=simulation_id,
                interviews=interviews_request,
                platform=None,
                timeout=180.0,
            )

            if not api_result.get("success", False):
                error_msg = api_result.get("error", "Unknown error")
                result.summary = f"Interview API call failed: {error_msg}."
                return result

            api_data = api_result.get("result", {})
            results_dict = (
                api_data.get("results", {}) if isinstance(api_data, dict) else {}
            )

            for i, agent_idx in enumerate(selected_indices):
                agent = selected_agents[i]
                agent_name = agent.get(
                    "realname", agent.get("username", f"Agent_{agent_idx}")
                )
                agent_role = agent.get("profession", "unknown")
                agent_bio = agent.get("bio", "")

                twitter_result = results_dict.get(f"twitter_{agent_idx}", {})
                reddit_result = results_dict.get(f"reddit_{agent_idx}", {})

                twitter_response = self._clean_tool_call_response(
                    twitter_result.get("response", "")
                )
                reddit_response = self._clean_tool_call_response(
                    reddit_result.get("response", "")
                )

                twitter_text = twitter_response if twitter_response else "(No reply)"
                reddit_text = reddit_response if reddit_response else "(No reply)"
                response_text = f"Twitter:\n{twitter_text}\n\nReddit:\n{reddit_text}"

                import re

                combined_responses = f"{twitter_response} {reddit_response}"
                clean_text = re.sub(r"#{1,6}\s+", "", combined_responses)
                clean_text = re.sub(r"\{[^}]*tool_name[^}]*\}", "", clean_text)

                sentences = re.split(r"[.!?]", clean_text)
                meaningful = [
                    s.strip() for s in sentences if 20 <= len(s.strip()) <= 150
                ]
                meaningful.sort(key=len, reverse=True)
                key_quotes = [s + "." for s in meaningful[:3]]

                interview = AgentInterview(
                    agent_name=agent_name,
                    agent_role=agent_role,
                    agent_bio=agent_bio[:1000],
                    question=combined_prompt,
                    response=response_text,
                    key_quotes=key_quotes[:5],
                )
                result.interviews.append(interview)

            result.interviewed_count = len(result.interviews)

        except ValueError as e:
            result.summary = f"Interview failed: {str(e)}."
            return result
        except Exception as e:
            logger.error(f"Interview API exception: {e}")
            result.summary = f"An error occurred during the interview: {str(e)}"
            return result

        if result.interviews:
            result.summary = self._generate_interview_summary(
                interviews=result.interviews,
                interview_requirement=interview_requirement,
            )

        return result

    @staticmethod
    def _clean_tool_call_response(response: str) -> str:
        if not response or not response.strip().startswith("{"):
            return response
        text = response.strip()
        if "tool_name" not in text[:80]:
            return response
        import re as _re

        try:
            data = json.loads(text)
            if isinstance(data, dict) and "arguments" in data:
                for key in ("content", "text", "body", "message", "reply"):
                    if key in data["arguments"]:
                        return str(data["arguments"][key])
        except (json.JSONDecodeError, KeyError, TypeError):
            match = _re.search(r'"content"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
            if match:
                return match.group(1).replace("\\n", "\n").replace('\\"', '"')
        return response

    def _load_agent_profiles(self, simulation_id: str) -> List[Dict[str, Any]]:
        import os
        import csv

        sim_dir = os.path.join(
            os.path.dirname(__file__), f"../../uploads/simulations/{simulation_id}"
        )

        profiles = []

        reddit_profile_path = os.path.join(sim_dir, "reddit_profiles.json")
        if os.path.exists(reddit_profile_path):
            try:
                with open(reddit_profile_path, "r", encoding="utf-8") as f:
                    profiles = json.load(f)
                return profiles
            except Exception as e:
                logger.warning(f"Failed to read reddit_profiles.json: {e}")

        twitter_profile_path = os.path.join(sim_dir, "twitter_profiles.csv")
        if os.path.exists(twitter_profile_path):
            try:
                with open(twitter_profile_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        profiles.append(
                            {
                                "realname": row.get("name", ""),
                                "username": row.get("username", ""),
                                "bio": row.get("description", ""),
                                "persona": row.get("user_char", ""),
                                "profession": "unknown",
                            }
                        )
                return profiles
            except Exception as e:
                logger.warning(f"Failed to read twitter_profiles.csv: {e}")

        return profiles

    def _select_agents_for_interview(
        self, profiles, interview_requirement, simulation_requirement, max_agents
    ):
        agent_summaries = []
        for i, profile in enumerate(profiles):
            agent_summaries.append(
                {
                    "index": i,
                    "name": profile.get(
                        "realname", profile.get("username", f"Agent_{i}")
                    ),
                    "profession": profile.get("profession", "unknown"),
                    "bio": profile.get("bio", "")[:200],
                    "interested_topics": profile.get("interested_topics", []),
                }
            )

        system_prompt = (
            "You are a professional interview planning expert. Select the most suitable interview objects.\n\n"
            "Return JSON format:\n"
            '{"selected_indices": [index list], "reasoning": "explanation"}'
        )

        agents_str = json.dumps(agent_summaries, ensure_ascii=False, indent=2)
        user_prompt = f"Interview requirements:\n{interview_requirement}\n\nSimulation background:\n{simulation_requirement or 'Not provided'}\n\nAgent list ({len(agent_summaries)}):\n{agents_str}\n\nSelect up to {max_agents} agents."

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )
            selected_indices = response.get("selected_indices", [])[:max_agents]
            reasoning = response.get("reasoning", "Auto-selected")
            selected_agents = []
            valid_indices = []
            for idx in selected_indices:
                if 0 <= idx < len(profiles):
                    selected_agents.append(profiles[idx])
                    valid_indices.append(idx)
            return selected_agents, valid_indices, reasoning
        except Exception as e:
            logger.warning(f"LLM agent selection failed: {e}")
            selected = profiles[:max_agents]
            indices = list(range(min(max_agents, len(profiles))))
            return selected, indices, "Default selection"

    def _generate_interview_questions(
        self, interview_requirement, simulation_requirement, selected_agents
    ):
        agent_roles = [a.get("profession", "unknown") for a in selected_agents]
        system_prompt = (
            "Generate 3-5 in-depth interview questions.\n"
            'Return JSON format: {"questions": ["Q1", "Q2", ...]}'
        )
        user_prompt = f"Interview requirement: {interview_requirement}\nBackground: {simulation_requirement or 'Not provided'}\nRoles: {', '.join(agent_roles)}"

        try:
            response = self.llm.chat_json(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.5,
            )
            return response.get(
                "questions", [f"What do you think about {interview_requirement}?"]
            )
        except Exception as e:
            return [
                f"What is your opinion about {interview_requirement}?",
                "How does this impact you?",
                "How should this be resolved?",
            ]

    def _generate_interview_summary(self, interviews, interview_requirement):
        if not interviews:
            return "No interviews completed"
        interview_texts = []
        for interview in interviews:
            interview_texts.append(
                f"Agent: {interview.agent_name}, Role: {interview.agent_role}\n{interview.response[:500]}"
            )

        system_prompt = (
            "Generate an interview summary. Extract main viewpoints, consensus and differences. "
            "Use plain text paragraphs. Control within 1000 words."
        )
        content_joined = "\n".join(interview_texts)
        user_prompt = f"Topic: {interview_requirement}\n\nContent:\n{content_joined}\n\nGenerate summary."

        try:
            return self.llm.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=800,
            )
        except Exception as e:
            return f"Interviewed {len(interviews)} agents: " + ", ".join(
                [i.agent_name for i in interviews]
            )


# Backward compatibility alias
ZepToolsService = GraphToolsService
