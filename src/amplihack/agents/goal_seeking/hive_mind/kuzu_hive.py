"""Kuzu-backed Hive Mind: Real graph database for multi-agent knowledge sharing.

Replaces the Python dict-based UnifiedHiveMind with real Kuzu persistence via
the amplihack-memory-lib CognitiveMemory system.  Every agent gets a
CognitiveMemory instance pointing at the same shared database, giving agent-
level isolation for local facts while enabling cross-agent promotion and query.

Architecture:
    HiveKuzuSchema  -- DDL for hive-only tables (HiveAgent, CONFIRMED_BY, etc.)
    AgentRegistry   -- Agent registration with trust scores and domain tracking
    HiveGateway     -- Validates facts before promotion, detects contradictions
    KuzuHiveMind    -- Main orchestrator: register agents, store, promote, query

Public API:
    KuzuHiveMind: Central orchestrator
    HiveKuzuSchema: Schema setup
    AgentRegistry: Agent management
    HiveGateway: Promotion gateway
"""

from __future__ import annotations

import hashlib
import logging
import sys
import time
import uuid
from pathlib import Path

# Import CognitiveMemory from the real amplihack-memory-lib
_MEMORY_LIB_PATH = "/home/azureuser/src/amplihack-memory-lib-real/src"
if _MEMORY_LIB_PATH not in sys.path:
    sys.path.insert(0, _MEMORY_LIB_PATH)

import kuzu
from amplihack_memory.cognitive_memory import CognitiveMemory

logger = logging.getLogger(__name__)

