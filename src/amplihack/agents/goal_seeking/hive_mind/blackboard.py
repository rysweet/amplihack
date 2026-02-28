"""Shared Blackboard Memory for Multi-Agent Hive Mind (Experiment 1).

Philosophy:
- Single responsibility: Cross-agent knowledge sharing via a shared Kuzu graph table
- Extends the existing per-agent memory model with a shared namespace
- Content-hash deduplication prevents redundant storage
- Each fact records its source_agent_id for provenance
- Uses the REAL Kuzu backend from amplihack-memory-lib

Public API:
    HiveMemoryStore: Low-level shared fact CRUD on a dedicated Kuzu HiveMemory table
    HiveMemoryBridge: Bridges an agent's local memory to the shared hive
    HiveRetrieval: Retrieval strategy that queries shared memory
    MultiAgentHive: Registry + coordinator for agents participating in the hive
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import kuzu

from ._utils import content_hash

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class SharedFact:
    """A fact stored in the shared hive memory.

    Attributes:
        fact_id: Unique identifier for this shared fact.
        content: The factual content text.
        concept: Topic or concept this fact belongs to.
        source_agent_id: ID of the agent that originally stored this fact.
        confidence: Confidence score (0.0-1.0).
        tags: Categorisation tags.
        content_hash: SHA-256 hash of content for deduplication.
        created_at: When the fact was stored.
    """

    fact_id: str
    content: str
    concept: str
    source_agent_id: str
    confidence: float
    tags: list[str] = field(default_factory=list)
    content_hash: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "fact_id": self.fact_id,
            "content": self.content,
            "concept": self.concept,
            "source_agent_id": self.source_agent_id,
            "confidence": self.confidence,
            "tags": self.tags,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat(),
        }


def _content_hash(content: str) -> str:
    """Compute SHA-256 hash of content for dedup.

    Delegates to the shared content_hash in _utils for consistency.
    """
    return content_hash(content)


def _new_id(prefix: str = "hive") -> str:
    """Generate a short unique id."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _ts_now() -> int:
    """Current Unix timestamp as integer."""
    return int(time.time())


# ---------------------------------------------------------------------------
# HiveMemoryStore
# ---------------------------------------------------------------------------


