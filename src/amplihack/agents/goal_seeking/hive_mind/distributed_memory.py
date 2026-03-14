"""Transparent distributed memory wrapper.

Wraps a local CognitiveMemory (or HierarchicalMemory) instance and a
DistributedHiveGraph transport behind the **same interface** that
CognitiveAdapter already uses for local-only operation.

Design principle (from docs/agent_memory_architecture.md):
    "The agent doesn't know or care whether memory is local or distributed.
     That's configuration."

CognitiveAdapter calls self.memory.search_facts(), self.memory.get_all_facts(),
self.memory.store_fact(), etc.  When topology=single, self.memory is a plain
CognitiveMemory.  When topology=distributed, self.memory is a
DistributedCognitiveMemory that wraps CognitiveMemory + hive transport.

All hive fan-out, dedup, and merge logic lives HERE — invisible to
CognitiveAdapter and GoalSeekingAgent.  The OODA loop code is identical
regardless of topology.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

logger = logging.getLogger(__name__)


class DistributedCognitiveMemory:
    """Transparent wrapper: local CognitiveMemory + distributed hive transport.

    Implements the same public interface as CognitiveMemory so that
    CognitiveAdapter treats it identically.  Reads fan out to the hive
    and merge results; writes store locally (promotion to hive is handled
    by the transport layer).

    Args:
        local_memory: The underlying CognitiveMemory (or HierarchicalMemory).
        hive_graph: A DistributedHiveGraph (or any object with query_facts,
            promote_fact, get_all_facts methods).
        agent_name: This agent's identifier.
        quality_threshold: Minimum quality score for hive promotion (0 disables).
    """

    def __init__(
        self,
        local_memory: Any,
        hive_graph: Any,
        agent_name: str,
        quality_threshold: float = 0.0,
    ) -> None:
        self._local = local_memory
        self._hive = hive_graph
        self._agent_name = agent_name
        self._quality_threshold = quality_threshold

    # ------------------------------------------------------------------
    # Reads: fan out to hive + merge with local
    # ------------------------------------------------------------------

    def search_facts(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
        **kwargs: Any,
    ) -> list:
        """Search local memory + distributed hive, merge, return top results.

        Returns the same type as CognitiveMemory.search_facts() — a list of
        semantic fact objects (or whatever the local backend returns).  Hive
        results are converted to the same dict format.
        """
        # Local search (fast, always available)
        local_results = self._local.search_facts(
            query=query, limit=limit * 3, min_confidence=min_confidence, **kwargs
        )

        # Distributed search via hive transport
        hive_dicts = self._query_hive(query, limit=limit)

        if not hive_dicts:
            return local_results[:limit] if local_results else []

        # Merge: local results first (higher trust), then hive, dedup by content
        return self._merge_fact_lists(local_results, hive_dicts, limit)

    def get_all_facts(self, limit: int = 50, **kwargs: Any) -> list:
        """Get all facts from local memory + distributed hive.

        Supports the optional ``query`` kwarg that CognitiveAdapter passes
        when calling from answer_question() context.
        """
        query = kwargs.get("query", "")

        local_results = self._local.get_all_facts(limit=limit)

        if query and query.strip():
            hive_dicts = self._query_hive(query.strip(), limit=limit)
        else:
            hive_dicts = self._get_all_hive_facts(limit=limit)

        if not hive_dicts:
            return local_results

        return self._merge_fact_lists(local_results, hive_dicts, limit)

    # ------------------------------------------------------------------
    # Writes: store locally + auto-promote to hive
    # ------------------------------------------------------------------

    def store_fact(self, *args: Any, **kwargs: Any) -> Any:
        """Store a fact locally, then promote to hive.

        Signature matches CognitiveMemory.store_fact().
        """
        result = self._local.store_fact(*args, **kwargs)
        self._auto_promote(args, kwargs)
        return result

    # ------------------------------------------------------------------
    # Delegate everything else to local memory
    # ------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        """Delegate all other attribute access to the local memory backend.

        This makes DistributedCognitiveMemory a transparent proxy: any method
        not explicitly overridden (store_episode, push_working, get_statistics,
        retrieve_by_entity, search_by_concept, etc.) goes straight to local.
        """
        return getattr(self._local, name)

    # ------------------------------------------------------------------
    # Internal: hive query + merge
    # ------------------------------------------------------------------

    def _query_hive(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Query the distributed hive for facts matching the query.

        Returns a list of dicts with outcome/context/confidence keys
        (same format as CognitiveAdapter._semantic_fact_to_dict output).
        """
        if self._hive is None:
            return []

        try:
            from .tracing import trace_log
            trace_log("distributed_memory", "querying hive for: %.80s", query[:80])
        except ImportError:
            pass

        try:
            # DistributedHiveGraph.query_facts returns list[HiveFact]
            if hasattr(self._hive, "query_facts"):
                facts = self._hive.query_facts(query, limit=limit)
                try:
                    from .tracing import trace_log
                    trace_log(
                        "distributed_memory",
                        "hive returned %d facts",
                        len(facts),
                    )
                except ImportError:
                    pass
                return [
                    {
                        "experience_id": getattr(f, "fact_id", ""),
                        "context": getattr(f, "concept", ""),
                        "outcome": getattr(f, "content", ""),
                        "confidence": float(getattr(f, "confidence", 0.5)),
                        "tags": list(getattr(f, "tags", [])),
                        "metadata": {},
                    }
                    for f in facts
                    if getattr(f, "content", "")
                ]
            # FederatedGraphStore fallback
            if hasattr(self._hive, "federated_query"):
                fqr = self._hive.federated_query(query, limit=limit)
                results = fqr.results if hasattr(fqr, "results") else fqr
                return [
                    {
                        "experience_id": "",
                        "context": r.get("concept", ""),
                        "outcome": r.get("content", ""),
                        "confidence": float(r.get("confidence", 0.5)),
                        "tags": list(r.get("tags", [])),
                        "metadata": {},
                    }
                    for r in results
                    if r.get("content")
                ]
        except Exception:
            logger.debug("Hive query failed (non-fatal)", exc_info=True)
        return []

    def _get_all_hive_facts(self, limit: int) -> list[dict[str, Any]]:
        """Get all facts from the hive (no query filter)."""
        if self._hive is None:
            return []
        try:
            if hasattr(self._hive, "get_all_facts"):
                facts = self._hive.get_all_facts(limit=limit)
                if facts and isinstance(facts[0], dict):
                    return facts[:limit]
                return [
                    {
                        "experience_id": getattr(f, "fact_id", ""),
                        "context": getattr(f, "concept", ""),
                        "outcome": getattr(f, "content", ""),
                        "confidence": float(getattr(f, "confidence", 0.5)),
                        "tags": list(getattr(f, "tags", [])),
                        "metadata": {},
                    }
                    for f in facts[:limit]
                    if getattr(f, "content", "")
                ]
        except Exception:
            logger.debug("Hive get_all_facts failed (non-fatal)", exc_info=True)
        return []

    def _merge_fact_lists(
        self,
        local_results: list,
        hive_dicts: list[dict[str, Any]],
        limit: int,
    ) -> list:
        """Merge local CognitiveMemory results with hive dict results.

        Local results are trusted first. Dedup by content text.
        Returns a list in the same format as local_results (objects or dicts).
        """
        seen: set[str] = set()
        merged: list = []

        # Local first (higher trust, already in correct format)
        for r in local_results:
            content = self._extract_content(r)
            if content:
                h = hashlib.md5(content.encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    merged.append(r)

        # Hive results (dict format)
        for r in hive_dicts:
            content = r.get("outcome", r.get("content", ""))
            if content:
                h = hashlib.md5(content.encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    merged.append(r)

        return merged[:limit]

    @staticmethod
    def _extract_content(result: Any) -> str:
        """Extract content string from a local memory result (object or dict)."""
        if isinstance(result, dict):
            return result.get("outcome", result.get("content", result.get("fact", "")))
        return getattr(result, "content", getattr(result, "outcome", str(result)))

    def _auto_promote(self, args: tuple, kwargs: dict) -> None:
        """Promote a stored fact to the hive (fire-and-forget)."""
        if self._hive is None or not hasattr(self._hive, "promote_fact"):
            return

        try:
            from .hive_graph import HiveFact
        except ImportError:
            return

        # Extract fact content from store_fact args/kwargs
        # CognitiveMemory.store_fact(content, concept, confidence, tags, metadata)
        content = kwargs.get("content", args[0] if len(args) > 0 else "")
        concept = kwargs.get("concept", args[1] if len(args) > 1 else "")
        confidence = float(kwargs.get("confidence", args[2] if len(args) > 2 else 0.8))
        tags = kwargs.get("tags", args[3] if len(args) > 3 else [])

        if not content:
            return

        # Quality gate
        if self._quality_threshold > 0:
            try:
                from amplihack.agents.goal_seeking.content_quality import (
                    score_content_quality,
                )
                quality = score_content_quality(content, concept)
                if quality < self._quality_threshold:
                    return
            except Exception:
                pass

        try:
            hive_fact = HiveFact(
                fact_id="",
                content=content,
                concept=concept,
                confidence=confidence,
                source_agent=self._agent_name,
                tags=list(tags) if tags else [],
            )
            if hasattr(self._hive, "get_agent"):
                agent = self._hive.get_agent(self._agent_name)
                if agent is None and hasattr(self._hive, "register_agent"):
                    self._hive.register_agent(self._agent_name)
            self._hive.promote_fact(self._agent_name, hive_fact)
        except Exception:
            logger.debug("Hive promotion failed (non-fatal)", exc_info=True)
