"""
Unit tests for Semantic Search and Relevance Scoring.

All tests are written to FAIL initially (TDD approach).
"""

from datetime import datetime, timedelta

from amplihack_memory import Experience, ExperienceType
from amplihack_memory.semantic_search import (
    SemanticSearchEngine,
    TFIDFSimilarity,
    calculate_relevance,
    retrieve_relevant_experiences,
)


class TestCalculateRelevance:
    """Test relevance calculation function."""

    def test_calculates_base_similarity(self):
        """calculate_relevance() uses text similarity as base score."""
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Python documentation quality check",
            outcome="Found issues",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        # Highly similar context
        relevance1 = calculate_relevance(exp, "Python documentation analysis")
        # Less similar context
        relevance2 = calculate_relevance(exp, "JavaScript code review")

        assert relevance1 > relevance2
        assert 0.0 <= relevance1 <= 1.0
        assert 0.0 <= relevance2 <= 1.0

    def test_weights_pattern_type_higher(self):
        """calculate_relevance() weights PATTERN experiences higher."""
        context_text = "SQL injection vulnerability"

        pattern_exp = Experience(
            experience_type=ExperienceType.PATTERN,
            context=context_text,
            outcome="Pattern found",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        success_exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context=context_text,
            outcome="Fixed vulnerability",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        query = "SQL injection detection"

        pattern_relevance = calculate_relevance(pattern_exp, query)
        success_relevance = calculate_relevance(success_exp, query)

        # Pattern should be weighted higher (1.5x)
        assert pattern_relevance > success_relevance

    def test_weights_insight_type_higher(self):
        """calculate_relevance() weights INSIGHT experiences higher."""
        context_text = "Refactoring improves maintainability"

        insight_exp = Experience(
            experience_type=ExperienceType.INSIGHT,
            context=context_text,
            outcome="High-level principle",
            confidence=0.9,
            timestamp=datetime.now(),
        )

        success_exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context=context_text,
            outcome="Refactored module",
            confidence=0.9,
            timestamp=datetime.now(),
        )

        query = "refactoring best practices"

        insight_relevance = calculate_relevance(insight_exp, query)
        success_relevance = calculate_relevance(success_exp, query)

        # Insight should be weighted higher (1.3x)
        assert insight_relevance > success_relevance

    def test_boosts_by_confidence(self):
        """calculate_relevance() boosts score by confidence level."""
        context_text = "Missing test coverage"

        high_conf = Experience(
            experience_type=ExperienceType.PATTERN,
            context=context_text,
            outcome="Result",
            confidence=0.95,
            timestamp=datetime.now(),
        )

        low_conf = Experience(
            experience_type=ExperienceType.PATTERN,
            context=context_text,
            outcome="Result",
            confidence=0.6,
            timestamp=datetime.now(),
        )

        query = "test coverage issues"

        high_relevance = calculate_relevance(high_conf, query)
        low_relevance = calculate_relevance(low_conf, query)

        assert high_relevance > low_relevance

    def test_boosts_recent_experiences(self):
        """calculate_relevance() boosts recent experiences."""
        context_text = "Performance optimization"

        recent = Experience(
            experience_type=ExperienceType.SUCCESS,
            context=context_text,
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now() - timedelta(days=5),
        )

        old = Experience(
            experience_type=ExperienceType.SUCCESS,
            context=context_text,
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now() - timedelta(days=60),
        )

        query = "performance improvements"

        recent_relevance = calculate_relevance(recent, query)
        old_relevance = calculate_relevance(old, query)

        # Recent should be more relevant
        assert recent_relevance > old_relevance

    def test_applies_recency_decay_over_90_days(self):
        """calculate_relevance() applies recency decay over 90 days."""
        context_text = "Code quality check"

        # Experience from different ages
        ages_days = [0, 30, 60, 90]
        relevances = []

        for days_ago in ages_days:
            exp = Experience(
                experience_type=ExperienceType.SUCCESS,
                context=context_text,
                outcome="Result",
                confidence=0.8,
                timestamp=datetime.now() - timedelta(days=days_ago),
            )
            relevances.append(calculate_relevance(exp, "code quality"))

        # Should decay over time
        assert relevances[0] > relevances[1] > relevances[2] > relevances[3]

    def test_caps_relevance_at_1_0(self):
        """calculate_relevance() caps maximum relevance at 1.0."""
        # Perfect match, pattern, high confidence, recent
        exp = Experience(
            experience_type=ExperienceType.PATTERN,
            context="Exact matching query text",
            outcome="Result",
            confidence=0.99,
            timestamp=datetime.now(),
        )

        relevance = calculate_relevance(exp, "Exact matching query text")

        assert relevance <= 1.0


