"""HiveGraph -- Protocol for distributed hive mind graph backends.

Supports multiple implementations:
- InMemoryHiveGraph: in-process dict-based implementation

Also supports federation: trees of hive minds where a hive can
contain sub-hives, with fact escalation and query routing up/down
the tree.

Philosophy:
- Single responsibility: define the graph contract and provide a working
  in-memory implementation
- Runtime-checkable Protocol so any backend can be validated with isinstance()
- Federation is core, not optional -- trees of hive minds from day one

Public API (the "studs"):
    HiveAgent: Agent node dataclass
    HiveFact: Fact node dataclass
    HiveEdge: Edge dataclass
    HiveGraph: Protocol defining the contract
    InMemoryHiveGraph: Dict-based implementation
    create_hive_graph: Factory for backend selection
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .constants import (
    BROADCAST_TAG_PREFIX,
    CONFIDENCE_SCORE_BOOST,
    DEFAULT_BROADCAST_THRESHOLD,
    DEFAULT_CONTRADICTION_OVERLAP,
    DEFAULT_TRUST_SCORE,
    DOMAIN_ROUTING_PRIORITY_MULTIPLIER,
    ESCALATION_TAG_PREFIX,
    FACT_ID_HEX_LENGTH,
    FEDERATED_QUERY_LIMIT_MULTIPLIER,
    FEDERATED_QUERY_MIN_LIMIT,
    GOSSIP_TAG_PREFIX,
    MAX_TRUST_SCORE,
    SECONDS_PER_HOUR,
)

logger = logging.getLogger(__name__)

# Graceful imports for retrieval pipeline modules
try:
    from .embeddings import EmbeddingGenerator as _EmbeddingGeneratorType

    _HAS_EMBEDDINGS = True
except ImportError:
    _EmbeddingGeneratorType = None  # type: ignore[assignment,misc]
    _HAS_EMBEDDINGS = False

try:
    from .reranker import hybrid_score_weighted, rrf_merge

    _HAS_RERANKER = True
except ImportError:
    _HAS_RERANKER = False

# Graceful imports for CRDT, gossip, and fact lifecycle modules
try:
    from .crdt import LWWRegister, ORSet

    _HAS_CRDT = True
except ImportError:
    _HAS_CRDT = False

try:
    from .gossip import run_gossip_round as _run_gossip_round

    _HAS_GOSSIP = True
except ImportError:
    _HAS_GOSSIP = False

try:
    from .fact_lifecycle import FactTTL, decay_confidence, gc_expired_facts

    _HAS_LIFECYCLE = True
except ImportError:
    _HAS_LIFECYCLE = False

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class HiveAgent:
    """An agent registered in the hive.

    Attributes:
        agent_id: Unique agent identifier.
        domain: Domain of expertise (e.g. "biology", "infrastructure").
        trust: Trust score, clamped to [0.0, 2.0]. Default 1.0.
        fact_count: Number of facts this agent has promoted.
        status: Agent status: "active", "suspended", "removed".
    """

    agent_id: str
    domain: str = ""
    trust: float = DEFAULT_TRUST_SCORE
    fact_count: int = 0
    status: str = "active"


@dataclass
class HiveFact:
    """A fact stored in the hive graph.

    Attributes:
        fact_id: Unique fact identifier.
        content: The factual text content.
        concept: Topic or concept this fact relates to.
        confidence: Confidence score (0.0-1.0).
        source_agent: ID of the agent that contributed this fact.
        tags: Categorization tags.
        status: Fact status: "promoted", "quarantined", "contradicted", "retracted".
        embedding: Optional dense vector for semantic search.
        created_at: Unix timestamp when the fact was created.
    """

    fact_id: str
    content: str
    concept: str = ""
    confidence: float = 0.8
    source_agent: str = ""
    tags: list[str] = field(default_factory=list)
    status: str = "promoted"
    embedding: Any = None
    created_at: float = field(default_factory=time.time)


@dataclass
class HiveEdge:
    """An edge in the hive graph.

    Attributes:
        source_id: Source node ID (agent_id or fact_id).
        target_id: Target node ID (agent_id or fact_id).
        edge_type: Edge type: PROMOTED, CONTRADICTS, CONFIRMED_BY, PARENT_HIVE.
        properties: Arbitrary key-value properties on the edge.
    """

    source_id: str
    target_id: str
    edge_type: str
    properties: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class HiveGraph(Protocol):
    """Protocol for distributed hive mind graph backends.

    Defines the full contract: agent registry, fact management, graph edges,
    contradiction detection, expertise routing, federation, stats, lifecycle.

    Any backend (in-memory, P2P Raft, ArangoDB, Redis, Neo4j) must satisfy
    this protocol.
    """

    @property
    def hive_id(self) -> str:
        """Unique identifier for this hive."""
        ...

    # -- Agent registry -------------------------------------------------------

    def register_agent(
        self, agent_id: str, domain: str = "", trust: float = DEFAULT_TRUST_SCORE
    ) -> None:
        """Register an agent in the hive."""
        ...

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the hive."""
        ...

    def get_agent(self, agent_id: str) -> HiveAgent | None:
        """Retrieve an agent by ID, or None if not found."""
        ...

    def list_agents(self) -> list[HiveAgent]:
        """List all registered agents."""
        ...

    def update_trust(self, agent_id: str, trust: float) -> None:
        """Set an agent's trust score (clamped to [0.0, MAX_TRUST_SCORE])."""
        ...

    # -- Fact management -------------------------------------------------------

    def promote_fact(self, agent_id: str, fact: HiveFact) -> str:
        """Promote a fact into the hive. Returns fact_id."""
        ...

    def get_fact(self, fact_id: str) -> HiveFact | None:
        """Retrieve a fact by ID, or None if not found."""
        ...

    def query_facts(self, query: str, limit: int = 20) -> list[HiveFact]:
        """Search facts by keyword query."""
        ...

    def retract_fact(self, fact_id: str) -> bool:
        """Retract a fact. Returns True if found and retracted."""
        ...

    # -- Graph edges -----------------------------------------------------------

    def add_edge(self, edge: HiveEdge) -> None:
        """Add an edge to the graph."""
        ...

    def get_edges(self, node_id: str, edge_type: str | None = None) -> list[HiveEdge]:
        """Get edges for a node, optionally filtered by type."""
        ...

    # -- Contradiction detection -----------------------------------------------

    def check_contradictions(self, content: str, concept: str) -> list[HiveFact]:
        """Find existing facts that may contradict the given content/concept."""
        ...

    # -- Expertise routing -----------------------------------------------------

    def route_query(self, query: str) -> list[str]:
        """Find agent IDs whose domain overlaps with the query keywords."""
        ...

    # -- Federation ------------------------------------------------------------

    def set_parent(self, parent: HiveGraph) -> None:
        """Set the parent hive in the federation tree."""
        ...

    def add_child(self, child: HiveGraph) -> None:
        """Add a child hive to the federation tree."""
        ...

    def escalate_fact(self, fact: HiveFact) -> bool:
        """Promote a fact to the parent hive. Returns True if parent accepted."""
        ...

    def broadcast_fact(self, fact: HiveFact) -> int:
        """Push a fact to all children. Returns count of children that received it."""
        ...

    def query_federated(self, query: str, limit: int = 20) -> list[HiveFact]:
        """Query local + parent + children for facts matching query."""
        ...

    # -- Stats & lifecycle -----------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return hive statistics."""
        ...

    def close(self) -> None:
        """Release resources."""
        ...


