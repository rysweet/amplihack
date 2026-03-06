# How to Integrate Memory into Existing Agents

Add persistent learning capabilities to your custom amplihack agents.

---

## Prerequisites

- Existing goal-seeking agent
- `amplihack-memory-lib` installed (`pip install amplihack-memory-lib`)
- Basic understanding of your agent's execution flow

---

## Quick Start (5 minutes)

For agents generated with the goal agent generator, simply regenerate with memory enabled:

```bash
amplihack goal-agent generate \
  --name "my-agent" \
  --objective "Your agent objective" \
  --enable-memory
```

This automatically adds memory integration. For manual integration, follow the steps below.

---

## Step 1: Add Memory Configuration

Create `memory_config.yaml` in your agent directory:

```yaml
# agents/my-agent/memory_config.yaml
memory:
  enabled: true

  experience_types:
    - success
    - failure
    - pattern
    - insight

  learning:
    min_confidence_to_apply: 0.7
    pattern_recognition_threshold: 3
    similarity_threshold: 0.7
    max_relevant_experiences: 10

  storage:
    max_size_mb: 100
    compression:
      enabled: true
      after_days: 30

  retention:
    max_age_days: 90
    max_experiences: 10000
```

---

## Step 2: Initialize Memory in Agent

Add memory connector to agent initialization:

```python
# agents/my-agent/agent.py

from amplihack_memory import MemoryConnector
from pathlib import Path
import yaml

class MyAgent:
    def __init__(self, agent_dir: Path):
        self.agent_dir = agent_dir
        self.name = agent_dir.name

        # Load memory configuration
        memory_config_path = agent_dir / "memory_config.yaml"
        with open(memory_config_path) as f:
            config = yaml.safe_load(f)

        # Initialize memory if enabled
        if config['memory']['enabled']:
            self.memory = MemoryConnector(
                agent_name=self.name,
                max_memory_mb=config['memory']['storage']['max_size_mb'],
                enable_compression=config['memory']['storage']['compression']['enabled']
            )
            self.memory_config = config['memory']
        else:
            self.memory = None

    def has_memory(self) -> bool:
        """Check if memory is enabled for this agent."""
        return self.memory is not None
```

---

## Step 3: Load Experiences Before Task

Retrieve relevant experiences before starting the task:

```python
from amplihack_memory import Experience, ExperienceType
from typing import List

class MyAgent:
    async def execute_task(self, task_description: str, target: Path):
        """Execute task with memory integration."""

        relevant_experiences = []

        # Load relevant past experiences
        if self.has_memory():
            relevant_experiences = self.memory.retrieve_relevant(
                current_context=task_description,
                top_k=self.memory_config['learning']['max_relevant_experiences'],
                min_similarity=self.memory_config['learning']['similarity_threshold']
            )

            print(f"[Memory] Loaded {len(relevant_experiences)} relevant experiences")

            # Separate by type
            patterns = [e for e in relevant_experiences if e.experience_type == ExperienceType.PATTERN]
            insights = [e for e in relevant_experiences if e.experience_type == ExperienceType.INSIGHT]

            print(f"[Memory] Applying {len(patterns)} known patterns")

        # Execute task with learned knowledge
        result = await self._execute_with_experiences(
            task_description,
            target,
            patterns,
            insights
        )

        return result
```

---

## Step 4: Store Experiences During Execution

Store experiences as the agent works:

```python
from datetime import datetime

class MyAgent:
    async def _execute_with_experiences(
        self,
        task_description: str,
        target: Path,
        known_patterns: List[Experience],
        known_insights: List[Experience]
    ):
        """Execute task and store experiences."""

        start_time = datetime.now()
        results = []

        # Apply known patterns first
        for pattern in known_patterns:
            if pattern.confidence >= self.memory_config['learning']['min_confidence_to_apply']:
                # Apply learned pattern
                pattern_results = self._apply_pattern(pattern, target)
                results.extend(pattern_results)

                # Store success if pattern worked
                if pattern_results:
                    if self.has_memory():
                        self.memory.store_experience(Experience(
                            experience_type=ExperienceType.SUCCESS,
                            context=f"Applied pattern: {pattern.context}",
                            outcome=f"Found {len(pattern_results)} matches",
                            confidence=min(pattern.confidence + 0.05, 1.0),  # Increase confidence
                            timestamp=datetime.now(),
                            metadata={"pattern_id": pattern.experience_id, "matches": len(pattern_results)}
                        ))

        # Discover new patterns
        new_discoveries = await self._discover_patterns(target, known_patterns)

        # Store new patterns
        if self.has_memory():
            for discovery in new_discoveries:
                self.memory.store_experience(discovery)
                print(f"[Memory] New pattern: {discovery.context}")

        results.extend(new_discoveries)

        # Calculate and store metrics
        runtime = (datetime.now() - start_time).total_seconds()

        return {
            "results": results,
            "runtime": runtime,
            "patterns_applied": len(known_patterns),
            "new_patterns": len(new_discoveries)
        }
```

