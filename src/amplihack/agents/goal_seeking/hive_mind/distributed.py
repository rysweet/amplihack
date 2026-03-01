"""Distributed Hive Mind: Each agent owns its own independent Kuzu database.

The hive mind is a coordination protocol, NOT a data store. Agents publish
events when they learn, and peers decide locally whether to incorporate.

Architecture:
    AgentNode           -- One agent with its own CognitiveMemory + Kuzu DB
    HiveCoordinator     -- Lightweight in-memory registry (no database)
    DistributedHiveMind -- Orchestrates agent creation, event propagation, routing

Public API:
    AgentNode: Individual agent with local DB
    HiveCoordinator: Registry + expertise map + trust tracking
    DistributedHiveMind: Full distributed system orchestrator
"""

from __future__ import annotations

import logging
import os
import time
from collections import OrderedDict

try:
    import kuzu
    from amplihack_memory.cognitive_memory import CognitiveMemory
except ImportError:
    kuzu = None  # type: ignore[assignment]
    CognitiveMemory = None  # type: ignore[assignment,misc]

try:
    from amplihack_memory.graph import FederatedGraphStore, KuzuGraphStore
except ImportError:
    FederatedGraphStore = None  # type: ignore[assignment,misc]
    KuzuGraphStore = None  # type: ignore[assignment,misc]

from .event_bus import BusEvent, EventBus, LocalEventBus, make_event

# Kuzu default max_db_size is 8TB which can cause Mmap failures when many
# independent databases are opened in the same process.  256MB is sufficient
# for agent-level fact storage and prevents virtual-memory exhaustion.
_DEFAULT_MAX_DB_SIZE = 256 * 1024 * 1024  # 256 MB
_MAX_INCORPORATED_EVENTS = 100_000  # Cap dedup set to prevent unbounded growth

logger = logging.getLogger(__name__)

