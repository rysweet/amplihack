"""NetworkGraphStore — GraphStore that replicates over a network transport.

Wraps a local GraphStore and replicates writes and search queries over
Azure Service Bus or Redis using the existing event_bus.py transports.

Architecture:
    - create_node: stores locally AND publishes a CREATE_NODE event
    - search_nodes: searches locally AND publishes a SEARCH_QUERY event,
      collects responses (with timeout), merges and deduplicates
    - _process_incoming: background thread that applies remote writes and
      responds to search queries from other agents

Usage:
    from amplihack.memory.network_store import NetworkGraphStore
    from amplihack.memory.memory_store import InMemoryGraphStore

    store = NetworkGraphStore(
        agent_id="agent_0",
        local_store=InMemoryGraphStore(),
        transport="azure_service_bus",
        connection_string="Endpoint=sb://...",
    )
    node_id = store.create_node("semantic_memory", {"concept": "sky", "content": "blue"})
    results = store.search_nodes("semantic_memory", "sky", limit=5)
    store.close()
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from typing import Any

from .graph_store import GraphStore

logger = logging.getLogger(__name__)

# How long (seconds) to wait for remote search responses
_SEARCH_TIMEOUT = 3.0
# How often (seconds) the background thread polls for incoming events
_POLL_INTERVAL = 0.5

# Event types used on the bus
_OP_CREATE_NODE = "network_graph.create_node"
_OP_CREATE_EDGE = "network_graph.create_edge"
_OP_SEARCH_QUERY = "network_graph.search_query"
_OP_SEARCH_RESPONSE = "network_graph.search_response"


class AgentRegistry:
    """Thread-safe registry of known agents for service discovery.

    NetworkGraphStore instances can share a registry to discover peers
    without relying on the transport layer alone.
    """

    def __init__(self) -> None:
        self._agents: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def register(self, agent_id: str, metadata: dict[str, Any] | None = None) -> None:
        """Register an agent with optional metadata."""
        with self._lock:
            self._agents[agent_id] = metadata or {}

    def unregister(self, agent_id: str) -> None:
        """Remove an agent from the registry."""
        with self._lock:
            self._agents.pop(agent_id, None)

    def list_agents(self) -> list[str]:
        """Return a list of all registered agent IDs."""
        with self._lock:
            return list(self._agents.keys())

    def get(self, agent_id: str) -> dict[str, Any] | None:
        """Return metadata for a registered agent, or None if not found."""
        with self._lock:
            return self._agents.get(agent_id)


class NetworkGraphStore:
    """GraphStore that wraps a local store and replicates over a network transport.

    Args:
        agent_id: Unique identifier for this agent on the bus.
        local_store: The backing local GraphStore (InMemoryGraphStore or KuzuGraphStore).
        transport: "local" | "redis" | "azure_service_bus"
        connection_string: Connection string for Azure Service Bus or Redis URL.
        topic_name: Service Bus topic name (default: "hive-graph").
        search_timeout: Seconds to wait for remote search responses.
        agent_registry: Optional shared AgentRegistry for peer discovery.
    """

    def __init__(
        self,
        agent_id: str,
        local_store: GraphStore,
        transport: str = "local",
        connection_string: str = "",
        topic_name: str = "hive-graph",
        search_timeout: float = _SEARCH_TIMEOUT,
        agent_registry: AgentRegistry | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._local = local_store
        self._transport = transport
        self._search_timeout = search_timeout
        self._agent_registry = agent_registry
        if agent_registry is not None:
            agent_registry.register(agent_id)

        # Pending search queries: query_id -> threading.Event + results list
        self._pending_searches: dict[str, dict[str, Any]] = {}
        self._pending_lock = threading.Lock()

        # Buffered LEARN_CONTENT events waiting to be drained via receive_events()
        self._learn_events: list[Any] = []
        self._learn_lock = threading.Lock()

        # Build the event bus
        self._bus = self._create_bus(transport, connection_string, topic_name)
        self._bus.subscribe(agent_id)

        # Start background thread
        self._running = True
        self._thread = threading.Thread(
            target=self._process_incoming,
            daemon=True,
            name=f"network-graph-{agent_id}",
        )
        self._thread.start()

    # ------------------------------------------------------------------
    # Bus factory
    # ------------------------------------------------------------------

    def _create_bus(self, transport: str, connection_string: str, topic_name: str) -> Any:
        """Create an event bus based on transport type."""
        from amplihack.agents.goal_seeking.hive_mind.event_bus import create_event_bus

        if transport == "local":
            return create_event_bus("local")
        if transport == "azure_service_bus":
            return create_event_bus(
                "azure",
                connection_string=connection_string,
                topic_name=topic_name,
            )
        if transport == "redis":
            return create_event_bus(
                "redis",
                redis_url=connection_string or "redis://localhost:6379",
                channel=topic_name,
            )
        raise ValueError(
            f"Unknown transport: {transport!r}. Valid: 'local', 'azure_service_bus', 'redis'"
        )

    # ------------------------------------------------------------------
    # GraphStore protocol implementation
    # ------------------------------------------------------------------

    def create_node(self, table: str, properties: dict[str, Any]) -> str:
        """Create node locally and publish to remote agents.

        Args:
            table: Node table name.
            properties: Node properties dict.

        Returns:
            Generated node_id string.
        """
        node_id = self._local.create_node(table, properties)
        props_with_id = dict(properties)
        props_with_id["node_id"] = node_id
        self._publish(
            _OP_CREATE_NODE,
            {
                "table": table,
                "node_id": node_id,
                "properties": props_with_id,
            },
        )
        return node_id

    def get_node(self, table: str, node_id: str) -> dict[str, Any] | None:
        """Retrieve a node from local store."""
        return self._local.get_node(table, node_id)

    def update_node(self, table: str, node_id: str, properties: dict[str, Any]) -> None:
        """Update node locally (no replication — use create for new facts)."""
        self._local.update_node(table, node_id, properties)

    def delete_node(self, table: str, node_id: str) -> None:
        """Delete node locally (no replication)."""
        self._local.delete_node(table, node_id)

    def query_nodes(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query nodes from local store only."""
        return self._local.query_nodes(table, filters, limit)

    def search_nodes(
        self,
        table: str,
        text: str,
        fields: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search locally and collect remote responses.

        1. Search local store.
        2. Publish SEARCH_QUERY to the bus.
        3. Wait up to search_timeout seconds for remote responses.
        4. Merge and deduplicate all results.

        Args:
            table: Node table to search.
            text: Search query text.
            fields: Fields to search (None = all string fields).
            limit: Max results per source before merge.

        Returns:
            Deduplicated merged results list.
        """
        local_results = self._local.search_nodes(table, text, fields, limit)

        if self._transport == "local":
            # Local bus — only one agent, no point in network search
            return local_results

        query_id = uuid.uuid4().hex
        event = threading.Event()
        remote_results: list[dict[str, Any]] = []

        with self._pending_lock:
            self._pending_searches[query_id] = {
                "event": event,
                "results": remote_results,
            }

        try:
            self._publish(
                _OP_SEARCH_QUERY,
                {
                    "query_id": query_id,
                    "table": table,
                    "text": text,
                    "fields": fields,
                    "limit": limit,
                },
            )
            # Wait for at least one response or timeout
            event.wait(timeout=self._search_timeout)
        finally:
            with self._pending_lock:
                self._pending_searches.pop(query_id, None)

        return self._merge_results(local_results, remote_results, limit)

    def create_edge(
        self,
        rel_type: str,
        from_table: str,
        from_id: str,
        to_table: str,
        to_id: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Create edge locally and publish to remote agents."""
        self._local.create_edge(rel_type, from_table, from_id, to_table, to_id, properties)
        self._publish(
            _OP_CREATE_EDGE,
            {
                "rel_type": rel_type,
                "from_table": from_table,
                "from_id": from_id,
                "to_table": to_table,
                "to_id": to_id,
                "properties": properties or {},
            },
        )

    def get_edges(
        self,
        node_id: str,
        rel_type: str | None = None,
        direction: str = "out",
    ) -> list[dict[str, Any]]:
        """Get edges from local store."""
        return self._local.get_edges(node_id, rel_type, direction)

    def delete_edge(self, rel_type: str, from_id: str, to_id: str) -> None:
        """Delete edge from local store."""
        self._local.delete_edge(rel_type, from_id, to_id)

    def ensure_table(self, table: str, schema: dict[str, str]) -> None:
        """Ensure table exists in local store."""
        self._local.ensure_table(table, schema)

    def ensure_rel_table(
        self,
        rel_type: str,
        from_table: str,
        to_table: str,
        schema: dict[str, str] | None = None,
    ) -> None:
        """Ensure relationship table exists in local store."""
        self._local.ensure_rel_table(rel_type, from_table, to_table, schema)

    def get_all_node_ids(self, table: str | None = None) -> set[str]:
        """Get all node IDs from local store."""
        return self._local.get_all_node_ids(table)

    def export_nodes(self, node_ids: list[str] | None = None) -> list[tuple[str, str, dict]]:
        """Export nodes from local store."""
        return self._local.export_nodes(node_ids)

    def export_edges(self, node_ids: list[str] | None = None) -> list[tuple[str, str, str, dict]]:
        """Export edges from local store."""
        return self._local.export_edges(node_ids)

    def import_nodes(self, nodes: list[tuple[str, str, dict]]) -> int:
        """Import nodes into local store."""
        return self._local.import_nodes(nodes)

    def import_edges(self, edges: list[tuple[str, str, str, dict]]) -> int:
        """Import edges into local store."""
        return self._local.import_edges(edges)

    def close(self) -> None:
        """Stop background thread and close bus + local store."""
        self._running = False
        if self._agent_registry is not None:
            self._agent_registry.unregister(self._agent_id)
        try:
            self._bus.unsubscribe(self._agent_id)
        except Exception:
            logger.debug("Error unsubscribing from bus", exc_info=True)
        try:
            self._bus.close()
        except Exception:
            logger.debug("Error closing bus", exc_info=True)
        try:
            self._local.close()
        except Exception:
            logger.debug("Error closing local store", exc_info=True)
        if self._thread.is_alive():
            self._thread.join(timeout=3.0)

    # ------------------------------------------------------------------
    # Background thread
    # ------------------------------------------------------------------

    def _process_incoming(self) -> None:
        """Background thread: poll bus and handle incoming events.

        - CREATE_NODE: apply write to local store
        - CREATE_EDGE: apply edge to local store
        - SEARCH_QUERY: run local search, publish SEARCH_RESPONSE
        - SEARCH_RESPONSE: wake up any waiting search_nodes() call
        """
        while self._running:
            try:
                events = self._bus.poll(self._agent_id)
                for event in events:
                    try:
                        self._handle_event(event)
                    except Exception:
                        logger.debug(
                            "Error handling event %s", event.event_type, exc_info=True
                        )
            except Exception:
                logger.debug("Error polling bus", exc_info=True)
            time.sleep(_POLL_INTERVAL)

    def _handle_event(self, event: Any) -> None:
        """Dispatch a single incoming bus event."""
        op = event.event_type
        payload = event.payload

        if op == _OP_CREATE_NODE:
            table = payload.get("table", "")
            props = payload.get("properties", {})
            if table and props:
                # Only apply if we don't already have this node
                node_id = props.get("node_id")
                if node_id and self._local.get_node(table, node_id) is None:
                    self._local.create_node(table, props)
                    logger.debug(
                        "Applied remote create_node: table=%s node_id=%s from=%s",
                        table,
                        node_id,
                        event.source_agent,
                    )

        elif op == _OP_CREATE_EDGE:
            self._local.create_edge(
                rel_type=payload.get("rel_type", ""),
                from_table=payload.get("from_table", ""),
                from_id=payload.get("from_id", ""),
                to_table=payload.get("to_table", ""),
                to_id=payload.get("to_id", ""),
                properties=payload.get("properties") or None,
            )
            logger.debug("Applied remote create_edge from=%s", event.source_agent)

        elif op == _OP_SEARCH_QUERY:
            query_id = payload.get("query_id", "")
            table = payload.get("table", "")
            text = payload.get("text", "")
            fields = payload.get("fields")
            limit = payload.get("limit", 20)
            if not query_id or not table:
                return
            results = self._local.search_nodes(table, text, fields, limit)
            self._publish(
                _OP_SEARCH_RESPONSE,
                {
                    "query_id": query_id,
                    "results": results,
                },
            )

        elif op == _OP_SEARCH_RESPONSE:
            query_id = payload.get("query_id", "")
            results = payload.get("results", [])
            with self._pending_lock:
                pending = self._pending_searches.get(query_id)
            if pending is not None:
                pending["results"].extend(results)
                pending["event"].set()

        elif op == "LEARN_CONTENT":
            # Buffer for the OODA loop to drain via receive_events()
            with self._learn_lock:
                self._learn_events.append(event)
            logger.debug(
                "Buffered LEARN_CONTENT event from %s (queue depth=%d)",
                event.source_agent,
                len(self._learn_events),
            )

    def receive_events(self) -> list[Any]:
        """Drain and return all buffered LEARN_CONTENT events.

        Called by the Memory facade so the OODA loop can process incoming
        learning events published by external agents or feed_content.py.

        Returns:
            List of BusEvent objects (LEARN_CONTENT type), oldest first.
        """
        with self._learn_lock:
            events = list(self._learn_events)
            self._learn_events.clear()
        return events

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Publish an event to the bus, serializing payload safely."""
        from amplihack.agents.goal_seeking.hive_mind.event_bus import make_event

        try:
            # Validate payload is JSON-serializable
            json.dumps(payload)
        except (TypeError, ValueError):
            logger.warning("NetworkGraphStore: payload not JSON-serializable, skipping publish")
            return

        event = make_event(event_type, self._agent_id, payload)
        try:
            self._bus.publish(event)
        except Exception:
            logger.debug("Failed to publish %s event", event_type, exc_info=True)

    @staticmethod
    def _merge_results(
        local: list[dict[str, Any]],
        remote: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Merge local and remote results, deduplicating by node_id."""
        seen: set[str] = set()
        merged: list[dict[str, Any]] = []
        for node in local + remote:
            nid = node.get("node_id")
            key = nid if nid else json.dumps(node, sort_keys=True, default=str)
            if key not in seen:
                seen.add(key)
                merged.append(node)
                if len(merged) >= limit:
                    break
        return merged


__all__ = ["AgentRegistry", "NetworkGraphStore"]