---

## Step 5: Recognize and Store Patterns

Implement pattern recognition:

```python
class MyAgent:
    def __init__(self, agent_dir: Path):
        # ... existing init code ...

        # Pattern recognition tracking
        self.pattern_candidates = {}  # Track potential patterns

    async def _discover_patterns(self, target: Path, known_patterns: List[Experience]) -> List[Experience]:
        """Discover new patterns by analyzing results."""

        new_patterns = []

        # Analyze results for recurring situations
        for result in self.current_results:
            pattern_key = self._extract_pattern_key(result)

            # Track occurrences
            if pattern_key not in self.pattern_candidates:
                self.pattern_candidates[pattern_key] = {
                    "count": 0,
                    "examples": [],
                    "first_seen": datetime.now()
                }

            self.pattern_candidates[pattern_key]["count"] += 1
            self.pattern_candidates[pattern_key]["examples"].append(result)

            # Recognize as pattern if threshold reached
            threshold = self.memory_config['learning']['pattern_recognition_threshold']
            if self.pattern_candidates[pattern_key]["count"] >= threshold:
                # Check if already known
                is_known = any(p.context == pattern_key for p in known_patterns)

                if not is_known:
                    # Create new pattern experience
                    pattern = Experience(
                        experience_type=ExperienceType.PATTERN,
                        context=pattern_key,
                        outcome=self._describe_pattern(self.pattern_candidates[pattern_key]),
                        confidence=min(0.5 + (self.pattern_candidates[pattern_key]["count"] * 0.1), 0.95),
                        timestamp=datetime.now(),
                        metadata={
                            "occurrences": self.pattern_candidates[pattern_key]["count"],
                            "examples": self.pattern_candidates[pattern_key]["examples"][:5]  # Store first 5
                        }
                    )
                    new_patterns.append(pattern)

        return new_patterns

    def _extract_pattern_key(self, result) -> str:
        """Extract a pattern identifier from a result."""
        # Example: For file analysis
        # Return something like "missing_docstring_in_function" or "unused_import"
        return result.issue_type

    def _describe_pattern(self, pattern_data) -> str:
        """Create human-readable pattern description."""
        return f"Occurs in {pattern_data['count']} instances. Pattern: {pattern_data['examples'][0].description}"
```

---

## Step 6: Store Success/Failure Outcomes

Store final outcomes:

```python
class MyAgent:
    async def execute_task(self, task_description: str, target: Path):
        """Execute task with success/failure tracking."""

        try:
            result = await self._execute_with_experiences(
                task_description,
                target,
                [],
                []
            )

            # Store successful execution
            if self.has_memory():
                self.memory.store_experience(Experience(
                    experience_type=ExperienceType.SUCCESS,
                    context=f"Task: {task_description}",
                    outcome=f"Completed successfully. {result['results']}",
                    confidence=0.9,
                    timestamp=datetime.now(),
                    metadata={
                        "runtime": result['runtime'],
                        "patterns_applied": result['patterns_applied'],
                        "new_patterns": result['new_patterns']
                    }
                ))

            return result

        except Exception as e:
            # Store failure for learning
            if self.has_memory():
                self.memory.store_experience(Experience(
                    experience_type=ExperienceType.FAILURE,
                    context=f"Task: {task_description}",
                    outcome=f"Failed: {str(e)}",
                    confidence=0.8,
                    timestamp=datetime.now(),
                    metadata={
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                ))

            raise
```

---

## Step 7: Add Learning Metrics

Track learning progress:

