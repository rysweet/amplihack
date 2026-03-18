"""Tests for distributed retrieval parity fixes.

Covers three regression vectors identified in the retrieval parity analysis:

1. search_facts() hive candidate budget — hive must get limit * HIVE_SEARCH_MULTIPLIER
   candidates, not just limit, so it has equal ranking headroom vs local.

2. _merge_fact_lists() no-query bias — without a query, local and hive facts must
   compete on equal footing (score 0.5 each) rather than local always winning (1.0 vs 0.0).

3. apphost.cs HIVE_ENABLE_DISTRIBUTED_RETRIEVAL default — must be "true" to match
   deploy.sh and ensure distributed retrieval is on by default for 100-agent topology.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Minimal stubs
# ---------------------------------------------------------------------------


class _SemanticFact:
    def __init__(
        self,
        content: str,
        concept: str = "test",
        confidence: float = 0.8,
    ) -> None:
        self.content = content
        self.concept = concept
        self.confidence = confidence
        self.fact_id = content[:20].replace(" ", "-")
        self.node_id = self.fact_id
        self.created_at = 0.0
        self.tags: list[str] = []
        self.source_agent = ""


class _RecordingLocalMemory:
    """Records search_facts calls so tests can inspect the limit argument."""

    def __init__(self, facts: list[_SemanticFact] | None = None) -> None:
        self._facts = facts or []
        self.search_calls: list[tuple[str, int]] = []
        self.all_facts_calls: list[int] = []

    def search_facts(
        self,
        query: str = "",
        limit: int = 10,
        min_confidence: float = 0.0,
        **kwargs: Any,
    ) -> list[_SemanticFact]:
        self.search_calls.append((query, limit))
        return self._facts[:limit]

    def get_all_facts(self, limit: int = 50, **kwargs: Any) -> list[_SemanticFact]:
        self.all_facts_calls.append(limit)
        return self._facts[:limit]

    def store_fact(self, *args: Any, **kwargs: Any) -> Any:
        return None


class _RecordingHive:
    """Records query_facts calls so tests can inspect the limit argument."""

    def __init__(self, results: list[dict[str, Any]] | None = None) -> None:
        self._results = results or []
        self.query_calls: list[tuple[str, int]] = []
        self.get_all_calls: list[int] = []

    def query_facts(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        self.query_calls.append((query, limit))
        return self._results[:limit]

    def get_all_facts(self, limit: int = 50) -> list[dict[str, Any]]:
        self.get_all_calls.append(limit)
        return self._results[:limit]

    def promote_fact(self, *args: Any, **kwargs: Any) -> None:
        pass


def _make_hive_fact(content: str) -> dict[str, Any]:
    return {
        "fact_id": content[:20].replace(" ", "-"),
        "concept": "test",
        "content": content,
        "confidence": 0.7,
        "source_agent": "agent-1",
        "tags": [],
    }


# ---------------------------------------------------------------------------
# Import under test
# ---------------------------------------------------------------------------


from amplihack.agents.goal_seeking.hive_mind.distributed_memory import (
    DistributedCognitiveMemory,
)
from amplihack.agents.goal_seeking.retrieval_constants import HIVE_SEARCH_MULTIPLIER

# ---------------------------------------------------------------------------
# Fix 1: search_facts() hive candidate budget parity
# ---------------------------------------------------------------------------


class TestSearchFactsHiveBudget:
    """Hive must receive limit * HIVE_SEARCH_MULTIPLIER, not just limit."""

    def _make(
        self, local_facts: list[_SemanticFact] | None = None, hive_facts: list[dict] | None = None
    ) -> tuple[DistributedCognitiveMemory, _RecordingLocalMemory, _RecordingHive]:
        local = _RecordingLocalMemory(local_facts)
        hive = _RecordingHive(hive_facts)
        mem = DistributedCognitiveMemory(local, hive, agent_name="test-agent")
        return mem, local, hive

    def test_hive_receives_multiplied_limit(self):
        mem, local, hive = self._make()
        mem.search_facts("project atlas", limit=10)

        assert len(hive.query_calls) == 1
        _, hive_limit = hive.query_calls[0]
        assert hive_limit == 10 * HIVE_SEARCH_MULTIPLIER, (
            f"Expected hive limit={10 * HIVE_SEARCH_MULTIPLIER}, got {hive_limit}. "
            "Hive must get limit * HIVE_SEARCH_MULTIPLIER to have equal candidate headroom."
        )

    def test_local_receives_multiplied_limit(self):
        """Local search budget should still be limit * HIVE_SEARCH_MULTIPLIER (pre-existing)."""
        mem, local, hive = self._make()
        mem.search_facts("project atlas", limit=5)

        assert len(local.search_calls) == 1
        _, local_limit = local.search_calls[0]
        assert local_limit == 5 * HIVE_SEARCH_MULTIPLIER

    def test_both_receive_same_multiplied_limit(self):
        """Local and hive receive the same broad-fetch limit — symmetric headroom."""
        mem, local, hive = self._make()
        limit = 7
        mem.search_facts("security log", limit=limit)

        _, local_limit = local.search_calls[0]
        _, hive_limit = hive.query_calls[0]
        assert local_limit == hive_limit, (
            f"Local and hive must receive the same limit ({local_limit} vs {hive_limit}). "
            "Asymmetric limits mean hive candidates are under-represented in the merge."
        )

    def test_merged_result_count_respects_limit(self):
        """Final result is capped at the requested limit."""
        local_facts = [_SemanticFact(f"local fact {i}") for i in range(20)]
        hive_facts = [_make_hive_fact(f"hive fact {i}") for i in range(20)]
        mem, _, _ = self._make(local_facts, hive_facts)

        results = mem.search_facts("fact", limit=5)
        assert len(results) <= 5, f"Expected ≤5 results, got {len(results)}"

    def test_empty_hive_returns_local_only(self):
        """When hive returns nothing, result is local facts (no crash)."""
        local_facts = [_SemanticFact("the server migration cost $450K")]
        mem, _, _ = self._make(local_facts, [])

        results = mem.search_facts("migration cost", limit=5)
        assert len(results) == 1
        assert "450K" in results[0].content


# ---------------------------------------------------------------------------
# Fix 2: _merge_fact_lists no-query bias
# ---------------------------------------------------------------------------


class TestMergeFactListsNoBias:
    """Without a query, local and hive facts must have equal scores."""

    def _make_mem_with_facts(
        self,
        local_content: list[str],
        hive_content: list[str],
    ) -> DistributedCognitiveMemory:
        local = _RecordingLocalMemory([_SemanticFact(c) for c in local_content])
        hive = _RecordingHive([_make_hive_fact(c) for c in hive_content])
        return DistributedCognitiveMemory(local, hive, agent_name="test-agent")

    def test_hive_facts_included_without_query(self):
        """Hive facts must appear in get_all_facts() results (not suppressed)."""
        mem = self._make_mem_with_facts(
            local_content=["local fact alpha"],
            hive_content=["hive fact beta"],
        )
        results = mem.get_all_facts(limit=10)

        # Both local and hive content should be present
        all_content = " ".join(
            (r.get("outcome", r.get("content", "")) if isinstance(r, dict) else r.content)
            for r in results
        )
        assert "alpha" in all_content, "Local fact must be present"
        assert "beta" in all_content, "Hive fact must be present — should not be suppressed by bias"

    def test_no_query_does_not_always_put_local_first(self):
        """When no query is given, hive facts can appear before local facts (deterministic tiebreaker)."""
        # "aaa..." sorts before "zzz..." — hive fact with 'aaa' should appear first
        local_content = ["zzz local fact"]
        hive_content = ["aaa hive fact"]

        mem = self._make_mem_with_facts(local_content, hive_content)
        results = mem.get_all_facts(limit=10)

        assert len(results) == 2

        # Extract text content
        def _text(r: Any) -> str:
            if isinstance(r, dict):
                return r.get("outcome", r.get("content", ""))
            return r.content

        # With equal scores (0.5), the secondary sort is content alphabetically
        # 'aaa hive fact' < 'zzz local fact', so hive fact comes first
        first_text = _text(results[0])
        second_text = _text(results[1])
        assert "aaa" in first_text, (
            f"Expected 'aaa hive fact' first (alphabetical tiebreaker), "
            f"got '{first_text}' then '{second_text}'. "
            "This indicates local facts are still getting score=1.0 while hive gets 0.5."
        )

    def test_with_query_hive_facts_ranked_by_relevance(self):
        """With a query, the most relevant fact wins regardless of source."""
        local_content = ["team meeting scheduled for Tuesday"]
        hive_content = ["critical security CVE-2024-1234 patched"]

        mem = self._make_mem_with_facts(local_content, hive_content)
        results = mem.search_facts("security vulnerability", limit=10)

        def _text(r: Any) -> str:
            if isinstance(r, dict):
                return r.get("outcome", r.get("content", ""))
            return r.content

        first_text = _text(results[0]) if results else ""
        assert "security" in first_text or "CVE" in first_text, (
            f"With query 'security vulnerability', hive's security fact should rank first, "
            f"got '{first_text}'"
        )

    def test_dedup_same_content_from_local_and_hive(self):
        """Facts with identical content are deduplicated regardless of source."""
        shared_content = "Sarah Chen's birthday is March 15"
        mem = self._make_mem_with_facts(
            local_content=[shared_content],
            hive_content=[shared_content],
        )
        results = mem.get_all_facts(limit=10)
        assert len(results) == 1, (
            f"Expected 1 deduplicated result, got {len(results)}. "
            "Same content from local and hive should appear only once."
        )


# ---------------------------------------------------------------------------
# Fix 3: apphost.cs HIVE_ENABLE_DISTRIBUTED_RETRIEVAL default
# ---------------------------------------------------------------------------


class TestApphostDistributedRetrievalDefault:
    """The Aspire apphost.cs must default HIVE_ENABLE_DISTRIBUTED_RETRIEVAL to 'true'."""

    def test_apphost_defaults_to_true(self):
        """apphost.cs must match deploy.sh default (true) for the federated-100 profile."""
        import pathlib

        apphost = (
            pathlib.Path(__file__).parents[2] / "deploy" / "azure_hive" / "aspire" / "apphost.cs"
        )
        assert apphost.exists(), f"apphost.cs not found at {apphost}"

        content = apphost.read_text()

        # Find the enableDistributedRetrieval GetConfig call
        idx = content.find('"azure:enableDistributedRetrieval"')
        assert idx != -1, "Could not find enableDistributedRetrieval config key in apphost.cs"

        # Extract the surrounding context (within 200 chars)
        snippet = content[idx : idx + 300]

        # The default value must be "true", not "false"
        assert '"true"' in snippet, (
            f"apphost.cs HIVE_ENABLE_DISTRIBUTED_RETRIEVAL default is not 'true'. "
            f"Found: {snippet!r}. "
            "This must match deploy.sh default=true — a false default silently disables "
            "distributed retrieval for 100-agent topology where each agent has only ~1% of corpus."
        )
        assert '"false"' not in snippet, (
            f"apphost.cs still has 'false' as default for HIVE_ENABLE_DISTRIBUTED_RETRIEVAL. "
            f"Found: {snippet!r}"
        )


# ---------------------------------------------------------------------------
# Merge helpers (internal unit tests)
# ---------------------------------------------------------------------------


class TestMergeHelpersSymmetry:
    """Unit tests for the internal merge helper methods."""

    def _make(self) -> DistributedCognitiveMemory:
        return DistributedCognitiveMemory(
            _RecordingLocalMemory(), _RecordingHive(), agent_name="test"
        )

    def test_relevance_score_empty_query_returns_zero(self):
        """_relevance_score with empty query returns 0.0 (no-op)."""
        mem = self._make()
        score = mem._relevance_score({"outcome": "some content"}, "")
        assert score == 0.0

    def test_relevance_score_exact_match(self):
        """_relevance_score gives a high score for a near-exact match."""
        mem = self._make()
        score = mem._relevance_score(
            {"outcome": "Sarah Chen birthday March 15"}, "Sarah Chen birthday"
        )
        assert score > 0.5, f"Expected high relevance score, got {score}"

    def test_relevance_score_no_overlap(self):
        """_relevance_score gives a low score for unrelated content."""
        mem = self._make()
        score = mem._relevance_score({"outcome": "quarterly revenue figures"}, "SSH login failure")
        assert score < 0.3, f"Expected low relevance score, got {score}"

    def test_extract_content_dict(self):
        """_extract_content handles dict facts."""
        mem = self._make()
        assert mem._extract_content({"outcome": "hello"}) == "hello"
        assert mem._extract_content({"content": "world"}) == "world"
        assert mem._extract_content({"fact": "test"}) == "test"

    def test_extract_content_object(self):
        """_extract_content handles object facts."""
        mem = self._make()
        fact = _SemanticFact("object content")
        assert mem._extract_content(fact) == "object content"
