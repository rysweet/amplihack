"""Hierarchical Knowledge Graph with Promotion/Pull mechanics.

Two-level graph architecture:
- Level 1 (Local): Each agent has its own fact store, isolated by agent_id
- Level 2 (Hive): Shared fact store visible to all agents

Facts move between levels via:
- Promotion: Agent proposes local fact -> other agents vote -> promoted if policy met
- Pull: Agent queries hive -> copies relevant facts to local context

Uses in-memory dicts for simplicity (experiment-grade, not production Kuzu).

Public API:
    HiveFact: Shared fact dataclass
    PromotionPolicy: Configurable promotion rules
    PromotionManager: Propose/vote/promote lifecycle
    PullManager: Query hive and pull to local
    HierarchicalKnowledgeGraph: Orchestrator for the two-level graph
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Stop words and tokenization (local copy to keep module self-contained)
# ---------------------------------------------------------------------------

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "about",
        "like",
        "through",
        "after",
        "over",
        "between",
        "out",
        "against",
        "during",
        "without",
        "before",
        "under",
        "around",
        "among",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "so",
        "yet",
        "both",
        "either",
        "neither",
        "each",
        "every",
        "all",
        "any",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "only",
        "own",
        "same",
        "than",
        "too",
        "very",
        "just",
        "because",
        "if",
        "when",
        "where",
        "how",
        "what",
        "which",
        "who",
        "whom",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
        "they",
        "them",
        "their",
    }
)


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase content words."""
    if not text:
        return set()
    words = text.lower().split()
    return {w.strip(".,;:!?()[]{}\"'") for w in words if len(w) > 2} - _STOP_WORDS


def _word_similarity(text_a: str, text_b: str) -> float:
    """Jaccard similarity on tokenized words."""
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union) if union else 0.0


def _query_relevance(query: str, text: str) -> float:
    """Fraction of query tokens found in text (directional relevance)."""
    q_tokens = _tokenize(query)
    t_tokens = _tokenize(text)
    if not q_tokens or not t_tokens:
        return 0.0
    return len(q_tokens & t_tokens) / len(q_tokens)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class HiveFact:
    """A fact in the shared hive knowledge graph.

    Attributes:
        fact_id: Unique identifier
        content: The textual fact
        confidence: Aggregated confidence across contributing agents
        source_agents: Which agents contributed/promoted this fact
        promotion_count: How many agents promoted this fact
        created_at: When the fact was first promoted to hive
        tags: Categorization tags
    """

    fact_id: str
    content: str
    confidence: float
    source_agents: list[str] = field(default_factory=list)
    promotion_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    tags: list[str] = field(default_factory=list)


@dataclass
class LocalFact:
    """A fact in an agent's local knowledge store.

    Attributes:
        fact_id: Unique identifier
        content: The textual fact
        confidence: Agent's confidence in this fact
        tags: Categorization tags
        created_at: When the fact was stored
        from_hive: Whether this fact was pulled from the hive
        hive_fact_id: If pulled from hive, the original hive fact_id
    """

    fact_id: str
    content: str
    confidence: float
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    from_hive: bool = False
    hive_fact_id: str | None = None


@dataclass
class PendingPromotion:
    """A fact proposed for promotion, awaiting votes.

    Attributes:
        fact_id: Unique identifier for the pending promotion
        content: The fact text proposed for promotion
        proposer_agent_id: Agent that proposed the promotion
        confidence: Proposer's confidence
        votes: Map of agent_id -> bool (True = approve, False = reject)
        tags: Tags from the proposer
        proposed_at: When the proposal was made
    """

    fact_id: str
    content: str
    proposer_agent_id: str
    confidence: float
    votes: dict[str, bool] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    proposed_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Promotion Policy
# ---------------------------------------------------------------------------


