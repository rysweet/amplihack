# How to Validate Agent Learning

Test that your memory-enabled agents actually learn and improve over time.

---

## Overview

Memory-enabled agents should demonstrably improve with experience. This guide shows how to write tests that validate learning behavior using gadugi-agentic-test.

---

## Why Validate Learning?

Without validation, you can't verify that:

- Experiences are being stored correctly
- Patterns are recognized across runs
- Performance actually improves
- Confidence scores increase appropriately

**Validation provides confidence** that your agent's learning system works as designed.

---

## Test Types

### 1. Storage Tests

Verify experiences are stored after execution.

```python
# agents/my-agent/tests/test_memory_storage.py

import pytest
from pathlib import Path
from ..agent import MyAgent
from amplihack_memory import ExperienceType

@pytest.fixture
def agent_with_clean_memory():
    """Create agent with empty memory."""
    agent = MyAgent(Path(__file__).parent.parent)
    if agent.has_memory():
        agent.memory.clear()
    return agent

def test_stores_success_experience_after_run(agent_with_clean_memory, tmp_path):
    """Verify agent stores at least one SUCCESS experience after execution."""

    # Execute task
    result = agent_with_clean_memory.execute_task("Test task", tmp_path)

    # Verify experiences stored
    stats = agent_with_clean_memory.memory.get_statistics()

    assert stats['total_experiences'] > 0, \
        "Agent should store at least one experience after execution"

    # Verify SUCCESS type
    successes = agent_with_clean_memory.memory.retrieve_experiences(
        experience_type=ExperienceType.SUCCESS
    )

    assert len(successes) > 0, \
        "Agent should store at least one SUCCESS experience"

def test_stores_metadata_in_experiences(agent_with_clean_memory, tmp_path):
    """Verify experiences include runtime metadata."""

    result = agent_with_clean_memory.execute_task("Test task", tmp_path)

    experiences = agent_with_clean_memory.memory.retrieve_experiences()

    assert len(experiences) > 0, "Should have experiences"

    # Check first experience has metadata
    exp = experiences[0]
    assert 'runtime_seconds' in exp.metadata, \
        "Experience should include runtime metadata"
    assert exp.metadata['runtime_seconds'] > 0, \
        "Runtime should be positive"

def test_stores_patterns_when_detected(agent_with_clean_memory, tmp_path):
    """Verify agent stores PATTERN experiences when patterns are recognized."""

    # Run multiple times to trigger pattern recognition
    for i in range(3):
        agent_with_clean_memory.execute_task(f"Test task {i}", tmp_path)

    # Check for pattern experiences
    patterns = agent_with_clean_memory.memory.retrieve_experiences(
        experience_type=ExperienceType.PATTERN
    )

    assert len(patterns) > 0, \
        "Agent should recognize and store patterns after multiple runs"
```

### 2. Retrieval Tests

Verify relevant experiences are retrieved before execution.

```python
# agents/my-agent/tests/test_memory_retrieval.py

import pytest
from pathlib import Path
from datetime import datetime
from ..agent import MyAgent
from amplihack_memory import Experience, ExperienceType

@pytest.fixture
def agent_with_mock_experiences():
    """Create agent with pre-populated memory."""
    agent = MyAgent(Path(__file__).parent.parent)
    agent.memory.clear()

    # Store relevant experience
    agent.memory.store_experience(Experience(
        experience_type=ExperienceType.PATTERN,
        context="Documentation files often lack examples",
        outcome="Check all doc files for code examples",
        confidence=0.9,
        timestamp=datetime.now()
    ))

    # Store irrelevant experience
    agent.memory.store_experience(Experience(
        experience_type=ExperienceType.SUCCESS,
        context="Fixed security vulnerability in authentication",
        outcome="Applied input validation",
        confidence=0.85,
        timestamp=datetime.now()
    ))

    return agent

def test_retrieves_relevant_experiences(agent_with_mock_experiences, tmp_path):
    """Verify agent retrieves relevant experiences before execution."""

    # Task similar to stored pattern
    task = "Analyze documentation for missing examples"

    # Execute (agent should retrieve relevant experience)
    result = agent_with_mock_experiences.execute_task(task, tmp_path)

    # Verify relevant experience was used
    assert result['patterns_applied'] > 0, \
        "Agent should apply relevant patterns"

def test_filters_by_confidence(agent_with_mock_experiences, tmp_path):
    """Verify agent only applies high-confidence patterns."""

    # Add low-confidence pattern
    agent_with_mock_experiences.memory.store_experience(Experience(
        experience_type=ExperienceType.PATTERN,
        context="Low confidence pattern",
        outcome="Should not be applied",
        confidence=0.4,  # Below typical threshold (0.7)
        timestamp=datetime.now()
    ))

    result = agent_with_mock_experiences.execute_task("Test task", tmp_path)

    # Low-confidence pattern should not be applied
    # (exact assertion depends on how your agent tracks this)
    stats = agent_with_mock_experiences.memory.get_statistics()
    assert stats['total_experiences'] >= 3, "Should have stored experiences"
```

