"""
Graph construction service
Interface 2: Build knowledge graph using LightRAG + PostgreSQL
"""

import os
import uuid
import time
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass

from ..config import Config
from ..models.task import TaskManager, TaskStatus
from ..utils.async_bridge import run_async
from .lightrag_manager import LightRAGManager
from .text_processor import TextProcessor


@dataclass
class GraphInfo:
    """Chart information"""
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


class GraphBuilderService:
    """
    Graph construction service
    Responsible for building knowledge graph via LightRAG + PostgreSQL
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize graph builder. api_key parameter kept for backward compatibility but unused."""
        if not Config.DATABASE_URL:
            raise ValueError("DATABASE_URL not configured")
        self.task_manager = TaskManager()

    def build_graph_async(
        self,
        text: str,
        ontology: Dict[str, Any],
        graph_name: str = "MiroFish Graph",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        batch_size: int = 3
    ) -> str:
        """
        Build a graph asynchronously

        Args:
            text: input text
            ontology: ontology definition (output from interface 1)
            graph_name: graph name
            chunk_size: text block size
            chunk_overlap: chunk overlap size
            batch_size: Number of blocks sent in each batch

        Returns:
            Task ID
        """
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
            args=(task_id, text, ontology, graph_name, chunk_size, chunk_overlap, batch_size)
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
        chunk_overlap: int,
        batch_size: int
    ):
        """Graph construction work thread"""
        try:
            self.task_manager.update_task(
                task_id,
                status=TaskStatus.PROCESSING,
                progress=5,
                message="Start building the map..."
            )

            # 1. Create a graph
            graph_id = self.create_graph(graph_name)
            self.task_manager.update_task(
                task_id,
                progress=10,
                message=f"Graph has been created: {graph_id}"
            )

            # 2. Set the ontology
            self.set_ontology(graph_id, ontology)
            self.task_manager.update_task(
                task_id,
                progress=15,
                message="Ontology has been set"
            )

            # 3. Text chunking
            chunks = TextProcessor.split_text(text, chunk_size, chunk_overlap)
            total_chunks = len(chunks)
            self.task_manager.update_task(
                task_id,
                progress=20,
                message=f"The text has been split into {total_chunks} chunks"
            )

            # 4. Insert data in batches (LightRAG processes synchronously, no episode polling needed)
            self.add_text_batches(
                graph_id, chunks, batch_size,
                lambda msg, prog: self.task_manager.update_task(
                    task_id,
                    progress=20 + int(prog * 0.7),  # 20-90%
                    message=msg
                )
            )

            # 5. Get graph information
            self.task_manager.update_task(
                task_id,
                progress=90,
                message="Get map information..."
            )

            graph_info = self._get_graph_info(graph_id)

            # Finish
            self.task_manager.complete_task(task_id, {
                "graph_id": graph_id,
                "graph_info": graph_info.to_dict(),
                "chunks_processed": total_chunks,
            })

        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.task_manager.fail_task(task_id, error_msg)

    def create_graph(self, name: str) -> str:
        """Create a new graph namespace"""
        graph_id = f"mirofish_{uuid.uuid4().hex[:16]}"
        run_async(LightRAGManager.create_new(graph_id))
        return graph_id

    def set_ontology(self, graph_id: str, ontology: Dict[str, Any]):
        """Store ontology in PostgreSQL for later use."""
        LightRAGManager.store_ontology(graph_id, ontology)

    def add_text_batches(
        self,
        graph_id: str,
        chunks: List[str],
        batch_size: int = 3,
        progress_callback: Optional[Callable] = None
    ) -> List[str]:
        """Add text to the graph in batches via LightRAG ainsert."""
        total_chunks = len(chunks)
        rag = run_async(LightRAGManager.get_or_create(graph_id))

        for i in range(0, total_chunks, batch_size):
            batch_chunks = chunks[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size

            if progress_callback:
                progress = (i + len(batch_chunks)) / total_chunks
                progress_callback(
                    f"Send {batch_num}/{total_batches} batch data ({len(batch_chunks)} chunks)...",
                    progress
                )

            # Insert batch as combined text
            combined = "\n\n".join(batch_chunks)
            try:
                run_async(rag.ainsert(combined))
                time.sleep(0.5)
            except Exception as e:
                if progress_callback:
                    progress_callback(f"Batch {batch_num} failed to send: {str(e)}", 0)
                raise

        return []  # No episode UUIDs in LightRAG

    def _get_graph_info(self, graph_id: str) -> GraphInfo:
        """Get graph information from PostgreSQL."""
        from .lightrag_entity_reader import EntityReader
        reader = EntityReader()

        nodes = reader.get_all_nodes(graph_id)
        edges = reader.get_all_edges(graph_id)

        entity_types = set()
        for node in nodes:
            for label in node.get("labels", []):
                if label not in ["Entity", "Node"]:
                    entity_types.add(label)

        return GraphInfo(
            graph_id=graph_id,
            node_count=len(nodes),
            edge_count=len(edges),
            entity_types=list(entity_types)
        )

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """
        Get complete graph data (including detailed information)

        Args:
            graph_id: graph ID

        Returns:
            A dictionary containing nodes and edges
        """
        from .lightrag_entity_reader import EntityReader
        reader = EntityReader()

        nodes = reader.get_all_nodes(graph_id)
        edges = reader.get_all_edges(graph_id)

        # Create node mapping to get node name
        node_map = {}
        for node in nodes:
            node_map[node["uuid"]] = node.get("name", "")

        nodes_data = []
        for node in nodes:
            nodes_data.append({
                "uuid": node["uuid"],
                "name": node["name"],
                "labels": node.get("labels", []),
                "summary": node.get("summary", ""),
                "attributes": node.get("attributes", {}),
                "created_at": None,
            })

        edges_data = []
        for edge in edges:
            edges_data.append({
                "uuid": edge["uuid"],
                "name": edge.get("name", ""),
                "fact": edge.get("fact", ""),
                "fact_type": edge.get("name", ""),
                "source_node_uuid": edge["source_node_uuid"],
                "target_node_uuid": edge["target_node_uuid"],
                "source_node_name": node_map.get(edge["source_node_uuid"], ""),
                "target_node_name": node_map.get(edge["target_node_uuid"], ""),
                "attributes": edge.get("attributes", {}),
                "created_at": None,
                "valid_at": None,
                "invalid_at": None,
                "expired_at": None,
                "episodes": [],
            })

        return {
            "graph_id": graph_id,
            "nodes": nodes_data,
            "edges": edges_data,
            "node_count": len(nodes_data),
            "edge_count": len(edges_data),
        }

    def delete_graph(self, graph_id: str):
        """Delete graph"""
        run_async(LightRAGManager.delete(graph_id))
