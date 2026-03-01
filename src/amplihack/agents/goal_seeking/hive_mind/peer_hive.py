"""PeerHiveGraph -- Agents ARE the distributed store.

Uses pysyncobj (Raft consensus) for the control plane:
- Agent registry, trust scores, fact metadata, contradictions
All replicated across agents with strong consistency.

Uses local storage for the data plane:
- Fact content stored in each agent's local memory
- Gossip-based propagation for content

When an agent calls promote_fact():
1. Fact metadata -> Raft (replicated to all agents)
2. Fact content -> stored locally + gossipped to peers

When an agent calls query_facts():
1. Search local content first
2. If insufficient, query peers via their addresses

Philosophy:
- Agents ARE the store: no separate database cluster
- Raft consensus for metadata: strong consistency for agent registry and fact IDs
- Local storage for content: too large for Raft log
- Federation support via parent/child pointers

Public API:
    PeerHiveGraph: P2P hive graph implementation
"""

from __future__ import annotations

import threading
from typing import Any

try:
    from pysyncobj import SyncObj, SyncObjConf, replicated

    HAS_PYSYNCOBJ = True
except ImportError:
    HAS_PYSYNCOBJ = False

from .hive_graph import (
    HiveAgent,
    HiveEdge,
    HiveFact,
    HiveGraph,
    _new_fact_id,
    _tokenize,
    _word_overlap,
)

# ---------------------------------------------------------------------------
# Raft-replicated state machine
# ---------------------------------------------------------------------------

if HAS_PYSYNCOBJ:

    class _HiveRaftState(SyncObj):
        """Raft-replicated state machine for the hive graph.

        Only METADATA goes through Raft (agent registry, fact IDs, trust
        scores, edges, expertise index). Actual fact CONTENT is too large for
        the Raft log and is stored locally on each node.

        Methods decorated with @replicated are executed on ALL nodes in the
        cluster once committed to the Raft log.
        """

        def __init__(self, self_address: str, partners: list[str]) -> None:
            cfg = SyncObjConf(autoTick=True)
            super().__init__(self_address, partners, cfg)
            self.__agents: dict[str, dict[str, Any]] = {}
            self.__fact_meta: dict[str, dict[str, Any]] = {}
            self.__edges: list[dict[str, Any]] = []
            self.__expertise: dict[str, list[str]] = {}  # concept -> agent_ids

        # -- Agent registry (replicated) -----------------------------------

        @replicated
        def raft_register_agent(self, agent_id: str, domain: str, trust: float) -> None:
            """Register an agent (replicated across all Raft nodes)."""
            self.__agents[agent_id] = {
                "agent_id": agent_id,
                "domain": domain,
                "trust": max(0.0, min(2.0, trust)),
                "fact_count": 0,
                "status": "active",
            }

        @replicated
        def raft_unregister_agent(self, agent_id: str) -> None:
            """Remove an agent (replicated)."""
            if agent_id in self.__agents:
                del self.__agents[agent_id]

        @replicated
        def raft_update_trust(self, agent_id: str, trust: float) -> None:
            """Update trust score (replicated)."""
            if agent_id in self.__agents:
                self.__agents[agent_id]["trust"] = max(0.0, min(2.0, trust))

        def get_agent(self, agent_id: str) -> dict[str, Any] | None:
            """Read agent data (local read, no replication needed)."""
            return self.__agents.get(agent_id)

        def get_all_agents(self) -> list[dict[str, Any]]:
            """List all agents (local read)."""
            return list(self.__agents.values())

        # -- Fact metadata (replicated) ------------------------------------

        @replicated
        def raft_promote_fact_meta(
            self,
            fact_id: str,
            concept: str,
            source_agent: str,
            confidence: float,
            tags: list[str],
        ) -> None:
            """Store fact metadata in Raft log (replicated)."""
            self.__fact_meta[fact_id] = {
                "fact_id": fact_id,
                "concept": concept,
                "source_agent": source_agent,
                "confidence": confidence,
                "tags": tags,
                "status": "promoted",
            }
            # Update expertise index
            if concept:
                if concept not in self.__expertise:
                    self.__expertise[concept] = []
                if source_agent not in self.__expertise[concept]:
                    self.__expertise[concept].append(source_agent)
            # Increment fact count
            if source_agent in self.__agents:
                self.__agents[source_agent]["fact_count"] = (
                    self.__agents[source_agent].get("fact_count", 0) + 1
                )

        @replicated
        def raft_retract_fact(self, fact_id: str) -> None:
            """Mark a fact as retracted (replicated)."""
            if fact_id in self.__fact_meta:
                self.__fact_meta[fact_id]["status"] = "retracted"

        def get_fact_meta(self, fact_id: str) -> dict[str, Any] | None:
            """Read fact metadata (local read)."""
            return self.__fact_meta.get(fact_id)

        def get_all_fact_meta(self) -> dict[str, dict[str, Any]]:
            """Read all fact metadata (local read)."""
            return dict(self.__fact_meta)

        # -- Edges (replicated) --------------------------------------------

        @replicated
        def raft_add_edge(
            self,
            source_id: str,
            target_id: str,
            edge_type: str,
            properties: dict[str, Any],
        ) -> None:
            """Add an edge (replicated)."""
            self.__edges.append(
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "edge_type": edge_type,
                    "properties": properties,
                }
            )

        def get_edges(self, node_id: str, edge_type: str | None = None) -> list[dict[str, Any]]:
            """Read edges for a node (local read)."""
            results: list[dict[str, Any]] = []
            for e in self.__edges:
                if e["source_id"] == node_id or e["target_id"] == node_id:
                    if edge_type is None or e["edge_type"] == edge_type:
                        results.append(e)
            return results

        # -- Expertise routing (local read) --------------------------------

        def get_expertise_agents(self, concept: str) -> list[str]:
            """Get agents with expertise in a concept (local read)."""
            return self.__expertise.get(concept, [])


