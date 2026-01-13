"""Unit tests fer token budget enforcement in memory retrieval.

Tests token counting, budget allocation, and enforcement logic
to ensure memory injection stays within 8000 token limit.

Philosophy:
- Strict budget enforcement (never exceed)
- Weighted allocation by relevance
- Transparent budget tracking
"""

import pytest

# These imports will fail until implementation exists (TDD)
try:
    from amplihack.memory.token_budget import (
        BudgetAllocation,
        TokenBudget,
        TokenCounter,
        WeightedAllocator,
        estimate_tokens,
    )

    from amplihack.memory.types import MemoryEntry, MemoryType
except ImportError:
    pytest.skip("Token budget not implemented yet", allow_module_level=True)


class TestTokenCounter:
    """Test token counting fer different content types."""

    def test_count_empty_string(self):
        """Empty string is 0 tokens."""
        assert TokenCounter.count("") == 0

    def test_count_simple_string(self):
        """Count tokens in simple string."""
        text = "Hello world"
        # Rough estimate: ~1.3 chars per token
        estimated = len(text) / 1.3
        actual = TokenCounter.count(text)
        # Allow 20% variance in estimation
        assert abs(actual - estimated) < estimated * 0.2

    def test_count_long_text(self):
        """Count tokens in longer text."""
        text = "The quick brown fox jumps over the lazy dog. " * 10
        count = TokenCounter.count(text)
        # Should be roughly 450 chars / 1.3 ≈ 346 tokens
        assert 250 < count < 450

    def test_count_code_snippet(self):
        """Count tokens in code (typically more tokens per char)."""
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        count = TokenCounter.count(code)
        # Code tends to have more tokens per character
        assert count > 20

    def test_count_json_structure(self):
        """Count tokens in JSON structure."""
        json_str = '{"key": "value", "nested": {"a": 1, "b": 2}}'
        count = TokenCounter.count(json_str)
        assert count > 0

    def test_estimate_tokens_helper(self):
        """Test quick token estimation helper."""
        text = "Test string"
        # estimate_tokens should be faster approximation
        estimated = estimate_tokens(text)
        actual = TokenCounter.count(text)
        # Should be reasonably close
        assert abs(estimated - actual) < 5


class TestTokenBudget:
    """Test TokenBudget allocation and enforcement."""

    def test_create_budget_with_limit(self):
        """Create budget with specified limit."""
        budget = TokenBudget(max_tokens=8000)
        assert budget.max_tokens == 8000
        assert budget.remaining == 8000
        assert budget.used == 0

    def test_allocate_within_budget(self):
        """Allocate tokens within budget succeeds."""
        budget = TokenBudget(max_tokens=1000)

        success = budget.allocate(500, "episodic-memory-1")
        assert success
        assert budget.used == 500
        assert budget.remaining == 500

    def test_allocate_exceeds_budget_fails(self):
        """Allocating more than budget fails."""
        budget = TokenBudget(max_tokens=1000)

        budget.allocate(800, "memory-1")

        # Try to allocate more than remaining
        success = budget.allocate(300, "memory-2")
        assert not success
        assert budget.used == 800  # First allocation still there

    def test_allocate_exact_budget(self):
        """Allocating exactly budget amount succeeds."""
        budget = TokenBudget(max_tokens=1000)

        success = budget.allocate(1000, "memory-1")
        assert success
        assert budget.remaining == 0

    def test_multiple_allocations(self):
        """Multiple allocations tracked correctly."""
        budget = TokenBudget(max_tokens=1000)

        budget.allocate(300, "memory-1")
        budget.allocate(200, "memory-2")
        budget.allocate(100, "memory-3")

        assert budget.used == 600
        assert budget.remaining == 400
        assert len(budget.allocations) == 3

    def test_deallocate_tokens(self):
        """Deallocating returns tokens to budget."""
        budget = TokenBudget(max_tokens=1000)

        budget.allocate(500, "memory-1")
        budget.deallocate("memory-1")

        assert budget.used == 0
        assert budget.remaining == 1000

    def test_reset_budget(self):
        """Reset clears all allocations."""
        budget = TokenBudget(max_tokens=1000)

        budget.allocate(300, "memory-1")
        budget.allocate(200, "memory-2")

        budget.reset()

        assert budget.used == 0
        assert budget.remaining == 1000
        assert len(budget.allocations) == 0

    def test_get_allocation_summary(self):
        """Get summary of current allocations."""
        budget = TokenBudget(max_tokens=1000)

        budget.allocate(300, "episodic-1")
        budget.allocate(200, "semantic-1")

        summary = budget.get_summary()
        assert summary["max_tokens"] == 1000
        assert summary["used"] == 500
        assert summary["remaining"] == 500
        assert summary["allocation_count"] == 2


