"""Cognitive memory system with six memory types.

Provides a single CognitiveMemory class that manages all six cognitive memory
types (sensory, working, episodic, semantic, procedural, prospective) backed
by a Kuzu graph database.

Each agent gets full isolation via an ``agent_id`` column stored in every
node table.
"""

import json
import logging
import time
import uuid
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import kuzu

logger = logging.getLogger(__name__)

from .memory_types import (
    EpisodicMemory,
    MemoryCategory,
    ProceduralMemory,
    ProspectiveMemory,
    SemanticFact,
    SensoryItem,
    WorkingMemorySlot,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WORKING_MEMORY_CAPACITY = 20


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _new_id(prefix: str = "mem") -> str:
    """Generate a short unique id with a human-readable prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _ts_now() -> int:
    """Current Unix timestamp as integer."""
    return int(time.time())


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

_NODE_TABLES = [
    """
    CREATE NODE TABLE IF NOT EXISTS SensoryMemory(
        node_id STRING,
        agent_id STRING,
        modality STRING,
        raw_data STRING,
        observation_order INT64,
        expires_at INT64,
        created_at INT64,
        PRIMARY KEY(node_id)
    )
    """,
    """
    CREATE NODE TABLE IF NOT EXISTS WorkingMemory(
        node_id STRING,
        agent_id STRING,
        slot_type STRING,
        content STRING,
        relevance DOUBLE,
        task_id STRING,
        created_at INT64,
        PRIMARY KEY(node_id)
    )
    """,
    """
    CREATE NODE TABLE IF NOT EXISTS EpisodicMemory(
        node_id STRING,
        agent_id STRING,
        content STRING,
        source_label STRING,
        temporal_index INT64,
        compressed BOOLEAN,
        metadata STRING,
        created_at INT64,
        PRIMARY KEY(node_id)
    )
    """,
    """
    CREATE NODE TABLE IF NOT EXISTS SemanticMemory(
        node_id STRING,
        agent_id STRING,
        concept STRING,
        content STRING,
        confidence DOUBLE,
        source_id STRING,
        tags STRING,
        metadata STRING,
        created_at INT64,
        PRIMARY KEY(node_id)
    )
    """,
    """
    CREATE NODE TABLE IF NOT EXISTS ProceduralMemory(
        node_id STRING,
        agent_id STRING,
        name STRING,
        steps STRING,
        prerequisites STRING,
        usage_count INT64,
        created_at INT64,
        PRIMARY KEY(node_id)
    )
    """,
    """
    CREATE NODE TABLE IF NOT EXISTS ProspectiveMemory(
        node_id STRING,
        agent_id STRING,
        desc_text STRING,
        trigger_condition STRING,
        action_on_trigger STRING,
        status STRING,
        priority INT64,
        created_at INT64,
        PRIMARY KEY(node_id)
    )
    """,
    """
    CREATE NODE TABLE IF NOT EXISTS ConsolidatedEpisode(
        node_id STRING,
        agent_id STRING,
        summary STRING,
        original_count INT64,
        created_at INT64,
        PRIMARY KEY(node_id)
    )
    """,
]

_REL_TABLES = [
    """
    CREATE REL TABLE IF NOT EXISTS SIMILAR_TO(
        FROM SemanticMemory TO SemanticMemory,
        similarity_score DOUBLE
    )
    """,
    """
    CREATE REL TABLE IF NOT EXISTS DERIVES_FROM(
        FROM SemanticMemory TO EpisodicMemory,
        derived_at INT64
    )
    """,
    """
    CREATE REL TABLE IF NOT EXISTS PROCEDURE_DERIVES_FROM(
        FROM ProceduralMemory TO EpisodicMemory,
        derived_at INT64
    )
    """,
    """
    CREATE REL TABLE IF NOT EXISTS CONSOLIDATES(
        FROM ConsolidatedEpisode TO EpisodicMemory,
        consolidated_at INT64
    )
    """,
    """
    CREATE REL TABLE IF NOT EXISTS ATTENDED_TO(
        FROM SensoryMemory TO EpisodicMemory,
        attended_at INT64
    )
    """,
]


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------


class CognitiveMemory:
    """Six-type cognitive memory backed by Kuzu.

    Args:
        agent_name: Identifier for the agent (used for row isolation).
        db_path: Filesystem path for the Kuzu database directory.
    """

    WORKING_MEMORY_CAPACITY = WORKING_MEMORY_CAPACITY

    def __init__(self, agent_name: str, db_path: str | Path) -> None:
        if not agent_name or not agent_name.strip():
            raise ValueError("agent_name cannot be empty")

        self.agent_name = agent_name.strip()
        self.db_path = Path(db_path)
        # Ensure the *parent* directory exists; Kuzu creates the db dir itself.
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._db = kuzu.Database(str(self.db_path))
        self._conn = kuzu.Connection(self._db)
        self._initialize_schema()

        # Monotonic counters (loaded from DB at startup)
        self._sensory_order = self._load_max_order("SensoryMemory", "observation_order")
        self._temporal_index = self._load_max_order("EpisodicMemory", "temporal_index")

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _initialize_schema(self) -> None:
        for ddl in _NODE_TABLES + _REL_TABLES:
            try:
                self._conn.execute(ddl)
            except Exception as exc:
                if "already exists" not in str(exc).lower():
                    raise

    def _load_max_order(self, table: str, column: str) -> int:
        result = self._conn.execute(
            f"MATCH (n:{table}) WHERE n.agent_id = $aid RETURN max(n.{column})",
            {"aid": self.agent_name},
        )
        if result.has_next():
            val = result.get_next()[0]
            if val is not None:
                return int(val)
        return 0

    # ==================================================================
    # SENSORY MEMORY
    # ==================================================================

    def record_sensory(
        self,
        modality: str,
        raw_data: str,
        ttl_seconds: int = 300,
    ) -> str:
        """Record a short-lived sensory observation.

        Args:
            modality: Channel name (e.g. "text", "code", "error").
            raw_data: The raw observation payload.
            ttl_seconds: Time-to-live in seconds (default 300 = 5 min).

        Returns:
            The node_id of the newly created sensory item.
        """
        node_id = _new_id("sen")
        now = _ts_now()
        self._sensory_order += 1
        self._conn.execute(
            """
            CREATE (:SensoryMemory {
                node_id: $nid,
                agent_id: $aid,
                modality: $mod,
                raw_data: $data,
                observation_order: $ord,
                expires_at: $exp,
                created_at: $ts
            })
            """,
            {
                "nid": node_id,
                "aid": self.agent_name,
                "mod": modality,
                "data": raw_data,
                "ord": self._sensory_order,
                "exp": now + ttl_seconds,
                "ts": now,
            },
        )
        return node_id

    def get_recent_sensory(self, limit: int = 10) -> list[SensoryItem]:
        """Return the most recent sensory items (not yet expired).

        Args:
            limit: Maximum items to return.

        Returns:
            List of SensoryItem ordered by observation_order descending.
        """
        now = _ts_now()
        result = self._conn.execute(
            """
            MATCH (s:SensoryMemory)
            WHERE s.agent_id = $aid AND s.expires_at > $now
            RETURN s.node_id, s.modality, s.raw_data,
                   s.observation_order, s.expires_at, s.created_at
            ORDER BY s.observation_order DESC
            LIMIT $lim
            """,
            {"aid": self.agent_name, "now": now, "lim": limit},
        )
        items: list[SensoryItem] = []
        while result.has_next():
            row = result.get_next()
            items.append(
                SensoryItem(
                    node_id=row[0],
                    modality=row[1],
                    raw_data=row[2],
                    observation_order=int(row[3]),
                    expires_at=float(row[4]),
                    created_at=datetime.fromtimestamp(row[5]),
                )
            )
        return items

    def attend_to_sensory(self, sensory_id: str, reason: str) -> str | None:
        """Promote a sensory item to an episodic memory and link them.

        Args:
            sensory_id: node_id of the sensory item to promote.
            reason: Why this observation is noteworthy.

        Returns:
            The node_id of the new episodic memory, or None if the
            sensory item was not found / already expired.
        """
        now = _ts_now()
        # Fetch the sensory item
        result = self._conn.execute(
            """
            MATCH (s:SensoryMemory)
            WHERE s.node_id = $sid AND s.agent_id = $aid AND s.expires_at > $now
            RETURN s.modality, s.raw_data
            """,
            {"sid": sensory_id, "aid": self.agent_name, "now": now},
        )
        if not result.has_next():
            return None

        modality, raw_data = result.get_next()
        content = f"[{modality}] {raw_data} -- attended: {reason}"

        ep_id = self.store_episode(content=content, source_label="sensory-attention")

        # Create ATTENDED_TO edge
        try:
            self._conn.execute(
                """
                MATCH (s:SensoryMemory), (e:EpisodicMemory)
                WHERE s.node_id = $sid AND e.node_id = $eid
                CREATE (s)-[:ATTENDED_TO {attended_at: $ts}]->(e)
                """,
                {"sid": sensory_id, "eid": ep_id, "ts": now},
            )
        except Exception as exc:
            logger.debug("ATTENDED_TO edge creation failed (best-effort): %s", exc)

        return ep_id

    def prune_expired_sensory(self) -> int:
        """Delete sensory items past their expiry time.

        Returns:
            Number of items pruned.
        """
        now = _ts_now()
        # Count first
        result = self._conn.execute(
            """
            MATCH (s:SensoryMemory)
            WHERE s.agent_id = $aid AND s.expires_at <= $now
            RETURN count(s)
            """,
            {"aid": self.agent_name, "now": now},
        )
        count = 0
        if result.has_next():
            count = int(result.get_next()[0])

        if count > 0:
            self._conn.execute(
                """
                MATCH (s:SensoryMemory)
                WHERE s.agent_id = $aid AND s.expires_at <= $now
                DELETE s
                """,
                {"aid": self.agent_name, "now": now},
            )
        return count

    # ==================================================================
    # WORKING MEMORY
    # ==================================================================

    def push_working(
        self,
        slot_type: str,
        content: str,
        task_id: str,
        relevance: float = 1.0,
    ) -> str:
        """Push a slot into working memory for a given task.

        If the task already has WORKING_MEMORY_CAPACITY slots, the
        least-relevant slot is evicted.

        Args:
            slot_type: Categorisation (e.g. "goal", "constraint").
            content: Payload.
            task_id: Task identifier.
            relevance: Priority weight (default 1.0).

        Returns:
            node_id of the new working-memory slot.
        """
        # Evict if at capacity
        existing = self.get_working(task_id)
        if len(existing) >= self.WORKING_MEMORY_CAPACITY:
            # Remove the lowest-relevance slot
            lowest = min(existing, key=lambda s: s.relevance)
            self._conn.execute(
                "MATCH (w:WorkingMemory) WHERE w.node_id = $nid DELETE w",
                {"nid": lowest.node_id},
            )

        node_id = _new_id("wrk")
        now = _ts_now()
        self._conn.execute(
            """
            CREATE (:WorkingMemory {
                node_id: $nid,
                agent_id: $aid,
                slot_type: $st,
                content: $cnt,
                relevance: $rel,
                task_id: $tid,
                created_at: $ts
            })
            """,
            {
                "nid": node_id,
                "aid": self.agent_name,
                "st": slot_type,
                "cnt": content,
                "rel": relevance,
                "tid": task_id,
                "ts": now,
            },
        )
        return node_id

    def get_working(self, task_id: str) -> list[WorkingMemorySlot]:
        """Retrieve working memory slots for a task.

        Args:
            task_id: Task identifier.

        Returns:
            List of WorkingMemorySlot ordered by relevance descending.
        """
        result = self._conn.execute(
            """
            MATCH (w:WorkingMemory)
            WHERE w.agent_id = $aid AND w.task_id = $tid
            RETURN w.node_id, w.slot_type, w.content,
                   w.relevance, w.task_id, w.created_at
            ORDER BY w.relevance DESC
            """,
            {"aid": self.agent_name, "tid": task_id},
        )
        slots: list[WorkingMemorySlot] = []
        while result.has_next():
            row = result.get_next()
            slots.append(
                WorkingMemorySlot(
                    node_id=row[0],
                    slot_type=row[1],
                    content=row[2],
                    relevance=float(row[3]),
                    task_id=row[4],
                    created_at=datetime.fromtimestamp(row[5]),
                )
            )
        return slots

    def clear_working(self, task_id: str) -> int:
        """Clear all working memory slots for a task.

        Args:
            task_id: Task identifier.

        Returns:
            Number of slots cleared.
        """
        result = self._conn.execute(
            """
            MATCH (w:WorkingMemory)
            WHERE w.agent_id = $aid AND w.task_id = $tid
            RETURN count(w)
            """,
            {"aid": self.agent_name, "tid": task_id},
        )
        count = 0
        if result.has_next():
            count = int(result.get_next()[0])

        if count > 0:
            self._conn.execute(
                """
                MATCH (w:WorkingMemory)
                WHERE w.agent_id = $aid AND w.task_id = $tid
                DELETE w
                """,
                {"aid": self.agent_name, "tid": task_id},
            )
        return count

    # ==================================================================
    # EPISODIC MEMORY
    # ==================================================================

    def store_episode(
        self,
        content: str,
        source_label: str,
        temporal_index: int | None = None,
        metadata: dict | None = None,
    ) -> str:
        """Store an episodic memory.

        Args:
            content: Episode description.
            source_label: Origin label (e.g. "user-session").
            temporal_index: Explicit ordering index. If None, auto-increments.
            metadata: Optional structured data.

        Returns:
            node_id of the stored episode.
        """
        node_id = _new_id("epi")
        now = _ts_now()
        if temporal_index is None:
            self._temporal_index += 1
            temporal_index = self._temporal_index
        else:
            # Keep our counter up to date
            if temporal_index > self._temporal_index:
                self._temporal_index = temporal_index

        meta_json = json.dumps(metadata) if metadata else "{}"

        self._conn.execute(
            """
            CREATE (:EpisodicMemory {
                node_id: $nid,
                agent_id: $aid,
                content: $cnt,
                source_label: $src,
                temporal_index: $tidx,
                compressed: false,
                metadata: $meta,
                created_at: $ts
            })
            """,
            {
                "nid": node_id,
                "aid": self.agent_name,
                "cnt": content,
                "src": source_label,
                "tidx": temporal_index,
                "meta": meta_json,
                "ts": now,
            },
        )
        return node_id

    def consolidate_episodes(
        self,
        batch_size: int = 10,
        summarizer: Callable[[list[str]], str] | None = None,
    ) -> str | None:
        """Consolidate the oldest un-compressed episodes into a summary.

        Args:
            batch_size: Number of episodes to consolidate per call.
            summarizer: Optional function ``(list[str]) -> str`` that
                produces a summary.  If None a simple concatenation is used.

        Returns:
            node_id of the ConsolidatedEpisode, or None if fewer than
            ``batch_size`` episodes are available.
        """
        result = self._conn.execute(
            """
            MATCH (e:EpisodicMemory)
            WHERE e.agent_id = $aid AND e.compressed = false
            RETURN e.node_id, e.content
            ORDER BY e.temporal_index ASC
            LIMIT $bs
            """,
            {"aid": self.agent_name, "bs": batch_size},
        )
        episodes: list[tuple[str, str]] = []
        while result.has_next():
            row = result.get_next()
            episodes.append((row[0], row[1]))

        if len(episodes) < batch_size:
            return None

        contents = [c for _, c in episodes]
        if summarizer is not None:
            summary = summarizer(contents)
        else:
            summary = " | ".join(contents)

        # Create consolidated node
        cons_id = _new_id("con")
        now = _ts_now()
        self._conn.execute(
            """
            CREATE (:ConsolidatedEpisode {
                node_id: $nid,
                agent_id: $aid,
                summary: $sum,
                original_count: $cnt,
                created_at: $ts
            })
            """,
            {
                "nid": cons_id,
                "aid": self.agent_name,
                "sum": summary,
                "cnt": len(episodes),
                "ts": now,
            },
        )

        # Mark originals as compressed and create edges
        for ep_id, _ in episodes:
            self._conn.execute(
                """
                MATCH (e:EpisodicMemory)
                WHERE e.node_id = $eid
                SET e.compressed = true
                """,
                {"eid": ep_id},
            )
            try:
                self._conn.execute(
                    """
                    MATCH (c:ConsolidatedEpisode), (e:EpisodicMemory)
                    WHERE c.node_id = $cid AND e.node_id = $eid
                    CREATE (c)-[:CONSOLIDATES {consolidated_at: $ts}]->(e)
                    """,
                    {"cid": cons_id, "eid": ep_id, "ts": now},
                )
            except Exception as exc:
                logger.debug("CONSOLIDATES edge creation failed (best-effort): %s", exc)

        return cons_id

    def get_episodes(
        self,
        limit: int = 20,
        include_compressed: bool = False,
    ) -> list[EpisodicMemory]:
        """Retrieve episodic memories.

        Args:
            limit: Maximum number of episodes.
            include_compressed: If False (default), exclude compressed episodes.

        Returns:
            List of EpisodicMemory sorted by temporal_index descending.
        """
        compressed_clause = "" if include_compressed else " AND e.compressed = false"
        result = self._conn.execute(
            f"""
            MATCH (e:EpisodicMemory)
            WHERE e.agent_id = $aid{compressed_clause}
            RETURN e.node_id, e.content, e.source_label,
                   e.temporal_index, e.compressed, e.created_at, e.metadata
            ORDER BY e.temporal_index DESC
            LIMIT $lim
            """,
            {"aid": self.agent_name, "lim": limit},
        )
        episodes: list[EpisodicMemory] = []
        while result.has_next():
            row = result.get_next()
            meta = {}
            if row[6]:
                try:
                    meta = json.loads(row[6])
                except (json.JSONDecodeError, TypeError):
                    logger.debug("Failed to parse episode metadata: %s", row[6])
            episodes.append(
                EpisodicMemory(
                    node_id=row[0],
                    content=row[1],
                    source_label=row[2],
                    temporal_index=int(row[3]),
                    compressed=bool(row[4]),
                    created_at=datetime.fromtimestamp(row[5]),
                    metadata=meta,
                )
            )
        return episodes

    # ==================================================================
    # SEMANTIC MEMORY
    # ==================================================================

    def store_fact(
        self,
        concept: str,
        content: str,
        confidence: float = 1.0,
        source_id: str = "",
        tags: list[str] | None = None,
        temporal_metadata: dict | None = None,
    ) -> str:
        """Store a semantic fact.

        Args:
            concept: The concept or topic.
            content: Factual content.
            confidence: Confidence score (0.0 - 1.0).
            source_id: Origin reference.
            tags: Categorisation tags.
            temporal_metadata: Optional structured metadata.

        Returns:
            node_id of the stored fact.
        """
        node_id = _new_id("sem")
        now = _ts_now()
        tags_json = json.dumps(tags) if tags else "[]"
        meta_json = json.dumps(temporal_metadata) if temporal_metadata else "{}"

        self._conn.execute(
            """
            CREATE (:SemanticMemory {
                node_id: $nid,
                agent_id: $aid,
                concept: $con,
                content: $cnt,
                confidence: $conf,
                source_id: $src,
                tags: $tags,
                metadata: $meta,
                created_at: $ts
            })
            """,
            {
                "nid": node_id,
                "aid": self.agent_name,
                "con": concept,
                "cnt": content,
                "conf": confidence,
                "src": source_id,
                "tags": tags_json,
                "meta": meta_json,
                "ts": now,
            },
        )
        return node_id

    def search_facts(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> list[SemanticFact]:
        """Search semantic facts by keyword matching on concept and content.

        Args:
            query: Search string (keywords matched via CONTAINS).
            limit: Maximum results.
            min_confidence: Minimum confidence threshold.

        Returns:
            List of matching SemanticFact ordered by confidence descending.
        """
        # Tokenise query and build OR conditions
        keywords = [w.strip() for w in query.split() if w.strip()]
        if not keywords:
            return self.get_all_facts(limit=limit)

        conditions = []
        params: dict = {
            "aid": self.agent_name,
            "minc": min_confidence,
            "lim": limit,
        }
        for i, kw in enumerate(keywords[:6]):
            pname = f"kw{i}"
            conditions.append(
                f"(lower(s.concept) CONTAINS lower(${pname}) "
                f"OR lower(s.content) CONTAINS lower(${pname}))"
            )
            params[pname] = kw

        where_kw = " OR ".join(conditions)
        result = self._conn.execute(
            f"""
            MATCH (s:SemanticMemory)
            WHERE s.agent_id = $aid
              AND s.confidence >= $minc
              AND ({where_kw})
            RETURN s.node_id, s.concept, s.content, s.confidence,
                   s.source_id, s.tags, s.metadata, s.created_at
            ORDER BY s.confidence DESC
            LIMIT $lim
            """,
            params,
        )
        return self._rows_to_facts(result)

    def get_all_facts(self, limit: int = 50) -> list[SemanticFact]:
        """Return all semantic facts for this agent.

        Args:
            limit: Maximum number of facts.

        Returns:
            List of SemanticFact ordered by confidence descending.
        """
        result = self._conn.execute(
            """
            MATCH (s:SemanticMemory)
            WHERE s.agent_id = $aid
            RETURN s.node_id, s.concept, s.content, s.confidence,
                   s.source_id, s.tags, s.metadata, s.created_at
            ORDER BY s.confidence DESC
            LIMIT $lim
            """,
            {"aid": self.agent_name, "lim": limit},
        )
        return self._rows_to_facts(result)

    @staticmethod
    def _rows_to_facts(result) -> list[SemanticFact]:
        facts: list[SemanticFact] = []
        while result.has_next():
            row = result.get_next()
            tags: list[str] = []
            if row[5]:
                try:
                    tags = json.loads(row[5])
                except (json.JSONDecodeError, TypeError):
                    logger.debug("Failed to parse fact tags: %s", row[5])
            meta: dict = {}
            if row[6]:
                try:
                    meta = json.loads(row[6])
                except (json.JSONDecodeError, TypeError):
                    logger.debug("Failed to parse fact metadata: %s", row[6])
            facts.append(
                SemanticFact(
                    node_id=row[0],
                    concept=row[1],
                    content=row[2],
                    confidence=float(row[3]),
                    source_id=row[4] or "",
                    tags=tags,
                    metadata=meta,
                    created_at=datetime.fromtimestamp(row[7]),
                )
            )
        return facts

    # ==================================================================
    # PROCEDURAL MEMORY
    # ==================================================================

    def store_procedure(
        self,
        name: str,
        steps: list[str],
        prerequisites: list[str] | None = None,
    ) -> str:
        """Store a reusable procedure.

        Args:
            name: Human-readable procedure name.
            steps: Ordered list of step descriptions.
            prerequisites: Conditions required before executing.

        Returns:
            node_id of the stored procedure.
        """
        node_id = _new_id("proc")
        now = _ts_now()
        steps_json = json.dumps(steps)
        prereqs_json = json.dumps(prerequisites) if prerequisites else "[]"

        self._conn.execute(
            """
            CREATE (:ProceduralMemory {
                node_id: $nid,
                agent_id: $aid,
                name: $name,
                steps: $steps,
                prerequisites: $prereqs,
                usage_count: 0,
                created_at: $ts
            })
            """,
            {
                "nid": node_id,
                "aid": self.agent_name,
                "name": name,
                "steps": steps_json,
                "prereqs": prereqs_json,
                "ts": now,
            },
        )
        return node_id

    def recall_procedure(
        self,
        query: str,
        limit: int = 5,
    ) -> list[ProceduralMemory]:
        """Recall procedures matching a query and increment their usage count.

        Args:
            query: Search keywords (matched against name and steps).
            limit: Maximum results.

        Returns:
            List of matching ProceduralMemory sorted by usage_count desc.
        """
        keywords = [w.strip() for w in query.split() if w.strip()]
        if not keywords:
            # Return most-used procedures
            result = self._conn.execute(
                """
                MATCH (p:ProceduralMemory)
                WHERE p.agent_id = $aid
                RETURN p.node_id, p.name, p.steps,
                       p.prerequisites, p.usage_count, p.created_at
                ORDER BY p.usage_count DESC
                LIMIT $lim
                """,
                {"aid": self.agent_name, "lim": limit},
            )
        else:
            conditions = []
            params: dict = {"aid": self.agent_name, "lim": limit}
            for i, kw in enumerate(keywords[:6]):
                pname = f"kw{i}"
                conditions.append(
                    f"(lower(p.name) CONTAINS lower(${pname}) "
                    f"OR lower(p.steps) CONTAINS lower(${pname}))"
                )
                params[pname] = kw

            where_kw = " OR ".join(conditions)
            result = self._conn.execute(
                f"""
                MATCH (p:ProceduralMemory)
                WHERE p.agent_id = $aid AND ({where_kw})
                RETURN p.node_id, p.name, p.steps,
                       p.prerequisites, p.usage_count, p.created_at
                ORDER BY p.usage_count DESC
                LIMIT $lim
                """,
                params,
            )

        procs: list[ProceduralMemory] = []
        while result.has_next():
            row = result.get_next()
            steps: list[str] = []
            if row[2]:
                try:
                    steps = json.loads(row[2])
                except (json.JSONDecodeError, TypeError):
                    logger.debug("Failed to parse procedure steps: %s", row[2])
            prereqs: list[str] = []
            if row[3]:
                try:
                    prereqs = json.loads(row[3])
                except (json.JSONDecodeError, TypeError):
                    logger.debug("Failed to parse procedure prereqs: %s", row[3])
            procs.append(
                ProceduralMemory(
                    node_id=row[0],
                    name=row[1],
                    steps=steps,
                    prerequisites=prereqs,
                    usage_count=int(row[4]),
                    created_at=datetime.fromtimestamp(row[5]),
                )
            )

        # Increment usage_count for all recalled procedures
        for proc in procs:
            self._conn.execute(
                """
                MATCH (p:ProceduralMemory)
                WHERE p.node_id = $nid
                SET p.usage_count = p.usage_count + 1
                """,
                {"nid": proc.node_id},
            )

        return procs

    # ==================================================================
    # PROSPECTIVE MEMORY
    # ==================================================================

    def store_prospective(
        self,
        description: str,
        trigger_condition: str,
        action_on_trigger: str,
        priority: int = 1,
    ) -> str:
        """Store a trigger-action pair for future evaluation.

        Args:
            description: What this prospective memory is about.
            trigger_condition: Text description of the trigger.
            action_on_trigger: What to do when fired.
            priority: Priority level (higher = more important).

        Returns:
            node_id of the stored prospective memory.
        """
        node_id = _new_id("pro")
        now = _ts_now()

        self._conn.execute(
            """
            CREATE (:ProspectiveMemory {
                node_id: $nid,
                agent_id: $aid,
                desc_text: $dtxt,
                trigger_condition: $trig,
                action_on_trigger: $act,
                status: $stat,
                priority: $pri,
                created_at: $ts
            })
            """,
            {
                "nid": node_id,
                "aid": self.agent_name,
                "dtxt": description,
                "trig": trigger_condition,
                "act": action_on_trigger,
                "stat": "pending",
                "pri": priority,
                "ts": now,
            },
        )
        return node_id

    def check_triggers(self, content: str) -> list[ProspectiveMemory]:
        """Check pending prospective memories against provided content.

        A simple keyword-overlap heuristic: if any word from the
        trigger_condition appears in ``content``, the prospective memory
        is considered triggered.

        Args:
            content: Text to evaluate against triggers.

        Returns:
            List of triggered ProspectiveMemory items (status set to "triggered").
        """
        result = self._conn.execute(
            """
            MATCH (p:ProspectiveMemory)
            WHERE p.agent_id = $aid AND p.status = $stat
            RETURN p.node_id, p.desc_text, p.trigger_condition,
                   p.action_on_trigger, p.status, p.priority, p.created_at
            ORDER BY p.priority DESC
            """,
            {"aid": self.agent_name, "stat": "pending"},
        )

        candidates: list[ProspectiveMemory] = []
        while result.has_next():
            row = result.get_next()
            candidates.append(
                ProspectiveMemory(
                    node_id=row[0],
                    description=row[1],
                    trigger_condition=row[2],
                    action_on_trigger=row[3],
                    status=row[4],
                    priority=int(row[5]),
                    created_at=datetime.fromtimestamp(row[6]),
                )
            )

        content_lower = content.lower()
        triggered: list[ProspectiveMemory] = []
        for pm in candidates:
            trigger_words = {w.lower() for w in pm.trigger_condition.split() if w.strip()}
            if any(w in content_lower for w in trigger_words):
                # Mark as triggered in the DB
                self._conn.execute(
                    """
                    MATCH (p:ProspectiveMemory)
                    WHERE p.node_id = $nid
                    SET p.status = $stat
                    """,
                    {"nid": pm.node_id, "stat": "triggered"},
                )
                pm.status = "triggered"
                triggered.append(pm)

        return triggered

    def resolve_prospective(self, node_id: str) -> None:
        """Mark a prospective memory as resolved.

        Args:
            node_id: The node_id to resolve.
        """
        self._conn.execute(
            """
            MATCH (p:ProspectiveMemory)
            WHERE p.node_id = $nid AND p.agent_id = $aid
            SET p.status = $stat
            """,
            {"nid": node_id, "aid": self.agent_name, "stat": "resolved"},
        )

    # ==================================================================
    # STATISTICS
    # ==================================================================

    def get_statistics(self) -> dict:
        """Return counts per memory type.

        Returns:
            Dictionary with keys for each MemoryCategory and their counts,
            plus a ``total`` key.
        """
        tables = {
            MemoryCategory.SENSORY: "SensoryMemory",
            MemoryCategory.WORKING: "WorkingMemory",
            MemoryCategory.EPISODIC: "EpisodicMemory",
            MemoryCategory.SEMANTIC: "SemanticMemory",
            MemoryCategory.PROCEDURAL: "ProceduralMemory",
            MemoryCategory.PROSPECTIVE: "ProspectiveMemory",
        }

        stats: dict = {}
        total = 0
        for category, table in tables.items():
            result = self._conn.execute(
                f"MATCH (n:{table}) WHERE n.agent_id = $aid RETURN count(n)",
                {"aid": self.agent_name},
            )
            count = 0
            if result.has_next():
                count = int(result.get_next()[0])
            stats[category.value] = count
            total += count

        stats["total"] = total
        return stats

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Release the Kuzu connection."""
        self._conn = None
        self._db = None
