"""Configurable deployer for distributed hive mind agents.

Works in two modes:
- LOCAL: All agents run as threads in the current process (for testing)
- AZURE: Agents run as Azure Container Apps (for production)

The deployer manages the full agent lifecycle:
- Create agents with their own Kuzu databases
- Connect them to the event bus and hive graph
- Scale up (add more agents) or down (remove agents)
- Health monitoring
- Graceful shutdown

Architecture:
    DeployMode   -- LOCAL (in-process) or AZURE (container apps)
    AgentConfig  -- Per-agent configuration (id, domain, trust, adversarial flag)
    HiveConfig   -- Global hive configuration (mode, bus backend, limits)
    HiveDeployer -- Lifecycle orchestrator (start, add/remove agents, learn, query, shutdown)

Public API:
    DeployMode: Deployment mode enum
    AgentConfig: Single agent configuration
    HiveConfig: Hive-wide configuration
    HiveDeployer: Main lifecycle orchestrator
"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Add memory lib to path
_MEMORY_LIB_PATH = "/home/azureuser/src/amplihack-memory-lib-real/src"
if _MEMORY_LIB_PATH not in sys.path:
    sys.path.insert(0, _MEMORY_LIB_PATH)

from amplihack_memory.cognitive_memory import CognitiveMemory

try:
    from amplihack_memory.graph import FederatedGraphStore, HiveGraphStore, KuzuGraphStore
except ImportError:
    FederatedGraphStore = None  # type: ignore[assignment,misc]
    HiveGraphStore = None  # type: ignore[assignment,misc]
    KuzuGraphStore = None  # type: ignore[assignment,misc]

from .distributed import (
    _DEFAULT_MAX_DB_SIZE,
    AgentNode,
    HiveCoordinator,
    _make_sized_cognitive_memory,
)
from .event_bus import create_event_bus
from .kuzu_hive import HiveGateway, HiveKuzuSchema

logger = logging.getLogger(__name__)

__all__ = [
    "DeployMode",
    "AgentConfig",
    "HiveConfig",
    "HiveDeployer",
]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


class DeployMode(Enum):
    LOCAL = "local"  # All in-process (testing)
    AZURE = "azure"  # Azure Container Apps (production)


@dataclass
class AgentConfig:
    """Configuration for a single agent.

    Attributes:
        agent_id: Unique identifier for this agent.
        domain: Domain of expertise (e.g. "biology", "infrastructure").
        fact_capacity: Maximum facts in local DB (advisory, not enforced by Kuzu).
        trust_initial: Starting trust score (default 1.0).
        is_adversarial: If True, trust is set to HiveConfig.adversary_trust.
    """

    agent_id: str
    domain: str = ""
    fact_capacity: int = 1000
    trust_initial: float = 1.0
    is_adversarial: bool = False


@dataclass
class HiveConfig:
    """Configuration for the entire hive.

    Attributes:
        base_dir: Root directory for all agent DBs. Auto-created if empty.
        mode: LOCAL (in-process) or AZURE (container apps).
        event_bus_backend: "local", "redis", or "azure".
        event_bus_config: Backend-specific config passed to create_event_bus.
        max_agents: Maximum number of agents allowed in the hive.
        propagation_rounds: Default number of propagation rounds.
        promotion_top_k: Not currently used; reserved for future batch promotion.
        adversary_trust: Trust score assigned to adversarial agents.
        azure_resource_group: Azure resource group for AZURE mode.
        azure_location: Azure region for AZURE mode.
        azure_service_bus_connection: Service Bus connection string for AZURE mode.
    """

    base_dir: str = ""
    mode: DeployMode = DeployMode.LOCAL
    event_bus_backend: str = "local"
    event_bus_config: dict[str, Any] = field(default_factory=dict)
    max_agents: int = 100
    propagation_rounds: int = 3
    promotion_top_k: int = 8
    adversary_trust: float = 0.2

    # Azure-specific (only used when mode=AZURE)
    azure_resource_group: str = "hive-mind-rg"
    azure_location: str = "eastus"
    azure_service_bus_connection: str = ""


# ---------------------------------------------------------------------------
# HiveDeployer
# ---------------------------------------------------------------------------


class HiveDeployer:
    """Manages distributed hive mind agent lifecycle.

    Handles the full lifecycle of a hive of agents: infrastructure setup,
    dynamic addition/removal of agents, fact learning and promotion through
    the gateway, event propagation, federated and routed queries, and
    graceful shutdown.

    Each agent gets its own Kuzu database directory. The hive itself has a
    separate Kuzu database for the shared graph (HiveGraphStore). A gateway
    validates promotions (trust check, contradiction detection) before
    facts enter the hive graph.

    Usage:
        deployer = HiveDeployer(HiveConfig())
        deployer.start()

        # Add agents dynamically
        deployer.add_agent(AgentConfig("bio_1", domain="biology"))
        deployer.add_agent(AgentConfig("chem_1", domain="chemistry"))

        # Agents learn, propagate, query
        deployer.learn("bio_1", "biology", "Cells are the basic unit of life", 0.95)
        deployer.propagate()
        results = deployer.query("chem_1", "cells biology")

        # Scale up
        deployer.add_agent(AgentConfig("bio_2", domain="biology"))

        # Scale down
        deployer.remove_agent("bio_2")  # agent's DB preserved

        # Shutdown
        deployer.shutdown()
    """

    def __init__(self, config: HiveConfig | None = None):
        self.config = config or HiveConfig()
        self._started = False
        self._agents: dict[str, AgentNode] = {}
        self._hive_store: HiveGraphStore | None = None
        self._hive_mem: CognitiveMemory | None = None
        self._event_bus = None
        self._coordinator: HiveCoordinator | None = None
        self._gateway: HiveGateway | None = None
        self._base_dir = ""
        self._owns_base_dir = False  # True if we created a tempdir

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Initialize the hive infrastructure.

        Creates the base directory, hive graph store with its own Kuzu DB,
        event bus, coordinator, and gateway. After this, agents can be added.

        Raises:
            RuntimeError: If already started.
        """
        if self._started:
            raise RuntimeError("HiveDeployer already started")

        if self.config.mode == DeployMode.AZURE:
            raise NotImplementedError("AZURE mode is not yet implemented. Use LOCAL mode for now.")

        # Create base directory
        if not self.config.base_dir:
            self._base_dir = tempfile.mkdtemp(prefix="hive_")
            self._owns_base_dir = True
        else:
            self._base_dir = self.config.base_dir
            os.makedirs(self._base_dir, exist_ok=True)

        # Create hive graph store (its own Kuzu DB)
        hive_graph_dir = os.path.join(self._base_dir, "hive_graph")
        os.makedirs(hive_graph_dir, exist_ok=True)
        hive_db_path = os.path.join(hive_graph_dir, "kuzu_db")

        if HiveGraphStore is not None:
            self._hive_store = HiveGraphStore(db_path=hive_db_path)

        # Create hive CognitiveMemory for gateway promotion storage
        hive_mem_path = os.path.join(self._base_dir, "hive_memory", "kuzu_db")
        self._hive_mem = _make_sized_cognitive_memory(
            "__hive__", hive_mem_path, _DEFAULT_MAX_DB_SIZE
        )

        # Set up hive-specific schema on the hive memory DB
        hive_schema = HiveKuzuSchema(self._hive_mem._conn)
        hive_schema.setup()

        # Create event bus
        self._event_bus = create_event_bus(
            self.config.event_bus_backend, **self.config.event_bus_config
        )

        # Create coordinator
        self._coordinator = HiveCoordinator()

        # Create gateway (uses hive memory for promotion storage)
        from .kuzu_hive import AgentRegistry

        registry = AgentRegistry(self._hive_mem._conn)
        self._gateway = HiveGateway(self._hive_mem, registry)

        self._started = True

    def shutdown(self, cleanup: bool = False) -> None:
        """Shutdown the hive: disconnect all agents, close event bus.

        Args:
            cleanup: If True, delete the base directory (including all
                     agent databases). If False (default), databases are
                     preserved on disk.
        """
        if not self._started:
            return

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
        self._hive_mem = None
        self._started = False

        # Remove temp directory if requested and we created it
        if cleanup and self._base_dir and os.path.isdir(self._base_dir):
            shutil.rmtree(self._base_dir, ignore_errors=True)
            self._base_dir = ""

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def add_agent(self, agent_config: AgentConfig) -> None:
        """Add an agent to the hive. Creates its own Kuzu DB.

        The agent gets:
        - Its own Kuzu database at base_dir/{agent_id}/kuzu_db
        - A FederatedGraphStore composing local + hive graph (if available)
        - Registration in the coordinator and event bus

        Args:
            agent_config: Configuration for the new agent.

        Raises:
            RuntimeError: If the deployer has not been started.
            ValueError: If agent_id already exists or max_agents reached.
        """
        if not self._started:
            raise RuntimeError("Call start() first")
        if agent_config.agent_id in self._agents:
            raise ValueError(f"Agent {agent_config.agent_id!r} already exists")
        if len(self._agents) >= self.config.max_agents:
            raise ValueError(f"Max agents ({self.config.max_agents}) reached")

        # Create agent with own DB + optional federated view
        agent_dir = os.path.join(self._base_dir, agent_config.agent_id, "kuzu_db")
        agent = AgentNode(
            agent_id=agent_config.agent_id,
            db_dir=agent_dir,
            domain=agent_config.domain,
            hive_store=self._hive_store,
        )

        # Join the hive (subscribe to bus, register in coordinator)
        agent.join_hive(self._event_bus, self._coordinator)

        # Register in the gateway's registry (for trust-based promotion)
        try:
            self._gateway.registry.register(agent_config.agent_id, agent_config.domain)
        except ValueError:
            pass  # Already registered (e.g. re-add after remove)

        # Set trust: adversarial agents get low trust
        if agent_config.is_adversarial:
            target_trust = self.config.adversary_trust
            current_trust = self._coordinator.check_trust(agent_config.agent_id)
            self._coordinator.update_trust(agent_config.agent_id, target_trust - current_trust)
            # Also update gateway registry trust
            try:
                agent_info = self._gateway.registry.get_agent(agent_config.agent_id)
                delta = target_trust - agent_info["trust_score"]
                self._gateway.registry.update_trust(agent_config.agent_id, delta)
            except (KeyError, Exception):
                pass
        elif agent_config.trust_initial != 1.0:
            delta = agent_config.trust_initial - 1.0
            self._coordinator.update_trust(agent_config.agent_id, delta)

        self._agents[agent_config.agent_id] = agent

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from the hive. Its local DB is preserved.

        The agent is disconnected from the event bus and coordinator,
        but its Kuzu database directory remains on disk.

        Args:
            agent_id: Agent to remove.

        Raises:
            KeyError: If agent not found.
        """
        if agent_id not in self._agents:
            raise KeyError(f"Agent {agent_id!r} not found in hive")
        agent = self._agents.pop(agent_id)
        agent.leave_hive()

    # ------------------------------------------------------------------
    # Learning and promotion
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

        The fact is stored in the agent's own Kuzu database and published
        to the event bus for peer propagation.

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
        """Promote a fact through the gateway to the hive graph.

        The gateway checks:
        1. Agent trust (rejects if below threshold)
        2. Contradictions against existing hive facts
        3. Creates appropriate edges (PROMOTED_TO_HIVE or CONTRADICTS)

        Args:
            agent_id: Promoting agent.
            concept: Topic/concept label.
            content: Fact text.
            confidence: Confidence score.

        Returns:
            Dict with status ('promoted', 'quarantined', 'rejected'),
            fact_node_id, contradictions, reason.

        Raises:
            KeyError: If agent not found.
            RuntimeError: If not started.
        """
        if not self._started:
            raise RuntimeError("Call start() first")
        self._get_agent(agent_id)  # Verify agent exists
        return self._gateway.submit_for_promotion(
            agent_id=agent_id,
            fact_content=content,
            confidence=confidence,
            concept=concept,
        )

    # ------------------------------------------------------------------
    # Propagation
    # ------------------------------------------------------------------

    def propagate(self) -> dict[str, int]:
        """Run one round of event propagation across all agents.

        Each agent polls its event bus mailbox and incorporates relevant
        peer facts (with discounted confidence and provenance tags).

        Returns:
            Dict of agent_id -> number of facts incorporated.
        """
        if not self._started:
            return {}
        results: dict[str, int] = {}
        for agent_id, agent in self._agents.items():
            count = agent.process_pending_events()
            results[agent_id] = count
        return results

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def query(self, agent_id: str, query_str: str, limit: int = 10) -> list[dict]:
        """Query via the agent's local CognitiveMemory (keyword search).

        Uses the agent's CognitiveMemory.search_facts() for keyword matching,
        which works on SemanticMemory nodes. The FederatedGraphStore is
        available for graph traversal scenarios (via agent.query_federated())
        but is not used here because its search_nodes operates on a different
        node type schema than CognitiveMemory.

        Args:
            agent_id: Agent to query through.
            query_str: Search keywords.
            limit: Maximum results.

        Returns:
            List of fact dicts with node_id, concept, content, confidence,
            tags, source_agent.

        Raises:
            KeyError: If agent not found.
        """
        agent = self._get_agent(agent_id)
        return agent.query(query_str, limit)

    def query_routed(self, query_str: str, limit: int = 10) -> list[dict]:
        """Query via expertise routing -- coordinator picks the best agent(s).

        The coordinator determines which agents are most likely to have
        relevant knowledge, then queries them and merges results.

        Args:
            query_str: Search query.
            limit: Maximum results.

        Returns:
            Deduplicated list of fact dicts from the most relevant agents.
        """
        if not self._started or not self._coordinator:
            return []

        experts = self._coordinator.route_query(query_str)
        results: list[dict] = []
        seen_content: set[str] = set()

        for expert_id in experts[:3]:
            if expert_id in self._agents:
                agent_results = self._agents[expert_id].query(query_str, limit=limit)
                for fact in agent_results:
                    content_key = fact["content"].strip().lower()
                    if content_key not in seen_content:
                        seen_content.add(content_key)
                        results.append(fact)

        return results[:limit]

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def get_agent_ids(self) -> list[str]:
        """List all active agent IDs.

        Returns:
            Sorted list of agent identifiers.
        """
        return sorted(self._agents.keys())

    def get_agent_info(self, agent_id: str) -> dict:
        """Get agent info: domain, trust, fact count, connected status.

        Args:
            agent_id: Agent to query.

        Returns:
            Dict with agent_id, domain, trust, fact_count, connected, db_dir.

        Raises:
            KeyError: If agent not found.
        """
        agent = self._get_agent(agent_id)
        trust = 0.0
        if self._coordinator:
            trust = self._coordinator.check_trust(agent_id)
        return {
            "agent_id": agent_id,
            "domain": agent.domain,
            "trust": trust,
            "fact_count": agent.get_fact_count(),
            "connected": agent.is_connected,
            "db_dir": agent.db_dir,
        }

    def get_hive_stats(self) -> dict:
        """Get hive-wide statistics.

        Returns:
            Dict with agent_count, agents (per-agent info), total_facts,
            mode, base_dir, coordinator_stats.
        """
        per_agent: dict[str, dict] = {}
        total_facts = 0
        for agent_id, agent in self._agents.items():
            fact_count = agent.get_fact_count()
            total_facts += fact_count
            trust = 0.0
            if self._coordinator:
                trust = self._coordinator.check_trust(agent_id)
            per_agent[agent_id] = {
                "domain": agent.domain,
                "trust": trust,
                "fact_count": fact_count,
                "connected": agent.is_connected,
            }

        coordinator_stats = {}
        if self._coordinator:
            coordinator_stats = self._coordinator.get_hive_stats()

        return {
            "agent_count": len(self._agents),
            "agents": per_agent,
            "total_facts": total_facts,
            "mode": self.config.mode.value,
            "base_dir": self._base_dir,
            "coordinator_stats": coordinator_stats,
        }

    @property
    def agent_count(self) -> int:
        """Number of active agents in the hive."""
        return len(self._agents)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_agent(self, agent_id: str) -> AgentNode:
        """Look up an agent, raising KeyError if not found."""
        if agent_id not in self._agents:
            raise KeyError(f"Agent {agent_id!r} not found in hive")
        return self._agents[agent_id]
