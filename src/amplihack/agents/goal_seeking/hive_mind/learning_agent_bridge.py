"""Bridge connecting LearningAgent to the UnifiedHiveMind.

Philosophy:
- Intercepts at the FACT STORAGE level (after LLM extraction, not before)
- Wraps the memory adapter, not the LearningAgent itself
- store_fact calls mirror facts into the hive (store + promote)
- search/get_all_facts augment local results with hive facts
- Factory function creates multiple connected agents sharing one hive

Public API:
    HiveAwareMemoryAdapter: Wraps any memory adapter to also write/read hive
    HiveAwareLearningAgent: LearningAgent with hive-connected memory
    create_hive_swarm: Factory for multiple agents sharing a hive
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from .unified import HiveMindConfig, UnifiedHiveMind

logger = logging.getLogger(__name__)

__all__ = [
    "HiveAwareMemoryAdapter",
    "HiveAwareLearningAgent",
    "create_hive_swarm",
]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class HiveBridgeConfig:
    """Configuration for the hive bridge behavior.

    Attributes:
        auto_promote: If True, every stored fact is also promoted to the hive.
            If False, facts are only stored locally in the hive (not promoted).
        promote_confidence_threshold: Minimum confidence to auto-promote a fact.
        hive_query_limit: Max results to fetch from hive when augmenting search.
        augment_search: If True, search results include hive facts.
        augment_get_all: If True, get_all_facts results include hive facts.
        hive_fact_confidence_discount: Discount applied to hive facts' confidence
            when merging with local results (0.0-1.0). Keeps local facts ranked
            higher for same content.
    """

    auto_promote: bool = True
    promote_confidence_threshold: float = 0.5
    hive_query_limit: int = 20
    augment_search: bool = True
    augment_get_all: bool = True
    hive_fact_confidence_discount: float = 0.9


# ---------------------------------------------------------------------------
# HiveAwareMemoryAdapter
# ---------------------------------------------------------------------------


class HiveAwareMemoryAdapter:
    """Wraps any LearningAgent-compatible memory adapter to bridge to the hive.

    Intercepts store_fact to mirror facts into the UnifiedHiveMind.
    Augments search and get_all_facts with hive knowledge from other agents.

    This is a transparent decorator: all methods not explicitly overridden
    are forwarded to the wrapped adapter via __getattr__.

    Args:
        wrapped: The original memory adapter (MemoryRetriever, FlatRetrieverAdapter, etc.)
        hive: The UnifiedHiveMind instance shared across agents.
        agent_id: This agent's unique ID in the hive.
        bridge_config: Controls bridge behavior (auto-promote, augmentation, etc.)

    Example:
        >>> from amplihack.agents.goal_seeking.memory_retrieval import MemoryRetriever
        >>> from amplihack.agents.goal_seeking.hive_mind.unified import UnifiedHiveMind
        >>> hive = UnifiedHiveMind()
        >>> hive.register_agent("agent_a")
        >>> base_memory = MemoryRetriever("agent_a")
        >>> hive_memory = HiveAwareMemoryAdapter(base_memory, hive, "agent_a")
        >>> hive_memory.store_fact("Biology", "Cells are the unit of life", 0.9)
        # Stored locally AND mirrored to hive
    """

    def __init__(
        self,
        wrapped: Any,
        hive: UnifiedHiveMind,
        agent_id: str,
        bridge_config: HiveBridgeConfig | None = None,
    ) -> None:
        self._wrapped = wrapped
        self._hive = hive
        self._agent_id = agent_id
        self._config = bridge_config or HiveBridgeConfig()

    def __getattr__(self, name: str) -> Any:
        """Forward all non-overridden attribute access to the wrapped adapter."""
        return getattr(self._wrapped, name)

    def store_fact(
        self,
        context: str,
        fact: str,
        confidence: float = 0.9,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> str:
        """Store a fact locally AND mirror it to the hive.

        The local store receives the original call. Then the fact is stored
        in the hive's local subgraph for this agent. If auto_promote is
        enabled and confidence meets the threshold, the fact is also promoted
        to the shared hive layer.

        Args:
            context: Topic/category of the fact.
            fact: The fact content.
            confidence: Confidence score 0.0-1.0.
            tags: Optional categorization tags.
            **kwargs: Additional keyword args forwarded to the wrapped adapter.

        Returns:
            experience_id from the wrapped adapter's store_fact.
        """
        # Step 1: Store in the original local memory
        result_id = self._wrapped.store_fact(
            context=context, fact=fact, confidence=confidence, tags=tags, **kwargs
        )

        # Step 2: Mirror to hive
        # Combine context + fact into a single content string for the hive,
        # since the hive uses a flat content model.
        hive_content = f"[{context}] {fact}" if context else fact
        hive_tags = list(tags or [])
        if context:
            hive_tags.append(f"topic:{context}")

        try:
            self._hive.store_fact(
                agent_id=self._agent_id,
                content=hive_content,
                confidence=confidence,
                tags=hive_tags,
            )

            # Auto-promote if configured and confidence meets threshold
            if (
                self._config.auto_promote
                and confidence >= self._config.promote_confidence_threshold
            ):
                self._hive.promote_fact(
                    agent_id=self._agent_id,
                    content=hive_content,
                    confidence=confidence,
                    tags=hive_tags,
                )
        except Exception as e:
            # Hive errors should not break local learning
            logger.warning("Failed to mirror fact to hive: %s", e)

        return result_id

    def search(
        self,
        query: str,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """Search local memory AND optionally augment with hive results.

        Local results come first. Hive results are appended with a slight
        confidence discount and deduplicated by content overlap.

        Args:
            query: Search query text.
            limit: Maximum results to return.
            **kwargs: Additional args forwarded to wrapped search.

        Returns:
            List of result dicts (local + hive, deduplicated).
        """
        # Get local results
        local_results = self._wrapped.search(query=query, limit=limit, **kwargs)

        if not self._config.augment_search:
            return local_results

        # Get hive results
        try:
            hive_results = self._hive.query_all(
                agent_id=self._agent_id,
                query=query,
                limit=self._config.hive_query_limit,
            )
        except Exception as e:
            logger.warning("Hive query failed, returning local only: %s", e)
            return local_results

        # Merge: deduplicate by content similarity
        return self._merge_results(local_results, hive_results, limit)

    def get_all_facts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get all local facts AND optionally include hive facts.

        Args:
            limit: Maximum number of facts.

        Returns:
            List of fact dicts (local + hive, deduplicated).
        """
        local_facts = self._wrapped.get_all_facts(limit=limit)

        if not self._config.augment_get_all:
            return local_facts

        # Query hive with broad search (empty query returns nothing in the
        # hierarchical graph, so we use a broad wildcard-like approach by
        # querying the agent's own knowledge summary topics).
        try:
            hive_results = self._hive.query_hive(
                query="",
                limit=self._config.hive_query_limit,
            )
            # Also get gossip facts via query_all
            hive_all = self._hive.query_all(
                agent_id=self._agent_id,
                query="knowledge facts information",
                limit=self._config.hive_query_limit,
            )
            # Combine both hive query approaches
            seen_ids = {r.get("fact_id") for r in hive_results}
            for item in hive_all:
                if item.get("fact_id") not in seen_ids:
                    hive_results.append(item)
                    seen_ids.add(item.get("fact_id"))
        except Exception as e:
            logger.warning("Hive get_all failed, returning local only: %s", e)
            return local_facts

        return self._merge_results(local_facts, hive_results, limit)

    def _merge_results(
        self,
        local_results: list[dict[str, Any]],
        hive_results: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        """Merge local and hive results, deduplicating by content.

        Local results take priority. Hive results are converted to the
        local dict format and have a slight confidence discount.

        Args:
            local_results: Facts from the local memory adapter.
            hive_results: Facts from the hive query.
            limit: Maximum total results.

        Returns:
            Merged, deduplicated list up to limit.
        """
        merged = list(local_results)

        # Build content fingerprints from local results for dedup
        local_content_set: set[str] = set()
        for item in local_results:
            # Use outcome (fact text) as dedup key
            content = item.get("outcome", item.get("content", ""))
            if content:
                local_content_set.add(content.strip().lower())

        discount = self._config.hive_fact_confidence_discount

        for hive_item in hive_results:
            hive_content = hive_item.get("content", "")
            if not hive_content:
                continue

            # Check for duplicate
            normalized = hive_content.strip().lower()
            if normalized in local_content_set:
                continue

            # Also check if the hive content (which has "[Topic] fact" format)
            # contains the same fact text as a local result
            is_dup = False
            for local_content in local_content_set:
                if local_content in normalized or normalized in local_content:
                    is_dup = True
                    break
            if is_dup:
                continue

            local_content_set.add(normalized)

            # Convert hive format to local adapter format
            # Hive facts have: fact_id, content, confidence, tags, source
            # Local facts have: experience_id, context, outcome, confidence, tags
            context = ""
            outcome = hive_content
            # Parse "[Topic] fact" format back into context + outcome
            if hive_content.startswith("[") and "]" in hive_content:
                bracket_end = hive_content.index("]")
                context = hive_content[1:bracket_end]
                outcome = hive_content[bracket_end + 1 :].strip()

            converted = {
                "experience_id": hive_item.get("fact_id", f"hive_{uuid.uuid4().hex[:8]}"),
                "context": context,
                "outcome": outcome,
                "confidence": hive_item.get("confidence", 0.8) * discount,
                "tags": hive_item.get("tags", [])
                + [f"hive:source:{hive_item.get('source', 'hive')}"],
                "timestamp": "",
                "metadata": {"hive_source": hive_item.get("source", "hive")},
            }
            merged.append(converted)

            if len(merged) >= limit:
                break

        return merged[:limit]


# ---------------------------------------------------------------------------
# HiveAwareLearningAgent
# ---------------------------------------------------------------------------


class HiveAwareLearningAgent:
    """LearningAgent wrapper that connects to a shared UnifiedHiveMind.

    Replaces the agent's memory adapter with a HiveAwareMemoryAdapter so that
    all fact storage is mirrored to the hive and all queries are augmented
    with hive knowledge.

    This is a thin wrapper: the LearningAgent instance is used directly,
    with only its `memory` attribute replaced.

    Args:
        agent: A LearningAgent instance.
        hive: The shared UnifiedHiveMind.
        agent_id: Unique agent ID for the hive (defaults to agent.agent_name).
        bridge_config: Optional bridge configuration.

    Example:
        >>> from amplihack.agents.goal_seeking.learning_agent import LearningAgent
        >>> from amplihack.agents.goal_seeking.hive_mind.unified import UnifiedHiveMind
        >>> hive = UnifiedHiveMind()
        >>> agent = LearningAgent("bio_agent")
        >>> hive_agent = HiveAwareLearningAgent(agent, hive)
        >>> hive_agent.learn_from_content("Cells are the basic unit of life.")
        # Facts stored locally AND in the hive
    """

    def __init__(
        self,
        agent: Any,
        hive: UnifiedHiveMind,
        agent_id: str | None = None,
        bridge_config: HiveBridgeConfig | None = None,
    ) -> None:
        self._agent = agent
        self._hive = hive
        self.agent_id = agent_id or agent.agent_name
        self._bridge_config = bridge_config or HiveBridgeConfig()

        # Register this agent with the hive
        try:
            hive.register_agent(self.agent_id)
        except ValueError:
            # Already registered (idempotent)
            pass

        # Replace the agent's memory with our hive-aware adapter
        self._original_memory = agent.memory
        self._hive_memory = HiveAwareMemoryAdapter(
            wrapped=agent.memory,
            hive=hive,
            agent_id=self.agent_id,
            bridge_config=self._bridge_config,
        )
        agent.memory = self._hive_memory

    @property
    def agent(self) -> Any:
        """Access the underlying LearningAgent."""
        return self._agent

    @property
    def hive(self) -> UnifiedHiveMind:
        """Access the shared hive."""
        return self._hive

    @property
    def hive_memory(self) -> HiveAwareMemoryAdapter:
        """Access the hive-aware memory adapter."""
        return self._hive_memory

    def learn_from_content(self, content: str) -> dict[str, Any]:
        """Learn from content -- delegates to the underlying agent.

        Because the agent's memory has been replaced with HiveAwareMemoryAdapter,
        all store_fact calls during learning are automatically mirrored to the hive.

        Args:
            content: Article or content text.

        Returns:
            Dictionary with learning results (facts_extracted, facts_stored, etc.)
        """
        return self._agent.learn_from_content(content)

    def answer_question(
        self,
        question: str,
        question_level: str = "L1",
        **kwargs: Any,
    ) -> str:
        """Answer a question using local + hive knowledge.

        The hive-aware memory adapter augments retrieved facts with hive
        knowledge before the LLM synthesizes an answer.

        Args:
            question: Question to answer.
            question_level: Complexity level (L1/L2/L3/L4).
            **kwargs: Additional args forwarded to LearningAgent.answer_question.

        Returns:
            Synthesized answer string.
        """
        return self._agent.answer_question(question, question_level, **kwargs)

    def store_fact_directly(
        self,
        context: str,
        fact: str,
        confidence: float = 0.9,
        tags: list[str] | None = None,
    ) -> str:
        """Store a fact directly (bypassing LLM extraction).

        Useful for tests and experiments where you want to inject facts
        without an LLM call.

        Args:
            context: Topic/category.
            fact: The fact content.
            confidence: Confidence score.
            tags: Optional tags.

        Returns:
            experience_id of the stored fact.
        """
        return self._hive_memory.store_fact(
            context=context, fact=fact, confidence=confidence, tags=tags
        )

    def query_hive(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Query the shared hive directly (bypassing local memory).

        Args:
            query: Search text.
            limit: Max results.

        Returns:
            List of hive fact dicts.
        """
        return self._hive.query_all(self.agent_id, query, limit=limit)

    def detach(self) -> None:
        """Restore the original memory adapter on the LearningAgent.

        Call this to disconnect from the hive without destroying the agent.
        """
        self._agent.memory = self._original_memory


# ---------------------------------------------------------------------------
# Factory: create_hive_swarm
# ---------------------------------------------------------------------------


@dataclass
class AgentConfig:
    """Configuration for a single agent in a hive swarm.

    Attributes:
        name: Agent name (used as both LearningAgent name and hive agent_id).
        model: LLM model for the agent (defaults to env EVAL_MODEL).
        use_hierarchical: Whether to use hierarchical memory.
        storage_path: Custom storage path for the agent's memory.
    """

    name: str
    model: str | None = None
    use_hierarchical: bool = False
    storage_path: Any = None


def create_hive_swarm(
    agent_configs: list[AgentConfig | dict[str, Any]],
    hive_config: HiveMindConfig | None = None,
    bridge_config: HiveBridgeConfig | None = None,
) -> tuple[list[HiveAwareLearningAgent], UnifiedHiveMind]:
    """Create multiple HiveAwareLearningAgents sharing a single UnifiedHiveMind.

    This is the primary factory for building a swarm of agents that share
    knowledge through the hive mind.

    Args:
        agent_configs: List of AgentConfig or dicts with keys: name, model,
            use_hierarchical, storage_path.
        hive_config: Configuration for the shared hive. Defaults to
            HiveMindConfig with consensus_required=1 for easy promotion.
        bridge_config: Bridge configuration shared across all agents.

    Returns:
        Tuple of (list of HiveAwareLearningAgents, the shared UnifiedHiveMind).

    Raises:
        ValueError: If agent_configs is empty or contains duplicate names.

    Example:
        >>> configs = [
        ...     AgentConfig(name="bio_agent"),
        ...     AgentConfig(name="chem_agent"),
        ...     AgentConfig(name="phys_agent"),
        ... ]
        >>> agents, hive = create_hive_swarm(configs)
        >>> agents[0].store_fact_directly("Biology", "DNA stores genetic info", 0.95)
        >>> results = agents[1].query_hive("genetic information")
        >>> # Agent 1 can find Agent 0's fact through the hive
    """
    if not agent_configs:
        raise ValueError("agent_configs cannot be empty")

    # Normalize configs
    normalized: list[AgentConfig] = []
    for cfg in agent_configs:
        if isinstance(cfg, dict):
            normalized.append(AgentConfig(**cfg))
        else:
            normalized.append(cfg)

    # Check for duplicate names
    names = [c.name for c in normalized]
    if len(names) != len(set(names)):
        raise ValueError(f"Duplicate agent names: {names}")

    # Create the shared hive
    hive = UnifiedHiveMind(config=hive_config)

    # Import LearningAgent here to avoid circular imports at module level
    from ..learning_agent import LearningAgent

    # Create agents
    agents: list[HiveAwareLearningAgent] = []
    for cfg in normalized:
        la_kwargs: dict[str, Any] = {"agent_name": cfg.name}
        if cfg.model:
            la_kwargs["model"] = cfg.model
        if cfg.use_hierarchical:
            la_kwargs["use_hierarchical"] = cfg.use_hierarchical
        if cfg.storage_path:
            la_kwargs["storage_path"] = cfg.storage_path

        learning_agent = LearningAgent(**la_kwargs)
        hive_agent = HiveAwareLearningAgent(
            agent=learning_agent,
            hive=hive,
            agent_id=cfg.name,
            bridge_config=bridge_config,
        )
        agents.append(hive_agent)

    return agents, hive
