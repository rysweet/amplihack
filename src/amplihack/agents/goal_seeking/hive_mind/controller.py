"""Desired-state HiveController that reads YAML config and reconciles actual
state to match.

Replaces the imperative HiveDeployer with a declarative, Kubernetes-style
controller.  You declare the desired state in a HiveManifest (from YAML or
dict), then call ``controller.apply()`` to converge the running system.

Architecture:
    HiveManifest    -- Desired state declaration (from YAML / dict)
    HiveState       -- Snapshot of actual running state
    HiveController  -- Reconciliation loop: desired -> actual
    InMemoryGraphStore -- Lightweight graph store for testing (no PG/Kuzu)

Public API:
    HiveManifest: Desired state for the hive mind system
    HiveState: Actual running state snapshot
    HiveController: Reconciliation controller
    GraphStoreConfig: Graph store configuration
    EventBusConfig: Event bus configuration
    AgentSpec: Per-agent desired state
    GatewayConfig: Gateway configuration
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Imports with fallback guards
# ---------------------------------------------------------------------------

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

try:
    from amplihack_memory.cognitive_memory import CognitiveMemory
except ImportError:
    CognitiveMemory = None  # type: ignore[assignment,misc]

try:
    from amplihack_memory.graph import KuzuGraphStore
except ImportError:
    KuzuGraphStore = None  # type: ignore[assignment,misc]

try:
    from .distributed import (
        AgentNode,
        HiveCoordinator,
        _make_sized_cognitive_memory,
    )
except ImportError:
    AgentNode = None  # type: ignore[assignment,misc]
    HiveCoordinator = None  # type: ignore[assignment,misc]
    _make_sized_cognitive_memory = None  # type: ignore[assignment]

try:
    from .event_bus import LocalEventBus, create_event_bus
except ImportError:
    LocalEventBus = None  # type: ignore[assignment,misc]
    create_event_bus = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# InMemoryGraphStore -- dict-based, no external dependencies
# ---------------------------------------------------------------------------


class InMemoryGraphStore:
    """Lightweight in-memory graph store for testing.

    Stores facts as dicts in memory.  Implements just enough of the graph store
    interface for the HiveController + HiveGateway to work without Kuzu or
    Postgres.  Not suitable for production.
    """

    def __init__(self, store_id: str = "memory") -> None:
        self._store_id = store_id
        self._facts: dict[str, dict[str, Any]] = {}
        self._agents: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []

    @property
    def store_id(self) -> str:
        return self._store_id

    def store_fact(
        self,
        concept: str,
        content: str,
        confidence: float = 0.8,
        source_id: str = "",
        tags: list[str] | None = None,
    ) -> str:
        """Store a fact and return its node_id."""
        node_id = f"mem_{uuid.uuid4().hex[:12]}"
        self._facts[node_id] = {
            "node_id": node_id,
            "concept": concept,
            "content": content,
            "confidence": confidence,
            "source_id": source_id,
            "tags": tags or [],
            "created_at": time.time(),
        }
        return node_id

    def search_facts(self, query: str, limit: int = 10) -> list[dict]:
        """Keyword search across stored facts."""
        keywords = [w.strip().lower() for w in query.split() if w.strip()]
        if not keywords:
            return list(self._facts.values())[:limit]

        scored: list[tuple[int, dict]] = []
        for fact in self._facts.values():
            text = f"{fact['concept']} {fact['content']}".lower()
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                scored.append((score, fact))

        scored.sort(key=lambda x: (-x[0], -x[1].get("confidence", 0.0)))
        return [f for _, f in scored[:limit]]

    def get_all_facts(self, limit: int = 500) -> list[dict]:
        """Return all stored facts."""
        return list(self._facts.values())[:limit]

    def get_statistics(self) -> dict:
        """Return basic stats."""
        return {"semantic": len(self._facts)}

    def close(self) -> None:
        """No-op: in-memory store has no external resources to release.

        Data is preserved so that references to this store remain valid
        after close().  Use clear() to explicitly wipe data.
        """

    def clear(self) -> None:
        """Explicitly destroy all in-memory data."""
        self._facts.clear()
        self._agents.clear()
        self._edges.clear()


# ---------------------------------------------------------------------------
# InMemoryGateway -- lightweight gateway for in-memory backend
# ---------------------------------------------------------------------------


class InMemoryGateway:
    """Gateway that validates facts before promotion to the hive.

    Works with InMemoryGraphStore instead of Kuzu-backed CognitiveMemory.
    Performs trust checks and contradiction detection using in-memory data.
    """

    def __init__(
        self,
        store: InMemoryGraphStore,
        trust_threshold: float = 0.3,
        contradiction_overlap: float = 0.4,
        consensus_required: int = 2,
    ) -> None:
        self._store = store
        self._trust_threshold = trust_threshold
        self._contradiction_overlap = contradiction_overlap
        self._consensus_required = consensus_required
        self._agent_trust: dict[str, float] = {}

    def set_trust(self, agent_id: str, trust: float) -> None:
        """Set trust score for an agent."""
        self._agent_trust[agent_id] = max(0.0, min(2.0, trust))

    def get_trust(self, agent_id: str) -> float:
        """Get trust score for an agent."""
        return self._agent_trust.get(agent_id, 1.0)

    def submit_for_promotion(
        self,
        agent_id: str,
        fact_content: str,
        confidence: float,
        concept: str = "",
    ) -> dict:
        """Submit a fact for promotion through the gateway.

        Performs:
        1. Trust check -- reject if below threshold
        2. Store the fact in the hive store
        3. Check for contradictions against existing facts
        4. Return status dict

        Args:
            agent_id: Promoting agent.
            fact_content: Fact text.
            confidence: Confidence score.
            concept: Topic/concept label.

        Returns:
            Dict with status, fact_node_id, contradictions, reason.
        """
        trust = self.get_trust(agent_id)
        if trust < self._trust_threshold:
            return {
                "status": "rejected",
                "fact_node_id": None,
                "contradictions": [],
                "reason": f"Agent trust {trust:.2f} below threshold {self._trust_threshold}",
            }

        # Store the fact
        node_id = self._store.store_fact(
            concept=concept,
            content=fact_content,
            confidence=confidence,
            source_id=agent_id,
            tags=["hive-promoted", f"from:{agent_id}"],
        )

        # Check for contradictions
        contradictions = self._find_contradictions(fact_content, concept, exclude_node_id=node_id)

        if contradictions:
            return {
                "status": "quarantined",
                "fact_node_id": node_id,
                "contradictions": contradictions,
                "reason": f"Found {len(contradictions)} potential contradiction(s)",
            }

        return {
            "status": "promoted",
            "fact_node_id": node_id,
            "contradictions": [],
            "reason": "Clean promotion",
        }

    def _find_contradictions(
        self,
        content: str,
        concept: str,
        exclude_node_id: str = "",
    ) -> list[dict]:
        """Search for contradictions among existing hive facts."""
        if not concept:
            return []

        candidates = []
        for fact in self._store._facts.values():
            if fact["node_id"] == exclude_node_id:
                continue
            if fact["concept"].lower() != concept.lower():
                continue
            if fact["content"] == content:
                continue
            overlap = self._word_overlap(content, fact["content"])
            if overlap >= self._contradiction_overlap:
                candidates.append(
                    {
                        "node_id": fact["node_id"],
                        "concept": fact["concept"],
                        "content": fact["content"],
                        "confidence": fact["confidence"],
                        "overlap": overlap,
                    }
                )
        return candidates

    @staticmethod
    def _word_overlap(a: str, b: str) -> float:
        """Jaccard word overlap between two strings."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0


# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------


@dataclass
class GraphStoreConfig:
    """Configuration for the hive's graph store backend.

    Attributes:
        backend: Store type -- "memory", "postgres+age", or "kuzu".
        connection_string: Connection string for postgres/remote backends.
        graph_name: Name of the graph in the backend.
        db_path: Filesystem path for kuzu backend.
    """

    backend: str = "memory"
    connection_string: str = ""
    graph_name: str = "hive_mind"
    db_path: str = ""


@dataclass
class EventBusConfig:
    """Configuration for the hive's event bus.

    Attributes:
        backend: Bus type -- "local", "pg_notify", "azure_service_bus".
        connection_string: Connection string for remote backends.
    """

    backend: str = "local"
    connection_string: str = ""


@dataclass
class AgentSpec:
    """Desired state for a single agent.

    Attributes:
        agent_id: Unique identifier for this agent.
        domain: Domain of expertise (e.g. "biology", "infrastructure").
        replicas: Number of replicas (reserved for future use, currently 1).
    """

    agent_id: str
    domain: str = ""
    replicas: int = 1


@dataclass
class GatewayConfig:
    """Configuration for the promotion gateway.

    Attributes:
        trust_threshold: Minimum trust score for promotion (0.0-2.0).
        contradiction_overlap: Word overlap threshold for contradiction detection.
        consensus_required: Number of confirmations needed (reserved).
    """

    trust_threshold: float = 0.3
    contradiction_overlap: float = 0.4
    consensus_required: int = 2


