"""
Unit tests for ExperienceStore - Store/retrieve experiences with auto-management.

All tests are written to FAIL initially (TDD approach).
"""

from datetime import datetime, timedelta

import pytest
from amplihack_memory import Experience, ExperienceStore, ExperienceType


class TestExperienceStoreInitialization:
    """Test ExperienceStore initialization and configuration."""

    def test_creates_store_with_agent_name(self, isolated_storage):
        """ExperienceStore initializes with agent name."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)
        assert store.agent_name == "test-agent"

    def test_enables_auto_compress_by_default(self, isolated_storage):
        """ExperienceStore enables auto-compression by default."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)
        assert store.auto_compress is True

    def test_can_disable_auto_compress(self, isolated_storage):
        """ExperienceStore can disable auto-compression."""
        store = ExperienceStore(
            agent_name="test-agent", auto_compress=False, storage_path=isolated_storage
        )
        assert store.auto_compress is False

    def test_accepts_max_age_days_limit(self, isolated_storage):
        """ExperienceStore accepts max_age_days retention policy."""
        store = ExperienceStore(
            agent_name="test-agent", max_age_days=90, storage_path=isolated_storage
        )
        assert store.max_age_days == 90

    def test_accepts_max_experiences_limit(self, isolated_storage):
        """ExperienceStore accepts max_experiences retention policy."""
        store = ExperienceStore(
            agent_name="test-agent", max_experiences=1000, storage_path=isolated_storage
        )
        assert store.max_experiences == 1000

    def test_no_retention_limits_by_default(self, isolated_storage):
        """ExperienceStore has no retention limits by default."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)
        assert store.max_age_days is None
        assert store.max_experiences is None


class TestExperienceStoreAddOperation:
    """Test experience addition with automatic management."""

    def test_adds_single_experience(self, isolated_storage):
        """ExperienceStore.add() stores a single experience."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)

        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test context",
            outcome="Test outcome",
            confidence=0.85,
            timestamp=datetime.now(),
        )

        exp_id = store.add(exp)
        assert exp_id is not None
        assert exp_id.startswith("exp_")

    def test_returns_unique_experience_ids(self, isolated_storage):
        """ExperienceStore.add() returns unique IDs for each experience."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)

        exp1 = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="First",
            outcome="Result 1",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        exp2 = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Second",
            outcome="Result 2",
            confidence=0.9,
            timestamp=datetime.now(),
        )

        id1 = store.add(exp1)
        id2 = store.add(exp2)

        assert id1 != id2

    def test_automatically_compresses_old_experiences(self, isolated_storage):
        """ExperienceStore automatically compresses experiences older than 30 days."""
        store = ExperienceStore(
            agent_name="test-agent", auto_compress=True, storage_path=isolated_storage
        )

        # Add old experience (31 days ago)
        old_exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Old experience " * 30,  # Large context (under 500 chars)
            outcome="Old result " * 30,
            confidence=0.8,
            timestamp=datetime.now() - timedelta(days=31),
        )
        store.add(old_exp)

        # Add recent experience
        new_exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="New experience",
            outcome="New result",
            confidence=0.9,
            timestamp=datetime.now(),
        )
        store.add(new_exp)

        # Check storage - old experience should be compressed
        stats = store.get_statistics()
        assert stats["compressed_experiences"] == 1

    def test_enforces_max_age_days_limit(self, isolated_storage):
        """ExperienceStore deletes experiences older than max_age_days."""
        store = ExperienceStore(
            agent_name="test-agent", max_age_days=30, storage_path=isolated_storage
        )

        # Add experience older than limit
        old_exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Too old",
            outcome="Should be deleted",
            confidence=0.8,
            timestamp=datetime.now() - timedelta(days=31),
        )
        store.add(old_exp)

        # Add experience within limit
        new_exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Recent",
            outcome="Should remain",
            confidence=0.9,
            timestamp=datetime.now(),
        )
        store.add(new_exp)

        # Trigger cleanup
        store._cleanup()

        # Only recent experience should remain
        experiences = store.search("")
        assert len(experiences) == 1
        assert experiences[0].context == "Recent"

    def test_enforces_max_experiences_limit(self, isolated_storage):
        """ExperienceStore deletes oldest experiences when max_experiences exceeded."""
        store = ExperienceStore(
            agent_name="test-agent", max_experiences=10, storage_path=isolated_storage
        )

        # Add 15 experiences
        for i in range(15):
            exp = Experience(
                experience_type=ExperienceType.SUCCESS,
                context=f"Experience {i}",
                outcome="Result",
                confidence=0.8,
                timestamp=datetime.now() - timedelta(hours=15 - i),
            )
            store.add(exp)

        # Trigger cleanup
        store._cleanup()

        # Should only keep 10 most recent experiences
        experiences = store.search("")
        assert len(experiences) == 10

        # Should have kept the most recent ones (5-14)
        contexts = {exp.context for exp in experiences}
        for i in range(5, 15):
            assert f"Experience {i}" in contexts

    def test_detects_duplicate_experiences(self, isolated_storage):
        """ExperienceStore detects and handles duplicate experiences."""
        import time

        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)

        # Create two experiences with same content but different timestamps
        exp1 = Experience(
            experience_type=ExperienceType.PATTERN,
            context="Duplicate pattern",
            outcome="Same outcome",
            confidence=0.85,
            timestamp=datetime.now(),
        )

        # Wait a tiny bit to ensure different timestamp
        time.sleep(0.01)

        exp2 = Experience(
            experience_type=ExperienceType.PATTERN,
            context="Duplicate pattern",
            outcome="Same outcome",
            confidence=0.85,
            timestamp=datetime.now(),
        )

        # Add both experiences
        id1 = store.add(exp1)
        id2 = store.add(exp2)

        # They should have different IDs due to different timestamps
        assert id1 != id2

        experiences = store.search("Duplicate pattern")
        # Should have stored both (they have different timestamps = different IDs)
        assert len(experiences) == 2


class TestExperienceStoreSearch:
    """Test advanced search functionality."""

    def test_searches_by_text_query(self, isolated_storage):
        """ExperienceStore.search() finds experiences by text query."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)

        # Add various experiences
        exps = [
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Documentation quality check",
                outcome="Found 5 issues",
                confidence=0.9,
                timestamp=datetime.now(),
            ),
            Experience(
                experience_type=ExperienceType.PATTERN,
                context="Missing examples in tutorials",
                outcome="Pattern occurs in 80% of files",
                confidence=0.95,
                timestamp=datetime.now(),
            ),
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Security vulnerability scan",
                outcome="No issues found",
                confidence=0.85,
                timestamp=datetime.now(),
            ),
        ]

        for exp in exps:
            store.add(exp)

        # Search for "documentation"
        results = store.search("documentation")
        assert len(results) == 1
        assert "Documentation" in results[0].context

        # Search for "tutorial"
        results = store.search("tutorial")
        assert len(results) == 1
        assert "tutorials" in results[0].context

    def test_searches_with_experience_type_filter(self, isolated_storage):
        """ExperienceStore.search() filters by experience type."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)

        # Add different types
        store.add(
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Success case",
                outcome="Worked",
                confidence=0.9,
                timestamp=datetime.now(),
            )
        )

        store.add(
            Experience(
                experience_type=ExperienceType.PATTERN,
                context="Pattern case",
                outcome="Recognized",
                confidence=0.95,
                timestamp=datetime.now(),
            )
        )

        store.add(
            Experience(
                experience_type=ExperienceType.FAILURE,
                context="Failure case",
                outcome="Failed",
                confidence=0.7,
                timestamp=datetime.now(),
            )
        )

        # Search only patterns
        patterns = store.search("case", experience_type=ExperienceType.PATTERN)
        assert len(patterns) == 1
        assert patterns[0].experience_type == ExperienceType.PATTERN

    def test_searches_with_min_confidence_filter(self, isolated_storage):
        """ExperienceStore.search() filters by minimum confidence."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)

        # Add experiences with different confidence levels
        for conf in [0.5, 0.7, 0.8, 0.9, 0.95]:
            store.add(
                Experience(
                    experience_type=ExperienceType.SUCCESS,
                    context=f"Confidence {conf}",
                    outcome="Result",
                    confidence=conf,
                    timestamp=datetime.now(),
                )
            )

        # Search with min_confidence=0.8
        results = store.search("Confidence", min_confidence=0.8)
        assert len(results) == 3  # 0.8, 0.9, 0.95

        # All results should have confidence >= 0.8
        for exp in results:
            assert exp.confidence >= 0.8

    def test_searches_with_limit(self, isolated_storage):
        """ExperienceStore.search() respects result limit."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)

        # Add 20 experiences
        for i in range(20):
            store.add(
                Experience(
                    experience_type=ExperienceType.SUCCESS,
                    context=f"Test {i}",
                    outcome="Result",
                    confidence=0.8,
                    timestamp=datetime.now(),
                )
            )

        # Search with limit=5
        results = store.search("Test", limit=5)
        assert len(results) == 5

    def test_search_returns_relevance_ordered_results(self, isolated_storage):
        """ExperienceStore.search() returns results ordered by relevance."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)

        store.add(
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Python documentation analysis",
                outcome="Perfect match",
                confidence=0.95,
                timestamp=datetime.now(),
            )
        )

        store.add(
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Python code review",
                outcome="Partial match",
                confidence=0.85,
                timestamp=datetime.now(),
            )
        )

        store.add(
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="JavaScript documentation",
                outcome="Partial match",
                confidence=0.9,
                timestamp=datetime.now(),
            )
        )

        # Search for "Python documentation"
        results = store.search("Python documentation")

        # First result should be the best match
        assert "Python documentation analysis" in results[0].context


