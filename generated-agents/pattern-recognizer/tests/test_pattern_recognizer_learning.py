"""
Integration tests for Code Pattern Recognizer Agent - Learning behavior.

Tests that agent learns code patterns and improves refactoring suggestions.

All tests written to FAIL initially (TDD approach).
"""

import pytest
from amplihack_memory import ExperienceType


@pytest.fixture
def code_with_duplication(tmp_path):
    """Create code with obvious duplication (shared fixture)."""
    code_dir = tmp_path / "src"
    code_dir.mkdir()

    # Similar error handling in multiple files
    for i in range(4):
        (code_dir / f"module_{i}.py").write_text(f"""
def process_data_{i}(data):
    try:
        result = transform(data)
        return result
    except Exception as e:
        print(f"Error: {{e}}")
        return None
        """)

    return code_dir


@pytest.fixture
def agent_with_memory(tmp_path):
    """Create agent with persistent memory (shared fixture)."""
    from pattern_recognizer import CodePatternRecognizer

    memory_path = tmp_path / "memory"
    agent = CodePatternRecognizer(enable_memory=True, memory_path=memory_path)
    agent.clear_memory()
    return agent


class TestPatternRecognizerExecution:
    """Test basic pattern recognizer execution."""

    @pytest.fixture
    def agent(self):
        """Create pattern recognizer agent."""
        from pattern_recognizer import CodePatternRecognizer

        agent = CodePatternRecognizer(enable_memory=True)
        agent.clear_memory()
        return agent

    def test_identifies_code_duplication(self, agent, code_with_duplication):
        """Agent identifies duplicated code patterns."""
        result = agent.execute(target=code_with_duplication)

        assert result.success is True
        assert result.patterns_found > 0
        assert (
            "duplication" in str(result.issues).lower() or "similar" in str(result.issues).lower()
        )

    def test_suggests_abstractions(self, agent, code_with_duplication):
        """Agent suggests refactoring abstractions."""
        result = agent.execute(target=code_with_duplication)

        suggestions = result.refactoring_suggestions
        assert len(suggestions) > 0
        # Should suggest extracting common pattern
        assert any("decorator" in s.lower() or "function" in s.lower() for s in suggestions)


class TestPatternRecognizerLearning:
    """Test learning behavior over multiple runs."""

    def test_learns_common_duplication_patterns(self, agent_with_memory, code_with_duplication):
        """Agent learns common duplication patterns."""
        agent = agent_with_memory

        # First run - discover patterns
        result1 = agent.execute(target=code_with_duplication)

        # Second run - should recognize patterns faster
        result2 = agent.execute(target=code_with_duplication)

        # Should have stored pattern
        patterns = agent.memory.retrieve_experiences(experience_type=ExperienceType.PATTERN)
        assert len(patterns) > 0

        # Should be faster on second run
        assert result2.runtime_seconds < result1.runtime_seconds

    def test_improves_suggestion_quality(self, agent_with_memory, tmp_path):
        """Agent improves refactoring suggestion quality over time."""
        agent = agent_with_memory

        code_dir = tmp_path / "code"
        code_dir.mkdir()

        # Create code with pattern
        (code_dir / "file1.py").write_text("""
def handler_a():
    setup()
    process()
    cleanup()

def handler_b():
    setup()
    transform()
    cleanup()
        """)

        # Multiple runs to learn pattern
        suggestions_quality = []

        for run in range(3):
            result = agent.execute(target=code_dir)
            # Quality metric: specificity of suggestions
            suggestions_quality.append(len(result.refactoring_suggestions))

        # Later runs should provide more specific suggestions
        assert suggestions_quality[2] >= suggestions_quality[0]

    def test_validates_runtime_improvement(self, agent_with_memory, code_with_duplication):
        """Agent shows >30% runtime improvement."""
        agent = agent_with_memory

        # Baseline
        result1 = agent.execute(target=code_with_duplication)
        baseline_runtime = result1.runtime_seconds

        # Learn patterns (run 3 times)
        for _ in range(3):
            agent.execute(target=code_with_duplication)

        # Final run
        result_final = agent.execute(target=code_with_duplication)
        final_runtime = result_final.runtime_seconds

        # Calculate improvement
        improvement = (baseline_runtime - final_runtime) / baseline_runtime

        assert improvement > 0.3, f"Expected >30% improvement, got {improvement * 100:.1f}%"