@dataclass
class HiveManifest:
    """Desired state for the entire hive mind system.

    Declarative configuration that tells HiveController what the running
    system should look like.  Like a Kubernetes manifest: you declare the
    desired state, and the controller reconciles.

    Attributes:
        name: Human-readable name for this hive.
        graph_store: Graph store backend configuration.
        event_bus: Event bus configuration.
        agents: List of desired agent specifications.
        gateway: Gateway (promotion validation) configuration.
    """

    name: str = "default-hive"
    graph_store: GraphStoreConfig = field(default_factory=GraphStoreConfig)
    event_bus: EventBusConfig = field(default_factory=EventBusConfig)
    agents: list[AgentSpec] = field(default_factory=list)
    gateway: GatewayConfig = field(default_factory=GatewayConfig)

    @classmethod
    def from_yaml(cls, path: str) -> HiveManifest:
        """Load manifest from a YAML file with environment variable substitution.

        Supports ``${VAR_NAME}`` syntax in string values, replaced with
        ``os.environ.get(VAR_NAME, "")``.

        Args:
            path: Filesystem path to the YAML file.

        Returns:
            Parsed HiveManifest.

        Raises:
            ImportError: If PyYAML is not installed.
            FileNotFoundError: If path does not exist.
        """
        if yaml is None:
            raise ImportError(
                "PyYAML is required for YAML loading. Install it with: pip install pyyaml"
            )
        with open(path) as f:
            raw = yaml.safe_load(f)

        raw = _substitute_env_vars(raw)
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, data: dict) -> HiveManifest:
        """Load manifest from a dictionary.

        Args:
            data: Dictionary with manifest fields.

        Returns:
            Parsed HiveManifest.
        """
        graph_store = GraphStoreConfig(
            **{
                k: v
                for k, v in data.get("graph_store", {}).items()
                if k in GraphStoreConfig.__dataclass_fields__
            }
        )
        event_bus = EventBusConfig(
            **{
                k: v
                for k, v in data.get("event_bus", {}).items()
                if k in EventBusConfig.__dataclass_fields__
            }
        )
        agents = [
            AgentSpec(**{k: v for k, v in a.items() if k in AgentSpec.__dataclass_fields__})
            for a in data.get("agents", [])
        ]
        gateway = GatewayConfig(
            **{
                k: v
                for k, v in data.get("gateway", {}).items()
                if k in GatewayConfig.__dataclass_fields__
            }
        )
        return cls(
            name=data.get("name", "default-hive"),
            graph_store=graph_store,
            event_bus=event_bus,
            agents=agents,
            gateway=gateway,
        )


# ---------------------------------------------------------------------------
# Environment variable substitution
# ---------------------------------------------------------------------------