### 3. Pattern Recognition Tests

Verify patterns are recognized after repeated occurrences.

```python
# agents/my-agent/tests/test_pattern_recognition.py

import pytest
from pathlib import Path
from ..agent import MyAgent
from amplihack_memory import ExperienceType

@pytest.fixture
def agent(tmp_path):
    """Create agent with clean memory."""
    agent = MyAgent(Path(__file__).parent.parent)
    agent.memory.clear()
    return agent

def test_recognizes_pattern_after_threshold(agent, tmp_path):
    """Verify pattern is recognized after threshold occurrences."""

    # Run agent multiple times with similar tasks
    threshold = 3  # Typical pattern recognition threshold

    for i in range(threshold):
        result = agent.execute_task(f"Test task {i}", tmp_path)

    # After threshold runs, pattern should be recognized
    patterns = agent.memory.retrieve_experiences(
        experience_type=ExperienceType.PATTERN
    )

    assert len(patterns) > 0, \
        f"Agent should recognize patterns after {threshold} similar runs"

def test_pattern_confidence_increases_with_validation(agent, tmp_path):
    """Verify pattern confidence increases when pattern is validated."""

    # Run to create initial pattern
    for i in range(3):
        agent.execute_task("Test task", tmp_path)

    patterns = agent.memory.retrieve_experiences(
        experience_type=ExperienceType.PATTERN
    )
    initial_confidence = patterns[0].confidence if patterns else 0

    # Run again (should apply pattern and increase confidence)
    agent.execute_task("Test task", tmp_path)

    patterns = agent.memory.retrieve_experiences(
        experience_type=ExperienceType.PATTERN
    )
    new_confidence = patterns[0].confidence if patterns else 0

    assert new_confidence >= initial_confidence, \
        "Pattern confidence should increase (or stay same) when validated"

def test_does_not_duplicate_known_patterns(agent, tmp_path):
    """Verify agent doesn't create duplicate pattern experiences."""

    # Run multiple times
    for i in range(5):
        agent.execute_task("Test task", tmp_path)

    patterns = agent.memory.retrieve_experiences(
        experience_type=ExperienceType.PATTERN
    )

    # Check for duplicates (same context)
    contexts = [p.context for p in patterns]
    unique_contexts = set(contexts)

    assert len(contexts) == len(unique_contexts), \
        "Agent should not create duplicate patterns with same context"
```

### 4. Learning Improvement Tests

Verify performance improves over time.

```python
# agents/my-agent/tests/test_learning_improvement.py

import pytest
from pathlib import Path
from ..agent import MyAgent

@pytest.fixture
def agent():
    """Create agent with clean memory."""
    agent = MyAgent(Path(__file__).parent.parent)
    agent.memory.clear()
    return agent

def test_runtime_improves_across_runs(agent, tmp_path):
    """Verify runtime improves (or stays stable) across multiple runs."""

    runtimes = []

    # Run 5 times
    for i in range(5):
        result = agent.execute_task("Test task", tmp_path)
        runtimes.append(result['runtime'])

    # Runtime should improve or stay stable (allow 10% variance)
    first_runtime = runtimes[0]
    last_runtime = runtimes[-1]

    assert last_runtime <= first_runtime * 1.1, \
        f"Runtime should improve or stay stable: {first_runtime}s → {last_runtime}s"

def test_pattern_application_increases_over_runs(agent, tmp_path):
    """Verify agent applies more patterns as it learns."""

    # First run: no patterns to apply
    result1 = agent.execute_task("Test task", tmp_path)
    patterns_applied_1 = result1.get('patterns_applied', 0)

    # Second and third runs: may recognize patterns
    agent.execute_task("Test task", tmp_path)
    agent.execute_task("Test task", tmp_path)

    # Fourth run: should apply learned patterns
    result4 = agent.execute_task("Test task", tmp_path)
    patterns_applied_4 = result4.get('patterns_applied', 0)

    assert patterns_applied_4 >= patterns_applied_1, \
        "Agent should apply more patterns after learning"

def test_knowledge_accumulation(agent, tmp_path):
    """Verify agent accumulates knowledge over time."""

    stats_history = []

    for i in range(5):
        agent.execute_task(f"Test task {i}", tmp_path)
        stats = agent.memory.get_statistics()
        stats_history.append(stats['total_experiences'])

    # Experience count should monotonically increase
    for i in range(1, len(stats_history)):
        assert stats_history[i] > stats_history[i-1], \
            f"Experience count should increase: {stats_history[i-1]} → {stats_history[i]}"
```

