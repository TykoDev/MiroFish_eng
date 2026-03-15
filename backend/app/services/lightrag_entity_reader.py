"""
LightRAG entity reading and filtering service.

Replaces ZepEntityReader — reads entities and relationships from
LightRAG's PostgreSQL tables instead of Zep Cloud API.
"""

import time
from typing import Dict, Any, List, Optional, Set, TypeVar
from dataclasses import dataclass, field

from ..config import Config
from ..utils.logger import get_logger
from .lightrag_manager import LightRAGManager
from .lightrag_tools import GraphToolsService

logger = get_logger("mirofish.lightrag_entity_reader")

T = TypeVar("T")


@dataclass
class EntityNode:
    """Entity node data structure"""

    uuid: str
    name: str
    labels: List[str]
    summary: str
    attributes: Dict[str, Any]
    related_edges: List[Dict[str, Any]] = field(default_factory=list)
    related_nodes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uuid": self.uuid,
            "name": self.name,
            "labels": self.labels,
            "summary": self.summary,
            "attributes": self.attributes,
            "related_edges": self.related_edges,
            "related_nodes": self.related_nodes,
        }

    def get_entity_type(self) -> Optional[str]:
        """Get the entity type (excluding the default Entity tag)"""
        for label in self.labels:
            if label not in ["Entity", "Node"]:
                return label
        return None


@dataclass
class FilteredEntities:
    """Filtered entity collection"""

    entities: List[EntityNode]
    entity_types: Set[str]
    total_count: int
    filtered_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities],
            "entity_types": list(self.entity_types),
            "total_count": self.total_count,
            "filtered_count": self.filtered_count,
        }


