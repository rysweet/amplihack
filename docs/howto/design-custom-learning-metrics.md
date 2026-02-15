# How to Design Custom Learning Metrics

Track domain-specific improvements in your memory-enabled agents.

---

## Overview

Default learning metrics (runtime improvement, pattern recognition rate) provide general insights, but domain-specific metrics reveal how agents improve at their specific tasks.

This guide shows how to design and implement custom metrics for your agent's domain.

---

## Understanding Metrics Types

### 1. Performance Metrics

**Measure**: How efficiently the agent completes tasks

**Examples**:

- Files processed per second
- API calls made (lower = better)
- Memory usage
- Cache hit rate

### 2. Quality Metrics

**Measure**: How well the agent achieves its objective

**Examples**:

- False positive rate (lower = better)
- True positive rate (higher = better)
- Precision and recall
- User satisfaction (if available)

### 3. Learning Metrics

**Measure**: How the agent's knowledge evolves

**Examples**:

- Patterns discovered per run
- Confidence score progression
- Knowledge reuse rate
- Insight generation rate

---

## Step 1: Define What Success Looks Like

Before designing metrics, clarify your agent's objective and what improvement means.

### Example: Documentation Analyzer

**Objective**: Analyze documentation quality and suggest improvements

**Success Criteria**:

- Finds all real issues (high recall)
- Doesn't flag false positives (high precision)
- Runs faster as it learns patterns
- Provides actionable suggestions

**Key Questions**:

1. What does "better" look like for this agent?
2. How do I measure that quantitatively?
3. What should improve over time?

---

## Step 2: Identify Measurable Signals

Extract quantitative data from agent execution.

### Example Signals

```python
# During execution, track:
class AgentExecution:
    def __init__(self):
        self.signals = {
            # Performance
            "runtime_seconds": 0.0,
            "files_processed": 0,
            "cache_hits": 0,
            "cache_misses": 0,

            # Quality
            "issues_found": 0,
            "false_positives": 0,  # Requires validation
            "suggestions_provided": 0,
            "suggestions_accepted": 0,  # Requires feedback

            # Learning
            "patterns_applied": 0,
            "patterns_discovered": 0,
            "experiences_retrieved": 0,
            "insights_generated": 0,

            # Context
            "run_number": 0,
            "target_size_kb": 0,
        }
```

Store these signals in experience metadata:

```python
from amplihack_memory import Experience, ExperienceType
from datetime import datetime

# After execution
self.memory.store_experience(Experience(
    experience_type=ExperienceType.SUCCESS,
    context=f"Analyzed {self.signals['files_processed']} files",
    outcome=f"Found {self.signals['issues_found']} issues",
    confidence=0.9,
    timestamp=datetime.now(),
    metadata=self.signals  # Store all signals
))
```

---

## Step 3: Design Metric Calculations

Create metrics from raw signals.

### Performance Metrics

```python
# agents/my-agent/metrics.py

from amplihack_memory import MemoryConnector, ExperienceType
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass

@dataclass
class PerformanceMetrics:
    avg_runtime_seconds: float
    files_per_second: float
    cache_hit_rate: float
    runtime_improvement_pct: float

def calculate_performance_metrics(
    memory: MemoryConnector,
    window_days: int = 30
) -> PerformanceMetrics:
    """Calculate performance metrics from experiences."""

    since = datetime.now() - timedelta(days=window_days)

    # Get all successful executions
    successes = memory.retrieve_experiences(
        experience_type=ExperienceType.SUCCESS,
        since=since
    )

    if not successes:
        return PerformanceMetrics(0, 0, 0, 0)

    # Extract signals
    runtimes = []
    files_counts = []
    cache_hits = []
    cache_total = []

    for exp in successes:
        if 'runtime_seconds' in exp.metadata:
            runtimes.append(exp.metadata['runtime_seconds'])
        if 'files_processed' in exp.metadata:
            files_counts.append(exp.metadata['files_processed'])
        if 'cache_hits' in exp.metadata and 'cache_misses' in exp.metadata:
            hits = exp.metadata['cache_hits']
            misses = exp.metadata['cache_misses']
            cache_hits.append(hits)
            cache_total.append(hits + misses)

    # Calculate metrics
    avg_runtime = sum(runtimes) / len(runtimes) if runtimes else 0
    avg_files = sum(files_counts) / len(files_counts) if files_counts else 0
    files_per_second = avg_files / avg_runtime if avg_runtime > 0 else 0

    cache_hit_rate = (
        sum(cache_hits) / sum(cache_total)
        if cache_total and sum(cache_total) > 0
        else 0
    )

    # Runtime improvement (first run vs current average)
    first_runtime = runtimes[0] if runtimes else 0
    improvement_pct = (
        ((first_runtime - avg_runtime) / first_runtime * 100)
        if first_runtime > 0
        else 0
    )

    return PerformanceMetrics(
        avg_runtime_seconds=avg_runtime,
        files_per_second=files_per_second,
        cache_hit_rate=cache_hit_rate,
        runtime_improvement_pct=improvement_pct
    )
```

