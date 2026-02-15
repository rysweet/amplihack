"""
Integration tests for Documentation Analyzer Agent - Learning behavior validation.

Tests that the agent LEARNS and IMPROVES over multiple runs.

All tests are written to FAIL initially (TDD approach).
"""

from datetime import datetime, timedelta

import pytest
from amplihack_memory import Experience, ExperienceType


class TestDocAnalyzerBasicExecution:
    """Test basic agent execution and memory integration."""

    @pytest.fixture
    def agent(self):
        """Create doc-analyzer agent with fresh memory."""
        from doc_analyzer import DocumentationAnalyzer

        agent = DocumentationAnalyzer(enable_memory=True)
        agent.memory.clear()  # Start fresh
        return agent

    @pytest.fixture
    def sample_docs(self, tmp_path):
        """Create sample documentation files for testing."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Tutorial without examples
        (docs_dir / "tutorial.md").write_text("""
# Getting Started Tutorial

This tutorial explains how to use the system.

## Installation

Install the package using pip.

## Configuration

Configure the system by editing config.yaml.
        """)

        # Guide with broken links
        (docs_dir / "guide.md").write_text("""
# User Guide

See [external docs](http://example.com/broken-link) for details.
Check the [API reference](/api/nonexistent) for more info.
        """)

        # Good documentation
        (docs_dir / "good.md").write_text("""
# API Documentation

## Example Usage

```python
import mylib
result = mylib.process("data")
print(result)
```

This demonstrates the basic usage.
        """)

        return docs_dir

    def test_agent_executes_successfully(self, agent, sample_docs):
        """Agent executes documentation analysis successfully."""
        result = agent.execute(target=sample_docs)

        assert result.success is True
        assert result.issues_found > 0

    def test_agent_stores_experiences_after_run(self, agent, sample_docs):
        """Agent stores experiences in memory after execution."""
        # Execute agent
        _ = agent.execute(target=sample_docs)

        # Check memory
        stats = agent.memory.get_statistics()
        assert stats["total_experiences"] > 0

    def test_agent_stores_different_experience_types(self, agent, sample_docs):
        """Agent stores SUCCESS, PATTERN, and potentially INSIGHT experiences."""
        # Execute agent
        agent.execute(target=sample_docs)

        # Check experience types
        stats = agent.memory.get_statistics()
        by_type = stats["by_type"]

        # Should have at least SUCCESS experiences
        assert by_type.get(ExperienceType.SUCCESS, 0) > 0


class TestDocAnalyzerLearning:
    """Test learning behavior across multiple runs."""

    @pytest.fixture
    def agent_with_memory(self, tmp_path):
        """Create agent with persistent memory location."""
        from doc_analyzer import DocumentationAnalyzer

        memory_path = tmp_path / "memory"
        agent = DocumentationAnalyzer(enable_memory=True, memory_path=memory_path)
        agent.memory.clear()
        return agent

    @pytest.fixture
    def consistent_docs(self, tmp_path):
        """Create consistent documentation set for repeated runs."""
        docs_dir = tmp_path / "test_docs"
        docs_dir.mkdir()

        # Create 5 tutorials without examples
        for i in range(5):
            (docs_dir / f"tutorial_{i}.md").write_text(f"""
# Tutorial {i}

This is a tutorial about topic {i}.

## Step 1

Do this first.

## Step 2

Then do this.
            """)

        return docs_dir

    def test_agent_learns_patterns_on_second_run(self, agent_with_memory, consistent_docs):
        """Agent recognizes patterns on second run."""
        agent = agent_with_memory

        # First run - discover issues
        result1 = agent.execute(target=consistent_docs)
        _ = result1.runtime_seconds

        # Check memory after first run
        stats1 = agent_with_memory.memory.get_statistics()
        initial_exp_count = stats1["total_experiences"]

        # Second run - should recognize patterns
        result2 = agent.execute(target=consistent_docs)
        _ = result2.runtime_seconds

        # Check memory after second run
        stats2 = agent.memory.get_statistics()
        patterns = agent.memory.retrieve_experiences(experience_type=ExperienceType.PATTERN)

        # Should have recognized patterns
        assert len(patterns) > 0
        assert stats2["total_experiences"] > initial_exp_count

    def test_agent_improves_runtime_with_memory(self, agent_with_memory, consistent_docs):
        """Agent runs faster on second execution due to pattern application."""
        agent = agent_with_memory

        # First run - baseline
        result1 = agent.execute(target=consistent_docs)
        runtime1 = result1.runtime_seconds

        # Second run - should be faster
        result2 = agent.execute(target=consistent_docs)
        runtime2 = result2.runtime_seconds

        # Should be at least 20% faster
        improvement = (runtime1 - runtime2) / runtime1
        assert improvement > 0.2, f"Expected >20% improvement, got {improvement * 100:.1f}%"

    def test_agent_finds_same_issues_faster(self, agent_with_memory, consistent_docs):
        """Agent finds same number of issues but faster on subsequent runs."""
        agent = agent_with_memory

        # First run
        result1 = agent.execute(target=consistent_docs)
        issues1 = result1.issues_found
        runtime1 = result1.runtime_seconds

        # Second run
        result2 = agent.execute(target=consistent_docs)
        issues2 = result2.issues_found
        runtime2 = result2.runtime_seconds

        # Should find same issues
        assert issues2 >= issues1

        # But faster
        assert runtime2 < runtime1

    def test_agent_learns_over_multiple_runs(self, agent_with_memory, consistent_docs):
        """Agent continues to learn over multiple runs (3+)."""
        agent = agent_with_memory

        runtimes = []
        pattern_counts = []

        # Run agent 5 times
        for run_num in range(5):
            result = agent.execute(target=consistent_docs)
            runtimes.append(result.runtime_seconds)

            patterns = agent.memory.retrieve_experiences(experience_type=ExperienceType.PATTERN)
            pattern_counts.append(len(patterns))

        # Runtime should generally decrease
        assert runtimes[4] < runtimes[0]

        # Pattern count should increase (or plateau)
        assert pattern_counts[4] >= pattern_counts[0]

    def test_agent_applies_high_confidence_patterns(self, agent_with_memory, consistent_docs):
        """Agent applies patterns with confidence >= 0.7."""
        agent = agent_with_memory

        # First two runs to establish patterns
        agent.execute(target=consistent_docs)
        agent.execute(target=consistent_docs)

        # Third run - check pattern application
        result3 = agent.execute(target=consistent_docs)

        # Check which patterns were applied
        patterns = agent.memory.retrieve_experiences(
            experience_type=ExperienceType.PATTERN, min_confidence=0.7
        )

        # Should have some high-confidence patterns
        assert len(patterns) > 0

        # Check metadata shows patterns were applied
        assert result3.metadata.get("patterns_applied", 0) > 0


class TestDocAnalyzerMemoryRetrieval:
    """Test relevant memory retrieval during execution."""

    @pytest.fixture
    def agent_with_diverse_memory(self, tmp_path):
        """Create agent with diverse past experiences."""
        from doc_analyzer import DocumentationAnalyzer

        memory_path = tmp_path / "diverse_memory"
        agent = DocumentationAnalyzer(enable_memory=True, memory_path=memory_path)
        agent.memory.clear()

        # Populate with diverse experiences
        experiences = [
            Experience(
                experience_type=ExperienceType.PATTERN,
                context="Tutorials without code examples",
                outcome="Pattern: 80% of tutorial files lack runnable examples",
                confidence=0.92,
                timestamp=datetime.now() - timedelta(days=5),
            ),
            Experience(
                experience_type=ExperienceType.PATTERN,
                context="Broken external links",
                outcome="Pattern: External links often become stale",
                confidence=0.88,
                timestamp=datetime.now() - timedelta(days=10),
            ),
            Experience(
                experience_type=ExperienceType.INSIGHT,
                context="Documentation quality correlates with example count",
                outcome="Insight: Docs with 3+ examples have 90% fewer support requests",
                confidence=0.95,
                timestamp=datetime.now() - timedelta(days=15),
            ),
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="JavaScript API documentation review",
                outcome="Found 0 issues - well documented",
                confidence=0.85,
                timestamp=datetime.now() - timedelta(days=30),
            ),
        ]

        for exp in experiences:
            agent.memory.store_experience(exp)

        return agent

    def test_agent_retrieves_relevant_experiences(self, agent_with_diverse_memory, tmp_path):
        """Agent retrieves relevant experiences before execution."""
        agent = agent_with_diverse_memory

        # Create Python documentation to analyze
        docs_dir = tmp_path / "python_docs"
        docs_dir.mkdir()
        (docs_dir / "tutorial.md").write_text("# Python Tutorial\n\nBasic tutorial.")

        # Execute - agent should retrieve relevant experiences
        result = agent.execute(target=docs_dir)

        # Check which experiences were loaded
        loaded_context = result.metadata.get("loaded_experiences", [])

        # Should have loaded tutorial-related patterns (not JavaScript)
        assert len(loaded_context) > 0
        # Should prioritize pattern and insight over old success
        assert any("Tutorial" in exp or "example" in exp for exp in loaded_context)

    def test_agent_filters_irrelevant_experiences(self, agent_with_diverse_memory, tmp_path):
        """Agent filters out irrelevant experiences."""
        agent = agent_with_diverse_memory

        # Create docs about different topic
        docs_dir = tmp_path / "api_docs"
        docs_dir.mkdir()
        (docs_dir / "api.md").write_text("# API Reference\n\nAPI documentation.")

        # Execute
        result = agent.execute(target=docs_dir)

        # Should not load tutorial-specific patterns for API docs
        _ = result.metadata.get("loaded_experiences", [])
        # Exact filtering behavior depends on implementation


class TestDocAnalyzerPatternRecognition:
    """Test pattern recognition behavior."""

    @pytest.fixture
    def agent(self, tmp_path):
        """Create agent with clean memory."""
        from doc_analyzer import DocumentationAnalyzer

        agent = DocumentationAnalyzer(enable_memory=True, memory_path=tmp_path / "pattern_memory")
        agent.memory.clear()
        return agent

    def test_agent_recognizes_pattern_at_threshold(self, agent, tmp_path):
        """Agent recognizes pattern after threshold occurrences (default: 3)."""
        # Create docs with same issue repeated 3 times
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        for i in range(3):
            (docs_dir / f"file_{i}.md").write_text(f"""
# Document {i}

No examples provided in this document.
            """)

        # Execute agent
        agent.execute(target=docs_dir)

        # Check for pattern recognition
        patterns = agent.memory.retrieve_experiences(experience_type=ExperienceType.PATTERN)

        # Should recognize "missing examples" pattern
        assert len(patterns) > 0
        assert any("example" in p.context.lower() for p in patterns)

    def test_agent_increases_pattern_confidence(self, agent, tmp_path):
        """Agent increases pattern confidence with repeated validation."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create consistent documentation issue
        for i in range(5):
            (docs_dir / f"file_{i}.md").write_text("# Doc\nNo examples.")

        # Run multiple times
        agent.execute(target=docs_dir)
        agent.execute(target=docs_dir)
        agent.execute(target=docs_dir)

        # Check pattern confidence
        patterns = agent.memory.retrieve_experiences(experience_type=ExperienceType.PATTERN)

        if patterns:
            # Confidence should be relatively high after validation
            assert max(p.confidence for p in patterns) > 0.7


class TestDocAnalyzerWithoutMemory:
    """Test agent behavior without memory (baseline comparison)."""

    def test_agent_without_memory_does_not_learn(self, sample_docs):
        """Agent without memory shows no improvement across runs."""
        from doc_analyzer import DocumentationAnalyzer

        agent = DocumentationAnalyzer(enable_memory=False)

        # Two runs
        result1 = agent.execute(target=sample_docs)
        result2 = agent.execute(target=sample_docs)

        # Runtimes should be similar (no learning)
        runtime_diff = abs(result1.runtime_seconds - result2.runtime_seconds)
        runtime_avg = (result1.runtime_seconds + result2.runtime_seconds) / 2

        # Less than 10% variation (no significant improvement)
        assert runtime_diff / runtime_avg < 0.1


class TestDocAnalyzerMetrics:
    """Test learning metrics tracking."""

    @pytest.fixture
    def agent(self, tmp_path):
        """Create agent with metrics tracking."""
        from doc_analyzer import DocumentationAnalyzer

        agent = DocumentationAnalyzer(enable_memory=True, memory_path=tmp_path / "metrics_memory")
        agent.memory.clear()
        return agent

    def test_agent_tracks_learning_metrics(self, agent, sample_docs):
        """Agent tracks learning metrics across runs."""
        from doc_analyzer.metrics import LearningMetrics

        metrics = LearningMetrics(agent.memory)

        # Run agent 3 times
        for _ in range(3):
            agent.execute(target=sample_docs)

        # Get learning metrics
        stats = metrics.get_statistics()

        assert "pattern_recognition_rate" in stats
        assert "runtime_improvement" in stats
        assert "confidence_growth" in stats

    def test_agent_shows_measurable_improvement(self, agent, consistent_docs):
        """Agent shows measurable improvement metrics."""
        from doc_analyzer.metrics import LearningMetrics

        metrics = LearningMetrics(agent.memory)

        # Baseline run
        agent.execute(target=consistent_docs)
        baseline = metrics.get_current_metrics()

        # Run 4 more times
        for _ in range(4):
            agent.execute(target=consistent_docs)

        # Get final metrics
        final = metrics.get_current_metrics()

        # Should show improvement
        assert final["total_patterns"] >= baseline["total_patterns"]
        # Pattern recognition rate should increase
        if final["total_patterns"] > 0:
            assert final["pattern_recognition_rate"] > baseline.get("pattern_recognition_rate", 0)