class TestTFIDFSimilarity:
    """Test TF-IDF similarity calculator."""

    def test_calculates_similarity_between_texts(self):
        """TFIDFSimilarity calculates similarity between two texts."""
        sim = TFIDFSimilarity()

        text1 = "Python documentation quality analysis"
        text2 = "Python documentation review"
        text3 = "JavaScript code optimization"

        # Similar texts should have high similarity
        sim_12 = sim.calculate(text1, text2)
        # Different texts should have low similarity
        sim_13 = sim.calculate(text1, text3)

        assert sim_12 > sim_13
        assert 0.0 <= sim_12 <= 1.0
        assert 0.0 <= sim_13 <= 1.0

    def test_identical_texts_have_similarity_1_0(self):
        """TFIDFSimilarity returns 1.0 for identical texts."""
        sim = TFIDFSimilarity()

        text = "This is a test document"
        similarity = sim.calculate(text, text)

        assert similarity == 1.0

    def test_completely_different_texts_have_low_similarity(self):
        """TFIDFSimilarity returns low score for unrelated texts."""
        sim = TFIDFSimilarity()

        text1 = "documentation quality analysis tutorial"
        text2 = "database query optimization performance"

        similarity = sim.calculate(text1, text2)

        # No common meaningful words
        assert similarity < 0.3

    def test_handles_empty_texts(self):
        """TFIDFSimilarity handles empty texts gracefully."""
        sim = TFIDFSimilarity()

        similarity = sim.calculate("", "test text")
        assert similarity == 0.0

        similarity = sim.calculate("test text", "")
        assert similarity == 0.0

    def test_is_case_insensitive(self):
        """TFIDFSimilarity is case-insensitive."""
        sim = TFIDFSimilarity()

        text1 = "Python Documentation"
        text2 = "python documentation"

        similarity = sim.calculate(text1, text2)
        assert similarity > 0.9  # Should be very similar despite case


class TestRetrieveRelevantExperiences:
    """Test relevant experience retrieval function."""

    def test_retrieves_most_relevant_experiences(self):
        """retrieve_relevant_experiences() returns most relevant matches."""
        experiences = [
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Python documentation quality check",
                outcome="Found 5 issues",
                confidence=0.9,
                timestamp=datetime.now(),
            ),
            Experience(
                experience_type=ExperienceType.PATTERN,
                context="Missing examples in Python tutorials",
                outcome="Pattern recognized",
                confidence=0.95,
                timestamp=datetime.now(),
            ),
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="JavaScript code review completed",
                outcome="No issues found",
                confidence=0.8,
                timestamp=datetime.now(),
            ),
        ]

        query = "Python documentation analysis"

        relevant = retrieve_relevant_experiences(
            experiences=experiences, current_context=query, top_k=2
        )

        # Should return top 2 most relevant (both Python-related)
        assert len(relevant) == 2
        assert all("Python" in exp.context for exp in relevant)

    def test_filters_by_min_similarity_threshold(self):
        """retrieve_relevant_experiences() filters by minimum similarity."""
        experiences = [
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Highly relevant context matching query",
                outcome="Result",
                confidence=0.9,
                timestamp=datetime.now(),
            ),
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Completely unrelated different topic",
                outcome="Result",
                confidence=0.9,
                timestamp=datetime.now(),
            ),
        ]

        query = "relevant context query"

        relevant = retrieve_relevant_experiences(
            experiences=experiences, current_context=query, top_k=10, min_similarity=0.5
        )

        # Should only return the relevant one
        assert len(relevant) == 1
        assert "relevant" in relevant[0].context.lower()

    def test_returns_empty_when_no_matches(self):
        """retrieve_relevant_experiences() returns empty list when no matches."""
        experiences = [
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Topic A discussion",
                outcome="Result",
                confidence=0.9,
                timestamp=datetime.now(),
            )
        ]

        query = "Completely unrelated topic B"

        relevant = retrieve_relevant_experiences(
            experiences=experiences, current_context=query, top_k=10, min_similarity=0.7
        )

        assert len(relevant) == 0

    def test_respects_top_k_limit(self):
        """retrieve_relevant_experiences() respects top_k limit."""
        # Create 20 similar experiences
        experiences = [
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context=f"Documentation quality check {i}",
                outcome="Result",
                confidence=0.8,
                timestamp=datetime.now(),
            )
            for i in range(20)
        ]

        query = "Documentation quality"

        relevant = retrieve_relevant_experiences(
            experiences=experiences, current_context=query, top_k=5
        )

        # Should only return top 5
        assert len(relevant) == 5

    def test_orders_by_relevance_score(self):
        """retrieve_relevant_experiences() orders results by relevance."""
        experiences = [
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Partial match with query",
                outcome="Result",
                confidence=0.7,
                timestamp=datetime.now() - timedelta(days=30),
            ),
            Experience(
                experience_type=ExperienceType.PATTERN,
                context="Perfect match with query terms",
                outcome="Result",
                confidence=0.95,
                timestamp=datetime.now(),
            ),
            Experience(
                experience_type=ExperienceType.FAILURE,
                context="Another partial match",
                outcome="Result",
                confidence=0.6,
                timestamp=datetime.now() - timedelta(days=60),
            ),
        ]

        query = "match with query"

        relevant = retrieve_relevant_experiences(
            experiences=experiences, current_context=query, top_k=3
        )

        # Best match should be first (pattern, high confidence, recent, perfect match)
        assert "Perfect match" in relevant[0].context