### Quality Metrics

```python
@dataclass
class QualityMetrics:
    precision: float  # True positives / (True positives + False positives)
    recall: float     # True positives / (True positives + False negatives)
    f1_score: float   # Harmonic mean of precision and recall
    avg_confidence: float

def calculate_quality_metrics(
    memory: MemoryConnector,
    window_days: int = 30
) -> QualityMetrics:
    """Calculate quality metrics from experiences."""

    since = datetime.now() - timedelta(days=window_days)

    successes = memory.retrieve_experiences(
        experience_type=ExperienceType.SUCCESS,
        since=since
    )

    if not successes:
        return QualityMetrics(0, 0, 0, 0)

    # Aggregate quality signals
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    confidences = []

    for exp in successes:
        # These require validation/feedback to be accurate
        true_positives += exp.metadata.get('true_positives', 0)
        false_positives += exp.metadata.get('false_positives', 0)
        false_negatives += exp.metadata.get('false_negatives', 0)
        confidences.append(exp.confidence)

    # Calculate metrics
    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0
        else 0
    )

    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0
        else 0
    )

    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )

    avg_confidence = sum(confidences) / len(confidences) if confidences else 0

    return QualityMetrics(
        precision=precision,
        recall=recall,
        f1_score=f1_score,
        avg_confidence=avg_confidence
    )
```

### Learning Metrics

```python
@dataclass
class LearningMetrics:
    total_patterns: int
    patterns_per_run: float
    pattern_recognition_rate: float
    knowledge_reuse_rate: float
    insights_generated: int

def calculate_learning_metrics(
    memory: MemoryConnector,
    window_days: int = 30
) -> LearningMetrics:
    """Calculate learning metrics from experiences."""

    since = datetime.now() - timedelta(days=window_days)

    # Get all experiences
    all_exps = memory.retrieve_experiences(since=since, limit=10000)

    # Separate by type
    patterns = [e for e in all_exps if e.experience_type == ExperienceType.PATTERN]
    successes = [e for e in all_exps if e.experience_type == ExperienceType.SUCCESS]
    insights = [e for e in all_exps if e.experience_type == ExperienceType.INSIGHT]

    if not successes:
        return LearningMetrics(0, 0, 0, 0, 0)

    # Calculate metrics
    total_patterns = len(patterns)
    num_runs = len(set(e.timestamp.date() for e in successes))  # Approximate runs by days
    patterns_per_run = total_patterns / num_runs if num_runs > 0 else 0

    # Pattern recognition rate: % of patterns applied vs discovered
    patterns_applied = sum(e.metadata.get('patterns_applied', 0) for e in successes)
    patterns_discovered = sum(e.metadata.get('patterns_discovered', 0) for e in successes)
    total_pattern_opportunities = patterns_applied + patterns_discovered

    pattern_recognition_rate = (
        patterns_applied / total_pattern_opportunities
        if total_pattern_opportunities > 0
        else 0
    )

    # Knowledge reuse rate: % of experiences retrieved
    experiences_retrieved = sum(e.metadata.get('experiences_retrieved', 0) for e in successes)
    knowledge_reuse_rate = (
        experiences_retrieved / len(all_exps)
        if len(all_exps) > 0
        else 0
    )

    return LearningMetrics(
        total_patterns=total_patterns,
        patterns_per_run=patterns_per_run,
        pattern_recognition_rate=pattern_recognition_rate,
        knowledge_reuse_rate=knowledge_reuse_rate,
        insights_generated=len(insights)
    )
```

---

## Step 4: Combine Into Agent-Specific Metrics

Create a unified metrics calculator:

