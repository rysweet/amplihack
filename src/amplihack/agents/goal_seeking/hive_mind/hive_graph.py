"""HiveGraph -- Protocol for distributed hive mind graph backends.

Supports multiple implementations:
- InMemoryHiveGraph: testing (no network)
- PeerHiveGraph: agents ARE the store (Raft consensus via pysyncobj)
- ArangoHiveGraph: ArangoDB cluster (future)
- RedisHiveGraph: Redis Cluster (future)

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
    InMemoryHiveGraph: Dict-based implementation for testing
    create_hive_graph: Factory for backend selection
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

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
    trust: float = 1.0
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
    """

    fact_id: str
    content: str
    concept: str = ""
    confidence: float = 0.8
    source_agent: str = ""
    tags: list[str] = field(default_factory=list)
    status: str = "promoted"


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

    def register_agent(self, agent_id: str, domain: str = "", trust: float = 1.0) -> None:
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
        """Set an agent's trust score (clamped to [0.0, 2.0])."""
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
    return f"hf_{uuid.uuid4().hex[:12]}"


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase word set, stripping short words."""
    return {w.lower() for w in text.split() if len(w) > 1}


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

    def __init__(self, hive_id: str = "test-hive") -> None:
        self._hive_id = hive_id
        self._agents: dict[str, HiveAgent] = {}
        self._facts: dict[str, HiveFact] = {}
        self._edges: list[HiveEdge] = []
        self._parent: HiveGraph | None = None
        self._children: list[HiveGraph] = []

    # -- Property --------------------------------------------------------------

    @property
    def hive_id(self) -> str:
        """Unique identifier for this hive."""
        return self._hive_id

    # -- Agent registry --------------------------------------------------------

    def register_agent(self, agent_id: str, domain: str = "", trust: float = 1.0) -> None:
        """Register an agent in the hive.

        Args:
            agent_id: Unique agent identifier.
            domain: Domain of expertise.
            trust: Initial trust score.

        Raises:
            ValueError: If agent_id is already registered.
        """
        if agent_id in self._agents:
            raise ValueError(f"Agent '{agent_id}' already registered")
        self._agents[agent_id] = HiveAgent(
            agent_id=agent_id,
            domain=domain,
            trust=max(0.0, min(2.0, trust)),
            fact_count=0,
            status="active",
        )

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the hive.

        Args:
            agent_id: Agent to remove.

        Raises:
            KeyError: If agent_id not found.
        """
        if agent_id not in self._agents:
            raise KeyError(f"Agent '{agent_id}' not found")
        self._agents[agent_id].status = "removed"
        del self._agents[agent_id]

    def get_agent(self, agent_id: str) -> HiveAgent | None:
        """Retrieve an agent by ID, or None if not found."""
        return self._agents.get(agent_id)

    def list_agents(self) -> list[HiveAgent]:
        """List all registered (active) agents."""
        return list(self._agents.values())

    def update_trust(self, agent_id: str, trust: float) -> None:
        """Set an agent's trust score.

        Args:
            agent_id: Agent to update.
            trust: New trust score (clamped to [0.0, 2.0]).

        Raises:
            KeyError: If agent not found.
        """
        agent = self._agents.get(agent_id)
        if agent is None:
            raise KeyError(f"Agent '{agent_id}' not found")
        agent.trust = max(0.0, min(2.0, trust))

    # -- Fact management -------------------------------------------------------

    def promote_fact(self, agent_id: str, fact: HiveFact) -> str:
        """Promote a fact into the hive.

        If fact.fact_id is empty, generates one. Records the source agent
        and increments their fact count.

        Args:
            agent_id: The promoting agent.
            fact: The fact to promote.

        Returns:
            The fact_id (generated if empty).

        Raises:
            KeyError: If agent_id not registered.
        """
        if agent_id not in self._agents:
            raise KeyError(f"Agent '{agent_id}' not registered")

        if not fact.fact_id:
            fact.fact_id = _new_fact_id()

        fact.source_agent = agent_id
        self._facts[fact.fact_id] = fact
        self._agents[agent_id].fact_count += 1
        return fact.fact_id

    def get_fact(self, fact_id: str) -> HiveFact | None:
        """Retrieve a fact by ID, or None if not found."""
        return self._facts.get(fact_id)

    def query_facts(self, query: str, limit: int = 20) -> list[HiveFact]:
        """Search facts by keyword query.

        Scores each fact by counting how many query keywords appear
        in either its content or concept. Returns top matches sorted
        by score descending, then confidence descending.

        Args:
            query: Space-separated keywords.
            limit: Maximum results.

        Returns:
            List of matching HiveFact.
        """
        if not query or not query.strip():
            return list(self._facts.values())[:limit]

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
                # Score: keyword hits + confidence as tiebreaker
                score = hits + fact.confidence * 0.01
                scored.append((score, fact))

        scored.sort(key=lambda x: (-x[0], -x[1].confidence))
        return [f for _, f in scored[:limit]]

    def retract_fact(self, fact_id: str) -> bool:
        """Retract a fact. Returns True if found and retracted."""
        fact = self._facts.get(fact_id)
        if fact is None:
            return False
        fact.status = "retracted"
        return True

    # -- Graph edges -----------------------------------------------------------

    def add_edge(self, edge: HiveEdge) -> None:
        """Add an edge to the graph."""
        self._edges.append(edge)

    def get_edges(self, node_id: str, edge_type: str | None = None) -> list[HiveEdge]:
        """Get edges for a node, optionally filtered by type.

        Returns edges where node_id is either source or target.
        """
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
            if overlap > 0.4:
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
        self._parent = parent

    def add_child(self, child: HiveGraph) -> None:
        """Add a child hive to the federation tree."""
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
            tags=list(fact.tags) + [f"escalated_from:{self._hive_id}"],
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
                tags=list(fact.tags) + [f"broadcast_from:{self._hive_id}"],
                status="promoted",
            )
            child.promote_fact(relay_id, broadcast_copy)
            count += 1
        return count

    def query_federated(self, query: str, limit: int = 20) -> list[HiveFact]:
        """Query local + parent + children for facts matching query.

        Deduplicates by content to avoid returning the same fact from
        multiple levels of the tree.

        Args:
            query: Space-separated keywords.
            limit: Maximum results.

        Returns:
            Merged, deduplicated list of HiveFact sorted by confidence.
        """
        # Local results
        results = list(self.query_facts(query, limit=limit))
        seen_content: set[str] = {f.content for f in results}

        # Parent results
        if self._parent is not None:
            parent_results = self._parent.query_facts(query, limit=limit)
            for f in parent_results:
                if f.content not in seen_content:
                    seen_content.add(f.content)
                    results.append(f)

        # Children results
        for child in self._children:
            child_results = child.query_facts(query, limit=limit)
            for f in child_results:
                if f.content not in seen_content:
                    seen_content.add(f.content)
                    results.append(f)

        # Sort by confidence descending, limit
        results.sort(key=lambda f: -f.confidence)
        return results[:limit]

    # -- Stats & lifecycle -----------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return hive statistics."""
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
        backend: Backend type: "memory", "p2p".
        **config: Backend-specific configuration.
            For "memory": hive_id (str)
            For "p2p": hive_id (str), self_address (str), peer_addresses (list[str])

    Returns:
        A HiveGraph implementation.

    Raises:
        ValueError: If backend is unknown.
    """
    if backend == "memory":
        return InMemoryHiveGraph(hive_id=config.get("hive_id", "test-hive"))
    if backend == "p2p":
        from .peer_hive import PeerHiveGraph

        return PeerHiveGraph(**config)
    raise ValueError(f"Unknown backend: {backend!r}. Available: memory, p2p")


__all__ = [
    "HiveAgent",
    "HiveFact",
    "HiveEdge",
    "HiveGraph",
    "InMemoryHiveGraph",
    "create_hive_graph",
]