```python
# agents/my-agent/metrics.py

from amplihack_memory import MemoryConnector
from typing import Dict, Any
from datetime import datetime, timedelta

class LearningMetrics:
    def __init__(self, memory: MemoryConnector):
        self.memory = memory

    def calculate_metrics(self, window_days: int = 30) -> Dict[str, Any]:
        """Calculate learning metrics over time window."""

        since = datetime.now() - timedelta(days=window_days)

        # Get all experiences in window
        all_experiences = self.memory.retrieve_experiences(since=since, limit=10000)

        if not all_experiences:
            return {"error": "No experiences in time window"}

        # Group by run (using day as proxy for runs)
        runs_by_day = {}
        for exp in all_experiences:
            day = exp.timestamp.date()
            if day not in runs_by_day:
                runs_by_day[day] = []
            runs_by_day[day].append(exp)

        # Calculate pattern recognition rate
        pattern_exps = self.memory.retrieve_experiences(
            experience_type=ExperienceType.PATTERN,
            since=since
        )
        total_patterns = len(pattern_exps)

        # Calculate runtime improvements
        success_exps = self.memory.retrieve_experiences(
            experience_type=ExperienceType.SUCCESS,
            since=since
        )
        runtimes = [e.metadata.get('runtime', 0) for e in success_exps if 'runtime' in e.metadata]

        avg_runtime = sum(runtimes) / len(runtimes) if runtimes else 0
        first_runtime = runtimes[0] if runtimes else 0
        runtime_improvement = ((first_runtime - avg_runtime) / first_runtime * 100) if first_runtime > 0 else 0

        # Calculate confidence growth
        confidence_values = [e.confidence for e in all_experiences]
        avg_confidence = sum(confidence_values) / len(confidence_values)

        return {
            "window_days": window_days,
            "total_runs": len(runs_by_day),
            "total_experiences": len(all_experiences),
            "patterns_recognized": total_patterns,
            "avg_runtime": avg_runtime,
            "runtime_improvement_pct": runtime_improvement,
            "avg_confidence": avg_confidence,
            "insights_gained": len([e for e in all_experiences if e.experience_type == ExperienceType.INSIGHT])
        }
```

---

## Step 8: Add Memory Management Commands

Provide CLI commands for memory operations:

```python
# agents/my-agent/cli.py

import click
from pathlib import Path
from .agent import MyAgent
from .metrics import LearningMetrics

@click.group()
def cli():
    """My Agent CLI with memory commands."""
    pass

@cli.command()
@click.argument('target', type=click.Path(exists=True))
def run(target):
    """Run agent on target."""
    agent = MyAgent(Path(__file__).parent)
    result = agent.execute_task("Analyze target", Path(target))
    click.echo(f"Complete: {result}")

@cli.command()
def memory_stats():
    """Show memory statistics."""
    agent = MyAgent(Path(__file__).parent)
    if not agent.has_memory():
        click.echo("Memory not enabled")
        return

    stats = agent.memory.get_statistics()
    click.echo(f"Total experiences: {stats['total_experiences']}")
    click.echo(f"Storage size: {stats['storage_size_kb']:.1f} KB")
    click.echo("\nBy type:")
    for exp_type, count in stats['by_type'].items():
        click.echo(f"  {exp_type.value}: {count}")

@cli.command()
@click.option('--window', default=30, help='Time window in days')
def metrics(window):
    """Show learning metrics."""
    agent = MyAgent(Path(__file__).parent)
    if not agent.has_memory():
        click.echo("Memory not enabled")
        return

    metrics = LearningMetrics(agent.memory)
    results = metrics.calculate_metrics(window_days=window)

    click.echo(f"\nLearning Metrics (Last {window} days):")
    click.echo(f"  Total runs: {results['total_runs']}")
    click.echo(f"  Patterns recognized: {results['patterns_recognized']}")
    click.echo(f"  Runtime improvement: {results['runtime_improvement_pct']:.1f}%")
    click.echo(f"  Average confidence: {results['avg_confidence']:.2f}")
    click.echo(f"  Insights gained: {results['insights_gained']}")

@cli.command()
@click.confirmation_option(prompt='Clear all memory?')
def memory_clear():
    """Clear agent memory."""
    agent = MyAgent(Path(__file__).parent)
    if not agent.has_memory():
        click.echo("Memory not enabled")
        return

    count = agent.memory.clear()
    click.echo(f"Deleted {count} experiences")

if __name__ == '__main__':
    cli()
```

---

## Step 9: Add Validation Tests

Test memory integration with gadugi-agentic-test:

```python
# agents/my-agent/tests/test_memory_integration.py

import pytest
from pathlib import Path
from ..agent import MyAgent
from amplihack_memory import ExperienceType

@pytest.fixture
def agent():
    """Create agent with clean memory."""
    agent = MyAgent(Path(__file__).parent.parent)
    if agent.has_memory():
        agent.memory.clear()
    return agent

def test_memory_enabled(agent):
    """Verify memory is enabled."""
    assert agent.has_memory(), "Memory should be enabled"

def test_stores_experiences_after_run(agent, tmp_path):
    """Verify agent stores experiences after execution."""
    # Run agent
    result = agent.execute_task("Test task", tmp_path)

    # Check experiences stored
    stats = agent.memory.get_statistics()
    assert stats['total_experiences'] > 0, "Should store at least one experience"

def test_recognizes_patterns_across_runs(agent, tmp_path):
    """Verify agent recognizes patterns across multiple runs."""
    # First run
    agent.execute_task("Test task 1", tmp_path)

    # Second run
    agent.execute_task("Test task 2", tmp_path)

    # Third run
    agent.execute_task("Test task 3", tmp_path)

    # Check for patterns
    patterns = agent.memory.retrieve_experiences(
        experience_type=ExperienceType.PATTERN
    )

    assert len(patterns) > 0, "Should recognize at least one pattern after 3 runs"

def test_runtime_improves_with_memory(agent, tmp_path):
    """Verify runtime improves with memory."""
    # First run
    result1 = agent.execute_task("Test task", tmp_path)
    runtime1 = result1['runtime']

    # Second run (same task)
    result2 = agent.execute_task("Test task", tmp_path)
    runtime2 = result2['runtime']

    # Runtime should improve (or at least not get worse by more than 10%)
    assert runtime2 <= runtime1 * 1.1, f"Second run ({runtime2}s) should be similar or faster than first ({runtime1}s)"

def test_applies_learned_patterns(agent, tmp_path):
    """Verify agent applies learned patterns."""
    # Store a known pattern
    from amplihack_memory import Experience
    from datetime import datetime

    agent.memory.store_experience(Experience(
        experience_type=ExperienceType.PATTERN,
        context="test_pattern_key",
        outcome="Test pattern description",
        confidence=0.9,
        timestamp=datetime.now()
    ))

    # Run agent
    result = agent.execute_task("Test task", tmp_path)

    # Check that pattern was applied
    assert result['patterns_applied'] > 0, "Should apply learned patterns"
```

---

## Best Practices

### 1. Store Context, Not Content

```python
# Good: Store references
experience = Experience(
    context="File auth.py line 42: Found security issue",
    metadata={"file": "auth.py", "line": 42, "issue_type": "hardcoded_credential"}
)

# Bad: Store full content
experience = Experience(
    context="Entire file contents here...",  # ❌ Too much data
)
```

### 2. Use Appropriate Experience Types

```python
# Use SUCCESS for actions that worked
Experience(
    experience_type=ExperienceType.SUCCESS,
    context="Fixed broken link by updating URL",
    outcome="Link now works"
)

# Use PATTERN for recurring situations
Experience(
    experience_type=ExperienceType.PATTERN,
    context="Tutorial files without 'example' heading lack code samples",
    outcome="Check all tutorial files for this pattern"
)

# Use INSIGHT for high-level learnings
Experience(
    experience_type=ExperienceType.INSIGHT,
    context="Clear examples reduce support requests",
    outcome="Prioritize adding examples to all guides"
)
```

### 3. Set Appropriate Confidence

```python
# High confidence: Verified across many instances
confidence=0.95

# Medium confidence: Seen a few times
confidence=0.75

# Low confidence: First occurrence
confidence=0.5
```

### 4. Include Useful Metadata

```python
experience = Experience(
    experience_type=ExperienceType.SUCCESS,
    context="Optimized database query",
    outcome="Reduced query time by 80%",
    metadata={
        "before_ms": 500,
        "after_ms": 100,
        "query_type": "SELECT with JOIN",
        "table": "users",
        "optimization": "added_index"
    }
)
```

---

## Troubleshooting

### Memory not persisting between runs

**Check 1**: Verify memory is enabled

```python
agent = MyAgent(agent_dir)
print(f"Memory enabled: {agent.has_memory()}")
```

**Check 2**: Verify experiences are being stored

```python
# Add debug logging
if self.has_memory():
    exp_id = self.memory.store_experience(exp)
    print(f"Stored experience: {exp_id}")
```

**Check 3**: Check storage permissions

```bash
ls -la ~/.amplihack/memory/
```

### Pattern recognition not working

**Issue**: Patterns not being recognized.

**Solution**: Lower the pattern recognition threshold:

```yaml
# memory_config.yaml
learning:
  pattern_recognition_threshold: 2 # Recognize after 2 occurrences instead of 3
```

### Memory growing too large

**Issue**: Storage size exceeds limits.

**Solution**: Adjust retention policy:

```yaml
# memory_config.yaml
retention:
  max_age_days: 60 # Keep only last 60 days
  max_experiences: 5000 # Limit to 5000 experiences
```

---

## Next Steps

- **[Design Custom Learning Metrics](./design-custom-learning-metrics.md)** - Track domain-specific improvements
- **[Validate Agent Learning](./validate-agent-learning.md)** - Test learning behavior
- **[Memory-Enabled Agents API Reference](../reference/memory-enabled-agents-api.md)** - Complete API documentation

---

**Last Updated**: 2026-02-14