__all__ = [
    "AgentNode",
    "HiveCoordinator",
    "DistributedHiveMind",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sized_cognitive_memory(
    agent_name: str, db_path: str, max_db_size: int = _DEFAULT_MAX_DB_SIZE
) -> CognitiveMemory:
    """Create a CognitiveMemory with a size-limited Kuzu database.

    The default CognitiveMemory.__init__ creates a kuzu.Database with the
    library default max_db_size (8 TB), which causes Mmap failures when many
    independent databases exist in the same process.  This factory creates
    the kuzu.Database with a controlled size, then constructs the
    CognitiveMemory on top of it.

    Args:
        agent_name: Agent identifier.
        db_path: Filesystem path for the Kuzu database.
        max_db_size: Maximum database size in bytes.

    Returns:
        Fully functional CognitiveMemory with size-limited database.

    Raises:
        ImportError: If kuzu or amplihack-memory-lib is not installed.
    """
    if kuzu is None or CognitiveMemory is None:
        raise ImportError(
            "kuzu and amplihack-memory-lib required. pip install kuzu amplihack-memory-lib"
        )
    from pathlib import Path

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    db = kuzu.Database(str(path), max_db_size=max_db_size)
    conn = kuzu.Connection(db)

    # Build the CognitiveMemory without calling __init__ (to avoid opening
    # a second kuzu.Database at the same path).
    mem = object.__new__(CognitiveMemory)
    mem.agent_name = agent_name.strip()
    mem.db_path = path
    mem._db = db
    mem._conn = conn
    mem.WORKING_MEMORY_CAPACITY = CognitiveMemory.WORKING_MEMORY_CAPACITY

    # Initialize schema (creates all node + rel tables)
    mem._initialize_schema()

    # Load monotonic counters
    mem._sensory_order = mem._load_max_order("SensoryMemory", "observation_order")
    mem._temporal_index = mem._load_max_order("EpisodicMemory", "temporal_index")

    return mem


# ---------------------------------------------------------------------------
# AgentNode
# ---------------------------------------------------------------------------


class AgentNode:
    """A single agent with its own independent Kuzu database.

    Each AgentNode has:
    - Its own CognitiveMemory backed by its own Kuzu directory
    - An optional connection to a hive event bus for peer sharing
    - A dedup set to avoid incorporating the same event twice

    When disconnected from the hive, the agent functions normally with
    its local DB -- joining and leaving are non-destructive operations.
    """

    def __init__(
        self,
        agent_id: str,
        db_dir: str,
        domain: str = "",
        max_db_size: int = _DEFAULT_MAX_DB_SIZE,
        hive_store: KuzuGraphStore | None = None,
    ) -> None:
        """Create an agent with its own independent database.

        Args:
            agent_id: Unique identifier for this agent.
            db_dir: Directory for this agent's Kuzu database.
            domain: Domain of expertise (e.g. "biology", "infrastructure").
            max_db_size: Maximum Kuzu DB size in bytes (default 256 MB).
                         Prevents Mmap exhaustion with many agents.
            hive_store: Optional hive graph store. When provided, a
                FederatedGraphStore is created that composes this agent's
                local graph with the shared hive graph, enabling cross-agent
                graph queries and traversal.
        """
        self.agent_id = agent_id
        self.domain = domain
        self.db_dir = db_dir
        self.memory = _make_sized_cognitive_memory(agent_id, db_dir, max_db_size)
        self._event_bus: EventBus | None = None
        self._coordinator: HiveCoordinator | None = None
        # Bounded dedup tracker: OrderedDict preserves insertion order so
        # we can evict the oldest entries when the cap is reached.
        self._incorporated_events: OrderedDict[str, None] = OrderedDict()

        # Federated graph: local agent graph + shared hive graph
        if hive_store is not None and KuzuGraphStore is not None:
            # Share the Kuzu DB instance from CognitiveMemory to avoid
            # opening a second database at the same path (Mmap error)
            local_graph = KuzuGraphStore(
                db_path=db_dir,
                store_id=agent_id,
                db=self.memory._db,  # share existing DB instance
            )
            local_graph._known_node_tables.add("SemanticMemory")
            self._federated: FederatedGraphStore | None = FederatedGraphStore(
                local_store=local_graph,
                hive_store=hive_store,
            )
        else:
            self._federated = None

    def learn(
        self,
        concept: str,
        content: str,
        confidence: float = 0.8,
        tags: list[str] | None = None,
    ) -> str:
        """Learn a fact into local DB. Publishes to hive if connected.

        Args:
            concept: Topic or concept label.
            content: The fact content.
            confidence: Confidence score (0.0 - 1.0).
            tags: Optional categorization tags.

        Returns:
            node_id of the stored fact.
        """
        resolved_tags = tags or []
        node_id = self.memory.store_fact(
            concept=concept,
            content=content,
            confidence=confidence,
            tags=resolved_tags,
        )
        # Publish event if connected to hive
        if self._event_bus is not None:
            event = make_event(
                event_type="FACT_LEARNED",
                source_agent=self.agent_id,
                payload={
                    "concept": concept,
                    "content": content,
                    "confidence": confidence,
                    "tags": resolved_tags,
                    "node_id": node_id,
                },
            )
            self._event_bus.publish(event)
            # Report to coordinator for expertise tracking
            if self._coordinator is not None:
                self._coordinator.report_fact(self.agent_id, concept)
        return node_id

    def query(self, query: str, limit: int = 10) -> list[dict]:
        """Query this agent's local DB only.

        Args:
            query: Search keywords.
            limit: Maximum results.

        Returns:
            List of fact dicts with node_id, concept, content, confidence, tags.
        """
        facts = self.memory.search_facts(query, limit=limit)
        return [
            {
                "node_id": f.node_id,
                "concept": f.concept,
                "content": f.content,
                "confidence": f.confidence,
                "tags": f.tags,
                "source_agent": self.agent_id,
            }
            for f in facts
        ]

    def get_all_facts(self, limit: int = 500) -> list[dict]:
        """Return all facts in this agent's local DB.

        Args:
            limit: Maximum facts to return.

        Returns:
            List of fact dicts.
        """
        facts = self.memory.get_all_facts(limit=limit)
        return [
            {
                "node_id": f.node_id,
                "concept": f.concept,
                "content": f.content,
                "confidence": f.confidence,
                "tags": f.tags,
                "source_agent": self.agent_id,
            }
            for f in facts
        ]

    def query_federated(self, query: str, limit: int = 10):
        """Query local + hive via the federated graph.

        When a hive_store was provided at construction, this queries both
        the agent's local graph and the shared hive graph, deduplicates
        results, and annotates them with source provenance.

        Falls back to local-only query when no federated graph is available.

        Args:
            query: Search query string.
            limit: Maximum results.

        Returns:
            FederatedQueryResult when federated graph available, otherwise
            a list of fact dicts from local-only query.
        """
        if self._federated is not None:
            return self._federated.federated_query(query, limit=limit)
        return self.query(query, limit)

    @property
    def federated(self) -> FederatedGraphStore | None:
        """Access the federated graph store, or None if not connected."""
        return self._federated

    def incorporate_peer_fact(self, event: BusEvent) -> bool:
        """Decide whether to incorporate a peer's fact into local DB.

        Peer facts are stored with discounted confidence (0.9x) and tagged
        with the source agent for provenance tracking.

        Args:
            event: A FACT_LEARNED or FACT_PROMOTED event from a peer.

        Returns:
            True if incorporated, False if rejected (duplicate or self-event).
        """
        if event.event_id in self._incorporated_events:
            return False
        if event.source_agent == self.agent_id:
            return False

        payload = event.payload
        peer_confidence = payload.get("confidence", 0.5) * 0.9
        peer_tags = list(payload.get("tags", []))
        peer_tags.append(f"from:{event.source_agent}")

        self.memory.store_fact(
            concept=payload.get("concept", ""),
            content=payload.get("content", ""),
            confidence=peer_confidence,
            tags=peer_tags,
        )
        # Add to bounded dedup tracker, evicting oldest if at capacity.
        self._incorporated_events[event.event_id] = None
        if len(self._incorporated_events) > _MAX_INCORPORATED_EVENTS:
            self._incorporated_events.popitem(last=False)  # evict oldest
        return True

    def join_hive(self, event_bus: EventBus, coordinator: HiveCoordinator) -> None:
        """Join the hive mind network.

        Args:
            event_bus: Event bus for publishing and receiving events.
            coordinator: Hive coordinator for registration and routing.
        """
        self._event_bus = event_bus
        self._coordinator = coordinator
        event_bus.subscribe(self.agent_id, ["FACT_LEARNED", "FACT_PROMOTED"])
        coordinator.register_agent(self.agent_id, self.domain)

    def leave_hive(self) -> None:
        """Leave the hive network. Local DB is completely unaffected."""
        if self._event_bus is not None:
            self._event_bus.unsubscribe(self.agent_id)
        if self._coordinator is not None:
            self._coordinator.unregister_agent(self.agent_id)
        self._event_bus = None
        self._coordinator = None

    def process_pending_events(self) -> int:
        """Process all pending events from the bus.

        Returns:
            Number of facts successfully incorporated.
        """
        if self._event_bus is None:
            return 0
        events = self._event_bus.poll(self.agent_id)
        count = 0
        for event in events:
            if self.incorporate_peer_fact(event):
                count += 1
        return count

    @property
    def is_connected(self) -> bool:
        """Whether this agent is currently connected to a hive."""
        return self._event_bus is not None

    def get_fact_count(self) -> int:
        """Count of facts in this agent's local DB."""
        stats = self.memory.get_statistics()
        return stats.get("semantic", 0)


# ---------------------------------------------------------------------------
# HiveCoordinator
# ---------------------------------------------------------------------------


class HiveCoordinator:
    """Lightweight coordinator for the distributed hive.

    NOT a database. Maintains in-memory state about who is in the hive,
    what they know, and trust scores. This is the virtual overlay that
    enables expertise routing without shared storage.
    """

    DEFAULT_TRUST = 1.0
    _MAX_CONTRADICTIONS = 10_000

    def __init__(self) -> None:
        # agent_id -> {domain, joined_at, fact_count, topics}
        self._agents: dict[str, dict] = {}
        # topic -> set of agent_ids -- who knows about what
        self._expertise: dict[str, set[str]] = {}
        # agent_id -> trust score
        self._trust: dict[str, float] = {}
        # detected contradictions (capped at _MAX_CONTRADICTIONS, newest kept)
        self._contradictions: list[dict] = []

    def register_agent(self, agent_id: str, domain: str = "") -> None:
        """Register an agent as participating in the hive.

        Args:
            agent_id: Unique identifier for the agent.
            domain: Domain of expertise.
        """
        self._agents[agent_id] = {
            "domain": domain,
            "joined_at": time.time(),
            "fact_count": 0,
            "topics": set(),
        }
        self._trust[agent_id] = self.DEFAULT_TRUST

        # Index domain as expertise
        if domain:
            for keyword in domain.lower().split():
                if keyword not in self._expertise:
                    self._expertise[keyword] = set()
                self._expertise[keyword].add(agent_id)

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the hive. Its local DB is unaffected.

        Args:
            agent_id: Agent to remove.
        """
        self._agents.pop(agent_id, None)
        self._trust.pop(agent_id, None)
        # Clean up expertise index
        for topic, agents in list(self._expertise.items()):
            agents.discard(agent_id)
            if not agents:
                del self._expertise[topic]

    def get_experts(self, topic: str) -> list[str]:
        """Which agents know about this topic?

        Args:
            topic: Topic keyword to search for.

        Returns:
            List of agent_ids sorted by trust (highest first).
        """
        topic_lower = topic.lower()
        matching_agents: set[str] = set()

        # Match against expertise keywords
        for keyword, agents in self._expertise.items():
            if topic_lower in keyword or keyword in topic_lower:
                matching_agents.update(agents)

        # Also check agent domains directly
        for agent_id, info in self._agents.items():
            domain = info.get("domain", "").lower()
            if topic_lower in domain or domain in topic_lower:
                matching_agents.add(agent_id)

        # Sort by trust descending
        sorted_agents = sorted(
            matching_agents,
            key=lambda a: self._trust.get(a, 0.0),
            reverse=True,
        )
        return sorted_agents

    def route_query(self, query: str) -> list[str]:
        """Route a query to the most relevant agents.

        Splits query into keywords and finds agents with matching expertise.
        Falls back to all agents if no specific experts found.

        Args:
            query: Query string.

        Returns:
            Ordered list of agent_ids (most relevant first).
        """
        keywords = [w.strip().lower() for w in query.split() if w.strip()]
        if not keywords:
            return list(self._agents.keys())

        # Collect agents matching any keyword, tracking match count
        agent_scores: dict[str, int] = {}
        for kw in keywords:
            experts = self.get_experts(kw)
            for agent_id in experts:
                agent_scores[agent_id] = agent_scores.get(agent_id, 0) + 1

        # Also check topics each agent has reported facts about
        for agent_id, info in self._agents.items():
            topics = info.get("topics", set())
            for kw in keywords:
                for topic in topics:
                    if kw in topic.lower():
                        agent_scores[agent_id] = agent_scores.get(agent_id, 0) + 1

        if not agent_scores:
            # No specific experts -- return all agents sorted by trust
            return sorted(
                self._agents.keys(),
                key=lambda a: self._trust.get(a, 0.0),
                reverse=True,
            )

        # Sort by match count * trust
        return sorted(
            agent_scores.keys(),
            key=lambda a: agent_scores[a] * self._trust.get(a, 1.0),
            reverse=True,
        )

    def report_fact(self, agent_id: str, concept: str) -> None:
        """Agent reports it has learned a fact about a concept.

        Updates the expertise map so future queries can route to this agent.

        Args:
            agent_id: The reporting agent.
            concept: The concept the fact is about.
        """
        if agent_id not in self._agents:
            return
        self._agents[agent_id]["fact_count"] = self._agents[agent_id].get("fact_count", 0) + 1
        self._agents[agent_id].setdefault("topics", set()).add(concept.lower())

        # Update expertise index
        for keyword in concept.lower().split():
            if keyword not in self._expertise:
                self._expertise[keyword] = set()
            self._expertise[keyword].add(agent_id)

    def check_trust(self, agent_id: str) -> float:
        """Get trust score for an agent.

        Args:
            agent_id: Agent to check.

        Returns:
            Trust score (default 1.0, range [0.0, 2.0]).
        """
        return self._trust.get(agent_id, 0.0)

    def update_trust(self, agent_id: str, delta: float) -> None:
        """Adjust an agent's trust score.

        Args:
            agent_id: Agent to update.
            delta: Amount to add (positive) or subtract (negative).
        """
        current = self._trust.get(agent_id, self.DEFAULT_TRUST)
        self._trust[agent_id] = max(0.0, min(2.0, current + delta))

    def report_contradiction(self, fact_a: dict, fact_b: dict) -> None:
        """Report a detected contradiction between two agents' facts.

        Args:
            fact_a: First fact dict (must include source_agent, content).
            fact_b: Second fact dict (must include source_agent, content).
        """
        self._contradictions.append(
            {
                "fact_a": fact_a,
                "fact_b": fact_b,
                "detected_at": time.time(),
                "resolved": False,
            }
        )
        # Cap the list to prevent unbounded growth, keeping most recent
        if len(self._contradictions) > self._MAX_CONTRADICTIONS:
            self._contradictions = self._contradictions[-self._MAX_CONTRADICTIONS :]

    def resolve_contradiction(self, index: int) -> bool:
        """Mark a contradiction as resolved by index.

        Args:
            index: Zero-based index into the contradictions list.

        Returns:
            True if the contradiction was marked resolved, False if index is out of range.
        """
        if 0 <= index < len(self._contradictions):
            self._contradictions[index]["resolved"] = True
            return True
        return False

    def get_hive_stats(self) -> dict:
        """Stats about the hive.

        Returns:
            Dict with agent_count, agents, total_facts, expertise_topics,
            contradictions_count. All values are JSON-serializable.
        """
        total_facts = sum(info.get("fact_count", 0) for info in self._agents.values())
        return {
            "agent_count": len(self._agents),
            "agents": {
                aid: {
                    "domain": info["domain"],
                    "trust": self._trust.get(aid, 0.0),
                    "fact_count": info.get("fact_count", 0),
                    "topics": sorted(info.get("topics", set())),
                }
                for aid, info in self._agents.items()
            },
            "total_facts_reported": total_facts,
            "expertise_topics": sorted(self._expertise.keys()),
            "contradictions_count": len(self._contradictions),
        }


# ---------------------------------------------------------------------------
# DistributedHiveMind
# ---------------------------------------------------------------------------


class DistributedHiveMind:
    """Distributed hive mind where each agent owns its own database.

    The hive mind is a coordination protocol, not a data store.
    Agents communicate through an event bus and the coordinator
    maintains a lightweight registry for expertise routing.

    Example:
        >>> hive = DistributedHiveMind("/tmp/test_hive")
        >>> agent_a = hive.create_agent("agent_a", domain="biology")
        >>> agent_b = hive.create_agent("agent_b", domain="chemistry")
        >>> agent_a.learn("biology", "DNA has a double helix", 0.95)
        >>> hive.propagate()  # agent_b now has the fact in its local DB
        >>> results = agent_b.query("DNA helix")
    """

    def __init__(
        self,
        base_dir: str,
        event_bus: EventBus | None = None,
    ) -> None:
        """Create a distributed hive mind.

        Args:
            base_dir: Base directory. Each agent gets base_dir/agent_id/kuzu_db.
            event_bus: Event bus for communication. Defaults to LocalEventBus.
        """
        self.base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)
        self.event_bus = event_bus or LocalEventBus()
        self.coordinator = HiveCoordinator()
        self._agents: dict[str, AgentNode] = {}

    def create_agent(self, agent_id: str, domain: str = "") -> AgentNode:
        """Create a new agent with its own independent Kuzu database.

        Args:
            agent_id: Unique identifier.
            domain: Domain of expertise.

        Returns:
            The new AgentNode, already joined to the hive.

        Raises:
            ValueError: If agent_id already exists.
        """
        if agent_id in self._agents:
            raise ValueError(f"Agent '{agent_id}' already exists in hive")

        agent_dir = os.path.join(self.base_dir, agent_id, "kuzu_db")
        agent = AgentNode(agent_id, agent_dir, domain)
        agent.join_hive(self.event_bus, self.coordinator)
        self._agents[agent_id] = agent
        return agent

    def get_agent(self, agent_id: str) -> AgentNode:
        """Get an existing agent by ID.

        Args:
            agent_id: Agent to look up.

        Returns:
            The AgentNode.

        Raises:
            KeyError: If agent not found.
        """
        if agent_id not in self._agents:
            raise KeyError(f"Agent '{agent_id}' not found in hive")
        return self._agents[agent_id]

    def propagate(self) -> dict[str, int]:
        """All agents process pending events from the bus.

        Each agent polls its mailbox and incorporates relevant peer facts.

        Returns:
            Dict of agent_id -> number of facts incorporated.
        """
        results: dict[str, int] = {}
        for agent_id, agent in self._agents.items():
            count = agent.process_pending_events()
            results[agent_id] = count
        return results

    def query_routed(
        self,
        asking_agent: str,
        query: str,
        limit: int = 10,
    ) -> list[dict]:
        """Query using expertise routing -- asks the RIGHT agents, not all.

        The coordinator determines which agents are most likely to have
        relevant knowledge and queries them first.

        Args:
            asking_agent: ID of the agent making the query.
            query: Search query.
            limit: Maximum results.

        Returns:
            List of fact dicts from the most relevant agents.
        """
        experts = self.coordinator.route_query(query)
        results: list[dict] = []
        seen_content: set[str] = set()

        for expert_id in experts[:3]:  # Top 3 experts
            if expert_id in self._agents:
                agent_results = self._agents[expert_id].query(query, limit=limit)
                for fact in agent_results:
                    content_key = fact["content"].strip().lower()
                    if content_key not in seen_content:
                        seen_content.add(content_key)
                        results.append(fact)

        return results[:limit]

    def query_all_agents(self, query: str, limit: int = 10) -> list[dict]:
        """Query ALL agents (broadcast) and merge results.

        Args:
            query: Search query.
            limit: Maximum results.

        Returns:
            Deduplicated, merged results sorted by confidence.
        """
        results: list[dict] = []
        seen_content: set[str] = set()

        for agent in self._agents.values():
            agent_results = agent.query(query, limit=limit)
            for fact in agent_results:
                content_key = fact["content"].strip().lower()
                if content_key not in seen_content:
                    seen_content.add(content_key)
                    results.append(fact)

        results.sort(key=lambda x: -x.get("confidence", 0.0))
        return results[:limit]

    def remove_agent(self, agent_id: str) -> None:
        """Remove agent from hive. Its local DB directory remains intact.

        Args:
            agent_id: Agent to remove.

        Raises:
            KeyError: If agent not found.
        """
        if agent_id not in self._agents:
            raise KeyError(f"Agent '{agent_id}' not found in hive")
        agent = self._agents.pop(agent_id)
        agent.leave_hive()

    def get_stats(self) -> dict:
        """Stats about the distributed hive.

        Returns:
            Dict with agent_count, coordinator_stats, per_agent facts.
        """
        per_agent: dict[str, dict] = {}
        for agent_id, agent in self._agents.items():
            per_agent[agent_id] = {
                "domain": agent.domain,
                "fact_count": agent.get_fact_count(),
                "connected": agent.is_connected,
                "db_dir": agent.db_dir,
            }
        return {
            "agent_count": len(self._agents),
            "per_agent": per_agent,
            "coordinator": self.coordinator.get_hive_stats(),
        }

    def close(self) -> None:
        """Shut down the hive: disconnect all agents, close event bus."""
        for agent in list(self._agents.values()):
            agent.leave_hive()
        self._agents.clear()
        self.event_bus.close()