class PromotionPolicy:
    """Configurable rules for when a fact qualifies for promotion to hive.

    Attributes:
        confidence_threshold: Minimum aggregated confidence to promote (0.0-1.0)
        consensus_required: How many agents must vote approve

    Example:
        >>> policy = PromotionPolicy(confidence_threshold=0.7, consensus_required=2)
        >>> policy.should_promote(pending, {"agent_a": True, "agent_b": True})
        True
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        consensus_required: int = 1,
    ) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError(f"confidence_threshold must be in [0, 1], got {confidence_threshold}")
        if consensus_required < 1:
            raise ValueError(f"consensus_required must be >= 1, got {consensus_required}")
        self.confidence_threshold = confidence_threshold
        self.consensus_required = consensus_required

    def aggregate_confidence(self, agent_confidences: list[float]) -> float:
        """Weighted average of agent confidences.

        Uses simple mean. With more agents agreeing, confidence is more reliable.

        Args:
            agent_confidences: List of confidence values from voting agents

        Returns:
            Aggregated confidence in [0.0, 1.0]
        """
        if not agent_confidences:
            return 0.0
        return sum(agent_confidences) / len(agent_confidences)

    def should_promote(
        self,
        pending: PendingPromotion,
        agent_votes: dict[str, bool],
    ) -> bool:
        """Decide if a pending fact qualifies for promotion.

        Checks:
        1. Number of approve votes >= consensus_required
        2. Aggregated confidence >= confidence_threshold

        Args:
            pending: The pending promotion record
            agent_votes: Map of agent_id -> vote (True=approve)

        Returns:
            True if the fact should be promoted to hive
        """
        approve_count = sum(1 for v in agent_votes.values() if v)
        if approve_count < self.consensus_required:
            return False

        # Collect confidences from approving agents: use the proposer's confidence
        # as baseline, each approver adds implicit confidence
        confidences = [pending.confidence]
        # Each approver implicitly adds confidence at 0.8 (they agree)
        for agent_id, vote in agent_votes.items():
            if vote and agent_id != pending.proposer_agent_id:
                confidences.append(0.8)

        aggregated = self.aggregate_confidence(confidences)
        return aggregated >= self.confidence_threshold


# ---------------------------------------------------------------------------
# Promotion Manager
# ---------------------------------------------------------------------------


class PromotionManager:
    """Manages the lifecycle of promoting local facts to the shared hive.

    Stores pending promotions in memory and coordinates the
    propose -> vote -> check_and_promote pipeline.

    Example:
        >>> pm = PromotionManager(policy=PromotionPolicy(consensus_required=2))
        >>> fact_id = pm.propose_promotion("agent_a", "Python is interpreted", 0.9)
        >>> pm.vote_on_promotion("agent_b", fact_id, True)
        >>> result = pm.check_and_promote(fact_id)
        >>> result is not None  # HiveFact if promoted
        True
    """

    def __init__(self, policy: PromotionPolicy | None = None) -> None:
        self.policy = policy or PromotionPolicy()
        self._pending: dict[str, PendingPromotion] = {}
        self._promoted: dict[str, HiveFact] = {}

    def propose_promotion(
        self,
        agent_id: str,
        fact_content: str,
        confidence: float,
        tags: list[str] | None = None,
    ) -> str:
        """Propose a local fact for promotion to hive.

        The proposer's vote is automatically counted as approve.

        Args:
            agent_id: Agent proposing the fact
            fact_content: The fact text
            confidence: Agent's confidence in the fact
            tags: Optional categorization tags

        Returns:
            fact_id of the pending promotion
        """
        fact_id = str(uuid.uuid4())
        pending = PendingPromotion(
            fact_id=fact_id,
            content=fact_content,
            proposer_agent_id=agent_id,
            confidence=confidence,
            votes={agent_id: True},
            tags=tags or [],
        )
        self._pending[fact_id] = pending
        return fact_id

    def vote_on_promotion(self, agent_id: str, fact_id: str, vote: bool) -> bool:
        """Cast a vote on a pending promotion.

        Args:
            agent_id: Voting agent
            fact_id: Fact being voted on
            vote: True to approve, False to reject

        Returns:
            True if vote was recorded, False if fact_id not found

        Raises:
            ValueError: If agent already voted on this fact
        """
        if fact_id not in self._pending:
            return False
        pending = self._pending[fact_id]
        if agent_id in pending.votes:
            raise ValueError(f"Agent {agent_id} already voted on fact {fact_id}")
        pending.votes[agent_id] = vote
        return True

    def check_and_promote(self, fact_id: str) -> HiveFact | None:
        """Check if a pending fact meets the policy and promote if so.

        If the fact meets the promotion policy, it is removed from pending
        and added to promoted. Otherwise, it stays pending.

        Args:
            fact_id: The pending fact to check

        Returns:
            HiveFact if promoted, None if not yet qualifying or not found
        """
        if fact_id not in self._pending:
            return None
        pending = self._pending[fact_id]
        if not self.policy.should_promote(pending, pending.votes):
            return None

        # Promote: create HiveFact
        approve_agents = [aid for aid, v in pending.votes.items() if v]
        # Aggregate confidence from proposer + approvers
        confidences = [pending.confidence]
        for aid in approve_agents:
            if aid != pending.proposer_agent_id:
                confidences.append(0.8)
        aggregated_conf = self.policy.aggregate_confidence(confidences)

        hive_fact = HiveFact(
            fact_id=pending.fact_id,
            content=pending.content,
            confidence=min(aggregated_conf, 1.0),
            source_agents=approve_agents,
            promotion_count=len(approve_agents),
            tags=pending.tags,
        )
        self._promoted[fact_id] = hive_fact
        del self._pending[fact_id]
        return hive_fact

    def get_pending_promotions(self) -> list[PendingPromotion]:
        """Return all facts currently awaiting consensus.

        Returns:
            List of PendingPromotion records
        """
        return list(self._pending.values())

    def get_promoted_facts(self) -> dict[str, HiveFact]:
        """Return all successfully promoted facts.

        Returns:
            Dict mapping fact_id to HiveFact
        """
        return dict(self._promoted)


# ---------------------------------------------------------------------------
# Pull Manager
# ---------------------------------------------------------------------------


class PullManager:
    """Manages pulling shared hive facts into an agent's local context.

    Provides query-based search over hive facts and tracks which facts
    each agent has pulled.

    Example:
        >>> pm = PullManager(hive_facts)
        >>> results = pm.query_hive("network latency", limit=5)
        >>> pm.pull_to_local("agent_a", results[0].fact_id)
    """

    def __init__(self, hive_store: dict[str, HiveFact] | None = None) -> None:
        self._hive_store = hive_store if hive_store is not None else {}
        self._pull_history: dict[str, list[str]] = {}  # agent_id -> [fact_ids]

    def set_hive_store(self, store: dict[str, HiveFact]) -> None:
        """Update the reference to the hive fact store.

        Args:
            store: Dict mapping fact_id to HiveFact
        """
        self._hive_store = store

    def query_hive(self, query: str, limit: int = 10) -> list[HiveFact]:
        """Search hive facts by relevance to a query.

        Uses directional query relevance (fraction of query tokens found in fact).

        Args:
            query: Search query text
            limit: Maximum number of results

        Returns:
            List of HiveFact sorted by relevance (most relevant first)
        """
        if not query or not self._hive_store:
            return []

        scored: list[tuple[float, HiveFact]] = []
        for hf in self._hive_store.values():
            # Combine content and tags for matching
            searchable = hf.content + " " + " ".join(hf.tags)
            relevance = _query_relevance(query, searchable)
            if relevance > 0.0:
                scored.append((relevance, hf))

        scored.sort(key=lambda x: -x[0])
        return [hf for _, hf in scored[:limit]]

    def pull_to_local(self, agent_id: str, fact_id: str) -> HiveFact | None:
        """Record that an agent pulled a hive fact to local context.

        Args:
            agent_id: The agent pulling the fact
            fact_id: The hive fact to pull

        Returns:
            The HiveFact if found, None otherwise
        """
        if fact_id not in self._hive_store:
            return None

        if agent_id not in self._pull_history:
            self._pull_history[agent_id] = []

        if fact_id not in self._pull_history[agent_id]:
            self._pull_history[agent_id].append(fact_id)

        return self._hive_store[fact_id]

    def get_pull_history(self, agent_id: str) -> list[str]:
        """Get the list of hive fact_ids an agent has pulled.

        Args:
            agent_id: The agent to query

        Returns:
            List of fact_ids the agent has pulled
        """
        return list(self._pull_history.get(agent_id, []))


# ---------------------------------------------------------------------------
# Hierarchical Knowledge Graph
# ---------------------------------------------------------------------------


class HierarchicalKnowledgeGraph:
    """Orchestrates a two-level knowledge graph: local per-agent + shared hive.

    Level 1 (Local): Each agent has isolated fact storage.
    Level 2 (Hive): Shared facts promoted via consensus.

    Agents store facts locally, propose high-confidence facts for promotion,
    vote on others' proposals, and pull hive facts into local context.

    Example:
        >>> hkg = HierarchicalKnowledgeGraph()
        >>> hkg.register_agent("agent_a")
        >>> hkg.register_agent("agent_b")
        >>> hkg.store_local_fact("agent_a", "Python is interpreted", 0.9, ["python"])
        >>> fact_id = hkg.promote_fact("agent_a", "Python is interpreted", 0.9)
        >>> results = hkg.query_hive("python language")
    """

    def __init__(self, promotion_policy: PromotionPolicy | None = None) -> None:
        self._policy = promotion_policy or PromotionPolicy()
        self._lock = threading.RLock()
        self._agents: set[str] = set()
        # Local facts: agent_id -> {fact_id -> LocalFact}
        self._local_stores: dict[str, dict[str, LocalFact]] = {}
        # Hive facts: fact_id -> HiveFact
        self._hive_store: dict[str, HiveFact] = {}
        # Managers
        self._promotion_mgr = PromotionManager(policy=self._policy)
        self._pull_mgr = PullManager(hive_store=self._hive_store)

    def register_agent(self, agent_id: str) -> None:
        """Register an agent in the knowledge graph.

        Creates an empty local store for the agent.

        Args:
            agent_id: Unique agent identifier
        """
        with self._lock:
            self._agents.add(agent_id)
            if agent_id not in self._local_stores:
                self._local_stores[agent_id] = {}

    def _ensure_agent(self, agent_id: str) -> None:
        """Raise ValueError if agent is not registered."""
        if agent_id not in self._agents:
            raise ValueError(f"Agent '{agent_id}' is not registered. Call register_agent first.")

    def store_local_fact(
        self,
        agent_id: str,
        fact: str,
        confidence: float,
        tags: list[str] | None = None,
    ) -> str:
        """Store a fact in an agent's local graph.

        Args:
            agent_id: The owning agent
            fact: Fact text
            confidence: Agent's confidence in [0.0, 1.0]
            tags: Optional categorization tags

        Returns:
            fact_id of the stored local fact
        """
        with self._lock:
            self._ensure_agent(agent_id)
            fact_id = str(uuid.uuid4())
            local_fact = LocalFact(
                fact_id=fact_id,
                content=fact,
                confidence=confidence,
                tags=tags or [],
            )
            self._local_stores[agent_id][fact_id] = local_fact
            return fact_id

    def promote_fact(
        self,
        agent_id: str,
        fact_content: str,
        confidence: float,
        tags: list[str] | None = None,
    ) -> str:
        """Propose a fact for promotion to the hive.

        The proposer automatically votes approve. Other agents must vote
        before the fact can be promoted (if consensus_required > 1).

        If consensus_required == 1, the fact is immediately promoted.

        Args:
            agent_id: The proposing agent
            fact_content: Fact text to promote
            confidence: Agent's confidence
            tags: Optional tags

        Returns:
            fact_id of the pending (or immediately promoted) fact
        """
        with self._lock:
            self._ensure_agent(agent_id)
            fact_id = self._promotion_mgr.propose_promotion(
                agent_id,
                fact_content,
                confidence,
                tags=tags,
            )
            # Try immediate promotion (works if consensus_required == 1)
            result = self._promotion_mgr.check_and_promote(fact_id)
            if result is not None:
                self._hive_store[result.fact_id] = result
            return fact_id

    def vote_on_promotion(self, agent_id: str, fact_id: str, vote: bool) -> HiveFact | None:
        """Vote on a pending promotion and auto-check if it qualifies.

        Args:
            agent_id: Voting agent
            fact_id: Pending fact
            vote: True to approve

        Returns:
            HiveFact if the vote caused promotion, None otherwise
        """
        with self._lock:
            self._ensure_agent(agent_id)
            recorded = self._promotion_mgr.vote_on_promotion(agent_id, fact_id, vote)
            if not recorded:
                return None
            result = self._promotion_mgr.check_and_promote(fact_id)
            if result is not None:
                self._hive_store[result.fact_id] = result
            return result

    def get_pending_promotions(self) -> list[PendingPromotion]:
        """Get all facts awaiting consensus votes.

        Returns:
            List of PendingPromotion records
        """
        return self._promotion_mgr.get_pending_promotions()

    def query_local(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
    ) -> list[LocalFact]:
        """Query an agent's local fact store by relevance.

        Args:
            agent_id: The agent whose local store to search
            query: Search query
            limit: Max results

        Returns:
            List of LocalFact sorted by relevance
        """
        with self._lock:
            self._ensure_agent(agent_id)
            local_facts = self._local_stores.get(agent_id, {})
            if not local_facts or not query:
                return []

            scored: list[tuple[float, LocalFact]] = []
            for lf in local_facts.values():
                searchable = lf.content + " " + " ".join(lf.tags)
                relevance = _query_relevance(query, searchable)
                if relevance > 0.0:
                    scored.append((relevance, lf))

            scored.sort(key=lambda x: -x[0])
            return [lf for _, lf in scored[:limit]]

    def query_hive(self, query: str, limit: int = 10) -> list[HiveFact]:
        """Query the shared hive facts by relevance.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of HiveFact sorted by relevance
        """
        with self._lock:
            return self._pull_mgr.query_hive(query, limit=limit)

    def pull_hive_fact(self, agent_id: str, fact_id: str) -> LocalFact | None:
        """Pull a hive fact into an agent's local store.

        Creates a local copy of the hive fact with from_hive=True.

        Args:
            agent_id: Agent pulling the fact
            fact_id: Hive fact to pull

        Returns:
            LocalFact copy if successful, None if fact not found
        """
        with self._lock:
            self._ensure_agent(agent_id)
            hive_fact = self._pull_mgr.pull_to_local(agent_id, fact_id)
            if hive_fact is None:
                return None

            # Check if already pulled (avoid duplicates)
            for lf in self._local_stores[agent_id].values():
                if lf.hive_fact_id == fact_id:
                    return lf

            local_fact = LocalFact(
                fact_id=str(uuid.uuid4()),
                content=hive_fact.content,
                confidence=hive_fact.confidence,
                tags=list(hive_fact.tags),
                from_hive=True,
                hive_fact_id=hive_fact.fact_id,
            )
            self._local_stores[agent_id][local_fact.fact_id] = local_fact
            return local_fact

    def query_combined(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query both local and hive, merge results by relevance.

        Returns dicts with 'source' field ('local' or 'hive') and the fact data.

        Args:
            agent_id: The querying agent
            query: Search query
            limit: Max total results

        Returns:
            List of dicts with keys: source, fact_id, content, confidence, tags, relevance
        """
        with self._lock:
            self._ensure_agent(agent_id)
            results: list[dict[str, Any]] = []

            # Score local facts
            local_facts = self._local_stores.get(agent_id, {})
            for lf in local_facts.values():
                searchable = lf.content + " " + " ".join(lf.tags)
                relevance = _query_relevance(query, searchable)
                if relevance > 0.0:
                    results.append(
                        {
                            "source": "local",
                            "fact_id": lf.fact_id,
                            "content": lf.content,
                            "confidence": lf.confidence,
                            "tags": lf.tags,
                            "relevance": relevance,
                        }
                    )

            # Score hive facts (avoid duplicates already pulled)
            pulled_hive_ids = {
                lf.hive_fact_id for lf in local_facts.values() if lf.from_hive and lf.hive_fact_id
            }
            for hf in self._hive_store.values():
                if hf.fact_id in pulled_hive_ids:
                    continue  # Already in local via pull
                searchable = hf.content + " " + " ".join(hf.tags)
                relevance = _query_relevance(query, searchable)
                if relevance > 0.0:
                    results.append(
                        {
                            "source": "hive",
                            "fact_id": hf.fact_id,
                            "content": hf.content,
                            "confidence": hf.confidence,
                            "tags": hf.tags,
                            "relevance": relevance,
                        }
                    )

            results.sort(key=lambda x: -x["relevance"])
            return results[:limit]

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about the knowledge graph.

        Returns:
            Dict with keys:
                registered_agents: number of agents
                local_facts_per_agent: dict of agent_id -> fact count
                hive_facts: total hive facts
                pending_promotions: facts awaiting votes
                promotion_rate: fraction of proposals that were promoted
                total_local_facts: sum across all agents
        """
        with self._lock:
            local_counts = {aid: len(facts) for aid, facts in self._local_stores.items()}
            total_local = sum(local_counts.values())
            promoted_count = len(self._hive_store)
            pending_count = len(self._promotion_mgr.get_pending_promotions())
            total_proposals = promoted_count + pending_count

            return {
                "registered_agents": len(self._agents),
                "local_facts_per_agent": local_counts,
                "hive_facts": promoted_count,
                "pending_promotions": pending_count,
                "promotion_rate": (
                    promoted_count / total_proposals if total_proposals > 0 else 0.0
                ),
                "total_local_facts": total_local,
            }


__all__ = [
    "HiveFact",
    "LocalFact",
    "PendingPromotion",
    "PromotionPolicy",
    "PromotionManager",
    "PullManager",
    "HierarchicalKnowledgeGraph",
]