class EntityReader:
    """
    LightRAG entity reading and filtering service.

    Main functions:
    1. Read all entities from LightRAG's PostgreSQL tables
    2. Filter out entities that match predefined entity types
    3. Get related edges and associated entities for each entity
    """

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or Config.DATABASE_URL
        if not self.database_url:
            raise ValueError("DATABASE_URL not configured")

    def _get_connection(self):
        """Get a database connection from the pool."""
        return LightRAGManager.get_connection()

    def _put_connection(self, conn):
        """Return a connection to the pool."""
        LightRAGManager.put_connection(conn)

    def get_all_nodes(self, graph_id: str) -> List[Dict[str, Any]]:
        """Get all entities for a graph namespace."""
        logger.info(f"Get all nodes of graph {graph_id}...")

        tools = GraphToolsService()
        nodes_data = [node.to_dict() for node in tools.get_all_nodes(graph_id)]

        logger.info(f"Get {len(nodes_data)} nodes in total")
        return nodes_data

    def get_all_edges(self, graph_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for a graph namespace."""
        logger.info(f"Get all edges of graph {graph_id}...")

        tools = GraphToolsService()
        edges_data = []
        for edge in tools.get_all_edges(graph_id):
            edges_data.append(
                {
                    "uuid": edge.uuid,
                    "name": edge.name,
                    "fact": edge.fact,
                    "source_node_uuid": edge.source_node_uuid,
                    "target_node_uuid": edge.target_node_uuid,
                    "attributes": {
                        "weight": 1.0,
                        "keywords": edge.name,
                    },
                }
            )

        logger.info(f"Get {len(edges_data)} edges in total")
        return edges_data

    def get_node_edges(self, graph_id: str, node_name: str) -> List[Dict[str, Any]]:
        """Get all edges related to a specific node."""
        try:
            rows = [
                edge
                for edge in self.get_all_edges(graph_id)
                if edge["source_node_uuid"] == node_name
                or edge["target_node_uuid"] == node_name
            ]

            edges_data = []
            for i, row in enumerate(rows):
                edges_data.append(
                    {
                        "uuid": f"edge_{node_name}_{i}",
                        "name": row.get("name") or "",
                        "fact": row.get("fact") or "",
                        "source_node_uuid": row.get("source_node_uuid") or "",
                        "target_node_uuid": row.get("target_node_uuid") or "",
                        "attributes": {
                            "weight": row.get("attributes", {}).get("weight", 1.0)
                        },
                    }
                )

            return edges_data
        except Exception as e:
            logger.warning(f"Failed to get edges for node {node_name}: {e}")
            return []

    def filter_defined_entities(
        self,
        graph_id: str,
        defined_entity_types: Optional[List[str]] = None,
        enrich_with_edges: bool = True,
    ) -> FilteredEntities:
        """Filter entities that match predefined entity types."""
        logger.info(f"Start filtering entities of graph {graph_id}...")

        all_nodes = self.get_all_nodes(graph_id)
        total_count = len(all_nodes)

        all_edges = self.get_all_edges(graph_id) if enrich_with_edges else []

        node_map = {n["uuid"]: n for n in all_nodes}

        filtered_entities = []
        entity_types_found = set()

        for node in all_nodes:
            labels = node.get("labels", [])
            custom_labels = [l for l in labels if l not in ["Entity", "Node"]]

            if not custom_labels:
                continue

            if defined_entity_types:
                matching_labels = [
                    l for l in custom_labels if l in defined_entity_types
                ]
                if not matching_labels:
                    continue
                entity_type = matching_labels[0]
            else:
                entity_type = custom_labels[0]

            entity_types_found.add(entity_type)

            entity = EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=labels,
                summary=node["summary"],
                attributes=node["attributes"],
            )

            if enrich_with_edges:
                related_edges = []
                related_node_uuids = set()

                for edge in all_edges:
                    if edge["source_node_uuid"] == node["uuid"]:
                        related_edges.append(
                            {
                                "direction": "outgoing",
                                "edge_name": edge["name"],
                                "fact": edge["fact"],
                                "target_node_uuid": edge["target_node_uuid"],
                            }
                        )
                        related_node_uuids.add(edge["target_node_uuid"])
                    elif edge["target_node_uuid"] == node["uuid"]:
                        related_edges.append(
                            {
                                "direction": "incoming",
                                "edge_name": edge["name"],
                                "fact": edge["fact"],
                                "source_node_uuid": edge["source_node_uuid"],
                            }
                        )
                        related_node_uuids.add(edge["source_node_uuid"])

                entity.related_edges = related_edges

                related_nodes = []
                for related_uuid in related_node_uuids:
                    if related_uuid in node_map:
                        related_node = node_map[related_uuid]
                        related_nodes.append(
                            {
                                "uuid": related_node["uuid"],
                                "name": related_node["name"],
                                "labels": related_node["labels"],
                                "summary": related_node.get("summary", ""),
                            }
                        )

                entity.related_nodes = related_nodes

            filtered_entities.append(entity)

        logger.info(
            f"Filtering completed: total nodes {total_count}, "
            f"meeting conditions {len(filtered_entities)}, "
            f"Entity type: {entity_types_found}"
        )

        return FilteredEntities(
            entities=filtered_entities,
            entity_types=entity_types_found,
            total_count=total_count,
            filtered_count=len(filtered_entities),
        )

    def get_entity_with_context(
        self, graph_id: str, entity_uuid: str
    ) -> Optional[EntityNode]:
        """Get a single entity and its complete context."""
        try:
            all_nodes = self.get_all_nodes(graph_id)
            node_map = {n["uuid"]: n for n in all_nodes}

            node = node_map.get(entity_uuid)
            if not node:
                return None

            edges = self.get_node_edges(graph_id, entity_uuid)

            related_edges = []
            related_node_uuids = set()

            for edge in edges:
                if edge["source_node_uuid"] == entity_uuid:
                    related_edges.append(
                        {
                            "direction": "outgoing",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "target_node_uuid": edge["target_node_uuid"],
                        }
                    )
                    related_node_uuids.add(edge["target_node_uuid"])
                else:
                    related_edges.append(
                        {
                            "direction": "incoming",
                            "edge_name": edge["name"],
                            "fact": edge["fact"],
                            "source_node_uuid": edge["source_node_uuid"],
                        }
                    )
                    related_node_uuids.add(edge["source_node_uuid"])

            related_nodes = []
            for related_uuid in related_node_uuids:
                if related_uuid in node_map:
                    rn = node_map[related_uuid]
                    related_nodes.append(
                        {
                            "uuid": rn["uuid"],
                            "name": rn["name"],
                            "labels": rn["labels"],
                            "summary": rn.get("summary", ""),
                        }
                    )

            return EntityNode(
                uuid=node["uuid"],
                name=node["name"],
                labels=node["labels"],
                summary=node["summary"],
                attributes=node["attributes"],
                related_edges=related_edges,
                related_nodes=related_nodes,
            )

        except Exception as e:
            logger.error(f"Failed to get entity {entity_uuid}: {e}")
            return None

    def get_entities_by_type(
        self, graph_id: str, entity_type: str, enrich_with_edges: bool = True
    ) -> List[EntityNode]:
        """Get all entities of the specified type."""
        result = self.filter_defined_entities(
            graph_id=graph_id,
            defined_entity_types=[entity_type],
            enrich_with_edges=enrich_with_edges,
        )
        return result.entities


# Backward compatibility alias
ZepEntityReader = EntityReader