### 5. Integration Tests

End-to-end validation of learning behavior.

```python
# agents/my-agent/tests/test_learning_integration.py

import pytest
from pathlib import Path
from ..agent import MyAgent
from ..metrics import calculate_agent_metrics

@pytest.fixture
def agent():
    """Create agent with clean memory."""
    agent = MyAgent(Path(__file__).parent.parent)
    agent.memory.clear()
    return agent

def test_complete_learning_cycle(agent, tmp_path):
    """
    Test complete learning cycle:
    1. Agent starts with no knowledge
    2. Agent learns from first execution
    3. Agent applies learned knowledge on second execution
    4. Agent improves performance
    """

    # Step 1: Verify clean slate
    stats = agent.memory.get_statistics()
    assert stats['total_experiences'] == 0, "Should start with no experiences"

    # Step 2: First execution (learning phase)
    result1 = agent.execute_task("Analyze test files", tmp_path)
    runtime1 = result1['runtime']
    issues1 = result1.get('issues_found', 0)

    stats_after_run1 = agent.memory.get_statistics()
    assert stats_after_run1['total_experiences'] > 0, \
        "Should store experiences after first run"

    # Step 3: Second execution (application phase)
    result2 = agent.execute_task("Analyze test files", tmp_path)
    runtime2 = result2['runtime']
    patterns_applied = result2.get('patterns_applied', 0)

    assert patterns_applied > 0, \
        "Should apply learned patterns on second run"

    # Step 4: Verify improvement
    assert runtime2 <= runtime1, \
        f"Runtime should improve: {runtime1}s → {runtime2}s"

def test_learning_metrics_calculation(agent, tmp_path):
    """Verify learning metrics can be calculated after runs."""

    # Execute multiple times
    for i in range(5):
        agent.execute_task(f"Task {i}", tmp_path)

    # Calculate metrics
    metrics = calculate_agent_metrics(agent.memory, window_days=1)

    # Verify metrics are calculable
    assert metrics.performance.avg_runtime_seconds > 0, \
        "Should calculate average runtime"

    assert metrics.learning.total_patterns >= 0, \
        "Should count patterns"

    assert metrics.summary['overall_improvement'] >= 0, \
        "Should calculate overall improvement score"

def test_memory_persistence_across_sessions(agent, tmp_path):
    """Verify memory persists across agent instances."""

    # Run 1: Create and store experiences
    agent.execute_task("Task 1", tmp_path)
    stats1 = agent.memory.get_statistics()

    # Create new agent instance (simulates new session)
    agent2 = MyAgent(Path(__file__).parent.parent)

    # Run 2: New instance should load previous experiences
    result = agent2.execute_task("Task 2", tmp_path)

    # Should have applied patterns from previous session
    assert result.get('patterns_applied', 0) > 0, \
        "New agent instance should load and apply previous experiences"
```

---

## Test Organization

Organize tests by validation type:

```
agents/my-agent/tests/
├── test_memory_storage.py        # Storage validation
├── test_memory_retrieval.py      # Retrieval validation
├── test_pattern_recognition.py   # Pattern detection
├── test_learning_improvement.py  # Performance improvement
├── test_learning_integration.py  # End-to-end validation
└── conftest.py                   # Shared fixtures
```

### Shared Fixtures

