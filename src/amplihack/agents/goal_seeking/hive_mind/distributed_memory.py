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
import itertools
import logging
from typing import Any

from ..retrieval_constants import (
    BIGRAM_WEIGHT,
    HIVE_SEARCH_MULTIPLIER,
    QUERY_KEYWORD_LIMIT,
    UNIGRAM_WEIGHT,
)

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
            query=query,
            limit=limit * HIVE_SEARCH_MULTIPLIER,
            min_confidence=min_confidence,
            **kwargs,
        )

        # Distributed search via hive transport
        hive_dicts = self._query_hive(query, limit=limit)

        if not hive_dicts:
            return local_results[:limit] if local_results else []

        # Merge with relevance-aware ranking against query
        return self._merge_fact_lists(local_results, hive_dicts, limit, query=query)

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

        return self._merge_fact_lists(local_results, hive_dicts, limit, query=query)

    def search_by_concept(
        self, keywords: list[str] | None = None, limit: int = 10, **kwargs: Any
    ) -> list:
        """Search by concept keywords across local memory + distributed hive.

        Delegates to local backend's search_by_concept if available, then
        queries hive with a combined keyword query and merges results.
        """
        if hasattr(self._local, "search_by_concept"):
            local_results = self._local.search_by_concept(keywords=keywords, limit=limit, **kwargs)
        else:
            # CognitiveMemory doesn't have search_by_concept — use search_facts as fallback
            query = " ".join(keywords[:QUERY_KEYWORD_LIMIT]) if keywords else ""
            local_results = self._local.search_facts(query=query, limit=limit) if query else []

        if keywords:
            query = " ".join(keywords[:QUERY_KEYWORD_LIMIT])
            hive_dicts = self._query_hive(query, limit=limit)
        else:
            hive_dicts = []

        if not hive_dicts:
            return local_results[:limit] if local_results else []

        return self._merge_fact_lists(
            local_results,
            hive_dicts,
            limit,
            query=" ".join(keywords[:QUERY_KEYWORD_LIMIT]) if keywords else "",
        )

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

        Dunder methods (except __getattr__ itself) are NOT delegated to avoid
        interfering with pickle, copy, and other Python protocols.
        """
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return getattr(self._local, name)

    def local_search_facts(self, query: str, limit: int = 10, **kwargs: Any) -> list:
        """Search ONLY the local memory backend — no distributed fan-out.

        Used by shard query handlers to avoid recursive SHARD_QUERY storms:
        when agent A queries agent B, agent B searches its own local memory
        only, not triggering another round of distributed queries.
        """
        return self._local.search_facts(query, limit, **kwargs)

    def local_get_all_facts(self, limit: int = 50, **kwargs: Any) -> list:
        """Retrieve facts from ONLY the local memory backend."""
        return self._local.get_all_facts(limit=limit, **kwargs)

    def __repr__(self) -> str:
        return (
            f"DistributedCognitiveMemory(agent={self._agent_name!r}, "
            f"local={type(self._local).__name__}, "
            f"hive={type(self._hive).__name__ if self._hive else 'None'})"
        )

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
        query: str = "",
    ) -> list:
        """Merge local CognitiveMemory results with hive dict results.

        All facts — local and hive — are scored for relevance against
        the query and sorted by score.  Dedup by content hash.  When no
        query is available, local facts rank first as a tiebreaker.

        Returns a list in the same format as local_results (objects or dicts).
        """
        seen: set[str] = set()
        scored: list[tuple[float, Any]] = []

        for r in local_results:
            content = self._extract_content(r)
            if content:
                h = hashlib.md5(content.encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    score = self._relevance_score(r, query) if query else 1.0
                    scored.append((score, r))

        for r in hive_dicts:
            content = r.get("outcome", r.get("content", ""))
            if content:
                h = hashlib.md5(content.encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    score = self._relevance_score(r, query) if query else 0.0
                    scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:limit]]

    @staticmethod
    def _relevance_score(result: Any, query: str) -> float:
        """Score a fact's relevance to a query using n-gram overlap.

        Mirrors the scoring approach in CognitiveAdapter._ngram_overlap_score
        so that local and hive facts are ranked on the same scale.
        """
        if not query:
            return 0.0

        # Extract text from result
        if isinstance(result, dict):
            content = result.get("outcome", result.get("content", ""))
            concept = result.get("context", result.get("concept", ""))
        else:
            content = getattr(result, "content", getattr(result, "outcome", ""))
            concept = getattr(result, "concept", getattr(result, "context", ""))

        text = f"{concept} {content}".lower()
        q_words = query.lower().split()
        t_words = text.split()

        if not q_words or not t_words:
            return 0.0

        # Unigram overlap
        t_set = set(t_words)
        q_terms = {w for w in q_words if len(w) > 1}
        unigram_hits = sum(
            1
            for t in q_terms
            if t in t_set or any(w.startswith(t) or t.startswith(w) for w in t_set if len(w) > 2)
        )
        unigram = unigram_hits / max(1, len(q_terms))

        # Bigram overlap
        q_bigrams = list(itertools.pairwise(q_words))
        t_bigrams = set(itertools.pairwise(t_words))
        bigram_hits = sum(1 for bg in q_bigrams if bg in t_bigrams)
        bigram = bigram_hits / max(1, len(q_bigrams)) if q_bigrams else 0.0

        return unigram * UNIGRAM_WEIGHT + bigram * BIGRAM_WEIGHT

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

        # Extract fact content from store_fact args/kwargs.
        # CognitiveMemory.store_fact(concept, content, confidence, source_id, tags, ...)
        # CognitiveAdapter always calls with kwargs, but handle positional too.
        concept = kwargs.get("concept", args[0] if len(args) > 0 else "")
        content = kwargs.get("content", args[1] if len(args) > 1 else "")
        confidence = float(kwargs.get("confidence", args[2] if len(args) > 2 else 0.8))
        tags = kwargs.get("tags", args[4] if len(args) > 4 else [])

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