```python
@dataclass
class AgentMetrics:
    """Complete metrics for agent."""
    performance: PerformanceMetrics
    quality: QualityMetrics
    learning: LearningMetrics
    summary: Dict[str, Any]

def calculate_agent_metrics(
    memory: MemoryConnector,
    window_days: int = 30
) -> AgentMetrics:
    """Calculate all metrics for agent."""

    perf = calculate_performance_metrics(memory, window_days)
    qual = calculate_quality_metrics(memory, window_days)
    learn = calculate_learning_metrics(memory, window_days)

    # Create summary
    summary = {
        "window_days": window_days,
        "overall_improvement": _calculate_overall_improvement(perf, qual, learn),
        "strengths": _identify_strengths(perf, qual, learn),
        "areas_for_improvement": _identify_weaknesses(perf, qual, learn)
    }

    return AgentMetrics(
        performance=perf,
        quality=qual,
        learning=learn,
        summary=summary
    )

def _calculate_overall_improvement(
    perf: PerformanceMetrics,
    qual: QualityMetrics,
    learn: LearningMetrics
) -> float:
    """Calculate single overall improvement score (0-100)."""

    # Weighted combination
    score = (
        perf.runtime_improvement_pct * 0.3 +
        qual.f1_score * 100 * 0.4 +
        learn.pattern_recognition_rate * 100 * 0.3
    )

    return max(0, min(100, score))

def _identify_strengths(
    perf: PerformanceMetrics,
    qual: QualityMetrics,
    learn: LearningMetrics
) -> List[str]:
    """Identify areas where agent excels."""

    strengths = []

    if perf.runtime_improvement_pct > 50:
        strengths.append("Strong performance improvement")

    if qual.precision > 0.9:
        strengths.append("High precision (low false positives)")

    if qual.recall > 0.9:
        strengths.append("High recall (finds most issues)")

    if learn.pattern_recognition_rate > 0.8:
        strengths.append("Excellent pattern recognition")

    if learn.insights_generated > 5:
        strengths.append("Generates valuable insights")

    return strengths

def _identify_weaknesses(
    perf: PerformanceMetrics,
    qual: QualityMetrics,
    learn: LearningMetrics
) -> List[str]:
    """Identify areas needing improvement."""

    weaknesses = []

    if perf.runtime_improvement_pct < 20:
        weaknesses.append("Limited performance improvement")

    if qual.precision < 0.7:
        weaknesses.append("High false positive rate")

    if qual.recall < 0.7:
        weaknesses.append("Missing real issues")

    if learn.pattern_recognition_rate < 0.5:
        weaknesses.append("Low pattern recognition rate")

    if learn.patterns_per_run < 1:
        weaknesses.append("Not discovering enough patterns")

    return weaknesses
```

---

## Step 5: Add CLI Command

Expose metrics via CLI:

```python
# agents/my-agent/cli.py

@cli.command()
@click.option('--window', default=30, help='Time window in days')
@click.option('--format', type=click.Choice(['text', 'json']), default='text')
def metrics(window, format):
    """Show agent learning metrics."""
    agent = MyAgent(Path(__file__).parent)

    if not agent.has_memory():
        click.echo("Memory not enabled")
        return

    from .metrics import calculate_agent_metrics
    metrics = calculate_agent_metrics(agent.memory, window_days=window)

    if format == 'json':
        import json
        print(json.dumps({
            "performance": metrics.performance.__dict__,
            "quality": metrics.quality.__dict__,
            "learning": metrics.learning.__dict__,
            "summary": metrics.summary
        }, indent=2))
        return

    # Text format
    click.echo(f"\n{'='*60}")
    click.echo(f"Agent Metrics (Last {window} days)")
    click.echo(f"{'='*60}\n")

    # Performance
    click.echo("PERFORMANCE:")
    click.echo(f"  Runtime improvement: {metrics.performance.runtime_improvement_pct:.1f}%")
    click.echo(f"  Files per second: {metrics.performance.files_per_second:.2f}")
    click.echo(f"  Cache hit rate: {metrics.performance.cache_hit_rate:.1%}")
    click.echo()

    # Quality
    click.echo("QUALITY:")
    click.echo(f"  Precision: {metrics.quality.precision:.2%}")
    click.echo(f"  Recall: {metrics.quality.recall:.2%}")
    click.echo(f"  F1 Score: {metrics.quality.f1_score:.2%}")
    click.echo(f"  Avg Confidence: {metrics.quality.avg_confidence:.2f}")
    click.echo()

    # Learning
    click.echo("LEARNING:")
    click.echo(f"  Total patterns: {metrics.learning.total_patterns}")
    click.echo(f"  Patterns per run: {metrics.learning.patterns_per_run:.1f}")
    click.echo(f"  Pattern recognition rate: {metrics.learning.pattern_recognition_rate:.1%}")
    click.echo(f"  Knowledge reuse rate: {metrics.learning.knowledge_reuse_rate:.1%}")
    click.echo(f"  Insights generated: {metrics.learning.insights_generated}")
    click.echo()

    # Summary
    click.echo("SUMMARY:")
    click.echo(f"  Overall improvement: {metrics.summary['overall_improvement']:.1f}/100")

    if metrics.summary['strengths']:
        click.echo("\n  Strengths:")
        for strength in metrics.summary['strengths']:
            click.echo(f"    ✓ {strength}")

    if metrics.summary['areas_for_improvement']:
        click.echo("\n  Areas for improvement:")
        for weakness in metrics.summary['areas_for_improvement']:
            click.echo(f"    ⚠ {weakness}")

    click.echo()
```

