"""Memory facade — simple remember() / recall() API over the full memory stack.

Abstracts backend selection, config resolution, and distributed topology
behind a minimal two-method interface that any agent can use without
understanding the underlying complexity.

Usage:
    from amplihack.memory import Memory

    mem = Memory("my-agent")
    mem.remember("The sky is blue")
    facts = mem.recall("sky colour")
    mem.close()

Topology modes:
    single (default): local-only CognitiveAdapter, no hive
    distributed: local CognitiveAdapter + shared DistributedHiveGraph
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Self

from .config import MemoryConfig
from .graph_store import GraphStore

logger = logging.getLogger(__name__)


class Memory:
    """High-level memory facade with remember() / recall() API.

    Args:
        agent_name: Unique identifier for this agent's memory partition.
        topology: "single" (default) or "distributed".
        backend: "cognitive" (default) or "hierarchical".
        storage_path: Override storage directory.
        shared_hive: Existing hive instance to join (distributed topology).
        model: Optional model name for cognitive backend.
        kuzu_buffer_pool_mb: Kuzu buffer pool size in MB.
        replication_factor: DHT replication factor (distributed topology).
        query_fanout: Max shards queried per request (distributed topology).
        gossip_enabled: Enable bloom-filter gossip (distributed topology).
        gossip_rounds: Rounds to run when run_gossip() is called.
        **kwargs: Additional config overrides forwarded to MemoryConfig.resolve().
    """

    def __init__(
        self,
        agent_name: str,
        *,
        topology: str | None = None,
        backend: str | None = None,
        storage_path: str | None = None,
        shared_hive: Any | None = None,
        model: str | None = None,
        kuzu_buffer_pool_mb: int | None = None,
        replication_factor: int | None = None,
        query_fanout: int | None = None,
        gossip_enabled: bool | None = None,
        gossip_rounds: int | None = None,
        memory_transport: str | None = None,
        memory_connection_string: str | None = None,
        **kwargs: Any,
    ) -> None:
        self._agent_name = agent_name

        # Resolve configuration
        explicit: dict[str, Any] = {}
        if topology is not None:
            explicit["topology"] = topology
        if backend is not None:
            explicit["backend"] = backend
        if storage_path is not None:
            explicit["storage_path"] = storage_path
        if shared_hive is not None:
            explicit["shared_hive"] = shared_hive
        if model is not None:
            explicit["model"] = model
        if kuzu_buffer_pool_mb is not None:
            explicit["kuzu_buffer_pool_mb"] = kuzu_buffer_pool_mb
        if replication_factor is not None:
            explicit["replication_factor"] = replication_factor
        if query_fanout is not None:
            explicit["query_fanout"] = query_fanout
        if gossip_enabled is not None:
            explicit["gossip_enabled"] = gossip_enabled
        if gossip_rounds is not None:
            explicit["gossip_rounds"] = gossip_rounds
        if memory_transport is not None:
            explicit["memory_transport"] = memory_transport
        if memory_connection_string is not None:
            explicit["memory_connection_string"] = memory_connection_string
        explicit.update(kwargs)

        self._cfg = MemoryConfig.resolve(agent_name, **explicit)

        self._hive: Any = None
        self._adapter: Any = None
        self._graph_store: GraphStore | None = None
        # Lazily created LearningAgent for LLM fact extraction in store()
        self._learning_agent: Any = None

        self._setup()

    # ------------------------------------------------------------------
    # Internal setup
    # ------------------------------------------------------------------

    def _setup(self) -> None:
        """Build backend adapter and hive (if distributed)."""
        cfg = self._cfg

        # Determine if we are using a network transport for distribution.
        # When a non-local transport is configured, NetworkGraphStore handles
        # cross-agent replication, so we skip the legacy DistributedHiveGraph.
        _transport = getattr(cfg, "memory_transport", "local") or "local"
        _use_network = _transport != "local"

        # --- Hive setup (distributed topology, local transport only) ---
        if cfg.topology == "distributed" and not _use_network:
            self._hive = self._build_hive(cfg)
        elif cfg.shared_hive is not None:
            # Caller supplied a hive directly
            self._hive = cfg.shared_hive

        # --- GraphStore setup ---
        self._graph_store = self._build_graph_store(cfg)

        # --- Adapter setup ---
        if cfg.backend == "hierarchical":
            self._adapter = self._build_hierarchical(cfg)
        else:
            self._adapter = self._build_cognitive(cfg)

        # --- Wire recall_fn: fix dual-storage path ---
        # NetworkGraphStore's search_query handler searches its own Kuzu DB
        # (populated only via CREATE_NODE replication).  LEARN_CONTENT facts go
        # into the CognitiveAdapter's Kuzu DB instead.  Setting recall_fn on the
        # NetworkGraphStore makes search_query route through the correct store.
        if _use_network and hasattr(self._graph_store, "recall_fn"):
            if self._adapter is not None and hasattr(self._adapter, "search"):
                self._graph_store.recall_fn = self._adapter.search  # type: ignore[union-attr, reportAttributeAccessIssue]
                logger.info(
                    "Memory[%s]: wired NetworkGraphStore.recall_fn → CognitiveAdapter.search",
                    cfg.agent_name,
                )

    def _build_graph_store(self, cfg: MemoryConfig) -> GraphStore:
        """Construct the appropriate GraphStore for the resolved config."""
        transport = getattr(cfg, "memory_transport", "local") or "local"
        conn_str = getattr(cfg, "memory_connection_string", "") or ""

        if cfg.topology == "distributed":
            # When a non-local transport is configured, wrap a KuzuGraphStore
            # in NetworkGraphStore so all agents share knowledge via the bus.
            if transport != "local":
                from pathlib import Path as _Path

                from .kuzu_store import KuzuGraphStore
                from .network_store import NetworkGraphStore

                db_path = _Path(cfg.storage_path) / "graph_store" if cfg.storage_path else None
                buffer_bytes = cfg.kuzu_buffer_pool_mb * 1024 * 1024
                local_base: GraphStore = KuzuGraphStore(  # type: ignore[assignment, reportAssignmentType]
                    db_path=db_path,
                    buffer_pool_size=buffer_bytes,
                )
                logger.info(
                    "Memory[%s]: distributed topology via NetworkGraphStore (transport=%s)",
                    cfg.agent_name,
                    transport,
                )
                return NetworkGraphStore(
                    agent_id=cfg.agent_name or "agent",
                    local_store=local_base,
                    transport=transport,
                    connection_string=conn_str,
                )

            # Fallback: legacy DHT-based sharded store (local transport only)
            from .distributed_store import DistributedGraphStore

            store = DistributedGraphStore(
                replication_factor=cfg.replication_factor,
                query_fanout=cfg.query_fanout,
                shard_backend=cfg.shard_backend,
                storage_path=cfg.storage_path or "/tmp/amplihack-shards",
                kuzu_buffer_pool_mb=cfg.kuzu_buffer_pool_mb,
            )
            store.add_agent(cfg.agent_name)
            return store  # type: ignore[return-value, reportReturnType]

        # cognitive (default) — requires Kuzu; raises ImportError if unavailable
        from pathlib import Path as _Path

        from .kuzu_store import KuzuGraphStore

        db_path = _Path(cfg.storage_path) / "graph_store" if cfg.storage_path else None
        buffer_bytes = cfg.kuzu_buffer_pool_mb * 1024 * 1024
        local: GraphStore = KuzuGraphStore(  # type: ignore[assignment, reportAssignmentType]
            db_path=db_path,
            buffer_pool_size=buffer_bytes,
        )

        # Wrap with NetworkGraphStore if a non-local transport is configured
        if transport != "local":
            from .network_store import NetworkGraphStore

            return NetworkGraphStore(
                agent_id=cfg.agent_name or "agent",
                local_store=local,
                transport=transport,
                connection_string=conn_str,
            )

        return local

    def _build_cognitive(self, cfg: MemoryConfig) -> Any:
        """Create a CognitiveAdapter with the resolved config."""
        from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter

        db_path = Path(cfg.storage_path) if cfg.storage_path else None
        buffer_pool_size = cfg.kuzu_buffer_pool_mb * 1024 * 1024

        return CognitiveAdapter(
            agent_name=cfg.agent_name,
            db_path=db_path,
            hive_store=self._hive,
            buffer_pool_size=buffer_pool_size,
        )

    def _build_hierarchical(self, cfg: MemoryConfig) -> Any:
        """Create a HierarchicalMemory instance."""
        from amplihack.agents.goal_seeking.hierarchical_memory import (
            HierarchicalMemory,  # type: ignore[attr-defined, reportAttributeAccessIssue]
        )

        db_path = Path(cfg.storage_path) if cfg.storage_path else None
        return HierarchicalMemory(agent_name=cfg.agent_name, db_path=db_path)

    def _build_hive(self, cfg: MemoryConfig) -> Any:
        """Create or reuse a DistributedHiveGraph."""
        if cfg.shared_hive is not None:
            hive = cfg.shared_hive
        else:
            from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
                DistributedHiveGraph,
            )

            hive = DistributedHiveGraph(
                hive_id=f"hive-{cfg.agent_name}",
                replication_factor=cfg.replication_factor,
                query_fanout=cfg.query_fanout,
                enable_gossip=cfg.gossip_enabled,
            )

        # Register this agent in the hive
        if hasattr(hive, "get_agent") and hasattr(hive, "register_agent"):
            if hive.get_agent(cfg.agent_name) is None:
                hive.register_agent(cfg.agent_name)

        return hive

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def graph_store(self) -> GraphStore | None:
        """Return the underlying GraphStore for direct graph operations."""
        return self._graph_store

    def remember(self, content: str) -> None:
        """Store a piece of knowledge.

        Extracts the content as a fact and stores it locally via the adapter.
        When topology=distributed the adapter auto-promotes to the shared hive.

        Args:
            content: Free-text fact or statement to remember.
        """
        if not content or not content.strip():
            return

        content = content.strip()

        # CognitiveAdapter / HierarchicalMemory — use store_fact
        if hasattr(self._adapter, "store_fact"):
            # Use "general" as a catch-all concept; the content is the fact.
            self._adapter.store_fact("general", content)
        else:
            logger.warning("Adapter %r has no store_fact method", type(self._adapter).__name__)

    def store(self, content: str) -> dict[str, Any]:
        """Store content with internal LLM fact extraction.

        Unlike ``remember()`` which stores content verbatim, ``store()``
        uses an LLM to extract structured facts from the content before
        storing them.  This absorbs what ``LearningAgent.learn_from_content()``
        previously did, so callers no longer need to import LearningAgent.

        Args:
            content: Free-text content (article, log entry, event text, etc.)

        Returns:
            Dict with ``facts_extracted`` and ``facts_stored`` counts.
        """
        if not content or not content.strip():
            return {"facts_extracted": 0, "facts_stored": 0, "content_summary": ""}

        agent = self._get_or_create_learning_agent()
        return asyncio.run(agent.learn_from_content(content))

    def _get_or_create_learning_agent(self) -> Any:
        """Return (lazily created) LearningAgent wired to this facade's adapter."""
        if self._learning_agent is None:
            from amplihack.agents.goal_seeking.learning_agent import LearningAgent

            self._learning_agent = LearningAgent(
                agent_name=self._cfg.agent_name or self._agent_name,
                model=self._cfg.model,
                storage_path=Path(self._cfg.storage_path) if self._cfg.storage_path else None,
                use_hierarchical=self._cfg.backend == "hierarchical",
                hive_store=self._hive,
            )
            # Wire LearningAgent to use this facade's adapter so both
            # store() and remember() write to the same underlying Kuzu DB.
            if self._adapter is not None:
                self._learning_agent.memory = self._adapter
        return self._learning_agent

    def recall(self, question: str, limit: int = 20) -> list[str]:
        """Search memory for facts relevant to the question.

        Searches local memory and, when topology=distributed, the shared hive.
        Deduplicates results before returning.

        Args:
            question: Natural-language query.
            limit: Maximum number of results.

        Returns:
            List of relevant fact strings, deduplicated.
        """
        if not question or not question.strip():
            return []

        # CognitiveAdapter / HierarchicalMemory
        if hasattr(self._adapter, "search"):
            raw = self._adapter.search(question.strip(), limit=limit)
            return self._extract_strings(raw, limit)

        return []

    def receive_events(self) -> list[Any]:
        """Drain and return all pending LEARN_CONTENT events from the network transport.

        Called by the OODA loop in agent_entrypoint.py so that incoming
        LEARN_CONTENT messages published to the Service Bus are surfaced for
        processing via memory.remember().

        Returns:
            List of BusEvent objects. Empty list when no transport is active
            or no events are pending.
        """
        if self._graph_store is not None and hasattr(self._graph_store, "receive_events"):
            return self._graph_store.receive_events()  # type: ignore[union-attr, reportAttributeAccessIssue]
        return []

    def receive_query_events(self) -> list[Any]:
        """Drain and return all pending QUERY events from the network transport.

        Called by the OODA loop in agent_entrypoint.py so that incoming
        QUERY messages can be processed via memory.recall() and responded to.

        Returns:
            List of BusEvent objects (QUERY type). Empty list when no transport
            is active or no query events are pending.
        """
        if self._graph_store is not None and hasattr(self._graph_store, "receive_query_events"):
            return self._graph_store.receive_query_events()  # type: ignore[union-attr, reportAttributeAccessIssue]
        return []

    def send_query_response(
        self,
        query_id: str,
        question: str,
        results: list[str],
    ) -> None:
        """Publish a QUERY_RESPONSE with cognitive memory recall results.

        Called by the OODA loop after processing a QUERY event via recall().

        Args:
            query_id: The query_id from the original QUERY event.
            question: The question that was asked.
            results: Recalled fact strings from this agent's cognitive memory.
        """
        if self._graph_store is not None and hasattr(self._graph_store, "send_query_response"):
            self._graph_store.send_query_response(query_id, question, results)  # type: ignore[union-attr, reportAttributeAccessIssue]

    def close(self) -> None:
        """Release all resources."""
        if self._adapter is not None and hasattr(self._adapter, "close"):
            try:
                self._adapter.close()
            except Exception:
                logger.debug("Error closing adapter", exc_info=True)
        if self._graph_store is not None:
            try:
                self._graph_store.close()
            except Exception:
                logger.debug("Error closing graph_store", exc_info=True)
        if self._hive is not None and hasattr(self._hive, "close"):
            try:
                self._hive.close()
            except Exception:
                logger.debug("Error closing hive", exc_info=True)

    def stats(self) -> dict[str, Any]:
        """Return memory statistics."""
        result: dict[str, Any] = {
            "agent_name": self._agent_name,
            "backend": self._cfg.backend,
            "topology": self._cfg.topology,
        }

        if hasattr(self._adapter, "get_statistics"):
            try:
                result["adapter_stats"] = self._adapter.get_statistics()
            except Exception:
                pass

        if self._hive is not None and hasattr(self._hive, "get_stats"):
            try:
                result["hive_stats"] = self._hive.get_stats()
            except Exception:
                pass

        return result

    def run_gossip(self) -> None:
        """Manually trigger a gossip round (distributed topology only).

        Runs gossip_rounds rounds on the shared hive.
        """
        if self._hive is None:
            return

        rounds = self._cfg.gossip_rounds
        if hasattr(self._hive, "run_gossip_round"):
            for _ in range(rounds):
                try:
                    self._hive.run_gossip_round()
                except Exception:
                    logger.debug("Gossip round failed", exc_info=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_strings(raw: list[dict[str, Any]], limit: int) -> list[str]:
        """Convert adapter result dicts to plain strings, deduplicating."""
        seen: set[str] = set()
        results: list[str] = []
        for item in raw:
            # Try common keys used by CognitiveAdapter / HierarchicalMemory
            text = (
                item.get("outcome")
                or item.get("fact")
                or item.get("content")
                or item.get("text")
                or ""
            )
            if text and text not in seen:
                seen.add(text)
                results.append(text)
                if len(results) >= limit:
                    break
        return results

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


__all__ = ["Memory"]