class TestPatternRecognizerMemory:
    """Test memory retrieval and application."""

    @pytest.fixture
    def agent_with_patterns(self, tmp_path):
        """Create agent with pre-populated patterns."""
        from datetime import datetime

        from amplihack_memory import Experience
        from pattern_recognizer import CodePatternRecognizer

        memory_path = tmp_path / "patterns_memory"
        agent = CodePatternRecognizer(enable_memory=True, memory_path=memory_path)
        agent.clear_memory()

        # Add known patterns
        patterns = [
            Experience(
                experience_type=ExperienceType.PATTERN,
                context="Repeated try-except blocks with same structure",
                outcome="Suggest decorator pattern for error handling",
                confidence=0.92,
                timestamp=datetime.now(),
            ),
            Experience(
                experience_type=ExperienceType.PATTERN,
                context="Multiple functions with identical setup/cleanup",
                outcome="Suggest context manager pattern",
                confidence=0.88,
                timestamp=datetime.now(),
            ),
        ]

        for pattern in patterns:
            agent.memory.store_experience(pattern)

        return agent

    def test_retrieves_relevant_patterns(self, agent_with_patterns, tmp_path):
        """Agent retrieves relevant patterns for new code."""
        agent = agent_with_patterns

        code_dir = tmp_path / "new_code"
        code_dir.mkdir()

        # Code with error handling pattern
        (code_dir / "api.py").write_text("""
def endpoint_a():
    try:
        return process_a()
    except Exception as e:
        log_error(e)
        return None

def endpoint_b():
    try:
        return process_b()
    except Exception as e:
        log_error(e)
        return None
        """)

        result = agent.execute(target=code_dir)

        # Should have loaded relevant pattern
        loaded = result.metadata.get("loaded_experiences", [])
        assert len(loaded) > 0
        assert any("try-except" in exp.lower() or "error" in exp.lower() for exp in loaded)

    def test_stores_successful_refactoring_patterns(self, agent_with_patterns, tmp_path):
        """Agent stores patterns from successful refactorings."""
        agent = agent_with_patterns

        # Simulate successful refactoring
        code_dir = tmp_path / "refactored_code"
        code_dir.mkdir()
        (code_dir / "before.py").write_text("duplicated code")

        _ = agent.execute(target=code_dir)

        # After refactoring validation, store success
        # (This would normally happen after user applies refactoring)

        # Check for new success experiences
        successes = agent.memory.retrieve_experiences(experience_type=ExperienceType.SUCCESS)
        assert len(successes) > 0


class TestPatternRecognizerMetrics:
    """Test metrics tracking."""

    def test_tracks_pattern_recognition_accuracy(self, agent_with_memory, tmp_path):
        """Agent tracks pattern recognition accuracy."""
        from pattern_recognizer.metrics import PatternRecognitionMetrics

        agent = agent_with_memory
        metrics = PatternRecognitionMetrics(agent.memory)

        code_dir = tmp_path / "code"
        code_dir.mkdir()
        (code_dir / "file.py").write_text("code with patterns")

        # Run multiple times
        for _ in range(5):
            agent.execute(target=code_dir)

        stats = metrics.get_accuracy_stats()

        assert "true_positives" in stats
        assert "false_positives" in stats
        assert "accuracy" in stats

    def test_measures_suggestion_acceptance_rate(self, agent_with_memory):
        """Agent tracks how often suggestions are accepted."""
        from pattern_recognizer.metrics import PatternRecognitionMetrics

        metrics = PatternRecognitionMetrics(agent_with_memory.memory)

        # Simulate suggestions and acceptances
        # (Would be tracked when user applies refactoring)

        stats = metrics.get_suggestion_stats()

        assert "total_suggestions" in stats
        assert "accepted_suggestions" in stats
        assert "acceptance_rate" in stats

    def test_calculates_confidence_progression(self, agent_with_memory, code_with_duplication):
        """Agent shows confidence progression over runs."""
        from pattern_recognizer.metrics import PatternRecognitionMetrics

        agent = agent_with_memory
        _ = PatternRecognitionMetrics(agent.memory)

        confidences = []

        for run in range(5):
            agent.execute(target=code_with_duplication)

            patterns = agent.memory.retrieve_experiences(experience_type=ExperienceType.PATTERN)

            if patterns:
                avg_conf = sum(p.confidence for p in patterns) / len(patterns)
                confidences.append(avg_conf)

        # Confidence should generally increase
        if len(confidences) > 1:
            assert confidences[-1] >= confidences[0]