class TestBudgetAllocation:
    """Test BudgetAllocation data structure."""

    def test_allocation_creation(self):
        """Create allocation with ID and token count."""
        allocation = BudgetAllocation(
            id="memory-123",
            tokens=500,
            memory_type=MemoryType.EPISODIC,
        )

        assert allocation.id == "memory-123"
        assert allocation.tokens == 500
        assert allocation.memory_type == MemoryType.EPISODIC

    def test_allocation_with_metadata(self):
        """Allocation can include metadata."""
        allocation = BudgetAllocation(
            id="memory-123",
            tokens=500,
            memory_type=MemoryType.SEMANTIC,
            metadata={
                "relevance_score": 0.9,
                "timestamp": "2025-01-11",
            },
        )

        assert allocation.metadata["relevance_score"] == 0.9


class TestWeightedAllocator:
    """Test weighted budget allocation by relevance."""

    def test_allocate_by_relevance_scores(self):
        """Allocate tokens weighted by relevance scores."""
        allocator = WeightedAllocator(max_tokens=1000)

        memories = [
            {"id": "mem-1", "content": "High relevance", "relevance": 0.9},
            {"id": "mem-2", "content": "Medium relevance", "relevance": 0.6},
            {"id": "mem-3", "content": "Low relevance", "relevance": 0.3},
        ]

        allocations = allocator.allocate(memories)

        # Higher relevance should get more tokens
        mem1_tokens = allocations["mem-1"]
        mem2_tokens = allocations["mem-2"]
        mem3_tokens = allocations["mem-3"]

        assert mem1_tokens > mem2_tokens > mem3_tokens
        assert sum([mem1_tokens, mem2_tokens, mem3_tokens]) <= 1000

    def test_allocate_prioritizes_recent(self):
        """When relevance equal, prioritize recent memories."""
        from datetime import datetime, timedelta

        allocator = WeightedAllocator(max_tokens=1000)

        now = datetime.now()
        memories = [
            {
                "id": "mem-1",
                "content": "Recent",
                "relevance": 0.8,
                "timestamp": now,
            },
            {
                "id": "mem-2",
                "content": "Old",
                "relevance": 0.8,
                "timestamp": now - timedelta(days=7),
            },
        ]

        allocations = allocator.allocate(memories)

        # Recent should get slightly more with same relevance
        assert allocations["mem-1"] >= allocations["mem-2"]

    def test_allocate_respects_budget_strict(self):
        """Allocator never exceeds budget."""
        allocator = WeightedAllocator(max_tokens=500)

        # Create many high-relevance memories
        memories = [{"id": f"mem-{i}", "content": "x" * 100, "relevance": 0.9} for i in range(20)]

        allocations = allocator.allocate(memories)

        total_tokens = sum(allocations.values())
        assert total_tokens <= 500

    def test_allocate_min_tokens_per_memory(self):
        """Each selected memory gets minimum viable tokens."""
        allocator = WeightedAllocator(
            max_tokens=1000,
            min_tokens_per_memory=50,
        )

        memories = [{"id": f"mem-{i}", "content": "test", "relevance": 0.8} for i in range(5)]

        allocations = allocator.allocate(memories)

        # Each memory should get at least minimum
        for tokens in allocations.values():
            assert tokens >= 50

    def test_allocate_excludes_low_relevance(self):
        """Memories below threshold excluded from allocation."""
        allocator = WeightedAllocator(
            max_tokens=1000,
            min_relevance=0.7,
        )

        memories = [
            {"id": "mem-1", "content": "High", "relevance": 0.9},
            {"id": "mem-2", "content": "Low", "relevance": 0.5},
        ]

        allocations = allocator.allocate(memories)

        # Only high-relevance memory allocated
        assert "mem-1" in allocations
        assert "mem-2" not in allocations


