"""Adapter wrapping CognitiveMemory (6-type) for backward compatibility.

Provides the same interface as FlatRetrieverAdapter (store_fact, search,
get_all_facts) while leveraging CognitiveMemory's 6 memory types:
- Sensory: raw input buffering with TTL
- Working: bounded task state tracking (20 slots)
- Episodic: events with consolidation
- Semantic: facts with confidence and similarity edges
- Procedural: step sequences with usage tracking
- Prospective: future intentions with trigger conditions

Philosophy:
- Drop-in replacement for FlatRetrieverAdapter
- Exposes additional cognitive capabilities via dedicated methods
- Falls back gracefully if CognitiveMemory unavailable
"""

from __future__ import annotations

import itertools
import logging
from pathlib import Path
from typing import Any

from .hive_mind.constants import (
    DEFAULT_CONFIDENCE_GATE,
    DEFAULT_QUALITY_THRESHOLD,
    KUZU_BUFFER_POOL_SIZE,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stop words for query filtering (improves search precision)
# ---------------------------------------------------------------------------
_QUERY_STOP_WORDS = frozenset(
    {
        "what",
        "is",
        "the",
        "a",
        "an",
        "are",
        "was",
        "were",
        "how",
        "does",
        "do",
        "and",
        "or",
        "of",
        "in",
        "to",
        "for",
        "with",
        "on",
        "at",
        "by",
        "from",
        "that",
        "this",
        "it",
        "as",
        "be",
        "been",
        "has",
        "have",
        "had",
        "will",
        "would",
        "could",
        "should",
        "did",
        "which",
        "who",
        "when",
        "where",
        "why",
        "any",
        "some",
        "all",
        "both",
        "each",
        "few",
        "more",
        "most",
        "other",
        "such",
        "into",
        "through",
        "during",
        "before",
        "after",
        "than",
        "then",
        "these",
        "those",
        "there",
        "their",
        "they",
        "its",
        "our",
        "your",
        "my",
        "we",
        "i",
        "you",
        "he",
        "she",
        "me",
        "him",
        "her",
        "them",
        "used",
        "found",
        "given",
        "made",
        "came",
        "went",
        "said",
        "got",
    }
)


def _filter_stop_words(query: str) -> str:
    """Return query with stop words removed, preserving meaningful terms."""
    words = [w.strip("?.,!;:'\"()[]") for w in query.lower().split()]
    filtered = [w for w in words if w and w not in _QUERY_STOP_WORDS and len(w) > 1]
    return " ".join(filtered) if filtered else query.lower()


def _ngram_overlap_score(query: str, text: str) -> float:
    """Score text by unigram + bigram overlap with query (after stop word removal).

    Returns a float in [0, 1] where higher = more overlap.
    """
    q_words = [w.strip("?.,!;:'\"") for w in query.lower().split()]
    t_words = text.lower().split()

    # Unigram overlap (stop-word filtered)
    q_terms = {w for w in q_words if w and w not in _QUERY_STOP_WORDS and len(w) > 1}
    t_set = set(t_words)
    # Also check substring containment for partial matches (e.g. "login" in "logins")
    unigram_hits = sum(
        1
        for t in q_terms
        if t in t_set or any(w.startswith(t) or t.startswith(w) for w in t_set if len(w) > 2)
    )
    unigram = unigram_hits / max(1, len(q_terms)) if q_terms else 0.0

    # Bigram overlap
    q_bigrams = list(itertools.pairwise(q_words))
    t_bigrams = set(itertools.pairwise(t_words))
    bigram_hits = sum(1 for bg in q_bigrams if bg in t_bigrams)
    bigram = bigram_hits / max(1, len(q_bigrams)) if q_bigrams else 0.0

    return unigram * 0.65 + bigram * 0.35


# Try importing CognitiveMemory, fall back to HierarchicalMemory
try:
    from amplihack_memory.cognitive_memory import CognitiveMemory  # type: ignore[import-not-found]

    HAS_COGNITIVE_MEMORY = True
except ImportError:
    HAS_COGNITIVE_MEMORY = False

# Graceful imports for retrieval pipeline modules
try:
    from .hive_mind.quality import score_content_quality

    _HAS_QUALITY = True
except ImportError:
    _HAS_QUALITY = False

try:
    from .hive_mind.query_expansion import expand_query

    _HAS_QUERY_EXPANSION = True
except ImportError:
    _HAS_QUERY_EXPANSION = False


class CognitiveAdapter:
    """Adapter providing FlatRetrieverAdapter-compatible interface over CognitiveMemory.

    Uses the 6-type CognitiveMemory system from amplihack-memory-lib.
    Falls back to FlatRetrieverAdapter if the library is not installed.

    Args:
        agent_name: Name of the owning agent
        db_path: Path to Kuzu database directory

    Example:
        >>> adapter = CognitiveAdapter("test_agent", "/tmp/test_db")
        >>> adapter.store_fact("Biology", "Cells are the basic unit of life")
        >>> results = adapter.search("cells")
        >>> print(results[0]["context"])  # "Biology"
    """

    def __init__(
        self,
        agent_name: str,
        db_path: str | Path | None = None,
        require_cognitive: bool = False,
        hive_store: Any | None = None,
        quality_threshold: float = DEFAULT_QUALITY_THRESHOLD,
        confidence_gate: float = DEFAULT_CONFIDENCE_GATE,
        enable_query_expansion: bool = False,
        buffer_pool_size: int = KUZU_BUFFER_POOL_SIZE,
    ):
        self.agent_name = agent_name
        self.memory: Any = None  # CognitiveMemory or HierarchicalMemory
        self._hive_store = hive_store  # Optional shared hive for distributed memory
        # Quality gate: reject facts below this quality score before promoting
        self._quality_threshold = quality_threshold
        # Confidence gate: skip hive results if max confidence below threshold
        self._confidence_gate = confidence_gate
        # Query expansion: opt-in, disabled by default
        self._enable_query_expansion = enable_query_expansion and _HAS_QUERY_EXPANSION
        # Buffer pool size for Kuzu (passed via functools.partial when creating the DB)
        self._buffer_pool_size = buffer_pool_size

        if db_path is None:
            db_path = Path.home() / ".amplihack" / "cognitive_memory" / agent_name
        elif isinstance(db_path, str):
            db_path = Path(db_path)

        self._db_path = db_path

        if HAS_COGNITIVE_MEMORY:
            # Clean path for Kuzu (needs non-existent directory)
            kuzu_path = db_path / "kuzu_db"
            if not kuzu_path.exists():
                kuzu_path.parent.mkdir(parents=True, exist_ok=True)

            # Note: CognitiveMemory creates kuzu.Database internally using its
            # own defaults. The buffer_pool_size parameter is accepted here for
            # API consistency but CognitiveMemory does not expose it.
            self.memory = CognitiveMemory(agent_name=agent_name, db_path=str(kuzu_path))
            self._cognitive = True
        else:
            if require_cognitive:
                raise ImportError(
                    "CognitiveMemory required but amplihack_memory.cognitive_memory "
                    "not available. Install amplihack-memory-lib."
                )
            # Fallback to HierarchicalMemory
            from .hierarchical_memory import HierarchicalMemory

            logger.warning(
                "CognitiveMemory not available, falling back to HierarchicalMemory. "
                "Install amplihack-memory-lib for full 6-type cognitive capabilities."
            )
            self.memory = HierarchicalMemory(agent_name=agent_name, db_path=db_path)
            self._cognitive = False

    @property
    def backend_type(self) -> str:
        """Return which memory backend is active."""
        return "cognitive" if self._cognitive else "hierarchical"

    # ------------------------------------------------------------------
    # FlatRetrieverAdapter-compatible interface
    # ------------------------------------------------------------------

    def store_fact(
        self,
        context: str,
        fact: str,
        confidence: float = 0.9,
        tags: list[str] | None = None,
        source_id: str = "",
        temporal_metadata: dict | None = None,
    ) -> str:
        """Store a fact as semantic knowledge.

        When a hive_store is connected, automatically promotes the fact to
        the shared hive after storing locally. This ensures facts flow from
        learn → local memory → shared hive without extra caller code.

        Args:
            context: Topic/concept
            fact: The fact content
            confidence: Confidence score 0.0-1.0
            tags: Optional tags
            source_id: Optional source episode ID
            temporal_metadata: Optional temporal context

        Returns:
            node_id of stored knowledge
        """
        if not context or not context.strip():
            raise ValueError("context cannot be empty")
        if not fact or not fact.strip():
            raise ValueError("fact cannot be empty")

        if self._cognitive:
            node_id = self.memory.store_fact(
                concept=context.strip(),
                content=fact.strip(),
                confidence=confidence,
                source_id=source_id,
                tags=tags,
                temporal_metadata=temporal_metadata,
            )
        else:
            node_id = self.memory.store_knowledge(
                content=fact.strip(),
                concept=context.strip(),
                confidence=confidence,
                source_id=source_id,
                tags=tags,
                temporal_metadata=temporal_metadata,
            )

        # Auto-promote to shared hive if connected
        self._promote_to_hive(context.strip(), fact.strip(), confidence, tags)

        return node_id

    def _promote_to_hive(
        self,
        context: str,
        fact: str,
        confidence: float,
        tags: list[str] | None = None,
    ) -> None:
        """Promote a fact to the shared hive store.

        Silently skips if no hive_store is connected or if the hive lacks
        the promote_fact method. Errors are logged but never raised to
        avoid disrupting local storage.
        """
        if self._hive_store is None:
            return
        if not hasattr(self._hive_store, "promote_fact"):
            return
        # Quality gate: reject low-quality content before promoting
        # Use getattr with default since tests may bypass __init__ via __new__
        quality_threshold = getattr(self, "_quality_threshold", DEFAULT_QUALITY_THRESHOLD)
        if _HAS_QUALITY and quality_threshold > 0:
            try:
                quality = score_content_quality(fact, context)
                if quality < quality_threshold:
                    logger.debug(
                        "Fact rejected by quality gate (%.2f < %.2f): %s",
                        quality,
                        quality_threshold,
                        fact[:80],
                    )
                    return
            except Exception:
                logger.debug("Quality scoring failed, proceeding with promotion")

        try:
            from .hive_mind.hive_graph import HiveFact

            hive_fact = HiveFact(
                fact_id="",
                content=fact,
                concept=context,
                confidence=confidence,
                source_agent=self.agent_name,
                tags=list(tags) if tags else [],
            )
            # Ensure agent is registered before promoting
            if hasattr(self._hive_store, "get_agent"):
                agent = self._hive_store.get_agent(self.agent_name)
                if agent is None and hasattr(self._hive_store, "register_agent"):
                    self._hive_store.register_agent(self.agent_name)
            self._hive_store.promote_fact(self.agent_name, hive_fact)
        except Exception:
            logger.debug("Failed to promote fact to hive (non-fatal)", exc_info=True)

    def search(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Search memory and return flat list of result dicts.

        Uses substring matching with n-gram overlap re-ranking for improved recall.
        Stop words are filtered before querying the backend to reduce noise.
        Falls back to full-corpus scan with n-gram ranking when filtered search
        returns no results so that all stored content is always reachable.

        When a hive_store is connected, searches both local memory and
        the shared hive, deduplicates by content, and returns merged results.
        """
        if not query or not query.strip():
            return []

        # Filter stop words for more targeted backend search
        filtered_query = _filter_stop_words(query)
        search_q = filtered_query if filtered_query.strip() else query.strip()

        if self._cognitive:
            # Request extra candidates so n-gram re-ranking has more to work with
            results = self.memory.search_facts(
                query=search_q, limit=limit * 3, min_confidence=min_confidence
            )
            local_results = [self._semantic_fact_to_dict(r) for r in results]
            # Fallback: scan all stored content when filtered search returns nothing
            if not local_results:
                all_facts = self.memory.get_all_facts(limit=limit * 5)
                local_results = [self._semantic_fact_to_dict(r) for r in all_facts]
        else:
            subgraph = self.memory.retrieve_subgraph(query=search_q, max_nodes=limit * 3)
            local_results = [
                self._node_to_dict(n) for n in subgraph.nodes if n.confidence >= min_confidence
            ]
            # Fallback: scan all stored content when filtered search returns nothing
            if not local_results and hasattr(self.memory, "get_all_knowledge"):
                nodes = self.memory.get_all_knowledge(limit=limit * 5)
                local_results = [self._node_to_dict(n) for n in nodes]

        # Re-rank by n-gram overlap with original query for relevance ordering
        if local_results:
            scored = []
            for r in local_results:
                content = r.get("outcome", r.get("content", ""))
                concept = r.get("context", r.get("concept", ""))
                score = _ngram_overlap_score(query, f"{concept} {content}")
                scored.append((score, r))
            scored.sort(key=lambda x: x[0], reverse=True)
            local_results = [r for _, r in scored[:limit]]

        if self._hive_store is None:
            try:
                from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

                trace_log(
                    "search", "LOCAL-ONLY: %d results (no hive_store)", len(local_results)
                )
            except ImportError:
                pass
            return local_results

        # Query hive and merge
        try:
            from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

            trace_log(
                "search",
                "local=%d results, querying hive for: %.80s",
                len(local_results),
                query.strip()[:80],
            )
        except ImportError:
            pass
        hive_results = self._search_hive(query.strip(), limit=limit)
        merged = self._merge_results(local_results, hive_results, limit)
        try:
            from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

            trace_log(
                "search",
                "local=%d hive=%d merged=%d",
                len(local_results),
                len(hive_results),
                len(merged),
            )
        except ImportError:
            pass
        return merged

    def search_local(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Search LOCAL memory only — no hive/distributed query.

        Used by shard query handlers to avoid recursive SHARD_QUERY storms:
        when agent A queries agent B, agent B must search only its own local
        memory, not trigger another round of distributed queries.
        """
        if not query or not query.strip():
            return []

        filtered_query = _filter_stop_words(query)
        search_q = filtered_query if filtered_query.strip() else query.strip()

        if self._cognitive:
            results = self.memory.search_facts(
                query=search_q, limit=limit * 3, min_confidence=min_confidence
            )
            local_results = [self._semantic_fact_to_dict(r) for r in results]
            if not local_results:
                all_facts = self.memory.get_all_facts(limit=limit * 5)
                local_results = [self._semantic_fact_to_dict(r) for r in all_facts]
        else:
            subgraph = self.memory.retrieve_subgraph(query=search_q, max_nodes=limit * 3)
            local_results = [
                self._node_to_dict(n) for n in subgraph.nodes if n.confidence >= min_confidence
            ]
            if not local_results and hasattr(self.memory, "get_all_knowledge"):
                nodes = self.memory.get_all_knowledge(limit=limit * 5)
                local_results = [self._node_to_dict(n) for n in nodes]

        if local_results:
            scored = []
            for r in local_results:
                content = r.get("outcome", r.get("content", ""))
                concept = r.get("context", r.get("concept", ""))
                score = _ngram_overlap_score(query, f"{concept} {content}")
                scored.append((score, r))
            scored.sort(key=lambda x: x[0], reverse=True)
            local_results = [r for _, r in scored[:limit]]

        return local_results

    def get_all_facts(self, limit: int = 50, query: str = "") -> list[dict[str, Any]]:
        """Retrieve all facts without keyword filtering.

        When a hive_store is connected, returns facts from both local
        memory and the shared hive, deduplicated by content.

        Args:
            limit: Maximum results to return.
            query: Optional question text. When provided and hive is a
                distributed graph, uses targeted ``_search_hive(query)``
                instead of ``_get_all_hive_facts()`` (which sends an
                empty-query ``query_facts("")`` that remote shards reject).
        """
        if self._cognitive:
            results = self.memory.get_all_facts(limit=limit)
            local_results = [self._semantic_fact_to_dict(r) for r in results]
        else:
            nodes = self.memory.get_all_knowledge(limit=limit)
            local_results = [self._node_to_dict(n) for n in nodes]

        if self._hive_store is None:
            return local_results

        if query and query.strip():
            # Targeted hive search — works with DistributedHiveGraph where
            # empty-query get_all_hive_facts returns nothing (remote shards
            # reject SHARD_QUERY with empty query).
            hive_results = self._search_hive(query.strip(), limit=limit)
        else:
            hive_results = self._get_all_hive_facts(limit=limit)
        return self._merge_results(local_results, hive_results, limit)

    @staticmethod
    def _hive_fact_to_dict(
        content: str,
        concept: str,
        confidence: float,
        tags: list[str] | None = None,
        source: str = "unknown",
    ) -> dict[str, Any]:
        """Convert a hive fact to the same dict format as local facts.

        Uses "outcome" key (not "fact") to match _semantic_fact_to_dict output,
        so LearningAgent can process hive facts identically to local ones.
        """
        return {
            "experience_id": "",
            "context": concept,
            "outcome": content,
            "confidence": confidence,
            "timestamp": "",
            "tags": tags or [],
            "metadata": {},
            "source": f"hive:{source}",
        }

    def _search_hive(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search the shared hive store.

        Optionally expands the query with synonyms when query expansion
        is enabled. Applies a confidence gate -- if the maximum confidence
        in results is below the threshold, returns empty list.

        Proposal 5: Prefer federated queries over local-only queries.
        Order: federated_query (FederatedGraphStore) → query_federated
        (InMemoryHiveGraph tree traversal) → query_facts (local only).
        """
        if self._hive_store is None:
            logger.info("_search_hive: no hive_store, skipping")
            return []

        logger.info("_search_hive: querying hive for '%s' (limit=%d)", query[:80], limit)

        # Optional query expansion
        search_query = query
        if self._enable_query_expansion and _HAS_QUERY_EXPANSION:
            try:
                expanded = expand_query(query)
                if expanded:
                    search_query = " ".join(expanded)
            except Exception:
                logger.debug("Query expansion failed, using original query")

        try:
            results = self._execute_hive_search(search_query, limit)

            # Confidence gate: skip hive results if max confidence below threshold
            if results and self._confidence_gate > 0:
                max_conf = max(r.get("confidence", 0.0) for r in results)
                if max_conf < self._confidence_gate:
                    logger.debug(
                        "Hive results below confidence gate (%.2f < %.2f)",
                        max_conf,
                        self._confidence_gate,
                    )
                    return []

            return results
        except Exception:
            logger.exception("Error searching hive store")
        return []

    def _execute_hive_search(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Execute the actual hive search using the best available method."""
        # FederatedGraphStore.federated_query returns FederatedQueryResult
        if hasattr(self._hive_store, "federated_query"):
            try:
                from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

                trace_log("_execute_hive_search", "using federated_query")
            except ImportError:
                pass
            fqr = self._hive_store.federated_query(query, limit=limit)
            results = [
                self._hive_fact_to_dict(
                    content=r.get("content", ""),
                    concept=r.get("concept", ""),
                    confidence=r.get("confidence", 0.5),
                    tags=r.get("tags", []),
                    source=r.get("source", "unknown"),
                )
                for r in (fqr.results if hasattr(fqr, "results") else fqr)
            ]
            try:
                from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

                trace_log("_execute_hive_search", "federated_query returned %d", len(results))
            except ImportError:
                pass
            return results
        # Proposal 5: Prefer query_federated (tree traversal)
        if hasattr(self._hive_store, "query_federated"):
            try:
                from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

                trace_log("_execute_hive_search", "using query_federated")
            except ImportError:
                pass
            facts = self._hive_store.query_federated(query, limit=limit)
            results = [
                self._hive_fact_to_dict(
                    content=f.content,
                    concept=f.concept,
                    confidence=f.confidence,
                    tags=getattr(f, "tags", []),
                    source=getattr(f, "source_agent", "unknown"),
                )
                for f in facts
            ]
            try:
                from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

                trace_log("_execute_hive_search", "query_federated returned %d", len(results))
            except ImportError:
                pass
            return results
        # Fallback: local-only query (no federation)
        if hasattr(self._hive_store, "query_facts"):
            try:
                from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

                trace_log("_execute_hive_search", "using query_facts (DHT fan-out)")
            except ImportError:
                pass
            facts = self._hive_store.query_facts(query, limit=limit)
            try:
                from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

                trace_log("_execute_hive_search", "query_facts returned %d facts", len(facts))
            except ImportError:
                pass
            return [
                self._hive_fact_to_dict(
                    content=f.content,
                    concept=f.concept,
                    confidence=f.confidence,
                    tags=getattr(f, "tags", []),
                    source=getattr(f, "source_agent", "unknown"),
                )
                for f in facts
            ]
        try:
            from amplihack.agents.goal_seeking.hive_mind.tracing import trace_log

            trace_log("_execute_hive_search", "NO search method found on hive_store!")
        except ImportError:
            pass
        return []

    def _get_all_hive_facts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get all facts from the shared hive store."""
        if self._hive_store is None:
            return []
        try:
            if hasattr(self._hive_store, "get_all_facts"):
                facts = self._hive_store.get_all_facts(limit=limit)
                if facts and isinstance(facts[0], dict):
                    return facts[:limit]
                return [
                    self._hive_fact_to_dict(
                        content=getattr(f, "content", ""),
                        concept=getattr(f, "concept", ""),
                        confidence=getattr(f, "confidence", 0.5),
                        tags=getattr(f, "tags", []),
                        source=getattr(f, "source_agent", "unknown"),
                    )
                    for f in facts[:limit]
                ]
            if hasattr(self._hive_store, "query_facts"):
                facts = self._hive_store.query_facts("", limit=limit)
                return [
                    self._hive_fact_to_dict(
                        content=f.content,
                        concept=f.concept,
                        confidence=f.confidence,
                        tags=getattr(f, "tags", []),
                        source=getattr(f, "source_agent", "unknown"),
                    )
                    for f in facts
                ]
        except Exception:
            logger.exception("Error getting all hive facts")
        return []

    @staticmethod
    def _merge_results(
        local: list[dict[str, Any]],
        hive: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Merge local and hive results, deduplicating by fact content.

        Both local and hive results use "outcome" key for fact content.
        """
        seen: set[str] = set()
        merged: list[dict[str, Any]] = []

        # Local facts first (higher trust)
        for r in local:
            content = r.get("outcome", r.get("fact", ""))
            if content and content not in seen:
                seen.add(content)
                merged.append(r)

        # Then hive facts
        for r in hive:
            content = r.get("outcome", r.get("fact", ""))
            if content and content not in seen:
                seen.add(content)
                merged.append(r)

        return merged[:limit]

    def get_statistics(self) -> dict[str, Any]:
        """Get memory statistics."""
        stats = self.memory.get_statistics()
        if self._cognitive:
            stats["total_experiences"] = stats.get("total", 0)
        return stats

    def retrieve_by_entity(self, entity_name: str, limit: int = 50) -> list[dict[str, Any]]:
        """Retrieve all facts about a specific entity.

        Args:
            entity_name: Entity name (case-insensitive)
            limit: Maximum results

        Returns:
            List of fact dicts matching the entity
        """
        if self._cognitive and hasattr(self.memory, "retrieve_by_entity"):
            results = self.memory.retrieve_by_entity(entity_name=entity_name, limit=limit)
            return [self._semantic_fact_to_dict(r) for r in results]
        if hasattr(self.memory, "retrieve_by_entity"):
            nodes = self.memory.retrieve_by_entity(entity_name=entity_name, limit=limit)
            return [self._node_to_dict(n) for n in nodes]
        return []

    def search_by_concept(self, keywords: list[str], limit: int = 30) -> list[dict[str, Any]]:
        """Search for facts by concept/content keyword matching.

        Args:
            keywords: List of keyword strings to search for
            limit: Maximum nodes to return per keyword

        Returns:
            List of fact dicts matching any of the keywords, including
            distributed hive results when a hive_store is connected.
        """
        if self._cognitive and hasattr(self.memory, "search_by_concept"):
            results = self.memory.search_by_concept(keywords=keywords, limit=limit)
            local_results: list[dict[str, Any]] = [self._semantic_fact_to_dict(r) for r in results]
        elif hasattr(self.memory, "search_by_concept"):
            nodes = self.memory.search_by_concept(keywords=keywords, limit=limit)
            local_results = [self._node_to_dict(n) for n in nodes]
        else:
            local_results = []

        if self._hive_store is None:
            return local_results

        # Also search the distributed hive for facts not in local memory
        query = " ".join(keywords[:4])
        hive_results = self._search_hive(query, limit=limit)
        return self._merge_results(local_results, hive_results, limit)

    def execute_aggregation(self, query_type: str, entity_filter: str = "") -> dict[str, Any]:
        """Execute Cypher aggregation query for meta-memory questions.

        Args:
            query_type: Type of aggregation
            entity_filter: Optional filter string

        Returns:
            Dict with aggregation results
        """
        if hasattr(self.memory, "execute_aggregation"):
            return self.memory.execute_aggregation(
                query_type=query_type, entity_filter=entity_filter
            )
        return {"count": 0, "query_type": query_type, "error": "Not supported"}

    def store_episode(self, content: str, source_label: str = "") -> str:
        """Store an episode (raw source content)."""
        return self.memory.store_episode(content=content, source_label=source_label)

    # ------------------------------------------------------------------
    # CognitiveMemory-specific capabilities
    # ------------------------------------------------------------------

    def push_working(
        self, slot_type: str, content: str, task_id: str, relevance: float = 1.0
    ) -> str | None:
        """Add to working memory (bounded, 20 slots per task)."""
        if self._cognitive:
            return self.memory.push_working(slot_type, content, task_id, relevance)
        return None

    def get_working(self, task_id: str) -> list[Any]:
        """Get working memory slots for a task."""
        if self._cognitive:
            return self.memory.get_working(task_id)
        return []

    def clear_working(self, task_id: str) -> int:
        """Clear working memory for a task."""
        if self._cognitive:
            return self.memory.clear_working(task_id)
        return 0

    def store_procedure(self, name: str, steps: list[str], **kwargs: Any) -> str | None:
        """Store a procedural memory (step sequence)."""
        if self._cognitive:
            return self.memory.store_procedure(name=name, steps=steps, **kwargs)
        return None

    def recall_procedure(self, query: str, limit: int = 5) -> list[Any]:
        """Recall a procedure by query."""
        if self._cognitive:
            return self.memory.recall_procedure(query=query, limit=limit)
        return []

    def store_prospective(
        self, description: str, trigger_condition: str, action: str, **kwargs: Any
    ) -> str | None:
        """Store a prospective memory (future intention)."""
        if self._cognitive:
            return self.memory.store_prospective(
                description=description,
                trigger_condition=trigger_condition,
                action_on_trigger=action,
                **kwargs,
            )
        return None

    def check_triggers(self, content: str) -> list[Any]:
        """Check if any prospective memories are triggered by content."""
        if self._cognitive:
            return self.memory.check_triggers(content)
        return []

    def record_sensory(self, modality: str, raw_data: str, ttl_seconds: int = 300) -> str | None:
        """Record sensory memory (short-lived observation)."""
        if self._cognitive:
            return self.memory.record_sensory(modality, raw_data, ttl_seconds)
        return None

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def flush_memory(self) -> None:
        """Flush underlying memory cache without losing data."""
        if hasattr(self.memory, "flush_memory"):
            self.memory.flush_memory()

    def close(self) -> None:
        """Close underlying memory."""
        self.memory.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    @staticmethod
    def _semantic_fact_to_dict(fact: Any) -> dict[str, Any]:
        """Convert CognitiveMemory SemanticFact to flat dict."""
        return {
            "experience_id": fact.node_id,
            "context": fact.concept,
            "outcome": fact.content,
            "confidence": fact.confidence,
            "timestamp": str(fact.created_at) if hasattr(fact, "created_at") else "",
            "tags": fact.tags if hasattr(fact, "tags") else [],
            "metadata": fact.metadata if hasattr(fact, "metadata") else {},
        }

    @staticmethod
    def _node_to_dict(node: Any) -> dict[str, Any]:
        """Convert HierarchicalMemory KnowledgeNode to flat dict."""
        return {
            "experience_id": node.node_id,
            "context": node.concept,
            "outcome": node.content,
            "confidence": node.confidence,
            "timestamp": node.created_at,
            "tags": node.tags,
            "metadata": node.metadata if hasattr(node, "metadata") else {},
        }


__all__ = ["CognitiveAdapter", "HAS_COGNITIVE_MEMORY"]
