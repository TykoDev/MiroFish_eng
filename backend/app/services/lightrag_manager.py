"""
Central LightRAG instance management.

Manages LightRAG instances per graph_id (namespace), providing
PostgreSQL-backed knowledge graph construction, entity extraction,
and hybrid search.
"""

import os
import asyncio
import hashlib
import re
import threading
from typing import Dict, Optional, Iterable
from urllib.parse import urlparse

import numpy as np
import psycopg2
import psycopg2.pool

from lightrag import LightRAG
from lightrag.llm.openai import openai_complete_if_cache
from lightrag.utils import EmbeddingFunc
from openai import APIStatusError, RateLimitError

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger("mirofish.lightrag_manager")

OPENROUTER_FALLBACK_MODELS = [
    "google/gemma-3-12b-it:free",
    "google/gemma-3-4b-it:free",
    "openai/gpt-oss-20b:free",
]


class LightRAGManager:
    """Central singleton that manages LightRAG instances per graph_id."""

    _instances: Dict[str, LightRAG] = {}
    _db_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
    _instance_locks: Dict[str, threading.Lock] = {}
    _locks_guard = threading.Lock()

    @classmethod
    def _get_instance_lock(cls, graph_id: str) -> threading.Lock:
        with cls._locks_guard:
            lock = cls._instance_locks.get(graph_id)
            if lock is None:
                lock = threading.Lock()
                cls._instance_locks[graph_id] = lock
            return lock

    @classmethod
    def _get_db_pool(cls) -> psycopg2.pool.ThreadedConnectionPool:
        """Get or create a database connection pool."""
        if cls._db_pool is None or cls._db_pool.closed:
            cls._db_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=2, maxconn=10, dsn=Config.DATABASE_URL
            )
        return cls._db_pool

    @classmethod
    def get_connection(cls):
        """Get a database connection from the pool."""
        return cls._get_db_pool().getconn()

    @classmethod
    def put_connection(cls, conn):
        """Return a connection to the pool."""
        cls._get_db_pool().putconn(conn)

    @classmethod
    async def get_or_create(cls, graph_id: str) -> LightRAG:
        """Get cached LightRAG instance or create new one for this graph namespace."""
        if graph_id in cls._instances:
            return cls._instances[graph_id]

        lock = cls._get_instance_lock(graph_id)
        with lock:
            if graph_id in cls._instances:
                return cls._instances[graph_id]
            return await cls.create_new(graph_id)

    @classmethod
    async def create_new(cls, graph_id: str) -> LightRAG:
        """Create fresh LightRAG instance for a graph build."""
        if graph_id in cls._instances:
            del cls._instances[graph_id]

        instance = cls._build_instance(graph_id)
        await instance.initialize_storages()
        cls._instances[graph_id] = instance
        logger.info(f"Created LightRAG instance for graph: {graph_id}")
        return instance

    @classmethod
    async def delete(cls, graph_id: str):
        """Delete all data for a graph namespace from PostgreSQL."""
        if graph_id in cls._instances:
            del cls._instances[graph_id]

        conn = cls.get_connection()
        try:
            with conn.cursor() as cur:
                # Delete from LightRAG tables by workspace
                for table in [
                    "lightrag_doc_chunks",
                    "lightrag_doc_full",
                    "lightrag_vdb_entity",
                    "lightrag_vdb_relation",
                    "lightrag_vdb_chunks",
                    "lightrag_graph_nodes",
                    "lightrag_graph_edges",
                    "lightrag_llm_cache",
                    "lightrag_key_value",
                ]:
                    try:
                        cur.execute(
                            f"DELETE FROM {table} WHERE workspace = %s", (graph_id,)
                        )
                    except psycopg2.Error:
                        conn.rollback()
                        continue

                # Delete from custom ontology table
                cur.execute(
                    "DELETE FROM mirofish_ontology WHERE graph_id = %s", (graph_id,)
                )
                conn.commit()
            logger.info(f"Deleted all data for graph: {graph_id}")
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to delete graph {graph_id}: {e}")
            raise
        finally:
            cls.put_connection(conn)

    @classmethod
    def _build_instance(cls, graph_id: str) -> LightRAG:
        """Configure LightRAG with PostgreSQL backend, embedding model, LLM."""
        working_dir = os.path.join(Config.UPLOAD_FOLDER, "lightrag_work", graph_id)
        os.makedirs(working_dir, exist_ok=True)
        cls._apply_postgres_env(graph_id)

        rag = LightRAG(
            working_dir=working_dir,
            workspace=graph_id,
            chunk_token_size=8000,
            chunk_overlap_token_size=400,
            # LLM config — uses same OpenAI-compatible API as the rest of MiroFish
            llm_model_func=cls._complete_with_fallback,
            llm_model_name=Config.LLM_MODEL_NAME,
            llm_model_kwargs={
                "api_key": Config.LLM_API_KEY,
                "base_url": Config.LLM_BASE_URL,
            },
            # Embedding config
            embedding_func=cls._build_embedding_func(),
            # PostgreSQL storage
            kv_storage="PGKVStorage",
            vector_storage="PGVectorStorage",
            graph_storage="PGGraphStorage",
            doc_status_storage="PGDocStatusStorage",
            vector_db_storage_cls_kwargs={
                "cosine_better_than_threshold": 0.2,
            },
        )
        return rag

    @classmethod
    def _build_embedding_func(cls) -> EmbeddingFunc:
        """Build a local embedding function compatible with the installed LightRAG API."""

        async def embedding_func(texts):
            return cls._local_hash_embeddings(texts)

        return EmbeddingFunc(
            embedding_dim=Config.EMBEDDING_DIMENSIONS,
            func=embedding_func,
            max_token_size=8192,
            model_name="local-hash-embedding",
        )

    @classmethod
    async def _complete_with_fallback(
        cls,
        prompt: str,
        system_prompt=None,
        history_messages=None,
        **kwargs,
    ):
        """Run a LightRAG completion with model fallback for OpenRouter free tiers."""
        last_error = None
        primary_model = kwargs.pop("model", Config.LLM_MODEL_NAME)

        if history_messages is None:
            history_messages = []

        for candidate in cls._iter_model_candidates(primary_model):
            try:
                return await openai_complete_if_cache(
                    model=candidate,
                    prompt=prompt,
                    system_prompt=system_prompt,
                    history_messages=history_messages,
                    **kwargs,
                )
            except Exception as exc:
                last_error = exc
                if not cls._should_fallback_model(exc):
                    raise
                logger.warning(
                    "LightRAG completion fallback from %s due to %s",
                    candidate,
                    exc,
                )

        if last_error is not None:
            raise last_error
        raise RuntimeError("No LLM candidate models were available")

    @classmethod
    def _iter_model_candidates(cls, primary_model: str) -> Iterable[str]:
        seen = set()
        for model in [primary_model, *OPENROUTER_FALLBACK_MODELS]:
            if model and model not in seen:
                seen.add(model)
                yield model

    @classmethod
    def _should_fallback_model(cls, exc: Exception) -> bool:
        if isinstance(exc, RateLimitError):
            return True
        if isinstance(exc, APIStatusError):
            return exc.status_code in {402, 429}

        message = str(exc).lower()
        return "insufficient credits" in message or "rate-limited upstream" in message

    @classmethod
    def _local_hash_embeddings(cls, texts):
        """Generate deterministic local embeddings without external API calls."""
        if isinstance(texts, str):
            texts = [texts]

        dim = Config.EMBEDDING_DIMENSIONS
        vectors = []

        for text in texts:
            vector = np.zeros(dim, dtype=np.float32)
            tokens = re.findall(r"[A-Za-z0-9_]+", (text or "").lower())

            if not tokens:
                tokens = ["empty"]

            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                for offset in range(0, 16, 4):
                    index = int.from_bytes(digest[offset : offset + 2], "big") % dim
                    sign = 1.0 if digest[offset + 2] % 2 == 0 else -1.0
                    weight = 1.0 + (digest[offset + 3] / 255.0)
                    vector[index] += sign * weight

            norm = float(np.linalg.norm(vector))
            if norm > 0:
                vector /= norm
            vectors.append(vector)

        return np.vstack(vectors)

    @classmethod
    def _apply_postgres_env(cls, graph_id: str):
        """Populate LightRAG's PostgreSQL environment variables from DATABASE_URL."""
        os.environ["POSTGRES_HOST"] = cls._parse_db_host()
        os.environ["POSTGRES_PORT"] = str(cls._parse_db_port())
        os.environ["POSTGRES_USER"] = cls._parse_db_user()
        os.environ["POSTGRES_PASSWORD"] = cls._parse_db_password()
        os.environ["POSTGRES_DATABASE"] = cls._parse_db_name()
        os.environ.pop("POSTGRES_WORKSPACE", None)

    @classmethod
    def _parse_db_host(cls) -> str:
        """Extract host from DATABASE_URL."""
        return cls._parse_db_component("host", "localhost")

    @classmethod
    def _parse_db_port(cls) -> int:
        """Extract port from DATABASE_URL."""
        return int(cls._parse_db_component("port", "5432"))

    @classmethod
    def _parse_db_user(cls) -> str:
        """Extract user from DATABASE_URL."""
        return cls._parse_db_component("user", "mirofish")

    @classmethod
    def _parse_db_password(cls) -> str:
        """Extract password from DATABASE_URL."""
        return cls._parse_db_component("password", "mirofish_secret")

    @classmethod
    def _parse_db_name(cls) -> str:
        """Extract database name from DATABASE_URL."""
        return cls._parse_db_component("dbname", "mirofish")

    @classmethod
    def _parse_db_component(cls, component: str, default: str) -> str:
        """Parse a component from the DATABASE_URL."""
        url = Config.DATABASE_URL or ""
        if not url:
            return default

        # postgresql://user:password@host:port/dbname
        try:
            parsed = urlparse(url)
            if component == "host":
                return parsed.hostname or default
            elif component == "port":
                return str(parsed.port or default)
            elif component == "user":
                return parsed.username or default
            elif component == "password":
                return parsed.password or default
            elif component == "dbname":
                return parsed.path.lstrip("/") or default
        except Exception:
            pass
        return default

    @classmethod
    def store_ontology(cls, graph_id: str, ontology_json: dict):
        """Store ontology JSON in PostgreSQL for later use."""
        import json

        conn = cls.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO mirofish_ontology (graph_id, ontology_json)
                       VALUES (%s, %s)
                       ON CONFLICT (graph_id) DO UPDATE SET ontology_json = EXCLUDED.ontology_json""",
                    (graph_id, json.dumps(ontology_json)),
                )
                conn.commit()
        finally:
            cls.put_connection(conn)

    @classmethod
    def get_ontology(cls, graph_id: str) -> Optional[dict]:
        """Retrieve ontology JSON from PostgreSQL."""
        import json

        conn = cls.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT ontology_json FROM mirofish_ontology WHERE graph_id = %s",
                    (graph_id,),
                )
                row = cur.fetchone()
                if row:
                    return row[0] if isinstance(row[0], dict) else json.loads(row[0])
                return None
        finally:
            cls.put_connection(conn)