class TestBudgetEnforcement:
    """Test strict budget enforcement during retrieval."""

    def test_retrieve_respects_budget(self):
        """Retrieval pipeline respects token budget."""
        budget = TokenBudget(max_tokens=500)

        # Create memories with known token counts
        memories = [
            MemoryEntry(
                id="mem-1",
                content="x" * 300,  # ~230 tokens
                relevance=0.9,
            ),
            MemoryEntry(
                id="mem-2",
                content="x" * 300,  # ~230 tokens
                relevance=0.8,
            ),
            MemoryEntry(
                id="mem-3",
                content="x" * 300,  # ~230 tokens
                relevance=0.7,
            ),
        ]

        # Can only fit 2 memories in budget
        selected = budget.select_within_budget(memories)

        total_tokens = sum(TokenCounter.count(mem.content) for mem in selected)
        assert total_tokens <= 500
        assert len(selected) <= 2

    def test_retrieve_empty_when_budget_zero(self):
        """Zero budget returns no memories."""
        budget = TokenBudget(max_tokens=0)

        memories = [
            MemoryEntry(id="mem-1", content="test", relevance=0.9),
        ]

        selected = budget.select_within_budget(memories)
        assert len(selected) == 0

    def test_retrieve_budget_error_on_negative(self):
        """Negative budget raises error."""
        with pytest.raises(ValueError, match="positive"):
            TokenBudget(max_tokens=-100)


class TestBudgetByMemoryType:
    """Test budget allocation across memory types."""

    def test_allocate_by_memory_type(self):
        """Allocate budget weighted by memory type priority."""
        budget = TokenBudget(max_tokens=1000)

        # Procedural and semantic get higher allocation
        type_weights = {
            MemoryType.PROCEDURAL: 0.3,  # 300 tokens
            MemoryType.SEMANTIC: 0.3,  # 300 tokens
            MemoryType.EPISODIC: 0.2,  # 200 tokens
            MemoryType.PROSPECTIVE: 0.1,  # 100 tokens
            MemoryType.WORKING: 0.1,  # 100 tokens
        }

        allocations = budget.allocate_by_type(type_weights)

        assert allocations[MemoryType.PROCEDURAL] == 300
        assert allocations[MemoryType.SEMANTIC] == 300
        assert allocations[MemoryType.EPISODIC] == 200
        assert sum(allocations.values()) == 1000

    def test_unused_type_budget_redistributed(self):
        """Unused budget from one type can be redistributed."""
        budget = TokenBudget(max_tokens=1000)

        # Episodic gets 500, Semantic gets 500
        budget.allocate_by_type(
            {
                MemoryType.EPISODIC: 0.5,
                MemoryType.SEMANTIC: 0.5,
            }
        )

        # Only use 200 of episodic budget
        budget.allocate(200, "episodic-1", MemoryType.EPISODIC)

        # Remaining episodic budget (300) can be redistributed
        redistributed = budget.get_redistributable()
        assert redistributed >= 300


class TestBudgetTracking:
    """Test budget tracking and reporting."""

    def test_budget_tracks_per_memory_type(self):
        """Track token usage per memory type."""
        budget = TokenBudget(max_tokens=1000)

        budget.allocate(300, "episodic-1", MemoryType.EPISODIC)
        budget.allocate(200, "semantic-1", MemoryType.SEMANTIC)

        usage = budget.get_usage_by_type()
        assert usage[MemoryType.EPISODIC] == 300
        assert usage[MemoryType.SEMANTIC] == 200

    def test_budget_reports_utilization(self):
        """Report budget utilization percentage."""
        budget = TokenBudget(max_tokens=1000)

        budget.allocate(750, "memory-1")

        assert budget.utilization == 0.75  # 75% utilized

    def test_budget_warns_near_limit(self):
        """Warn when approaching budget limit."""
        budget = TokenBudget(max_tokens=1000, warn_threshold=0.9)

        budget.allocate(850, "memory-1")

        # Should trigger warning at 85% (below 90% threshold)
        assert budget.should_warn()

        warnings = budget.get_warnings()
        assert len(warnings) > 0
        assert "90%" in warnings[0] or "approaching" in warnings[0].lower()