```python
# agents/my-agent/tests/conftest.py

import pytest
from pathlib import Path
from ..agent import MyAgent

@pytest.fixture
def test_data_dir():
    """Directory containing test data."""
    return Path(__file__).parent / "data"

@pytest.fixture
def agent_with_clean_memory():
    """Create agent with empty memory."""
    agent = MyAgent(Path(__file__).parent.parent)
    if agent.has_memory():
        agent.memory.clear()
    yield agent
    # Cleanup after test
    if agent.has_memory():
        agent.memory.clear()

@pytest.fixture
def agent_with_baseline():
    """Create agent with baseline experiences for comparison."""
    agent = MyAgent(Path(__file__).parent.parent)
    agent.memory.clear()

    # Store baseline experiences
    from amplihack_memory import Experience, ExperienceType
    from datetime import datetime

    baseline_experiences = [
        Experience(
            experience_type=ExperienceType.PATTERN,
            context="Common pattern 1",
            outcome="Description",
            confidence=0.8,
            timestamp=datetime.now()
        ),
        Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Previous successful run",
            outcome="Completed",
            confidence=0.9,
            timestamp=datetime.now(),
            metadata={"runtime_seconds": 45}
        ),
    ]

    for exp in baseline_experiences:
        agent.memory.store_experience(exp)

    return agent
```

---

## Running Tests

### Run All Learning Tests

```bash
# Run all tests for agent
pytest agents/my-agent/tests/

# Run specific test file
pytest agents/my-agent/tests/test_learning_improvement.py

# Run specific test
pytest agents/my-agent/tests/test_learning_improvement.py::test_runtime_improves_across_runs

# Run with verbose output
pytest agents/my-agent/tests/ -v

# Run with debug output
pytest agents/my-agent/tests/ -s
```

### Integration with gadugi-agentic-test

Use gadugi-agentic-test for orchestrated testing:

```yaml
# tests/learning_validation.yaml
test_suite: memory_enabled_agent_validation

personas:
  - name: validator
    type: tester
    objective: Validate agent learning behavior

tests:
  - name: storage_validation
    persona: validator
    command: pytest agents/my-agent/tests/test_memory_storage.py
    success_criteria:
      - exit_code: 0
      - output_contains: "PASSED"

  - name: learning_improvement_validation
    persona: validator
    command: pytest agents/my-agent/tests/test_learning_improvement.py
    success_criteria:
      - exit_code: 0
      - runtime_improvement: true

  - name: integration_validation
    persona: validator
    command: pytest agents/my-agent/tests/test_learning_integration.py
    success_criteria:
      - exit_code: 0
      - all_assertions_pass: true
```

Run with:

```bash
gadugi-agentic-test run tests/learning_validation.yaml
```

---

## Continuous Validation

### Pre-commit Hook

Validate learning behavior before commits:

```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-agent-learning
        name: Validate Agent Learning
        entry: pytest agents/my-agent/tests/
        language: system
        pass_filenames: false
        always_run: false
        files: ^agents/my-agent/
```

### CI Integration

```yaml
# .github/workflows/validate-learning.yml
name: Validate Agent Learning

on:
  pull_request:
    paths:
      - "agents/**"

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: |
          pip install -e .
          pip install amplihack-memory-lib

      - name: Run learning validation tests
        run: |
          pytest agents/my-agent/tests/ -v --tb=short

      - name: Check learning metrics
        run: |
          python -m my_agent metrics --window 7 --format json > metrics.json
          # Validate metrics meet thresholds
          python scripts/validate_metrics.py metrics.json
```

---

## Troubleshooting Test Failures

### Test: `test_stores_experiences_after_run` fails

**Symptom**: Agent doesn't store experiences after execution.

**Diagnosis**:

```python
# Add debug logging
def test_stores_experiences_after_run(agent, tmp_path):
    result = agent.execute_task("Test task", tmp_path)

    # Debug: Check if memory is enabled
    print(f"Memory enabled: {agent.has_memory()}")

    # Debug: Check result
    print(f"Result: {result}")

    stats = agent.memory.get_statistics()
    print(f"Stats: {stats}")

    assert stats['total_experiences'] > 0
```

**Common causes**:

1. Memory not enabled in configuration
2. Agent not calling `memory.store_experience()`
3. Exception during storage (check logs)

### Test: `test_runtime_improves_across_runs` fails

**Symptom**: Runtime doesn't improve or gets worse.

**Diagnosis**:

```python
def test_runtime_improves_across_runs(agent, tmp_path):
    runtimes = []

    for i in range(5):
        result = agent.execute_task("Test task", tmp_path)
        runtime = result['runtime']
        runtimes.append(runtime)
        print(f"Run {i+1}: {runtime}s")

    # Print pattern application
    final_result = agent.execute_task("Test task", tmp_path)
    print(f"Patterns applied: {final_result.get('patterns_applied', 0)}")
```

**Common causes**:

1. Pattern recognition threshold not met (need more runs)
2. Patterns not being applied (check confidence threshold)
3. Test data too simple (no patterns to recognize)
4. Overhead of memory operations exceeds gains