# ---------------------------------------------------------------------------
# InMemoryHiveGraph
# ---------------------------------------------------------------------------


def _new_fact_id() -> str:
    """Generate a unique fact ID."""
    return f"hf_{uuid.uuid4().hex[:FACT_ID_HEX_LENGTH]}"


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase word set, stripping short words."""
    return {w.lower() for w in text.split() if len(w) > 1}


def _federated_keyword_score(fact: Any, keywords: set[str]) -> float:
    """Compute keyword-based score for federated query re-ranking."""
    fact_words = _tokenize(f"{fact.content} {fact.concept}")
    hits = len(keywords & fact_words)
    return hits + fact.confidence * CONFIDENCE_SCORE_BOOST


def _word_overlap(a: str, b: str) -> float:
    """Compute Jaccard word overlap between two strings."""
    words_a = _tokenize(a)
    words_b = _tokenize(b)
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union) if union else 0.0


class InMemoryHiveGraph:
    """In-memory implementation of HiveGraph for testing.

    Not distributed -- all state lives in Python dicts. Useful for unit tests
    and single-process scenarios.

    Args:
        hive_id: Unique identifier for this hive instance.

    Example:
        >>> hive = InMemoryHiveGraph("test-hive")
        >>> hive.register_agent("agent_a", domain="biology")
        >>> fid = hive.promote_fact("agent_a", HiveFact(
        ...     fact_id="f1", content="DNA stores info", concept="genetics"))
        >>> results = hive.query_facts("DNA genetics")
        >>> assert len(results) >= 1
    """

    def __init__(
        self,
        hive_id: str = "test-hive",
        broadcast_threshold: float = DEFAULT_BROADCAST_THRESHOLD,
        embedding_generator: Any | None = None,
        enable_gossip: bool = False,
        enable_ttl: bool = False,
    ) -> None:
        self._hive_id = hive_id
        self._broadcast_threshold = max(0.0, min(1.0, broadcast_threshold))
        self._agents: dict[str, HiveAgent] = {}
        self._facts: dict[str, HiveFact] = {}
        self._edges: list[HiveEdge] = []
        self._parent: HiveGraph | None = None
        self._children: list[HiveGraph] = []
        self._lock = threading.RLock()
        # Embedding support: when provided, promote_fact generates embeddings
        # and query_facts uses vector search as primary signal
        self._embedding_generator = embedding_generator
        self._embeddings: dict[str, list[float]] = {}  # fact_id -> embedding vector

        # CRDT backing stores (graceful: no-op if crdt module unavailable)
        if _HAS_CRDT:
            self._fact_set: ORSet = ORSet()
            self._trust_registers: dict[str, LWWRegister] = {}

        # Gossip protocol (requires gossip module)
        self._enable_gossip = enable_gossip and _HAS_GOSSIP
        self._gossip_peers: list[Any] = []

        # Fact lifecycle / TTL (requires fact_lifecycle module)
        self._enable_ttl = enable_ttl and _HAS_LIFECYCLE
        self._ttl_registry: dict[str, Any] = {}
        self._original_confidences: dict[str, float] = {}  # for correct repeated decay

    # -- Property --------------------------------------------------------------

    @property
    def hive_id(self) -> str:
        """Unique identifier for this hive."""
        return self._hive_id

    # -- Agent registry --------------------------------------------------------

    def register_agent(
        self, agent_id: str, domain: str = "", trust: float = DEFAULT_TRUST_SCORE
    ) -> None:
        """Register an agent in the hive.

        Args:
            agent_id: Unique agent identifier.
            domain: Domain of expertise.
            trust: Initial trust score.

        Raises:
            ValueError: If agent_id is already registered.
        """
        with self._lock:
            if agent_id in self._agents:
                raise ValueError(f"Agent '{agent_id}' already registered")
            clamped_trust = max(0.0, min(MAX_TRUST_SCORE, trust))
            self._agents[agent_id] = HiveAgent(
                agent_id=agent_id,
                domain=domain,
                trust=clamped_trust,
                fact_count=0,
                status="active",
            )
            if _HAS_CRDT:
                reg = LWWRegister()
                reg.set(clamped_trust, time.time())
                self._trust_registers[agent_id] = reg

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the hive.

        Args:
            agent_id: Agent to remove.

        Raises:
            KeyError: If agent_id not found.
        """
        with self._lock:
            if agent_id not in self._agents:
                raise KeyError(f"Agent '{agent_id}' not found")
            del self._agents[agent_id]
            if _HAS_CRDT:
                self._trust_registers.pop(agent_id, None)

    def get_agent(self, agent_id: str) -> HiveAgent | None:
        """Retrieve an agent by ID, or None if not found."""
        with self._lock:
            return self._agents.get(agent_id)

    def list_agents(self) -> list[HiveAgent]:
        """List all registered (active) agents."""
        with self._lock:
            return list(self._agents.values())

    def update_trust(self, agent_id: str, trust: float) -> None:
        """Set an agent's trust score.

        Args:
            agent_id: Agent to update.
            trust: New trust score (clamped to [0.0, 2.0]).

        Raises:
            KeyError: If agent not found.
        """
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                raise KeyError(f"Agent '{agent_id}' not found")
            clamped = max(0.0, min(MAX_TRUST_SCORE, trust))
            agent.trust = clamped
            if _HAS_CRDT:
                if agent_id not in self._trust_registers:
                    self._trust_registers[agent_id] = LWWRegister()
                self._trust_registers[agent_id].set(clamped, time.time())

    # -- Fact management -------------------------------------------------------

    def promote_fact(self, agent_id: str, fact: HiveFact) -> str:
        """Promote a fact into the hive.

        If fact.fact_id is empty, generates one. Records the source agent
        and increments their fact count. Confidence is clamped to [0.0, 1.0].

        When this hive has a parent and the fact's confidence >= 0.9,
        the fact is automatically broadcast to sibling groups via the parent
        (Proposal 4: cross-group replication for high-confidence facts).

        Args:
            agent_id: The promoting agent.
            fact: The fact to promote.

        Returns:
            The fact_id (generated if empty).

        Raises:
            KeyError: If agent_id not registered.
        """
        with self._lock:
            if agent_id not in self._agents:
                raise KeyError(f"Agent '{agent_id}' not registered")

            if not fact.fact_id:
                fact.fact_id = _new_fact_id()

            fact.source_agent = agent_id
            fact.confidence = max(0.0, min(1.0, fact.confidence))
            self._facts[fact.fact_id] = fact
            self._agents[agent_id].fact_count += 1
            fact_id = fact.fact_id

            # Track in ORSet for CRDT-based merge
            if _HAS_CRDT:
                self._fact_set.add(fact.fact_id)

            # Register TTL metadata when lifecycle is enabled
            if self._enable_ttl:
                self._ttl_registry[fact.fact_id] = FactTTL(
                    fact_id=fact.fact_id,
                    created_at=fact.created_at,
                )
                self._original_confidences[fact.fact_id] = fact.confidence

            # Generate embedding if generator available
            if self._embedding_generator is not None:
                try:
                    text = f"{fact.content} {fact.concept}".strip()
                    emb = self._embedding_generator.embed(text)
                    if emb is not None:
                        # Convert numpy arrays to plain lists if needed
                        self._embeddings[fact.fact_id] = (
                            emb.tolist() if hasattr(emb, "tolist") else list(emb)
                        )
                except Exception:
                    logger.debug("Failed to generate embedding for fact %s", fact.fact_id)

            # Snapshot state under lock for thread-safe post-lock operations
            fact_tags = list(fact.tags)
            fact_confidence = fact.confidence
            parent_ref = self._parent
            broadcast_threshold = self._broadcast_threshold
            gossip_enabled = self._enable_gossip
            gossip_peers = list(self._gossip_peers) if self._gossip_peers else []

        # Proposal 4: Auto-replicate high-confidence facts to sibling groups.
        # Guard: only broadcast original facts (not already-broadcast copies)
        # to prevent infinite recursion (child->parent->child->...).
        is_broadcast_copy = any(
            t.startswith(BROADCAST_TAG_PREFIX) or t.startswith(ESCALATION_TAG_PREFIX)
            for t in fact_tags
        )
        if (
            fact_confidence >= broadcast_threshold
            and parent_ref is not None
            and not is_broadcast_copy
        ):
            self.escalate_fact(fact)
            parent_ref.broadcast_fact(fact)

        # Auto-gossip on promote when gossip is enabled
        if gossip_enabled and gossip_peers:
            is_gossip_copy = any(t.startswith(GOSSIP_TAG_PREFIX) for t in fact_tags)
            if not is_gossip_copy and not is_broadcast_copy:
                try:
                    _run_gossip_round(self, gossip_peers)
                except Exception:
                    logger.debug("Auto-gossip failed for fact %s", fact_id)

        return fact_id

    def get_fact(self, fact_id: str) -> HiveFact | None:
        """Retrieve a fact by ID, or None if not found."""
        with self._lock:
            return self._facts.get(fact_id)

    def query_facts(self, query: str, limit: int = 20) -> list[HiveFact]:
        """Search facts by keyword query, with optional vector search.

        When an embedding_generator is available, uses vector search as
        the primary signal with hybrid scoring (semantic_similarity 0.5 +
        confirmation_count 0.3 + source_trust 0.2). Falls back to keyword
        search if embeddings unavailable or vector search fails.

        Args:
            query: Space-separated keywords.
            limit: Maximum results.

        Returns:
            List of matching HiveFact.
        """
        with self._lock:
            # Apply confidence decay before scoring when TTL is enabled
            if self._enable_ttl:
                self._apply_ttl_decay()

            if not query or not query.strip():
                return list(self._facts.values())[:limit]

            # Try vector search first when embeddings are available
            if self._embedding_generator is not None and self._embeddings and _HAS_RERANKER:
                try:
                    return self._vector_query(query, limit)
                except Exception:
                    logger.debug("Vector search failed, falling back to keyword search")

            # Keyword fallback
            return self._keyword_query(query, limit)

    def _cosine_sim(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import math

        if len(a) != len(b) or not a:
            # Pad shorter vector
            max_len = max(len(a), len(b))
            a = a + [0.0] * (max_len - len(a))
            b = b + [0.0] * (max_len - len(b))
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _vector_query(self, query: str, limit: int) -> list[HiveFact]:
        """Vector search with hybrid scoring. Must be called under lock."""
        query_emb = self._embedding_generator.embed(query)
        if query_emb is None:
            return self._keyword_query(query, limit)
        query_vec = query_emb.tolist() if hasattr(query_emb, "tolist") else list(query_emb)

        scored: list[tuple[float, HiveFact]] = []
        for fact in self._facts.values():
            if fact.status == "retracted":
                continue
            fact_emb = self._embeddings.get(fact.fact_id)
            if fact_emb is None:
                continue
            sim = self._cosine_sim(query_vec, fact_emb)
            # Count confirmations from edges
            conf_count = sum(
                1
                for e in self._edges
                if e.target_id == fact.fact_id and e.edge_type == "CONFIRMED_BY"
            )
            agent = self._agents.get(fact.source_agent)
            trust = agent.trust if agent else DEFAULT_TRUST_SCORE
            score = hybrid_score_weighted(
                semantic_similarity=sim,
                confirmation_count=conf_count,
                source_trust=trust,
            )
            scored.append((score, fact))

        scored.sort(key=lambda x: (-x[0], -x[1].confidence))
        return [f for _, f in scored[:limit]]

    def _keyword_query(self, query: str, limit: int) -> list[HiveFact]:
        """Keyword-based search. Must be called under lock."""
        keywords = _tokenize(query)
        if not keywords:
            return list(self._facts.values())[:limit]

        scored: list[tuple[float, HiveFact]] = []
        for fact in self._facts.values():
            if fact.status == "retracted":
                continue
            fact_words = _tokenize(f"{fact.content} {fact.concept}")
            hits = len(keywords & fact_words)
            if hits > 0:
                score = hits + fact.confidence * CONFIDENCE_SCORE_BOOST
                scored.append((score, fact))

        scored.sort(key=lambda x: (-x[0], -x[1].confidence))
        return [f for _, f in scored[:limit]]

    def retract_fact(self, fact_id: str) -> bool:
        """Retract a fact. Returns True if found and retracted."""
        with self._lock:
            fact = self._facts.get(fact_id)
            if fact is None:
                return False
            fact.status = "retracted"
            if _HAS_CRDT:
                self._fact_set.remove(fact_id)
            return True

    # -- Graph edges -----------------------------------------------------------

    def add_edge(self, edge: HiveEdge) -> None:
        """Add an edge to the graph."""
        with self._lock:
            self._edges.append(edge)

    def get_edges(self, node_id: str, edge_type: str | None = None) -> list[HiveEdge]:
        """Get edges for a node, optionally filtered by type.

        Returns edges where node_id is either source or target.
        """
        with self._lock:
            results: list[HiveEdge] = []
            for e in self._edges:
                if e.source_id == node_id or e.target_id == node_id:
                    if edge_type is None or e.edge_type == edge_type:
                        results.append(e)
            return results

    # -- Contradiction detection -----------------------------------------------

    def check_contradictions(self, content: str, concept: str) -> list[HiveFact]:
        """Find existing facts that may contradict the given content.

        A contradiction requires:
        1. Same concept (case-insensitive)
        2. Word overlap > 0.4 (Jaccard similarity)
        3. Different content

        Args:
            content: The new fact content to check.
            concept: The concept/topic to match.

        Returns:
            List of potentially contradicting HiveFact.
        """
        if not concept:
            return []

        with self._lock:
            contradictions: list[HiveFact] = []
            concept_lower = concept.lower()

            for fact in self._facts.values():
                if fact.status == "retracted":
                    continue
                if fact.concept.lower() != concept_lower:
                    continue
                if fact.content == content:
                    continue
                overlap = _word_overlap(content, fact.content)
                if overlap > DEFAULT_CONTRADICTION_OVERLAP:
                    contradictions.append(fact)

            return contradictions

    # -- Expertise routing -----------------------------------------------------

    def route_query(self, query: str) -> list[str]:
        """Find agent IDs whose domain overlaps with query keywords.

        Returns agents sorted by overlap score descending.
        """
        if not query or not query.strip():
            return []

        query_words = _tokenize(query)
        if not query_words:
            return []

        with self._lock:
            scored: list[tuple[float, str]] = []
            for agent in self._agents.values():
                if agent.status != "active":
                    continue
                domain_words = _tokenize(agent.domain)
                if not domain_words:
                    continue
                hits = len(query_words & domain_words)
                if hits > 0:
                    scored.append((hits, agent.agent_id))

        scored.sort(key=lambda x: -x[0])
        return [agent_id for _, agent_id in scored]

    # -- Federation ------------------------------------------------------------

    def set_parent(self, parent: HiveGraph) -> None:
        """Set the parent hive in the federation tree."""
        with self._lock:
            self._parent = parent

    def add_child(self, child: HiveGraph) -> None:
        """Add a child hive to the federation tree.

        Duplicate children (by hive_id) are silently ignored.
        """
        with self._lock:
            existing_ids = {c.hive_id for c in self._children}
            if child.hive_id not in existing_ids:
                self._children.append(child)

    def escalate_fact(self, fact: HiveFact) -> bool:
        """Promote a fact to the parent hive.

        Creates a synthetic "__escalated__" agent in the parent if needed,
        then promotes the fact there.

        Returns:
            True if parent accepted the fact, False if no parent.
        """
        if self._parent is None:
            return False

        # Ensure a relay agent exists in the parent for escalated facts
        relay_id = f"__relay_{self._hive_id}__"
        if self._parent.get_agent(relay_id) is None:
            self._parent.register_agent(relay_id, domain="relay")

        # Create a copy of the fact with a new ID for the parent
        escalated = HiveFact(
            fact_id=_new_fact_id(),
            content=fact.content,
            concept=fact.concept,
            confidence=fact.confidence,
            source_agent=fact.source_agent,
            tags=list(fact.tags) + [f"{ESCALATION_TAG_PREFIX}{self._hive_id}"],
            status="promoted",
        )
        self._parent.promote_fact(relay_id, escalated)

        # Add a PARENT_HIVE edge
        self._parent.add_edge(
            HiveEdge(
                source_id=self._hive_id,
                target_id=escalated.fact_id,
                edge_type="PARENT_HIVE",
                properties={"child_hive": self._hive_id},
            )
        )
        return True

    def broadcast_fact(self, fact: HiveFact) -> int:
        """Push a fact to all children.

        Creates a relay agent in each child if needed.

        Returns:
            Count of children that received the fact.
        """
        count = 0
        for child in self._children:
            relay_id = f"__relay_{self._hive_id}__"
            if child.get_agent(relay_id) is None:
                child.register_agent(relay_id, domain="relay")

            broadcast_copy = HiveFact(
                fact_id=_new_fact_id(),
                content=fact.content,
                concept=fact.concept,
                confidence=fact.confidence,
                source_agent=fact.source_agent,
                tags=list(fact.tags) + [f"{BROADCAST_TAG_PREFIX}{self._hive_id}"],
                status="promoted",
            )
            child.promote_fact(relay_id, broadcast_copy)
            count += 1
        return count

    def query_federated(
        self,
        query: str,
        limit: int = 20,
        _visited: set[str] | None = None,
    ) -> list[HiveFact]:
        """Query the entire federation tree for facts matching query.

        Two-phase approach (Proposals 1+2):
          Phase 1: Collect ALL matching facts from every hive in the tree
                   (no per-hive cap — Proposal 1).
          Phase 2: Global re-rank by keyword score, return top-K.

        Query routing (Proposal 3): Children whose agents have matching
        domains get 3x the internal limit, ensuring domain-relevant groups
        contribute more facts to the global pool.

        Args:
            query: Space-separated keywords.
            limit: Maximum results.
            _visited: Internal — hive_ids already queried (prevents loops).

        Returns:
            Merged, deduplicated list of HiveFact sorted by keyword relevance.
        """
        if _visited is None:
            _visited = set()
        if self._hive_id in _visited:
            return []
        _visited.add(self._hive_id)

        # Proposal 1: Remove the 2000 cap. Use uncapped 10x multiplier so
        # global re-ranking sees ALL candidates from each hive.
        internal_limit = max(limit * FEDERATED_QUERY_LIMIT_MULTIPLIER, FEDERATED_QUERY_MIN_LIMIT)

        # Phase 1: Collect from local hive
        results = list(self.query_facts(query, limit=internal_limit))
        seen_content: set[str] = {f.content for f in results}

        # Snapshot parent/children under lock for thread safety
        with self._lock:
            parent = self._parent
            children = list(self._children)

        # Proposal 3: Query routing — identify which children have agents
        # whose domains match the query. Give those children 3x the limit.
        keywords = _tokenize(query)
        priority_child_ids: set[str] = set()
        if keywords:
            for child in children:
                routed = child.route_query(query)
                if routed:
                    priority_child_ids.add(child.hive_id)

        # Parent (recursive, with visited set to prevent loops)
        if parent is not None:
            parent_results = parent.query_federated(
                query,
                limit=internal_limit,
                _visited=_visited,
            )
            for f in parent_results:
                if f.content not in seen_content:
                    seen_content.add(f.content)
                    results.append(f)

        # Children (recursive, with routing-based limits)
        for child in children:
            child_limit = (
                internal_limit * DOMAIN_ROUTING_PRIORITY_MULTIPLIER
                if child.hive_id in priority_child_ids
                else internal_limit
            )
            child_results = child.query_federated(
                query,
                limit=child_limit,
                _visited=_visited,
            )
            for f in child_results:
                if f.content not in seen_content:
                    seen_content.add(f.content)
                    results.append(f)

        # Phase 2: Global re-ranking
        # Use RRF merge when multiple sources contributed facts
        # (keyword ranking + confidence ranking), with graceful fallback
        has_multi_source = len(children) > 0 or parent is not None
        if keywords and _HAS_RERANKER and has_multi_source:
            try:
                keyword_ranked = sorted(
                    results, key=lambda f: -_federated_keyword_score(f, keywords)
                )
                confidence_ranked = sorted(results, key=lambda f: -f.confidence)
                scored_facts = rrf_merge(
                    keyword_ranked,
                    confidence_ranked,
                    key="fact_id",
                    limit=len(results),
                )
                results = [sf.fact for sf in scored_facts]
            except Exception:
                logger.debug("RRF merge failed, falling back to keyword re-ranking")
                results.sort(key=lambda f: (-_federated_keyword_score(f, keywords), -f.confidence))
        elif keywords:
            results.sort(key=lambda f: (-_federated_keyword_score(f, keywords), -f.confidence))
        else:
            results.sort(key=lambda f: -f.confidence)

        return results[:limit]

    # -- TTL decay (private) ---------------------------------------------------

    def _apply_ttl_decay(self) -> None:
        """Apply confidence decay to facts with TTL entries. Must be called under lock."""
        now = time.time()
        for fact_id, ttl in self._ttl_registry.items():
            fact = self._facts.get(fact_id)
            if fact is not None and fact.status != "retracted":
                original = self._original_confidences.get(fact_id, fact.confidence)
                elapsed_hours = (now - ttl.created_at) / SECONDS_PER_HOUR
                if elapsed_hours > 0:
                    fact.confidence = decay_confidence(
                        original, elapsed_hours, ttl.confidence_decay_rate
                    )

    # -- CRDT merge ------------------------------------------------------------

    def merge_state(self, other: InMemoryHiveGraph) -> None:
        """Merge CRDTs from another hive replica for eventual consistency.

        Merges ORSets (fact membership) and LWWRegisters (agent trust).
        When CRDTs are unavailable, this is a no-op.

        Args:
            other: Another InMemoryHiveGraph to merge state from.
        """
        if not _HAS_CRDT:
            return

        with self._lock:
            # Merge fact ORSets
            self._fact_set.merge(other._fact_set)

            # Copy HiveFact objects from other that we don't have yet
            for fact_id, fact in other._facts.items():
                if fact_id not in self._facts:
                    self._facts[fact_id] = HiveFact(
                        fact_id=fact.fact_id,
                        content=fact.content,
                        concept=fact.concept,
                        confidence=fact.confidence,
                        source_agent=fact.source_agent,
                        tags=list(fact.tags),
                        status=fact.status,
                        embedding=fact.embedding,
                        created_at=fact.created_at,
                    )

            # Sync fact status with ORSet membership (add-wins semantics)
            live_ids = self._fact_set.items
            for fact_id, fact in self._facts.items():
                if fact_id not in live_ids and fact.status != "retracted":
                    fact.status = "retracted"
                elif fact_id in live_ids and fact.status == "retracted":
                    fact.status = "promoted"

            # Merge trust LWWRegisters and sync agent trust values
            for agent_id, reg in other._trust_registers.items():
                if agent_id not in self._trust_registers:
                    self._trust_registers[agent_id] = LWWRegister()
                self._trust_registers[agent_id].merge(reg)
                merged_trust = self._trust_registers[agent_id].get()
                if merged_trust is not None and agent_id in self._agents:
                    self._agents[agent_id].trust = max(0.0, min(MAX_TRUST_SCORE, merged_trust))

    # -- Gossip ----------------------------------------------------------------

    def run_gossip(self, peers: list[Any]) -> dict[str, list[str]]:
        """Run a gossip round, sharing top facts with selected peers.

        Stores the peer list for automatic gossip on future promote_fact calls
        (when enable_gossip=True).

        Args:
            peers: List of HiveGraph peers to gossip with.

        Returns:
            Dict mapping peer hive_id to list of shared fact_ids.
            Empty dict if gossip module unavailable.
        """
        self._gossip_peers = list(peers)
        if not _HAS_GOSSIP:
            return {}
        return _run_gossip_round(self, peers)

    # -- Garbage collection ----------------------------------------------------

    def gc(self) -> list[str]:
        """Garbage-collect expired facts based on TTL.

        Returns:
            List of fact_ids that were garbage-collected.
            Empty list if TTL is not enabled.
        """
        if not self._enable_ttl:
            return []
        removed = gc_expired_facts(self, self._ttl_registry)
        # Clean up original confidence records for GC'd facts
        for fid in removed:
            self._original_confidences.pop(fid, None)
        return removed

    # -- Stats & lifecycle -----------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return hive statistics."""
        with self._lock:
            active_facts = sum(1 for f in self._facts.values() if f.status != "retracted")
            return {
                "hive_id": self._hive_id,
                "agent_count": len(self._agents),
                "fact_count": len(self._facts),
                "active_facts": active_facts,
                "edge_count": len(self._edges),
                "has_parent": self._parent is not None,
                "child_count": len(self._children),
            }

    def close(self) -> None:
        """Release resources (no-op for in-memory)."""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_hive_graph(backend: str = "memory", **config: Any) -> HiveGraph:
    """Factory for HiveGraph backends.

    Args:
        backend: Backend type: "memory".
        **config: Backend-specific configuration.
            For "memory": hive_id (str)

    Returns:
        A HiveGraph implementation.

    Raises:
        ValueError: If backend is unknown.
    """
    if backend == "memory":
        return InMemoryHiveGraph(hive_id=config.get("hive_id", "test-hive"))
    raise ValueError(f"Unknown backend: {backend!r}. Available: memory")


__all__ = [
    "HiveAgent",
    "HiveFact",
    "HiveEdge",
    "HiveGraph",
    "InMemoryHiveGraph",
    "create_hive_graph",
]