**Usage**:

```bash
# View metrics
python -m my_agent metrics --window 30

# Export as JSON
python -m my_agent metrics --format json > metrics.json
```

---

## Step 6: Validate Metrics

Test that metrics accurately reflect agent behavior:

```python
# agents/my-agent/tests/test_metrics.py

import pytest
from pathlib import Path
from ..agent import MyAgent
from ..metrics import calculate_agent_metrics
from amplihack_memory import Experience, ExperienceType
from datetime import datetime

@pytest.fixture
def agent_with_mock_data(tmp_path):
    """Create agent and populate with mock experiences."""
    agent = MyAgent(tmp_path)
    agent.memory.clear()

    # Add mock experiences simulating improvement
    for run in range(5):
        # Runtime improves
        runtime = 100 - (run * 10)  # 100s → 60s

        # Quality improves
        true_pos = 10 + run  # 10 → 14
        false_pos = 5 - run  # 5 → 1

        agent.memory.store_experience(Experience(
            experience_type=ExperienceType.SUCCESS,
            context=f"Run {run + 1}",
            outcome="Completed",
            confidence=0.8,
            timestamp=datetime.now(),
            metadata={
                "runtime_seconds": runtime,
                "files_processed": 50,
                "true_positives": true_pos,
                "false_positives": false_pos,
                "false_negatives": 2,
                "patterns_applied": run * 2,
                "patterns_discovered": max(3 - run, 0)
            }
        ))

    return agent

def test_performance_metrics_show_improvement(agent_with_mock_data):
    """Verify performance metrics detect improvement."""
    metrics = calculate_agent_metrics(agent_with_mock_data.memory)

    # Should show runtime improvement
    assert metrics.performance.runtime_improvement_pct > 30, \
        "Should detect runtime improvement"

def test_quality_metrics_show_improvement(agent_with_mock_data):
    """Verify quality metrics detect improvement."""
    metrics = calculate_agent_metrics(agent_with_mock_data.memory)

    # Precision should be good (low false positives)
    assert metrics.quality.precision > 0.7, \
        "Precision should be reasonable"

def test_learning_metrics_show_progress(agent_with_mock_data):
    """Verify learning metrics show progress."""
    metrics = calculate_agent_metrics(agent_with_mock_data.memory)

    # Pattern recognition rate should increase
    assert metrics.learning.pattern_recognition_rate > 0.5, \
        "Should show increasing pattern recognition"

def test_overall_score_improves_with_better_metrics(agent_with_mock_data):
    """Verify overall score increases with improvements."""
    metrics = calculate_agent_metrics(agent_with_mock_data.memory)

    assert metrics.summary['overall_improvement'] > 50, \
        "Overall score should reflect improvements"
```

---

## Domain-Specific Examples

### Security Scanner Metrics

```python
@dataclass
class SecurityMetrics:
    vulnerabilities_found: int
    false_positive_rate: float
    critical_findings: int
    avg_severity_score: float
    coverage_pct: float  # % of codebase scanned

def calculate_security_metrics(memory: MemoryConnector) -> SecurityMetrics:
    successes = memory.retrieve_experiences(experience_type=ExperienceType.SUCCESS)

    total_vulns = sum(e.metadata.get('vulnerabilities_found', 0) for e in successes)
    false_pos = sum(e.metadata.get('false_positives', 0) for e in successes)
    critical = sum(e.metadata.get('critical_findings', 0) for e in successes)
    severities = [e.metadata.get('avg_severity', 0) for e in successes]
    coverage = [e.metadata.get('coverage_pct', 0) for e in successes]

    return SecurityMetrics(
        vulnerabilities_found=total_vulns,
        false_positive_rate=false_pos / total_vulns if total_vulns > 0 else 0,
        critical_findings=critical,
        avg_severity_score=sum(severities) / len(severities) if severities else 0,
        coverage_pct=sum(coverage) / len(coverage) if coverage else 0
    )
```