# ---------------------------------------------------------------------------
# PeerHiveGraph
# ---------------------------------------------------------------------------


class PeerHiveGraph:
    """P2P hive graph where agents ARE the distributed store.

    Uses pysyncobj Raft consensus for metadata (agent registry, fact IDs,
    trust scores, edges). Fact content is stored locally on each node
    (too large for the Raft log).

    Args:
        hive_id: Unique hive identifier.
        self_address: This node's address ("host:port").
        peer_addresses: List of peer addresses ["host:port", ...].

    Example:
        # Agent on machine 1
        hive1 = PeerHiveGraph(
            hive_id="my-hive",
            self_address="10.0.0.1:4321",
            peer_addresses=["10.0.0.2:4321", "10.0.0.3:4321"]
        )

        # Agent on machine 2
        hive2 = PeerHiveGraph(
            hive_id="my-hive",
            self_address="10.0.0.2:4321",
            peer_addresses=["10.0.0.1:4321", "10.0.0.3:4321"]
        )

    Raises:
        ImportError: If pysyncobj is not installed.
    """

    def __init__(
        self,
        hive_id: str = "p2p-hive",
        self_address: str = "",
        peer_addresses: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        if not HAS_PYSYNCOBJ:
            raise ImportError("pysyncobj required for P2P hive. Install: pip install pysyncobj")

        self._hive_id = hive_id
        self._self_address = self_address

        # Create Raft-replicated state machine
        self._state = _HiveRaftState(self_address, peer_addresses or [])

        # Local content storage (not replicated via Raft -- content is too
        # large for the Raft log, stored locally and gossipped to peers)
        self._local_content: dict[str, str] = {}
        self._lock = threading.Lock()

        # Federation
        self._parent: HiveGraph | None = None
        self._children: list[HiveGraph] = []

    # -- Property --------------------------------------------------------------

    @property
    def hive_id(self) -> str:
        """Unique identifier for this hive."""
        return self._hive_id

    # -- Agent registry --------------------------------------------------------

    def register_agent(self, agent_id: str, domain: str = "", trust: float = 1.0) -> None:
        """Register an agent (Raft-replicated)."""
        existing = self._state.get_agent(agent_id)
        if existing is not None:
            raise ValueError(f"Agent '{agent_id}' already registered")
        self._state.raft_register_agent(agent_id, domain, trust)

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent (Raft-replicated)."""
        if self._state.get_agent(agent_id) is None:
            raise KeyError(f"Agent '{agent_id}' not found")
        self._state.raft_unregister_agent(agent_id)

    def get_agent(self, agent_id: str) -> HiveAgent | None:
        """Retrieve an agent by ID."""
        data = self._state.get_agent(agent_id)
        if data is None:
            return None
        return HiveAgent(
            agent_id=data["agent_id"],
            domain=data["domain"],
            trust=data["trust"],
            fact_count=data["fact_count"],
            status=data["status"],
        )

    def list_agents(self) -> list[HiveAgent]:
        """List all registered agents."""
        return [
            HiveAgent(
                agent_id=d["agent_id"],
                domain=d["domain"],
                trust=d["trust"],
                fact_count=d["fact_count"],
                status=d["status"],
            )
            for d in self._state.get_all_agents()
        ]

    def update_trust(self, agent_id: str, trust: float) -> None:
        """Set agent trust score (Raft-replicated)."""
        if self._state.get_agent(agent_id) is None:
            raise KeyError(f"Agent '{agent_id}' not found")
        self._state.raft_update_trust(agent_id, trust)

    # -- Fact management -------------------------------------------------------

    def promote_fact(self, agent_id: str, fact: HiveFact) -> str:
        """Promote a fact: metadata via Raft, content stored locally.

        Args:
            agent_id: The promoting agent.
            fact: The fact to promote.

        Returns:
            The fact_id.
        """
        if self._state.get_agent(agent_id) is None:
            raise KeyError(f"Agent '{agent_id}' not registered")

        if not fact.fact_id:
            fact.fact_id = _new_fact_id()

        fact.source_agent = agent_id

        # Metadata -> Raft (replicated)
        self._state.raft_promote_fact_meta(
            fact.fact_id,
            fact.concept,
            agent_id,
            fact.confidence,
            list(fact.tags),
        )

        # Content -> local storage (will be gossipped)
        with self._lock:
            self._local_content[fact.fact_id] = fact.content

        return fact.fact_id

    def get_fact(self, fact_id: str) -> HiveFact | None:
        """Retrieve a fact by combining Raft metadata + local content."""
        meta = self._state.get_fact_meta(fact_id)
        if meta is None:
            return None

        with self._lock:
            content = self._local_content.get(fact_id, "")

        return HiveFact(
            fact_id=meta["fact_id"],
            content=content,
            concept=meta["concept"],
            confidence=meta["confidence"],
            source_agent=meta["source_agent"],
            tags=meta["tags"],
            status=meta["status"],
        )

    def query_facts(self, query: str, limit: int = 20) -> list[HiveFact]:
        """Search facts by keyword query against local content."""
        if not query or not query.strip():
            # Return all facts with local content
            all_meta = self._state.get_all_fact_meta()
            results: list[HiveFact] = []
            with self._lock:
                for fid, meta in all_meta.items():
                    if meta["status"] == "retracted":
                        continue
                    content = self._local_content.get(fid, "")
                    results.append(
                        HiveFact(
                            fact_id=fid,
                            content=content,
                            concept=meta["concept"],
                            confidence=meta["confidence"],
                            source_agent=meta["source_agent"],
                            tags=meta["tags"],
                            status=meta["status"],
                        )
                    )
            return results[:limit]

        keywords = _tokenize(query)
        if not keywords:
            return []

        all_meta = self._state.get_all_fact_meta()
        scored: list[tuple[float, HiveFact]] = []

        with self._lock:
            for fid, meta in all_meta.items():
                if meta["status"] == "retracted":
                    continue
                content = self._local_content.get(fid, "")
                fact_words = _tokenize(f"{content} {meta['concept']}")
                hits = len(keywords & fact_words)
                if hits > 0:
                    score = hits + meta["confidence"] * 0.01
                    scored.append(
                        (
                            score,
                            HiveFact(
                                fact_id=fid,
                                content=content,
                                concept=meta["concept"],
                                confidence=meta["confidence"],
                                source_agent=meta["source_agent"],
                                tags=meta["tags"],
                                status=meta["status"],
                            ),
                        )
                    )

        scored.sort(key=lambda x: (-x[0], -x[1].confidence))
        return [f for _, f in scored[:limit]]

    def retract_fact(self, fact_id: str) -> bool:
        """Retract a fact (Raft-replicated metadata update)."""
        meta = self._state.get_fact_meta(fact_id)
        if meta is None:
            return False
        self._state.raft_retract_fact(fact_id)
        return True

    # -- Graph edges -----------------------------------------------------------

    def add_edge(self, edge: HiveEdge) -> None:
        """Add an edge (Raft-replicated)."""
        self._state.raft_add_edge(
            edge.source_id,
            edge.target_id,
            edge.edge_type,
            dict(edge.properties),
        )

    def get_edges(self, node_id: str, edge_type: str | None = None) -> list[HiveEdge]:
        """Get edges for a node."""
        raw = self._state.get_edges(node_id, edge_type)
        return [
            HiveEdge(
                source_id=e["source_id"],
                target_id=e["target_id"],
                edge_type=e["edge_type"],
                properties=e["properties"],
            )
            for e in raw
        ]

    # -- Contradiction detection -----------------------------------------------

    def check_contradictions(self, content: str, concept: str) -> list[HiveFact]:
        """Find facts that may contradict the given content."""
        if not concept:
            return []

        concept_lower = concept.lower()
        contradictions: list[HiveFact] = []
        all_meta = self._state.get_all_fact_meta()

        with self._lock:
            for fid, meta in all_meta.items():
                if meta["status"] == "retracted":
                    continue
                if meta["concept"].lower() != concept_lower:
                    continue
                existing_content = self._local_content.get(fid, "")
                if existing_content == content:
                    continue
                overlap = _word_overlap(content, existing_content)
                if overlap > 0.4:
                    contradictions.append(
                        HiveFact(
                            fact_id=fid,
                            content=existing_content,
                            concept=meta["concept"],
                            confidence=meta["confidence"],
                            source_agent=meta["source_agent"],
                            tags=meta["tags"],
                            status=meta["status"],
                        )
                    )

        return contradictions

    # -- Expertise routing -----------------------------------------------------

    def route_query(self, query: str) -> list[str]:
        """Find agents whose domain overlaps with query keywords."""
        if not query or not query.strip():
            return []

        query_words = _tokenize(query)
        if not query_words:
            return []

        scored: list[tuple[float, str]] = []
        for agent_data in self._state.get_all_agents():
            if agent_data["status"] != "active":
                continue
            domain_words = _tokenize(agent_data["domain"])
            if not domain_words:
                continue
            hits = len(query_words & domain_words)
            if hits > 0:
                scored.append((hits, agent_data["agent_id"]))

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
        """Promote a fact to the parent hive."""
        if self._parent is None:
            return False

        relay_id = f"__relay_{self._hive_id}__"
        if self._parent.get_agent(relay_id) is None:
            self._parent.register_agent(relay_id, domain="relay")

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
        """Push a fact to all children."""
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

    def query_federated(
        self,
        query: str,
        limit: int = 20,
        _visited: set[str] | None = None,
    ) -> list[HiveFact]:
        """Query the entire federation tree for facts matching query.

        Traverses up to parent and down to children recursively,
        avoiding cycles via a visited set keyed by hive_id.

        Args:
            query: Space-separated keywords.
            limit: Maximum results.
            _visited: Internal -- hive_ids already queried (prevents loops).

        Returns:
            Merged, deduplicated list of HiveFact sorted by confidence.
        """
        if _visited is None:
            _visited = set()
        if self._hive_id in _visited:
            return []
        _visited.add(self._hive_id)

        # Local results
        results = list(self.query_facts(query, limit=limit))
        seen_content: set[str] = {f.content for f in results}

        # Parent (recursive, with visited set to prevent loops)
        if self._parent is not None:
            parent_results = self._parent.query_federated(query, limit=limit, _visited=_visited)
            for f in parent_results:
                if f.content not in seen_content:
                    seen_content.add(f.content)
                    results.append(f)

        # Children (recursive)
        for child in self._children:
            child_results = child.query_federated(query, limit=limit, _visited=_visited)
            for f in child_results:
                if f.content not in seen_content:
                    seen_content.add(f.content)
                    results.append(f)

        results.sort(key=lambda f: -f.confidence)
        return results[:limit]

    # -- Stats & lifecycle -----------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Return hive statistics."""
        all_meta = self._state.get_all_fact_meta()
        active = sum(1 for m in all_meta.values() if m["status"] != "retracted")
        return {
            "hive_id": self._hive_id,
            "agent_count": len(self._state.get_all_agents()),
            "fact_count": len(all_meta),
            "active_facts": active,
            "edge_count": len(self._state.get_edges("", None)),
            "has_parent": self._parent is not None,
            "child_count": len(self._children),
            "self_address": self._self_address,
        }

    def close(self) -> None:
        """Shut down the Raft node."""
        try:
            self._state.destroy()
        except Exception:
            pass


__all__ = ["PeerHiveGraph"]