class TestExperienceStoreStatistics:
    """Test statistics and metrics."""

    def test_returns_total_experiences_count(self, isolated_storage):
        """ExperienceStore returns total experiences count."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)

        # Add 10 experiences
        for i in range(10):
            store.add(
                Experience(
                    experience_type=ExperienceType.SUCCESS,
                    context=f"Test {i}",
                    outcome="Result",
                    confidence=0.8,
                    timestamp=datetime.now(),
                )
            )

        stats = store.get_statistics()
        assert stats["total_experiences"] == 10

    def test_returns_count_by_type(self, isolated_storage):
        """ExperienceStore returns count by experience type."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)

        # Add different types
        types = [
            ExperienceType.SUCCESS,
            ExperienceType.SUCCESS,
            ExperienceType.FAILURE,
            ExperienceType.PATTERN,
            ExperienceType.PATTERN,
            ExperienceType.PATTERN,
            ExperienceType.INSIGHT,
        ]

        for exp_type in types:
            store.add(
                Experience(
                    experience_type=exp_type,
                    context="Test",
                    outcome="Result",
                    confidence=0.8,
                    timestamp=datetime.now(),
                )
            )

        stats = store.get_statistics()
        assert stats["by_type"][ExperienceType.SUCCESS] == 2
        assert stats["by_type"][ExperienceType.FAILURE] == 1
        assert stats["by_type"][ExperienceType.PATTERN] == 3
        assert stats["by_type"][ExperienceType.INSIGHT] == 1

    def test_returns_storage_size(self, isolated_storage):
        """ExperienceStore returns storage size in KB."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)

        # Add experience with known size
        store.add(
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="A" * 400,  # 400 chars context (under 500 limit)
                outcome="B" * 400,  # 400 chars outcome
                confidence=0.8,
                timestamp=datetime.now(),
            )
        )

        stats = store.get_statistics()
        assert stats["storage_size_kb"] > 0

    def test_returns_compression_ratio(self, isolated_storage):
        """ExperienceStore returns compression ratio when compression enabled."""
        store = ExperienceStore(
            agent_name="test-agent", auto_compress=True, storage_path=isolated_storage
        )

        # Add old experience that should be compressed
        store.add(
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="X" * 400,  # Large compressible content (under 500 limit)
                outcome="Y" * 400,
                confidence=0.8,
                timestamp=datetime.now() - timedelta(days=31),
            )
        )

        # Trigger compression
        store._cleanup()

        stats = store.get_statistics()
        # Compression ratio should be > 1.0 (e.g., 3:1 = 3.0)
        assert stats.get("compression_ratio", 1.0) > 1.0


class TestExperienceStoreCleanup:
    """Test automatic cleanup behavior."""

    def test_cleanup_runs_on_add_when_needed(self, isolated_storage):
        """ExperienceStore runs cleanup automatically on add() when limits exceeded."""
        store = ExperienceStore(
            agent_name="test-agent", max_experiences=5, storage_path=isolated_storage
        )

        # Add 10 experiences
        for i in range(10):
            store.add(
                Experience(
                    experience_type=ExperienceType.SUCCESS,
                    context=f"Test {i}",
                    outcome="Result",
                    confidence=0.8,
                    timestamp=datetime.now() - timedelta(hours=10 - i),
                )
            )

        # Should have automatically cleaned up to keep only 5
        stats = store.get_statistics()
        assert stats["total_experiences"] == 5

    def test_cleanup_preserves_high_confidence_patterns(self, isolated_storage):
        """ExperienceStore preserves high-confidence patterns during cleanup."""
        store = ExperienceStore(
            agent_name="test-agent", max_experiences=5, storage_path=isolated_storage
        )

        # Add high-confidence pattern
        store.add(
            Experience(
                experience_type=ExperienceType.PATTERN,
                context="Important pattern",
                outcome="Critical insight",
                confidence=0.98,
                timestamp=datetime.now() - timedelta(days=60),  # Old but important
            )
        )

        # Add many low-confidence successes
        for i in range(10):
            store.add(
                Experience(
                    experience_type=ExperienceType.SUCCESS,
                    context=f"Regular success {i}",
                    outcome="Result",
                    confidence=0.7,
                    timestamp=datetime.now(),
                )
            )

        # High-confidence pattern should be preserved
        patterns = store.search("Important pattern")
        assert len(patterns) == 1
        assert patterns[0].confidence == 0.98

    def test_cleanup_vacuums_database(self, isolated_storage):
        """ExperienceStore vacuums database after cleanup to reclaim space."""
        store = ExperienceStore(
            agent_name="test-agent", max_age_days=7, storage_path=isolated_storage
        )

        # Add old experiences
        for i in range(100):
            store.add(
                Experience(
                    experience_type=ExperienceType.SUCCESS,
                    context=f"Old {i}",
                    outcome="Result",
                    confidence=0.8,
                    timestamp=datetime.now() - timedelta(days=30),
                )
            )

        # Add recent experience
        store.add(
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Recent",
                outcome="Result",
                confidence=0.8,
                timestamp=datetime.now(),
            )
        )

        # Run cleanup
        store._cleanup()

        # Storage size should be reduced
        stats = store.get_statistics()
        # After vacuum, storage should be much smaller
        assert stats["storage_size_kb"] < 50  # Much less than 100 experiences would take


class TestExperienceStoreErrorHandling:
    """Test error handling."""

    def test_raises_on_invalid_experience(self, isolated_storage):
        """ExperienceStore raises ValueError for invalid experiences (from Experience validation)."""
        store = ExperienceStore(agent_name="test-agent", storage_path=isolated_storage)

        # Empty context (raises ValueError in Experience.__post_init__)
        with pytest.raises(ValueError):
            store.add(
                Experience(
                    experience_type=ExperienceType.SUCCESS,
                    context="",
                    outcome="Result",
                    confidence=0.8,
                    timestamp=datetime.now(),
                )
            )

        # Empty outcome
        with pytest.raises(ValueError):
            store.add(
                Experience(
                    experience_type=ExperienceType.SUCCESS,
                    context="Context",
                    outcome="",
                    confidence=0.8,
                    timestamp=datetime.now(),
                )
            )

        # Invalid confidence (< 0)
        with pytest.raises(ValueError):
            store.add(
                Experience(
                    experience_type=ExperienceType.SUCCESS,
                    context="Context",
                    outcome="Result",
                    confidence=-0.1,
                    timestamp=datetime.now(),
                )
            )

        # Invalid confidence (> 1)
        with pytest.raises(ValueError):
            store.add(
                Experience(
                    experience_type=ExperienceType.SUCCESS,
                    context="Context",
                    outcome="Result",
                    confidence=1.5,
                    timestamp=datetime.now(),
                )
            )

    def test_handles_storage_quota_exceeded(self, isolated_storage):
        """ExperienceStore handles storage quota exceeded gracefully."""
        from amplihack_memory.exceptions import MemoryQuotaExceededError

        store = ExperienceStore(
            agent_name="test-agent",
            max_memory_mb=1,  # Very small quota
            storage_path=isolated_storage,
        )

        # Try to add many large experiences
        with pytest.raises(MemoryQuotaExceededError):
            for i in range(1000):
                store.add(
                    Experience(
                        experience_type=ExperienceType.SUCCESS,
                        context="X" * 400,  # 400 chars (under 500 limit)
                        outcome="Y" * 400,
                        confidence=0.8,
                        timestamp=datetime.now(),
                    )
                )