class TestSemanticSearchEngine:
    """Test SemanticSearchEngine class."""

    def test_initializes_with_experiences(self):
        """SemanticSearchEngine initializes with experience corpus."""
        experiences = [
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Test experience",
                outcome="Result",
                confidence=0.8,
                timestamp=datetime.now(),
            )
        ]

        engine = SemanticSearchEngine(experiences)
        assert engine.corpus_size == 1

    def test_builds_search_index(self):
        """SemanticSearchEngine builds search index on initialization."""
        experiences = [
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context=f"Document {i}",
                outcome="Result",
                confidence=0.8,
                timestamp=datetime.now(),
            )
            for i in range(10)
        ]

        engine = SemanticSearchEngine(experiences)

        # Index should be built
        assert engine.is_indexed()
        assert engine.corpus_size == 10

    def test_performs_fast_similarity_search(self):
        """SemanticSearchEngine performs fast similarity search."""
        import time

        # Create large corpus
        experiences = [
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context=f"Document about topic {i % 20}",
                outcome="Result",
                confidence=0.8,
                timestamp=datetime.now(),
            )
            for i in range(1000)
        ]

        engine = SemanticSearchEngine(experiences)

        query = "Document about topic 5"

        start = time.time()
        results = engine.search(query, top_k=10)
        elapsed_ms = (time.time() - start) * 1000

        # Should complete in < 50ms (performance requirement)
        assert elapsed_ms < 50
        assert len(results) == 10

    def test_updates_index_with_new_experiences(self):
        """SemanticSearchEngine can update index with new experiences."""
        initial_experiences = [
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Initial document",
                outcome="Result",
                confidence=0.8,
                timestamp=datetime.now(),
            )
        ]

        engine = SemanticSearchEngine(initial_experiences)
        assert engine.corpus_size == 1

        # Add new experience
        new_exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="New document",
            outcome="Result",
            confidence=0.9,
            timestamp=datetime.now(),
        )

        engine.add_experience(new_exp)
        assert engine.corpus_size == 2

        # Should be searchable
        results = engine.search("New document", top_k=1)
        assert len(results) == 1
        assert "New document" in results[0].context

    def test_removes_experiences_from_index(self):
        """SemanticSearchEngine can remove experiences from index."""
        experiences = [
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context=f"Document {i}",
                outcome="Result",
                confidence=0.8,
                timestamp=datetime.now(),
            )
            for i in range(5)
        ]

        engine = SemanticSearchEngine(experiences)
        exp_to_remove = experiences[2]

        engine.remove_experience(exp_to_remove.experience_id)
        assert engine.corpus_size == 4

        # Should not appear in search results
        results = engine.search("Document 2", top_k=5)
        assert not any(exp.experience_id == exp_to_remove.experience_id for exp in results)
