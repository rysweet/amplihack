"""Memory Agent: Specialized retrieval strategy selection for knowledge graphs.

Philosophy:
- Single responsibility: Decide HOW to retrieve, not WHAT to synthesize
- Entity-centric retrieval for who/what questions
- Temporal retrieval for when/how-did-X-change questions
- Cypher aggregation for how-many/list-all questions
- Full-text keyword search for needle-in-haystack
- Two-phase retrieval: broad keyword filter then precise reranking

Public API:
    MemoryAgent: Strategy-selecting retrieval agent
    RetrievalStrategy: Enum of retrieval approaches
"""

from __future__ import annotations

import logging
import re
from enum import Enum
from typing import Any

from ..similarity import rerank_facts_by_query

logger = logging.getLogger(__name__)


class RetrievalStrategy(str, Enum):
    """Retrieval strategy selection for different question types."""

    ENTITY_CENTRIC = "entity_centric"
    TEMPORAL = "temporal"
    AGGREGATION = "aggregation"
    FULL_TEXT = "full_text"
    SIMPLE_ALL = "simple_all"
    TWO_PHASE = "two_phase"


class MemoryAgent:
    """Specialized memory retrieval agent.

    Selects the optimal retrieval strategy based on question characteristics
    and delegates to the appropriate HierarchicalMemory method.

    Unlike LearningAgent which handles both retrieval and synthesis,
    MemoryAgent ONLY handles retrieval, returning raw facts for the
    coordinator or reasoning agent to synthesize.

    Args:
        memory: A FlatRetrieverAdapter or compatible memory interface
        agent_name: Name of the owning agent

    Example:
        >>> from ..flat_retriever_adapter import FlatRetrieverAdapter
        >>> memory = FlatRetrieverAdapter("test", "/tmp/db")
        >>> mem_agent = MemoryAgent(memory=memory, agent_name="test")
        >>> facts = mem_agent.retrieve(question="What is Sarah Chen's hobby?",
        ...                            intent={"intent": "simple_recall"})
    """

    def __init__(self, memory: Any, agent_name: str = "memory_agent"):
        self.memory = memory
        self.agent_name = agent_name

    def select_strategy(self, question: str, intent: dict[str, Any]) -> RetrievalStrategy:
        """Select the best retrieval strategy for a question.

        Args:
            question: The question text
            intent: Intent classification dict from _detect_intent

        Returns:
            RetrievalStrategy enum value
        """
        intent_type = intent.get("intent", "simple_recall")

        # Meta-memory: always use aggregation
        if intent_type == "meta_memory":
            return RetrievalStrategy.AGGREGATION

        # Temporal questions: temporal retrieval
        if intent.get("needs_temporal"):
            return RetrievalStrategy.TEMPORAL

        # Check KB size
        kb_size = self._get_kb_size()

        # Small KB: dump everything
        if kb_size <= 150:
            return RetrievalStrategy.SIMPLE_ALL

        # Entity-centric: if question contains proper nouns
        if self._has_entity_reference(question):
            return RetrievalStrategy.ENTITY_CENTRIC

        # Large KB with no entity reference: two-phase (keyword then rerank)
        if kb_size > 150:
            return RetrievalStrategy.TWO_PHASE

        return RetrievalStrategy.FULL_TEXT

    def retrieve(
        self,
        question: str,
        intent: dict[str, Any],
        max_facts: int = 60,
    ) -> list[dict[str, Any]]:
        """Retrieve facts using the optimal strategy for the question.

        Args:
            question: The question text
            intent: Intent classification dict
            max_facts: Maximum facts to return

        Returns:
            List of fact dicts, ordered by relevance
        """
        strategy = self.select_strategy(question, intent)
        logger.debug("MemoryAgent strategy: %s for '%s'", strategy.value, question[:60])

        if strategy == RetrievalStrategy.AGGREGATION:
            return self._aggregation_retrieve(question, intent)

        if strategy == RetrievalStrategy.SIMPLE_ALL:
            return self._simple_all_retrieve(question, max_facts)

        if strategy == RetrievalStrategy.ENTITY_CENTRIC:
            facts = self._entity_retrieve(question, max_facts)
            if facts:
                return facts
            # Fall through to two-phase if entity retrieval finds nothing
            strategy = RetrievalStrategy.TWO_PHASE

        if strategy == RetrievalStrategy.TEMPORAL:
            return self._temporal_retrieve(question, max_facts)

        if strategy == RetrievalStrategy.TWO_PHASE:
            return self._two_phase_retrieve(question, max_facts)

        # Default: full text search
        return self._full_text_retrieve(question, max_facts)

    def _get_kb_size(self) -> int:
        """Get the number of facts in the knowledge base."""
        if hasattr(self.memory, "get_all_facts"):
            return len(self.memory.get_all_facts(limit=151))
        return 0

    def _has_entity_reference(self, question: str) -> bool:
        """Check if the question references a specific entity (proper noun)."""
        # Multi-word proper nouns
        if re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", question):
            return True
        # Possessive proper nouns: "Fatima's"
        if re.findall(r"\b([A-Z][a-z]+)'s\b", question):
            return True
        return False

    def _aggregation_retrieve(self, question: str, intent: dict[str, Any]) -> list[dict[str, Any]]:
        """Retrieve via Cypher aggregation for meta-memory questions."""
        if not hasattr(self.memory, "execute_aggregation"):
            return self._simple_all_retrieve(question, 50)

        q_lower = question.lower()
        results: list[dict[str, Any]] = []

        # Detect entity type being asked about
        entity_type = ""
        for kw in ("project", "people", "person", "team", "member"):
            if kw in q_lower:
                entity_type = kw
                break

        if entity_type == "project":
            agg = self.memory.execute_aggregation("list_concepts", entity_filter="project")
            if agg.get("items"):
                items = agg["items"]
                results.append(
                    {
                        "context": "Meta-memory: Project count",
                        "outcome": f"There are {len(items)} distinct project-related concepts: {', '.join(items)}",
                        "confidence": 1.0,
                        "timestamp": "",
                        "tags": ["meta_memory"],
                        "metadata": {"aggregation": True},
                    }
                )

        if entity_type in ("people", "person", "member", "team"):
            agg = self.memory.execute_aggregation("list_entities")
            if agg.get("items"):
                items = agg["items"]
                results.append(
                    {
                        "context": "Meta-memory: Entity list",
                        "outcome": f"There are {len(items)} distinct entities: {', '.join(items)}",
                        "confidence": 1.0,
                        "timestamp": "",
                        "tags": ["meta_memory"],
                        "metadata": {"aggregation": True},
                    }
                )

        # General fallback: count everything
        if not results:
            entity_agg = self.memory.execute_aggregation("list_entities")
            concept_agg = self.memory.execute_aggregation("count_by_concept")
            total_agg = self.memory.execute_aggregation("count_total")

            parts = []
            if total_agg.get("count"):
                parts.append(f"Total facts: {total_agg['count']}")
            if entity_agg.get("items"):
                parts.append(
                    f"Entities ({len(entity_agg['items'])}): {', '.join(entity_agg['items'][:30])}"
                )
            if concept_agg.get("items"):
                top = list(concept_agg["items"].items())[:20]
                parts.append("Concepts: " + ", ".join(f"{c} ({n})" for c, n in top))

            if parts:
                results.append(
                    {
                        "context": "Meta-memory summary",
                        "outcome": ". ".join(parts),
                        "confidence": 1.0,
                        "timestamp": "",
                        "tags": ["meta_memory"],
                        "metadata": {"aggregation": True},
                    }
                )

        # Also include regular facts for context
        regular = self._simple_all_retrieve(question, 20)
        results.extend(regular[:20])
        return results

    def _simple_all_retrieve(self, question: str, max_facts: int) -> list[dict[str, Any]]:
        """Get all facts for small KBs."""
        if hasattr(self.memory, "get_all_facts"):
            facts = self.memory.get_all_facts(limit=max_facts)
            return rerank_facts_by_query(facts, question)
        return []

    def _entity_retrieve(self, question: str, max_facts: int) -> list[dict[str, Any]]:
        """Retrieve facts about specific entities mentioned in the question."""
        if not hasattr(self.memory, "retrieve_by_entity"):
            return []

        # Extract entity candidates
        candidates = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", question)
        possessives = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'s\b", question)
        candidates.extend(possessives)

        all_facts: list[dict[str, Any]] = []
        seen: set[str] = set()

        for candidate in candidates:
            entity_facts = self.memory.retrieve_by_entity(candidate, limit=max_facts)
            for fact in entity_facts:
                fid = fact.get("experience_id", "")
                if fid and fid not in seen:
                    seen.add(fid)
                    all_facts.append(fact)

        return rerank_facts_by_query(all_facts, question) if all_facts else []

    def _temporal_retrieve(self, question: str, max_facts: int) -> list[dict[str, Any]]:
        """Retrieve facts sorted by temporal order."""
        # Get all facts, then sort by temporal_index
        facts = self._simple_all_retrieve(question, max_facts)

        def temporal_key(fact: dict) -> tuple:
            meta = fact.get("metadata", {})
            t_idx = meta.get("temporal_index", 999999) if meta else 999999
            return (t_idx, fact.get("timestamp", ""))

        return sorted(facts, key=temporal_key)

    def _two_phase_retrieve(self, question: str, max_facts: int) -> list[dict[str, Any]]:
        """Two-phase retrieval: broad keyword search then precise reranking.

        Phase 1: Search with a large limit to get a broad candidate set
        Phase 2: Rerank candidates by query relevance, return top-k
        """
        # Phase 1: Broad keyword search
        broad_limit = min(max_facts * 3, 200)
        candidates = self.memory.search(query=question, limit=broad_limit)

        if not candidates:
            # Fall back to all facts
            if hasattr(self.memory, "get_all_facts"):
                candidates = self.memory.get_all_facts(limit=broad_limit)

        if not candidates:
            return []

        # Phase 2: Rerank by query relevance
        reranked = rerank_facts_by_query(candidates, question, top_k=max_facts)
        return reranked

    def _full_text_retrieve(self, question: str, max_facts: int) -> list[dict[str, Any]]:
        """Standard keyword search."""
        results = self.memory.search(query=question, limit=max_facts)
        return rerank_facts_by_query(results, question) if results else []


__all__ = ["MemoryAgent", "RetrievalStrategy"]