### Performance Optimizer Metrics

```python
@dataclass
class OptimizationMetrics:
    optimizations_suggested: int
    optimizations_applied: int
    avg_speedup_pct: float
    memory_reduction_mb: float
    cost_savings_estimate: float

def calculate_optimization_metrics(memory: MemoryConnector) -> OptimizationMetrics:
    successes = memory.retrieve_experiences(experience_type=ExperienceType.SUCCESS)

    suggested = sum(e.metadata.get('suggestions', 0) for e in successes)
    applied = sum(e.metadata.get('applied', 0) for e in successes)
    speedups = [e.metadata.get('speedup_pct', 0) for e in successes]
    memory_saved = [e.metadata.get('memory_reduction_mb', 0) for e in successes]

    avg_speedup = sum(speedups) / len(speedups) if speedups else 0
    total_memory_saved = sum(memory_saved)
    cost_savings = total_memory_saved * 0.01  # $0.01 per MB saved (example)

    return OptimizationMetrics(
        optimizations_suggested=suggested,
        optimizations_applied=applied,
        avg_speedup_pct=avg_speedup,
        memory_reduction_mb=total_memory_saved,
        cost_savings_estimate=cost_savings
    )
```

---

## Best Practices

### 1. Track Signals During Execution

Don't try to reconstruct metrics after the fact. Track signals as work happens:

```python
class AgentExecution:
    def __init__(self):
        self.metrics_tracker = MetricsTracker()

    async def process_file(self, file: Path):
        start = time.time()

        # Process file
        result = await self._analyze_file(file)

        # Track signal immediately
        self.metrics_tracker.record("file_processed", {
            "runtime": time.time() - start,
            "issues_found": len(result.issues),
            "file_size_kb": file.stat().st_size / 1024
        })
```

### 2. Require Validation for Quality Metrics

Quality metrics (precision, recall) require ground truth. Plan for validation:

```python
# Store results for validation
experience = Experience(
    experience_type=ExperienceType.SUCCESS,
    context="Found 5 issues",
    outcome="Issues: [list]",
    metadata={
        "findings": findings,
        "validated": False,  # Will be validated later
        "validation_id": str(uuid.uuid4())
    }
)

# Later, after human review
def validate_findings(validation_id: str, results: ValidationResults):
    """Update experience with validation results."""
    exp = memory.get_experience_by_validation_id(validation_id)

    exp.metadata['validated'] = True
    exp.metadata['true_positives'] = results.true_positives
    exp.metadata['false_positives'] = results.false_positives
    exp.metadata['false_negatives'] = results.false_negatives

    memory.update_experience(exp)
```

### 3. Use Baselines for Comparison

Always compare to a baseline:

```python
# First run establishes baseline
if not memory.has_baseline():
    memory.set_baseline(metrics)
    print("Baseline established")
else:
    baseline = memory.get_baseline()
    improvement = metrics.compare_to(baseline)
    print(f"Improvement vs baseline: {improvement:.1%}")
```

### 4. Visualize Trends

Create trend visualizations:

```python
@cli.command()
def metrics_trend():
    """Show metrics trend over time."""
    agent = MyAgent(Path(__file__).parent)

    # Get metrics for each week
    weeks = []
    for week in range(12, 0, -1):
        metrics = calculate_agent_metrics(
            agent.memory,
            window_days=7,
            offset_days=week * 7
        )
        weeks.append(metrics)

    # ASCII chart
    print("\nRuntime Improvement Trend:")
    print("Week | Improvement")
    print("-----+------------")
    for i, metrics in enumerate(weeks):
        bar = "█" * int(metrics.performance.runtime_improvement_pct / 5)
        print(f"  {12-i:2d} | {bar} {metrics.performance.runtime_improvement_pct:.1f}%")
```

---

## Next Steps

- **[Validate Agent Learning](./validate-agent-learning.md)** - Test learning behavior
- **[Memory-Enabled Agents API Reference](../reference/memory-enabled-agents-api.md)** - Technical documentation
- **[Troubleshooting Memory Issues](../troubleshooting/memory-enabled-agents.md)** - Fix common problems

---

**Last Updated**: 2026-02-14