def _substitute_env_vars(obj: Any) -> Any:
    """Recursively substitute ${VAR_NAME} in string values.

    Uses os.environ.get(VAR_NAME, '') for undefined variables.
    """
    if isinstance(obj, str):
        return re.sub(
            r"\$\{(\w+)\}",
            lambda m: os.environ.get(m.group(1), ""),
            obj,
        )
    if isinstance(obj, dict):
        return {k: _substitute_env_vars(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_substitute_env_vars(item) for item in obj]
    return obj


# ---------------------------------------------------------------------------
# HiveState -- actual state snapshot
# ---------------------------------------------------------------------------


@dataclass
class HiveState:
    """Snapshot of the actual running hive state.

    Attributes:
        agents: Mapping of agent_id to status dict (status, domain, fact_count).
        hive_store_connected: Whether the hive graph store is connected.
        event_bus_connected: Whether the event bus is connected.
    """

    agents: dict[str, dict] = field(default_factory=dict)
    hive_store_connected: bool = False
    event_bus_connected: bool = False


# ---------------------------------------------------------------------------
# HiveController -- desired-state reconciliation
# ---------------------------------------------------------------------------


class HiveController:
    """Desired-state reconciliation controller for the distributed hive.

    Like a Kubernetes controller: reads desired state from a HiveManifest,
    compares with actual state, and takes actions to converge.

    Key property: ``apply()`` is idempotent.  Calling it twice with the same
    manifest is a no-op.

    Example:
        >>> manifest = HiveManifest.from_dict({
        ...     "name": "test-hive",
        ...     "agents": [{"agent_id": "bio", "domain": "biology"}],
        ... })
        >>> ctrl = HiveController(manifest)
        >>> state = ctrl.apply()
        >>> assert len(state.agents) == 1
        >>> ctrl.shutdown()
    """

    def __init__(self, manifest: HiveManifest) -> None:
        self.manifest = manifest
        self._hive_store: InMemoryGraphStore | Any = None
        self._event_bus: Any = None
        self._agents: dict[str, AgentNode] = {}
        self._coordinator: HiveCoordinator | None = None
        self._gateway: InMemoryGateway | None = None
        self._base_dir: str = ""
        self._owns_base_dir: bool = False

    # ------------------------------------------------------------------
    # Core reconciliation
    # ------------------------------------------------------------------

    def apply(self) -> HiveState:
        """Apply the manifest -- create/destroy agents to match desired state.

        Idempotent: calling apply() twice with the same manifest is a no-op.

        Returns:
            Current HiveState after reconciliation.
        """
        # 1. Ensure hive graph store is connected
        self._ensure_hive_store()

        # 2. Ensure event bus is connected
        self._ensure_event_bus()

        # 3. Ensure coordinator exists
        if self._coordinator is None:
            if HiveCoordinator is None:
                raise ImportError(
                    "HiveCoordinator unavailable. pip install kuzu amplihack-memory-lib"
                )
            self._coordinator = HiveCoordinator()

        # 4. Ensure gateway exists
        self._ensure_gateway()

        # 5. Ensure base directory
        self._ensure_base_dir()

        # 6. Reconcile agents: desired vs actual
        desired_ids = {a.agent_id for a in self.manifest.agents}
        actual_ids = set(self._agents.keys())

        # Create agents that should exist but don't
        for spec in self.manifest.agents:
            if spec.agent_id not in actual_ids:
                self._create_agent(spec)

        # Remove agents that exist but shouldn't
        for agent_id in actual_ids - desired_ids:
            self._remove_agent(agent_id)

        return self.get_state()

    def get_state(self) -> HiveState:
        """Return current actual state.

        Returns:
            HiveState snapshot with agent info and connection status.
        """
        agents: dict[str, dict] = {}
        for agent_id, agent in self._agents.items():
            agents[agent_id] = {
                "status": "running" if agent.is_connected else "disconnected",
                "domain": agent.domain,
                "fact_count": agent.get_fact_count(),
            }
        return HiveState(
            agents=agents,
            hive_store_connected=self._hive_store is not None,
            event_bus_connected=self._event_bus is not None,
        )

    # ------------------------------------------------------------------
    # Agent operations
    # ------------------------------------------------------------------

    def learn(
        self,
        agent_id: str,
        concept: str,
        content: str,
        confidence: float = 0.8,
        tags: list[str] | None = None,
    ) -> str:
        """Have an agent learn a fact into its local DB.

        Publishes to the event bus for peer propagation.

        Args:
            agent_id: Agent that will learn the fact.
            concept: Topic or concept label.
            content: The fact content.
            confidence: Confidence score (0.0-1.0).
            tags: Optional categorization tags.

        Returns:
            node_id of the stored fact.

        Raises:
            KeyError: If agent not found.
        """
        agent = self._get_agent(agent_id)
        return agent.learn(concept, content, confidence, tags)

    def promote(
        self,
        agent_id: str,
        concept: str,
        content: str,
        confidence: float,
    ) -> dict:
        """Promote a fact through the gateway to the hive.

        The gateway performs trust checks and contradiction detection.

        Args:
            agent_id: Promoting agent.
            concept: Topic/concept label.
            content: Fact text.
            confidence: Confidence score.

        Returns:
            Dict with status, fact_node_id, contradictions, reason.

        Raises:
            KeyError: If agent not found.
            RuntimeError: If gateway not initialized.
        """
        self._get_agent(agent_id)  # Verify agent exists

        if self._gateway is None:
            raise RuntimeError("Gateway not initialized -- call apply() first")

        return self._gateway.submit_for_promotion(
            agent_id=agent_id,
            fact_content=content,
            confidence=confidence,
            concept=concept,
        )

    def propagate(self) -> dict[str, int]:
        """Run one round of event propagation across all agents.

        Each agent polls its event bus mailbox and incorporates relevant
        peer facts.

        Returns:
            Dict of agent_id -> number of facts incorporated.
        """
        results: dict[str, int] = {}
        for agent_id, agent in self._agents.items():
            count = agent.process_pending_events()
            results[agent_id] = count
        return results

    def query(
        self,
        agent_id: str,
        query_text: str,
        limit: int = 10,
    ) -> list[dict]:
        """Query an agent's local memory.

        Falls back to federated query if available.

        Args:
            agent_id: Agent to query through.
            query_text: Search keywords.
            limit: Maximum results.

        Returns:
            List of fact dicts.

        Raises:
            KeyError: If agent not found.
        """
        agent = self._get_agent(agent_id)
        return agent.query(query_text, limit=limit)

    def query_routed(
        self,
        query_text: str,
        limit: int = 10,
    ) -> list[dict]:
        """Route query to the most relevant agent(s) using expertise routing.

        The coordinator determines which agents are most likely to have
        relevant knowledge.

        Args:
            query_text: Search query.
            limit: Maximum results.

        Returns:
            Deduplicated list of fact dicts from expert agents.
        """
        if self._coordinator is None:
            return []

        experts = self._coordinator.route_query(query_text)
        results: list[dict] = []
        seen_content: set[str] = set()

        for expert_id in experts[:3]:
            if expert_id in self._agents:
                agent_results = self._agents[expert_id].query(query_text, limit=limit)
                for fact in agent_results:
                    content_key = fact["content"].strip().lower()
                    if content_key not in seen_content:
                        seen_content.add(content_key)
                        results.append(fact)

        return results[:limit]

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self, cleanup: bool = False) -> None:
        """Shutdown all agents and release resources.

        Args:
            cleanup: If True, delete the base directory including all
                     agent databases.
        """
        # Disconnect all agents
        for agent in list(self._agents.values()):
            agent.leave_hive()
        self._agents.clear()

        # Close event bus
        if self._event_bus is not None:
            self._event_bus.close()
            self._event_bus = None

        # Close hive store
        if self._hive_store is not None:
            self._hive_store.close()
            self._hive_store = None

        self._coordinator = None
        self._gateway = None

        # Remove temp directory if requested
        if cleanup and self._base_dir and os.path.isdir(self._base_dir):
            shutil.rmtree(self._base_dir, ignore_errors=True)
            self._base_dir = ""

    # ------------------------------------------------------------------
    # Private: infrastructure setup
    # ------------------------------------------------------------------

    def _ensure_base_dir(self) -> None:
        """Create base directory for agent databases if needed."""
        if self._base_dir:
            return

        store_cfg = self.manifest.graph_store
        if store_cfg.db_path:
            self._base_dir = store_cfg.db_path
        else:
            self._base_dir = tempfile.mkdtemp(prefix="hive_ctrl_")
            self._owns_base_dir = True

        os.makedirs(self._base_dir, exist_ok=True)

    def _ensure_hive_store(self) -> None:
        """Connect or create the hive graph store based on config."""
        if self._hive_store is not None:
            return

        backend = self.manifest.graph_store.backend

        if backend == "memory":
            self._hive_store = InMemoryGraphStore(store_id=self.manifest.graph_store.graph_name)
        elif backend == "kuzu":
            self._ensure_base_dir()
            hive_graph_dir = os.path.join(self._base_dir, "hive_graph")
            os.makedirs(hive_graph_dir, exist_ok=True)
            hive_db_path = os.path.join(hive_graph_dir, "kuzu_db")

            if KuzuGraphStore is not None:
                self._hive_store = KuzuGraphStore(db_path=hive_db_path)
        else:
            # For unknown backends, fall back to memory
            logger.warning(
                "Unknown graph_store backend %r, falling back to memory",
                backend,
            )
            self._hive_store = InMemoryGraphStore(store_id=self.manifest.graph_store.graph_name)

    def _ensure_event_bus(self) -> None:
        """Connect or create the event bus based on config."""
        if self._event_bus is not None:
            return

        backend = self.manifest.event_bus.backend

        if backend == "local" and LocalEventBus is not None:
            self._event_bus = LocalEventBus()
        elif create_event_bus is not None:
            kwargs: dict[str, Any] = {}
            if self.manifest.event_bus.connection_string:
                kwargs["connection_string"] = self.manifest.event_bus.connection_string
            self._event_bus = create_event_bus(backend, **kwargs)
        else:
            # Bare minimum fallback
            if LocalEventBus is None:
                raise ImportError("LocalEventBus unavailable. Event bus module failed to import.")
            self._event_bus = LocalEventBus()

    def _ensure_gateway(self) -> None:
        """Create the gateway based on config and backend."""
        if self._gateway is not None:
            return

        gw_cfg = self.manifest.gateway

        # All backends use InMemoryGateway for promotion validation
        self._gateway = InMemoryGateway(
            store=self._hive_store,
            trust_threshold=gw_cfg.trust_threshold,
            contradiction_overlap=gw_cfg.contradiction_overlap,
            consensus_required=gw_cfg.consensus_required,
        )

    # ------------------------------------------------------------------
    # Private: agent lifecycle
    # ------------------------------------------------------------------

    def _create_agent(self, spec: AgentSpec) -> None:
        """Create an agent from its specification."""
        self._ensure_base_dir()

        agent_dir = os.path.join(self._base_dir, spec.agent_id, "kuzu_db")
        hive_store = (
            self._hive_store if not isinstance(self._hive_store, InMemoryGraphStore) else None
        )

        agent = AgentNode(
            agent_id=spec.agent_id,
            db_dir=agent_dir,
            domain=spec.domain,
            hive_store=hive_store,
        )
        agent.join_hive(self._event_bus, self._coordinator)

        # Register trust in gateway
        if isinstance(self._gateway, InMemoryGateway):
            self._gateway.set_trust(spec.agent_id, 1.0)

        self._agents[spec.agent_id] = agent

    def _remove_agent(self, agent_id: str) -> None:
        """Remove an agent from the hive.  Its local DB is preserved."""
        if agent_id not in self._agents:
            return
        agent = self._agents.pop(agent_id)
        agent.leave_hive()

    def _get_agent(self, agent_id: str) -> AgentNode:
        """Look up an agent, raising KeyError if not found."""
        if agent_id not in self._agents:
            raise KeyError(f"Agent {agent_id!r} not found in hive")
        return self._agents[agent_id]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "GraphStoreConfig",
    "EventBusConfig",
    "AgentSpec",
    "GatewayConfig",
    "HiveManifest",
    "HiveState",
    "HiveController",
    "InMemoryGraphStore",
    "InMemoryGateway",
]