class HiveMemoryStore:
    """Low-level shared fact storage backed by a Kuzu HiveMemory node table.

    Unlike per-agent ExperienceStore which filters by agent_name, this store
    has NO agent filter on reads -- all facts are shared across agents.
    The source_agent_id column records provenance.

    Args:
        db_path: Path to the shared Kuzu database directory.

    Example:
        >>> store = HiveMemoryStore(Path("/tmp/hive_db"))
        >>> fid = store.store_shared_fact("Python uses indentation", "agent_a", 0.9, ["python"])
        >>> results = store.query_shared_facts("indentation")
        >>> assert len(results) >= 1
    """

    _SCHEMA_DDL = """
        CREATE NODE TABLE IF NOT EXISTS HiveMemory(
            fact_id STRING,
            content STRING,
            concept STRING,
            source_agent_id STRING,
            confidence DOUBLE,
            tags STRING,
            content_hash STRING,
            created_at INT64,
            PRIMARY KEY(fact_id)
        )
    """

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._db = kuzu.Database(str(self.db_path))
        self._conn = kuzu.Connection(self._db)
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Create the HiveMemory table if it does not exist."""
        try:
            self._conn.execute(self._SCHEMA_DDL)
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise

    def store_shared_fact(
        self,
        fact: str,
        source_agent_id: str,
        confidence: float = 0.9,
        tags: list[str] | None = None,
        concept: str = "",
    ) -> str:
        """Store a fact in the shared hive memory.

        Deduplicates by content hash. If a fact with the same content already
        exists, returns the existing fact_id instead of creating a duplicate.

        Args:
            fact: The factual content text.
            source_agent_id: ID of the contributing agent.
            confidence: Confidence score (0.0-1.0).
            tags: Optional categorisation tags.
            concept: Optional topic/concept label.

        Returns:
            fact_id of the stored (or existing) fact.
        """
        if not fact or not fact.strip():
            raise ValueError("fact cannot be empty")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")

        chash = _content_hash(fact)

        # Check for duplicate
        existing = self._find_by_hash(chash)
        if existing:
            logger.debug("Dedup hit: fact already exists as %s", existing)
            return existing

        fact_id = _new_id("hive")
        tags_json = json.dumps(tags) if tags else "[]"

        self._conn.execute(
            """
            CREATE (:HiveMemory {
                fact_id: $fid,
                content: $cnt,
                concept: $con,
                source_agent_id: $src,
                confidence: $conf,
                tags: $tags,
                content_hash: $chash,
                created_at: $ts
            })
            """,
            {
                "fid": fact_id,
                "cnt": fact.strip(),
                "con": concept.strip(),
                "src": source_agent_id,
                "conf": confidence,
                "tags": tags_json,
                "chash": chash,
                "ts": _ts_now(),
            },
        )
        return fact_id

    def query_shared_facts(
        self,
        query: str,
        limit: int = 50,
        min_confidence: float = 0.0,
    ) -> list[SharedFact]:
        """Retrieve shared facts matching a keyword query.

        No agent_id filter -- searches across ALL agents' contributions.

        Args:
            query: Search keywords (matched via CONTAINS on content and concept).
            limit: Maximum results to return.
            min_confidence: Minimum confidence threshold.

        Returns:
            List of SharedFact ordered by confidence descending.
        """
        if not query or not query.strip():
            return self.get_all_shared_facts(limit=limit)

        keywords = [w.strip() for w in query.split() if w.strip()]
        if not keywords:
            return self.get_all_shared_facts(limit=limit)

        conditions = []
        params: dict[str, Any] = {"minc": min_confidence, "lim": limit}
        for i, kw in enumerate(keywords[:6]):
            pname = f"kw{i}"
            conditions.append(
                f"(lower(h.content) CONTAINS lower(${pname}) "
                f"OR lower(h.concept) CONTAINS lower(${pname}))"
            )
            params[pname] = kw

        where_kw = " OR ".join(conditions)
        result = self._conn.execute(
            f"""
            MATCH (h:HiveMemory)
            WHERE h.confidence >= $minc
              AND ({where_kw})
            RETURN h.fact_id, h.content, h.concept, h.source_agent_id,
                   h.confidence, h.tags, h.content_hash, h.created_at
            ORDER BY h.confidence DESC
            LIMIT $lim
            """,
            params,
        )
        return self._rows_to_shared_facts(result)

    def get_shared_facts_by_topic(
        self,
        topic: str,
        limit: int = 50,
    ) -> list[SharedFact]:
        """Retrieve shared facts filtered by concept/topic.

        Args:
            topic: Topic string (case-insensitive CONTAINS match on concept).
            limit: Maximum results.

        Returns:
            List of SharedFact matching the topic.
        """
        if not topic or not topic.strip():
            return []

        result = self._conn.execute(
            """
            MATCH (h:HiveMemory)
            WHERE lower(h.concept) CONTAINS lower($topic)
            RETURN h.fact_id, h.content, h.concept, h.source_agent_id,
                   h.confidence, h.tags, h.content_hash, h.created_at
            ORDER BY h.confidence DESC
            LIMIT $lim
            """,
            {"topic": topic.strip(), "lim": limit},
        )
        return self._rows_to_shared_facts(result)

    def get_all_shared_facts(self, limit: int = 500) -> list[SharedFact]:
        """Retrieve all shared facts.

        Args:
            limit: Maximum facts to return.

        Returns:
            List of all SharedFact ordered by confidence descending.
        """
        result = self._conn.execute(
            """
            MATCH (h:HiveMemory)
            RETURN h.fact_id, h.content, h.concept, h.source_agent_id,
                   h.confidence, h.tags, h.content_hash, h.created_at
            ORDER BY h.confidence DESC
            LIMIT $lim
            """,
            {"lim": limit},
        )
        return self._rows_to_shared_facts(result)

    def get_fact_count(self) -> int:
        """Return the total number of facts in the hive."""
        result = self._conn.execute("MATCH (h:HiveMemory) RETURN count(h)")
        if result.has_next():
            return int(result.get_next()[0])
        return 0

    def _find_by_hash(self, chash: str) -> str | None:
        """Find an existing fact by content hash. Returns fact_id or None."""
        result = self._conn.execute(
            """
            MATCH (h:HiveMemory)
            WHERE h.content_hash = $chash
            RETURN h.fact_id
            LIMIT 1
            """,
            {"chash": chash},
        )
        if result.has_next():
            return result.get_next()[0]
        return None

    @staticmethod
    def _rows_to_shared_facts(result) -> list[SharedFact]:
        """Convert Kuzu query result rows to SharedFact list."""
        facts: list[SharedFact] = []
        while result.has_next():
            row = result.get_next()
            tags: list[str] = []
            if row[5]:
                try:
                    tags = json.loads(row[5])
                except (json.JSONDecodeError, TypeError):
                    pass
            facts.append(
                SharedFact(
                    fact_id=row[0],
                    content=row[1],
                    concept=row[2],
                    source_agent_id=row[3],
                    confidence=float(row[4]),
                    tags=tags,
                    content_hash=row[6] or "",
                    created_at=datetime.fromtimestamp(row[7]),
                )
            )
        return facts


# ---------------------------------------------------------------------------
# HiveMemoryBridge
# ---------------------------------------------------------------------------


class HiveMemoryBridge:
    """Bridges between an agent's local memory and the shared hive memory.

    Provides promote (local -> hive) and pull (hive -> local context) operations.
    Uses content hashing for deduplication.

    Args:
        agent_id: The agent's identifier.
        local_memory: The agent's local memory adapter (CognitiveAdapter or MemoryRetriever).
        hive_store: The shared HiveMemoryStore instance.

    Example:
        >>> bridge = HiveMemoryBridge("agent_a", local_mem, hive_store)
        >>> bridge.promote_to_hive("sem_abc123")
        >>> pulled = bridge.pull_from_hive("infrastructure")
        >>> assert len(pulled) > 0
    """

    def __init__(
        self,
        agent_id: str,
        local_memory: Any,
        hive_store: HiveMemoryStore,
    ) -> None:
        self.agent_id = agent_id
        self.local_memory = local_memory
        self.hive_store = hive_store

    def promote_to_hive(
        self,
        fact_content: str,
        concept: str = "",
        confidence: float = 0.9,
        tags: list[str] | None = None,
    ) -> str:
        """Copy a local fact to the shared hive memory.

        Args:
            fact_content: The fact text to promote.
            concept: Topic/concept label.
            confidence: Confidence score.
            tags: Optional tags.

        Returns:
            fact_id in the hive store (may be existing if dedup hit).
        """
        return self.hive_store.store_shared_fact(
            fact=fact_content,
            source_agent_id=self.agent_id,
            confidence=confidence,
            tags=tags,
            concept=concept,
        )

    def promote_all_local_facts(self, limit: int = 500) -> list[str]:
        """Promote all local facts to the hive.

        Reads from the local memory adapter and stores each fact in the hive.

        Args:
            limit: Maximum local facts to promote.

        Returns:
            List of hive fact_ids.
        """
        local_facts = self._get_local_facts(limit)
        fact_ids: list[str] = []
        for lf in local_facts:
            content = lf.get("outcome", lf.get("content", ""))
            concept = lf.get("context", lf.get("concept", ""))
            confidence = lf.get("confidence", 0.9)
            tags = lf.get("tags", [])
            if content and content.strip():
                fid = self.promote_to_hive(
                    fact_content=content,
                    concept=concept,
                    confidence=confidence,
                    tags=tags,
                )
                fact_ids.append(fid)
        return fact_ids

    def pull_from_hive(
        self,
        query: str,
        limit: int = 10,
        exclude_self: bool = False,
    ) -> list[dict[str, Any]]:
        """Pull relevant shared facts from the hive as local context dicts.

        Args:
            query: Search query.
            limit: Maximum facts to pull.
            exclude_self: If True, exclude facts originally stored by this agent.

        Returns:
            List of fact dicts compatible with the local memory format.
        """
        shared_facts = self.hive_store.query_shared_facts(query, limit=limit * 2)

        results: list[dict[str, Any]] = []
        for sf in shared_facts:
            if exclude_self and sf.source_agent_id == self.agent_id:
                continue
            results.append(
                {
                    "context": sf.concept,
                    "outcome": sf.content,
                    "confidence": sf.confidence,
                    "tags": sf.tags,
                    "timestamp": sf.created_at.isoformat(),
                    "metadata": {
                        "source": "hive",
                        "source_agent_id": sf.source_agent_id,
                        "fact_id": sf.fact_id,
                    },
                }
            )
            if len(results) >= limit:
                break
        return results

    def _get_local_facts(self, limit: int) -> list[dict[str, Any]]:
        """Retrieve facts from the local memory adapter."""
        if hasattr(self.local_memory, "get_all_facts"):
            return self.local_memory.get_all_facts(limit=limit)
        if hasattr(self.local_memory, "store") and hasattr(self.local_memory.store, "connector"):
            experiences = self.local_memory.store.connector.retrieve_experiences(limit=limit)
            return [
                {
                    "context": e.context,
                    "outcome": e.outcome,
                    "confidence": e.confidence,
                    "tags": e.tags or [],
                }
                for e in experiences
            ]
        return []


# ---------------------------------------------------------------------------
# HiveRetrieval
# ---------------------------------------------------------------------------


class HiveRetrieval:
    """Retrieval strategy that queries the shared hive memory.

    Integrates with the existing MemoryAgent retrieval flow by providing
    a retrieve() method that returns facts in the standard dict format.

    Args:
        hive_store: The shared HiveMemoryStore.
        requesting_agent_id: ID of the agent making the query.

    Example:
        >>> retrieval = HiveRetrieval(hive_store, "agent_a")
        >>> facts = retrieval.retrieve("infrastructure setup", max_facts=20)
        >>> for f in facts:
        ...     print(f["outcome"], "from", f["metadata"]["source_agent_id"])
    """

    def __init__(
        self,
        hive_store: HiveMemoryStore,
        requesting_agent_id: str = "",
    ) -> None:
        self.hive_store = hive_store
        self.requesting_agent_id = requesting_agent_id

    def retrieve(
        self,
        question: str,
        max_facts: int = 50,
        exclude_self: bool = False,
    ) -> list[dict[str, Any]]:
        """Retrieve facts from the shared hive matching a question.

        Args:
            question: The question/query text.
            max_facts: Maximum facts to return.
            exclude_self: If True, exclude facts from the requesting agent.

        Returns:
            List of fact dicts in the standard format (context, outcome, confidence, ...).
        """
        shared_facts = self.hive_store.query_shared_facts(query=question, limit=max_facts * 2)

        results: list[dict[str, Any]] = []
        for sf in shared_facts:
            if exclude_self and sf.source_agent_id == self.requesting_agent_id:
                continue
            results.append(
                {
                    "context": sf.concept,
                    "outcome": sf.content,
                    "confidence": sf.confidence,
                    "tags": sf.tags,
                    "timestamp": sf.created_at.isoformat(),
                    "metadata": {
                        "source": "hive",
                        "source_agent_id": sf.source_agent_id,
                        "fact_id": sf.fact_id,
                    },
                }
            )
            if len(results) >= max_facts:
                break
        return results


# ---------------------------------------------------------------------------
# MultiAgentHive
# ---------------------------------------------------------------------------


class MultiAgentHive:
    """Registry and coordinator for agents participating in the hive.

    Manages a shared HiveMemoryStore and a set of registered agents.
    Provides broadcast (store to hive) and query (read from hive) operations.

    Args:
        hive_db_path: Path to the shared Kuzu database directory.

    Example:
        >>> hive = MultiAgentHive(Path("/tmp/multi_hive_db"))
        >>> hive.register_agent("agent_a")
        >>> hive.broadcast_fact("Python uses indentation for blocks", "agent_a", 0.95)
        >>> results = hive.query_hive("indentation", "agent_b")
        >>> assert len(results) >= 1
    """

    def __init__(self, hive_db_path: Path | str) -> None:
        self.hive_db_path = Path(hive_db_path)
        self.store = HiveMemoryStore(self.hive_db_path)
        self._agents: dict[str, dict[str, Any]] = {}
        self._bridges: dict[str, HiveMemoryBridge] = {}

    def register_agent(
        self,
        agent_id: str,
        local_memory: Any = None,
    ) -> None:
        """Register an agent with the hive.

        Args:
            agent_id: The agent's unique identifier.
            local_memory: Optional local memory adapter for bridge operations.
        """
        self._agents[agent_id] = {
            "agent_id": agent_id,
            "registered_at": datetime.now().isoformat(),
        }
        if local_memory is not None:
            self._bridges[agent_id] = HiveMemoryBridge(
                agent_id=agent_id,
                local_memory=local_memory,
                hive_store=self.store,
            )
        logger.debug("Agent '%s' registered with hive", agent_id)

    def get_registered_agents(self) -> list[str]:
        """Return list of registered agent IDs."""
        return list(self._agents.keys())

    def broadcast_fact(
        self,
        fact: str,
        source_agent_id: str,
        confidence: float = 0.9,
        tags: list[str] | None = None,
        concept: str = "",
    ) -> str:
        """Store a fact in the shared hive memory.

        Args:
            fact: The factual content.
            source_agent_id: ID of the contributing agent.
            confidence: Confidence score (0.0-1.0).
            tags: Optional tags.
            concept: Optional topic/concept.

        Returns:
            fact_id of the stored fact.
        """
        return self.store.store_shared_fact(
            fact=fact,
            source_agent_id=source_agent_id,
            confidence=confidence,
            tags=tags,
            concept=concept,
        )

    def query_hive(
        self,
        query: str,
        requesting_agent_id: str = "",
        limit: int = 50,
        exclude_self: bool = False,
    ) -> list[dict[str, Any]]:
        """Query the shared hive and return results with provenance.

        Args:
            query: Search query.
            requesting_agent_id: ID of the querying agent.
            limit: Maximum results.
            exclude_self: If True, exclude facts from the requesting agent.

        Returns:
            List of fact dicts with source attribution.
        """
        retrieval = HiveRetrieval(
            hive_store=self.store,
            requesting_agent_id=requesting_agent_id,
        )
        return retrieval.retrieve(
            question=query,
            max_facts=limit,
            exclude_self=exclude_self,
        )

    def promote_agent_facts(self, agent_id: str, limit: int = 500) -> list[str]:
        """Promote all local facts from a registered agent to the hive.

        Args:
            agent_id: The agent whose local facts to promote.
            limit: Maximum facts to promote.

        Returns:
            List of hive fact_ids.

        Raises:
            KeyError: If agent has no bridge (no local_memory was provided).
        """
        if agent_id not in self._bridges:
            raise KeyError(
                f"Agent '{agent_id}' has no bridge. Register with local_memory to use promote."
            )
        return self._bridges[agent_id].promote_all_local_facts(limit=limit)

    def get_statistics(self) -> dict[str, Any]:
        """Return hive statistics.

        Returns:
            Dict with total_facts, agent_count, and per-agent fact counts.
        """
        total = self.store.get_fact_count()
        all_facts = self.store.get_all_shared_facts(limit=10000)
        per_agent: dict[str, int] = {}
        for f in all_facts:
            per_agent[f.source_agent_id] = per_agent.get(f.source_agent_id, 0) + 1

        return {
            "total_facts": total,
            "agent_count": len(self._agents),
            "registered_agents": list(self._agents.keys()),
            "facts_per_agent": per_agent,
        }