__all__ = [
    "HiveKuzuSchema",
    "AgentRegistry",
    "HiveGateway",
    "KuzuHiveMind",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _content_hash(text: str) -> str:
    """SHA-256 of normalized text for deduplication."""
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()


def _new_id(prefix: str = "hive") -> str:
    """Generate a short unique ID with a human-readable prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _ts_now() -> int:
    """Current Unix timestamp as integer."""
    return int(time.time())


# ---------------------------------------------------------------------------
# HiveKuzuSchema
# ---------------------------------------------------------------------------


class HiveKuzuSchema:
    """Creates hive-specific tables in a shared Kuzu database.

    The CognitiveMemory class already creates SemanticMemory and other core
    tables.  This class adds hive-only tables for agent registry, cross-agent
    confirmation edges, contradiction edges, and promotion tracking.

    All DDL runs through a CognitiveMemory instance's connection to avoid
    multiple kuzu.Database objects on the same path (which don't share
    in-memory state reliably).
    """

    _HIVE_NODE_TABLES = [
        """
        CREATE NODE TABLE IF NOT EXISTS HiveAgent(
            agent_id STRING,
            domain STRING,
            trust_score DOUBLE,
            fact_count INT64,
            registered_at INT64,
            PRIMARY KEY(agent_id)
        )
        """,
    ]

    _HIVE_REL_TABLES = [
        """
        CREATE REL TABLE IF NOT EXISTS CONFIRMED_BY(
            FROM SemanticMemory TO SemanticMemory,
            confirmed_at INT64,
            confirming_agent STRING
        )
        """,
        """
        CREATE REL TABLE IF NOT EXISTS CONTRADICTS(
            FROM SemanticMemory TO SemanticMemory,
            detected_at INT64,
            resolution STRING,
            winner_id STRING
        )
        """,
        """
        CREATE REL TABLE IF NOT EXISTS PROMOTED_TO_HIVE(
            FROM HiveAgent TO SemanticMemory,
            promoted_at INT64,
            status STRING
        )
        """,
    ]

    def __init__(self, conn: kuzu.Connection) -> None:
        """Wrap an existing Kuzu connection for schema setup.

        Args:
            conn: Active Kuzu connection (from a CognitiveMemory instance).
        """
        self._conn = conn

    def setup(self) -> None:
        """Create all hive-specific tables (node + rel).

        SemanticMemory must already exist (created by CognitiveMemory).
        """
        self.setup_node_tables()
        self.setup_rel_tables()

    def setup_node_tables(self) -> None:
        """Create hive-only node tables (HiveAgent)."""
        for ddl in self._HIVE_NODE_TABLES:
            try:
                self._conn.execute(ddl)
            except Exception as exc:
                if "already exists" not in str(exc).lower():
                    raise

    def setup_rel_tables(self) -> None:
        """Create hive relationship tables (CONFIRMED_BY, CONTRADICTS, etc.)."""
        for ddl in self._HIVE_REL_TABLES:
            try:
                self._conn.execute(ddl)
            except Exception as exc:
                if "already exists" not in str(exc).lower():
                    raise

    @property
    def connection(self) -> kuzu.Connection:
        """Expose connection for other components sharing this DB."""
        return self._conn


# ---------------------------------------------------------------------------
# AgentRegistry
# ---------------------------------------------------------------------------


class AgentRegistry:
    """Agent registry backed by Kuzu HiveAgent nodes.

    Tracks registered agents with trust scores and domain expertise.
    Trust scores start at 1.0 and can be adjusted via update_trust().
    """

    DEFAULT_TRUST = 1.0

    def __init__(self, conn: kuzu.Connection) -> None:
        """Initialize registry with a Kuzu connection.

        Args:
            conn: Active Kuzu connection to the shared database.
        """
        self._conn = conn

    def register(self, agent_id: str, domain: str = "") -> None:
        """Register an agent in the hive.

        Args:
            agent_id: Unique identifier for the agent.
            domain: Domain of expertise (e.g. "biology", "infrastructure").

        Raises:
            ValueError: If agent_id is already registered.
        """
        result = self._conn.execute(
            "MATCH (a:HiveAgent) WHERE a.agent_id = $aid RETURN a.agent_id",
            {"aid": agent_id},
        )
        if result.has_next():
            raise ValueError(f"Agent '{agent_id}' is already registered")

        now = _ts_now()
        self._conn.execute(
            """
            CREATE (:HiveAgent {
                agent_id: $aid,
                domain: $dom,
                trust_score: $trust,
                fact_count: 0,
                registered_at: $ts
            })
            """,
            {
                "aid": agent_id,
                "dom": domain,
                "trust": self.DEFAULT_TRUST,
                "ts": now,
            },
        )

    def update_trust(self, agent_id: str, delta: float) -> None:
        """Adjust an agent's trust score.

        The trust score is clamped to [0.0, 2.0].

        Args:
            agent_id: Agent to update.
            delta: Amount to add (positive) or subtract (negative).
        """
        agent = self.get_agent(agent_id)
        new_trust = max(0.0, min(2.0, agent["trust_score"] + delta))
        self._conn.execute(
            """
            MATCH (a:HiveAgent) WHERE a.agent_id = $aid
            SET a.trust_score = $trust
            """,
            {"aid": agent_id, "trust": new_trust},
        )

    def increment_fact_count(self, agent_id: str) -> None:
        """Increment the agent's promoted fact count by 1."""
        self._conn.execute(
            """
            MATCH (a:HiveAgent) WHERE a.agent_id = $aid
            SET a.fact_count = a.fact_count + 1
            """,
            {"aid": agent_id},
        )

    def get_agent(self, agent_id: str) -> dict:
        """Retrieve agent details.

        Args:
            agent_id: Agent to look up.

        Returns:
            Dict with agent_id, domain, trust_score, fact_count, registered_at.

        Raises:
            KeyError: If agent is not registered.
        """
        result = self._conn.execute(
            """
            MATCH (a:HiveAgent) WHERE a.agent_id = $aid
            RETURN a.agent_id, a.domain, a.trust_score, a.fact_count, a.registered_at
            """,
            {"aid": agent_id},
        )
        if not result.has_next():
            raise KeyError(f"Agent '{agent_id}' not found in registry")
        row = result.get_next()
        return {
            "agent_id": row[0],
            "domain": row[1],
            "trust_score": float(row[2]),
            "fact_count": int(row[3]),
            "registered_at": int(row[4]),
        }

    def get_all_agents(self) -> list[dict]:
        """Return all registered agents.

        Returns:
            List of agent dicts sorted by trust_score descending.
        """
        result = self._conn.execute(
            """
            MATCH (a:HiveAgent)
            RETURN a.agent_id, a.domain, a.trust_score, a.fact_count, a.registered_at
            ORDER BY a.trust_score DESC
            """
        )
        agents = []
        while result.has_next():
            row = result.get_next()
            agents.append(
                {
                    "agent_id": row[0],
                    "domain": row[1],
                    "trust_score": float(row[2]),
                    "fact_count": int(row[3]),
                    "registered_at": int(row[4]),
                }
            )
        return agents

    def get_agents_by_domain(self, domain: str) -> list[dict]:
        """Return agents matching a domain.

        Args:
            domain: Domain string to match (case-insensitive CONTAINS).

        Returns:
            List of agent dicts whose domain contains the query.
        """
        result = self._conn.execute(
            """
            MATCH (a:HiveAgent)
            WHERE lower(a.domain) CONTAINS lower($dom)
            RETURN a.agent_id, a.domain, a.trust_score, a.fact_count, a.registered_at
            ORDER BY a.trust_score DESC
            """,
            {"dom": domain},
        )
        agents = []
        while result.has_next():
            row = result.get_next()
            agents.append(
                {
                    "agent_id": row[0],
                    "domain": row[1],
                    "trust_score": float(row[2]),
                    "fact_count": int(row[3]),
                    "registered_at": int(row[4]),
                }
            )
        return agents

    def get_agent_count(self) -> int:
        """Return the number of registered agents."""
        result = self._conn.execute("MATCH (a:HiveAgent) RETURN count(a)")
        if result.has_next():
            return int(result.get_next()[0])
        return 0


# ---------------------------------------------------------------------------
# HiveGateway
# ---------------------------------------------------------------------------


class HiveGateway:
    """Gateway that validates facts before promotion to the hive.

    Checks for contradictions against existing promoted facts and verifies
    agent trust before allowing promotion.  Creates PROMOTED_TO_HIVE edges
    for clean promotions and CONTRADICTS edges when conflicts are found.

    Stores promoted facts through the hive CognitiveMemory instance to ensure
    all queries through that instance can find them.
    """

    TRUST_THRESHOLD = 0.3
    QUARANTINE_STATUS = "quarantined"
    PROMOTED_STATUS = "promoted"
    REJECTED_STATUS = "rejected"

    def __init__(
        self,
        hive_mem: CognitiveMemory,
        registry: AgentRegistry,
    ) -> None:
        """Initialize the gateway.

        Args:
            hive_mem: CognitiveMemory instance for the "__hive__" agent.
                      Used for storing promoted facts and searching for
                      contradictions.
            registry: Agent registry for trust lookups.
        """
        self._hive_mem = hive_mem
        # Use the hive_mem's own connection for edge creation so everything
        # is visible through the same kuzu.Database instance.
        self._conn = hive_mem._conn
        self.registry = registry

    def submit_for_promotion(
        self,
        agent_id: str,
        fact_content: str,
        confidence: float,
        concept: str = "",
    ) -> dict:
        """Submit a fact for promotion to the hive.

        Performs validation:
        1. Check agent trust score (reject if below threshold)
        2. Check for contradictions against existing hive facts
        3. If clean and trusted, promote (create PROMOTED_TO_HIVE edge)
        4. If contradiction found, quarantine and create CONTRADICTS edge
        5. If low trust, reject

        Args:
            agent_id: The submitting agent.
            fact_content: The fact text to promote.
            confidence: Confidence score.
            concept: Optional concept/topic label.

        Returns:
            Dict with keys: status ('promoted', 'quarantined', 'rejected'),
            fact_node_id, contradictions (list), reason.
        """
        # Step 1: Check trust
        try:
            agent_info = self.registry.get_agent(agent_id)
        except KeyError:
            return {
                "status": self.REJECTED_STATUS,
                "fact_node_id": None,
                "contradictions": [],
                "reason": f"Agent '{agent_id}' not registered",
            }

        trust = agent_info["trust_score"]
        if trust < self.TRUST_THRESHOLD:
            return {
                "status": self.REJECTED_STATUS,
                "fact_node_id": None,
                "contradictions": [],
                "reason": f"Agent trust score {trust:.2f} below threshold {self.TRUST_THRESHOLD}",
            }

        # Step 2: Store the fact via the hive CognitiveMemory so it's
        # visible through search_facts() on the same instance.
        fact_node_id = self._hive_mem.store_fact(
            concept=concept,
            content=fact_content,
            confidence=confidence,
            source_id=agent_id,
            tags=["hive-promoted", f"from:{agent_id}"],
        )

        # Step 3: Check for contradictions against other hive facts
        contradictions = self.find_contradictions(
            fact_content, concept, exclude_node_id=fact_node_id
        )

        if contradictions:
            # Create CONTRADICTS edges
            for contra in contradictions:
                try:
                    self._conn.execute(
                        """
                        MATCH (a:SemanticMemory), (b:SemanticMemory)
                        WHERE a.node_id = $aid AND b.node_id = $bid
                        CREATE (a)-[:CONTRADICTS {
                            detected_at: $ts,
                            resolution: $res,
                            winner_id: $wid
                        }]->(b)
                        """,
                        {
                            "aid": fact_node_id,
                            "bid": contra["node_id"],
                            "ts": _ts_now(),
                            "res": "unresolved",
                            "wid": "",
                        },
                    )
                except Exception as exc:
                    logger.debug("CONTRADICTS edge creation failed: %s", exc)

            return {
                "status": self.QUARANTINE_STATUS,
                "fact_node_id": fact_node_id,
                "contradictions": contradictions,
                "reason": f"Found {len(contradictions)} potential contradiction(s)",
            }

        # Step 4: Clean promotion -- create PROMOTED_TO_HIVE edge
        try:
            self._conn.execute(
                """
                MATCH (h:HiveAgent), (s:SemanticMemory)
                WHERE h.agent_id = $hid AND s.node_id = $sid
                CREATE (h)-[:PROMOTED_TO_HIVE {
                    promoted_at: $ts,
                    status: $stat
                }]->(s)
                """,
                {
                    "hid": agent_id,
                    "sid": fact_node_id,
                    "ts": _ts_now(),
                    "stat": self.PROMOTED_STATUS,
                },
            )
        except Exception as exc:
            logger.debug("PROMOTED_TO_HIVE edge creation failed: %s", exc)

        # Increment agent's fact count
        self.registry.increment_fact_count(agent_id)

        return {
            "status": self.PROMOTED_STATUS,
            "fact_node_id": fact_node_id,
            "contradictions": [],
            "reason": "Clean promotion",
        }

    def find_contradictions(
        self,
        content: str,
        concept: str,
        exclude_node_id: str = "",
    ) -> list[dict]:
        """Search existing hive facts for potential contradictions.

        A contradiction is a fact with the same concept but different content.
        Only checks facts owned by the hive agent.

        Args:
            content: The fact content to check against.
            concept: The concept/topic to match.
            exclude_node_id: Node to exclude (the fact being checked).

        Returns:
            List of dicts with node_id, concept, content, confidence.
        """
        if not concept:
            return []

        hive_agent_id = self._hive_mem.agent_name
        result = self._conn.execute(
            """
            MATCH (s:SemanticMemory)
            WHERE s.agent_id = $aid
              AND lower(s.concept) = lower($con)
              AND s.content <> $cnt
              AND s.node_id <> $excl
            RETURN s.node_id, s.concept, s.content, s.confidence
            """,
            {
                "aid": hive_agent_id,
                "con": concept,
                "cnt": content,
                "excl": exclude_node_id,
            },
        )
        contradictions = []
        while result.has_next():
            row = result.get_next()
            contradictions.append(
                {
                    "node_id": row[0],
                    "concept": row[1],
                    "content": row[2],
                    "confidence": float(row[3]),
                }
            )
        return contradictions

    def resolve_contradiction(self, fact_a_id: str, fact_b_id: str, winner: str) -> None:
        """Resolve a contradiction by marking the winner.

        Args:
            fact_a_id: One side of the contradiction.
            fact_b_id: Other side of the contradiction.
            winner: The node_id of the winning fact.
        """
        try:
            self._conn.execute(
                """
                MATCH (a:SemanticMemory)-[c:CONTRADICTS]->(b:SemanticMemory)
                WHERE a.node_id = $aid AND b.node_id = $bid
                SET c.resolution = $res, c.winner_id = $wid
                """,
                {
                    "aid": fact_a_id,
                    "bid": fact_b_id,
                    "res": "resolved",
                    "wid": winner,
                },
            )
        except Exception as exc:
            logger.debug("resolve_contradiction failed: %s", exc)


# ---------------------------------------------------------------------------
# KuzuHiveMind
# ---------------------------------------------------------------------------


class KuzuHiveMind:
    """Hive mind backed by real Kuzu graph database.

    Uses a SINGLE kuzu.Database instance for the entire hive.  The bootstrap
    CognitiveMemory (agent_name="__hive__") creates the Database and all base
    tables.  All other components (schema, registry, gateway, per-agent
    memories) share that same Database via additional kuzu.Connection objects.

    Example:
        >>> hive = KuzuHiveMind("/tmp/test_hive")
        >>> mem_a = hive.register_agent("agent_a", domain="biology")
        >>> mem_b = hive.register_agent("agent_b", domain="chemistry")
        >>> hive.store_fact("agent_a", "proteins", "Proteins fold into 3D structures", 0.9)
        >>> result = hive.promote_fact("agent_a", "proteins", "Proteins fold into 3D structures", 0.9)
        >>> hive_facts = hive.query_hive("proteins")
    """

    HIVE_AGENT_ID = "__hive__"

    def __init__(self, db_path: str = "/tmp/hive_test.db") -> None:
        """Initialize the Kuzu-backed hive mind.

        Args:
            db_path: Filesystem path for the shared Kuzu database.
        """
        self.db_path = db_path

        # Phase 1: Create the bootstrap CognitiveMemory.
        # This creates the kuzu.Database AND all base tables (SemanticMemory,
        # EpisodicMemory, etc.) plus the SIMILAR_TO edge.
        self._hive_mem = CognitiveMemory(agent_name=self.HIVE_AGENT_ID, db_path=db_path)

        # Phase 2: Reuse the hive_mem's Database for a second connection
        # dedicated to hive-specific DDL and registry/gateway operations.
        self._shared_db = self._hive_mem._db
        self._admin_conn = kuzu.Connection(self._shared_db)

        # Phase 3: Create hive-specific tables via the admin connection
        self.schema = HiveKuzuSchema(self._admin_conn)
        self.schema.setup()

        # Phase 4: Registry and gateway share the admin connection
        self.registry = AgentRegistry(self._admin_conn)
        self.gateway = HiveGateway(self._hive_mem, self.registry)

        # Per-agent CognitiveMemory instances (share the same Database)
        self._agents: dict[str, CognitiveMemory] = {}

    def register_agent(self, agent_id: str, domain: str = "") -> CognitiveMemory:
        """Register an agent and return its CognitiveMemory instance.

        Args:
            agent_id: Unique agent identifier.
            domain: Domain of expertise.

        Returns:
            CognitiveMemory instance for this agent, sharing the hive DB.

        Raises:
            ValueError: If agent_id is already registered.
        """
        if agent_id in self._agents:
            raise ValueError(f"Agent '{agent_id}' is already registered")

        self.registry.register(agent_id, domain)

        # Create a CognitiveMemory that reuses the shared Database.
        # We construct it manually to avoid creating a second kuzu.Database.
        mem = _make_cognitive_memory(agent_id, self._shared_db, self.db_path)
        self._agents[agent_id] = mem
        return mem

    def store_fact(
        self,
        agent_id: str,
        concept: str,
        content: str,
        confidence: float = 0.8,
        tags: list[str] | None = None,
    ) -> str:
        """Store a fact in the agent's local Kuzu memory.

        Args:
            agent_id: Owning agent.
            concept: Topic/concept label.
            content: Fact text.
            confidence: Confidence score (0.0-1.0).
            tags: Optional categorization tags.

        Returns:
            node_id of the stored fact.

        Raises:
            ValueError: If agent is not registered.
        """
        self._ensure_agent(agent_id)
        mem = self._agents[agent_id]
        return mem.store_fact(
            concept=concept,
            content=content,
            confidence=confidence,
            tags=tags or [],
        )

    def promote_fact(
        self,
        agent_id: str,
        concept: str,
        content: str,
        confidence: float,
    ) -> dict:
        """Promote a fact through the gateway to the hive.

        Args:
            agent_id: Promoting agent.
            concept: Topic/concept label.
            content: Fact text.
            confidence: Confidence score.

        Returns:
            Dict with status ('promoted', 'quarantined', 'rejected'),
            fact_node_id, contradictions, reason.
        """
        self._ensure_agent(agent_id)
        return self.gateway.submit_for_promotion(
            agent_id=agent_id,
            fact_content=content,
            confidence=confidence,
            concept=concept,
        )

    def query_local(self, agent_id: str, query: str, limit: int = 10) -> list[dict]:
        """Query only this agent's local Kuzu memory.

        Args:
            agent_id: Agent whose local memory to search.
            query: Search keywords.
            limit: Maximum results.

        Returns:
            List of fact dicts with node_id, concept, content, confidence,
            source, tags.
        """
        self._ensure_agent(agent_id)
        mem = self._agents[agent_id]
        facts = mem.search_facts(query, limit=limit)
        return [
            {
                "node_id": f.node_id,
                "concept": f.concept,
                "content": f.content,
                "confidence": f.confidence,
                "source": "local",
                "tags": f.tags,
            }
            for f in facts
        ]

    def query_hive(self, query: str, limit: int = 10) -> list[dict]:
        """Query all promoted facts across all agents.

        Args:
            query: Search keywords.
            limit: Maximum results.

        Returns:
            List of fact dicts with node_id, concept, content, confidence,
            source, tags.
        """
        facts = self._hive_mem.search_facts(query, limit=limit)
        return [
            {
                "node_id": f.node_id,
                "concept": f.concept,
                "content": f.content,
                "confidence": f.confidence,
                "source": "hive",
                "tags": f.tags,
            }
            for f in facts
        ]

    def query_all(self, agent_id: str, query: str, limit: int = 20) -> list[dict]:
        """Query local + hive, deduplicate by content hash.

        Args:
            agent_id: Agent for local context.
            query: Search keywords.
            limit: Maximum results.

        Returns:
            Merged, deduplicated list sorted by confidence descending.
        """
        local = self.query_local(agent_id, query, limit=limit)
        hive = self.query_hive(query, limit=limit)

        seen_hashes: set[str] = set()
        merged: list[dict] = []

        for fact in local + hive:
            ch = _content_hash(fact["content"])
            if ch not in seen_hashes:
                seen_hashes.add(ch)
                merged.append(fact)

        merged.sort(key=lambda x: -x.get("confidence", 0.0))
        return merged[:limit]

    def get_stats(self) -> dict:
        """Return hive statistics.

        Returns:
            Dict with agent_count, registered_agents, total_local_facts,
            total_hive_facts, per_agent_stats.
        """
        agents = self.registry.get_all_agents()
        per_agent: dict[str, dict] = {}
        total_local = 0

        for agent_info in agents:
            aid = agent_info["agent_id"]
            mem = self._agents.get(aid)
            if mem is not None:
                stats = mem.get_statistics()
                local_count = stats.get("semantic", 0)
                total_local += local_count
                per_agent[aid] = {
                    "local_facts": local_count,
                    "trust_score": agent_info["trust_score"],
                    "promoted_facts": agent_info["fact_count"],
                    "domain": agent_info["domain"],
                }

        hive_stats = self._hive_mem.get_statistics()
        total_hive = hive_stats.get("semantic", 0)

        return {
            "agent_count": len(agents),
            "registered_agents": [a["agent_id"] for a in agents],
            "total_local_facts": total_local,
            "total_hive_facts": total_hive,
            "per_agent": per_agent,
        }

    def get_agent_memory(self, agent_id: str) -> CognitiveMemory:
        """Get the CognitiveMemory instance for an agent.

        Args:
            agent_id: Agent to look up.

        Returns:
            The agent's CognitiveMemory instance.

        Raises:
            ValueError: If agent is not registered.
        """
        self._ensure_agent(agent_id)
        return self._agents[agent_id]

    def _ensure_agent(self, agent_id: str) -> None:
        """Raise ValueError if agent is not registered."""
        if agent_id not in self._agents:
            raise ValueError(f"Agent '{agent_id}' is not registered. Call register_agent first.")


# ---------------------------------------------------------------------------
# CognitiveMemory factory (reuses shared Database)
# ---------------------------------------------------------------------------


def _make_cognitive_memory(
    agent_name: str, shared_db: kuzu.Database, db_path: str
) -> CognitiveMemory:
    """Create a CognitiveMemory that reuses an existing kuzu.Database.

    CognitiveMemory.__init__ normally creates its own kuzu.Database.
    We bypass this by constructing the object, then overriding _db and _conn
    with a connection from the shared database.

    Args:
        agent_name: Agent identifier.
        shared_db: Existing kuzu.Database to reuse.
        db_path: Path for metadata (not opened again).

    Returns:
        Fully functional CognitiveMemory sharing the given database.
    """
    # Create the object without calling __init__ (to avoid opening a new DB)
    mem = object.__new__(CognitiveMemory)
    mem.agent_name = agent_name.strip()
    mem.db_path = Path(db_path)
    mem._db = shared_db
    mem._conn = kuzu.Connection(shared_db)
    mem.WORKING_MEMORY_CAPACITY = CognitiveMemory.WORKING_MEMORY_CAPACITY

    # Schema is already initialized by the hive_mem bootstrap.
    # Just load the monotonic counters.
    mem._sensory_order = mem._load_max_order("SensoryMemory", "observation_order")
    mem._temporal_index = mem._load_max_order("EpisodicMemory", "temporal_index")

    return mem