**Solution**: Adjust test expectations:

```python
# Allow for variance
assert last_runtime <= first_runtime * 1.2, \
    "Runtime should not degrade significantly"
```

### Test: `test_recognizes_pattern_after_threshold` fails

**Symptom**: Patterns not recognized after multiple runs.

**Diagnosis**:

```python
def test_recognizes_pattern_after_threshold(agent, tmp_path):
    for i in range(3):
        result = agent.execute_task("Test task", tmp_path)
        print(f"Run {i+1} discoveries: {result.get('discoveries', [])}")

    patterns = agent.memory.retrieve_experiences(
        experience_type=ExperienceType.PATTERN
    )

    print(f"Patterns found: {len(patterns)}")
    for p in patterns:
        print(f"  - {p.context} (confidence: {p.confidence})")
```

**Common causes**:

1. Discoveries not consistent across runs (no actual pattern)
2. Pattern key extraction not working
3. Pattern recognition threshold set too high

---

## Best Practices

### 1. Test with Realistic Data

Use realistic test data that contains actual patterns:

```python
@pytest.fixture
def realistic_test_data(tmp_path):
    """Create realistic test data with patterns."""

    # Create multiple files with similar issues
    for i in range(5):
        file_path = tmp_path / f"tutorial_{i}.md"
        file_path.write_text("""
# Tutorial

This is a tutorial without code examples.

## Steps

1. Do something
2. Do something else
""")

    return tmp_path
```

### 2. Use Parametrized Tests

Test across different scenarios:

```python
@pytest.mark.parametrize("num_runs,expected_patterns", [
    (2, 0),  # Not enough runs to recognize pattern
    (3, 1),  # Threshold met, should recognize 1 pattern
    (5, 1),  # More runs, same pattern (not duplicate)
])
def test_pattern_recognition_threshold(agent, tmp_path, num_runs, expected_patterns):
    """Test pattern recognition at different run counts."""

    for i in range(num_runs):
        agent.execute_task("Test task", tmp_path)

    patterns = agent.memory.retrieve_experiences(
        experience_type=ExperienceType.PATTERN
    )

    assert len(patterns) == expected_patterns
```

### 3. Isolate Tests

Ensure tests don't interfere with each other:

```python
@pytest.fixture(autouse=True)
def isolate_memory(agent):
    """Automatically clear memory before and after each test."""
    if agent.has_memory():
        agent.memory.clear()

    yield

    if agent.has_memory():
        agent.memory.clear()
```

### 4. Test Edge Cases

```python
def test_handles_empty_target(agent, tmp_path):
    """Verify agent handles empty target gracefully."""

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    result = agent.execute_task("Test task", empty_dir)

    # Should complete without error
    assert result is not None

    # Should still store experience (even if nothing found)
    stats = agent.memory.get_statistics()
    assert stats['total_experiences'] > 0

def test_handles_memory_quota_exceeded(agent, tmp_path):
    """Verify agent handles memory quota gracefully."""

    # Fill memory to quota
    from amplihack_memory import Experience, ExperienceType
    from datetime import datetime

    for i in range(10000):  # Exceed typical quota
        agent.memory.store_experience(Experience(
            experience_type=ExperienceType.SUCCESS,
            context=f"Experience {i}",
            outcome="Test",
            confidence=0.8,
            timestamp=datetime.now()
        ))

    # Should still work (oldest experiences pruned)
    result = agent.execute_task("Test task", tmp_path)
    assert result is not None
```

---

## Metrics for Validation

Track these metrics to validate learning effectiveness:

| Metric                       | Target               | Indicates                          |
| ---------------------------- | -------------------- | ---------------------------------- |
| **Storage rate**             | 100%                 | All executions store experiences   |
| **Pattern recognition rate** | > 70% by run 10      | Agent learns recurring patterns    |
| **Runtime improvement**      | > 40% by run 10      | Patterns actually help performance |
| **Confidence growth**        | +0.05 per validation | Patterns become more confident     |
| **False positive rate**      | < 20%                | Patterns are accurate              |

---

## Next Steps

- **[Design Custom Learning Metrics](./design-custom-learning-metrics.md)** - Track domain-specific improvements
- **[Memory-Enabled Agents API Reference](../reference/memory-enabled-agents-api.md)** - Technical documentation
- **[Troubleshooting Memory Issues](../troubleshooting/memory-enabled-agents.md)** - Fix common problems

---

**Last Updated**: 2026-02-14
