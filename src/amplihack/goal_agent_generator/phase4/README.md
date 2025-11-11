# Phase 4: Learning and Adaptation from Execution History

Phase 4 implements a complete learning and adaptation system that tracks agent execution, analyzes performance patterns, and automatically improves future executions.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Learning & Adaptation                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Execution   │    │ Performance  │    │  Adaptation  │
│   Tracking   │───▶│   Analysis   │───▶│    Engine    │
└──────────────┘    └──────────────┘    └──────────────┘
        │                                       │
        ▼                                       ▼
┌──────────────┐                      ┌──────────────┐
│  Execution   │                      │  Optimized   │
│   Database   │                      │    Plans     │
└──────────────┘                      └──────────────┘
        │
        ▼
┌──────────────┐
│Self-Healing  │
│   Manager    │
└──────────────┘
```

## Components

### 1. ExecutionTracker (`execution_tracker.py`)

Tracks agent execution in real-time, capturing all events, tool usage, and errors.

**Key Features:**
- Real-time event capture
- JSONL streaming for persistence
- Phase-level tracking
- Tool usage monitoring
- Error recording

**Usage:**
```python
from amplihack.goal_agent_generator.phase4 import ExecutionTracker

# Initialize tracker
tracker = ExecutionTracker(agent_bundle, output_dir=Path("./traces"))

# Track execution
tracker.start_phase("analysis")
tracker.record_tool_use("bash", {"command": "ls"}, duration_ms=50)
tracker.end_phase("analysis", success=True)

# Complete execution
trace = tracker.complete("Task completed successfully")
```

### 2. ExecutionDatabase (`execution_database.py`)

Persistent SQLite database for execution history with 30-day retention.

**Schema:**
- `executions`: Execution metadata
- `events`: Individual execution events
- `metrics`: Aggregated metrics

**Usage:**
```python
from amplihack.goal_agent_generator.phase4 import ExecutionDatabase

# Initialize database
db = ExecutionDatabase(Path("./execution_history.db"))

# Store trace
db.store_trace(trace)

# Query by domain
executions = db.query_by_domain("security", limit=50)

# Get statistics
stats = db.get_domain_statistics("security", days=30)
```

### 3. MetricsCollector (`metrics_collector.py`)

Aggregates metrics from execution traces: durations, success rates, tool usage.

**Metrics Collected:**
- Total execution duration
- Phase-level metrics (estimated vs actual)
- Success rates
- Error counts
- Tool usage patterns
- API call counts
- Token usage estimates

**Usage:**
```python
from amplihack.goal_agent_generator.phase4 import MetricsCollector

# Collect metrics
metrics = MetricsCollector.collect_metrics(trace)

# Calculate percentiles
durations = [m.total_duration_seconds for m in metrics_list]
percentiles = MetricsCollector.calculate_percentiles(durations, [50, 95, 99])

# Aggregate multiple executions
aggregated = MetricsCollector.aggregate_metrics(metrics_list)
```

### 4. PerformanceAnalyzer (`performance_analyzer.py`)

Analyzes execution history to identify patterns and generate insights.

**Analysis Features:**
- Identifies slow phases
- Finds common failure patterns
- Determines optimal phase ordering
- Calculates confidence scores
- Generates actionable recommendations

**Usage:**
```python
from amplihack.goal_agent_generator.phase4 import PerformanceAnalyzer

analyzer = PerformanceAnalyzer(min_sample_size=10)

# Analyze domain performance
insights = analyzer.analyze_domain(traces, "data-processing")

print(f"Sample size: {insights.sample_size}")
print(f"Confidence: {insights.confidence_score}")
for recommendation in insights.recommendations:
    print(f"- {recommendation}")

# Compare before/after optimization
comparison = analyzer.compare_before_after(
    before_traces, after_traces, "security"
)
```

### 5. AdaptationEngine (`adaptation_engine.py`)

Modifies execution plans based on learned patterns.

**Adaptations:**
- Reorders phases for efficiency
- Adjusts duration estimates
- Adds error handling capabilities
- Inserts validation checkpoints
- Optimizes parallel execution

**Usage:**
```python
from amplihack.goal_agent_generator.phase4 import AdaptationEngine

engine = AdaptationEngine(min_confidence=0.5)

# Adapt plan based on insights
adapted_plan = engine.adapt_plan(original_plan, insights)

print(f"Adaptations: {adapted_plan.adaptation_count}")
print(f"Expected improvement: {adapted_plan.expected_improvement}%")

# Create A/B test variants
variants = engine.create_ab_test(original_plan, adapted_plan)

# Decide whether to use adapted plan
if engine.should_use_adapted_plan(insights, risk_tolerance=0.7):
    plan = adapted_plan
```

### 6. PlanOptimizer (`plan_optimizer.py`)

Optimizes plans using historical data from similar executions.

**Optimization Features:**
- Finds similar past executions
- Extracts best practices
- Adjusts estimates based on actuals
- Adds risk factors
- Confidence scoring

**Usage:**
```python
from amplihack.goal_agent_generator.phase4 import PlanOptimizer

optimizer = PlanOptimizer(database)

# Optimize plan
optimized_plan, info = optimizer.optimize_plan(goal, initial_plan)

if info['optimized']:
    print(f"Found {info['similar_count']} similar executions")
    print(f"Confidence: {info['confidence']}")
    for practice in info['best_practices']:
        print(f"- {practice}")

# Get recommendations
recommendations = optimizer.get_recommendations(goal)

# Compare two plans
comparison = optimizer.compare_plans(plan_a, plan_b, goal)
print(f"Recommended: Plan {comparison['recommended']}")
```

### 7. SelfHealingManager (`self_healing_manager.py`)

Detects and recovers from execution failures using learned strategies.

**Recovery Strategies:**
- **Retry**: For transient failures (timeouts, network)
- **Skip**: For non-critical failures
- **Simplify**: For resource exhaustion
- **Escalate**: For permission issues or fatal errors

**Usage:**
```python
from amplihack.goal_agent_generator.phase4 import SelfHealingManager

manager = SelfHealingManager(max_retries=3)

# Detect failure
try:
    execute_phase(phase)
except Exception as error:
    failure_type = manager.detect_failure(trace, phase, error)

    # Generate recovery strategy
    strategy = manager.generate_recovery_strategy(
        trace, phase, failure_type, retry_count=0
    )

    # Execute recovery
    success = manager.execute_recovery(strategy, trace)

    if not success:
        if manager.should_abort_execution(trace, consecutive_failures=3):
            abort_execution()

# Get recovery statistics
stats = manager.get_recovery_statistics()
report = manager.create_recovery_report(trace)
```

## Data Models

All models are defined in `models.py`:

- **ExecutionEvent**: Single event during execution
- **ExecutionTrace**: Complete execution record
- **PhaseMetrics**: Metrics for individual phases
- **ExecutionMetrics**: Aggregated execution metrics
- **PerformanceInsights**: Analysis results and recommendations
- **AdaptedExecutionPlan**: Modified plan with adaptations
- **RecoveryStrategy**: Failure recovery strategy

## Integration Example

Complete learning cycle:

```python
from amplihack.goal_agent_generator.phase4 import (
    ExecutionTracker,
    ExecutionDatabase,
    MetricsCollector,
    PerformanceAnalyzer,
    AdaptationEngine,
    PlanOptimizer,
)

# 1. Track execution
tracker = ExecutionTracker(bundle)
# ... execute agent ...
trace = tracker.complete("Success")

# 2. Store in database
db = ExecutionDatabase()
db.store_trace(trace)
metrics = MetricsCollector.collect_metrics(trace)
db.store_metrics(trace.execution_id, metrics)

# 3. Analyze performance periodically
traces = [db.get_trace(e["execution_id"]) for e in db.query_by_domain("security")]
analyzer = PerformanceAnalyzer()
insights = analyzer.analyze_domain(traces, "security")

# 4. Optimize future plans
optimizer = PlanOptimizer(db)
optimized_plan, info = optimizer.optimize_plan(goal, initial_plan)

# 5. Adapt based on insights
engine = AdaptationEngine()
adapted_plan = engine.adapt_plan(optimized_plan, insights)

# 6. Use improved plan
if engine.should_use_adapted_plan(insights):
    final_plan = adapted_plan
```

## Testing

Comprehensive test suite in `tests/phase4/`:

```bash
# Run all Phase 4 tests
pytest src/amplihack/goal_agent_generator/tests/phase4/

# Run specific test modules
pytest src/amplihack/goal_agent_generator/tests/phase4/test_execution_tracker.py
pytest src/amplihack/goal_agent_generator/tests/phase4/test_performance_analyzer.py
pytest src/amplihack/goal_agent_generator/tests/phase4/test_phase4_integration.py
```

## Performance Characteristics

- **Database**: SQLite for simplicity, can handle 10k+ executions
- **Query Performance**: < 100ms for typical queries
- **Retention**: 30-day automatic cleanup
- **Analysis**: O(n) complexity for most operations
- **Memory**: Streams data, minimal memory footprint

## Configuration

Environment variables:

```bash
# Database path
EXECUTION_DB_PATH=./execution_history.db

# Trace storage
TRACE_OUTPUT_DIR=./traces

# Analysis settings
MIN_SAMPLE_SIZE=10
MIN_CONFIDENCE=0.5

# Self-healing settings
MAX_RETRIES=3
RETENTION_DAYS=30
```

## Best Practices

1. **Track Everything**: Enable tracking for all agent executions
2. **Analyze Regularly**: Run analysis weekly or after 20+ executions
3. **Start Conservative**: Use low risk tolerance initially
4. **Monitor Adaptations**: Track adapted plan performance
5. **Review Insights**: Human review of recommendations before applying
6. **Clean Old Data**: Run cleanup monthly
7. **A/B Test Changes**: Compare original vs adapted plans

## Future Enhancements

- PostgreSQL support for production scale
- Real-time streaming analytics
- Machine learning for pattern detection
- Cross-domain learning
- Distributed tracing support
- Advanced A/B testing framework
- Automated rollback on regression

## Philosophy: Ruthless Simplicity

Phase 4 follows the "zero-BS" principle:

- SQLite for MVP (no complex database setup)
- Basic statistics (no ML overkill)
- Graceful degradation (works without historical data)
- Every function works (no placeholders)
- Clear contracts (input/output well-defined)

## Success Metrics

- **Coverage**: 95%+ test coverage
- **Reliability**: All tests pass
- **Performance**: < 1s for analysis of 100 executions
- **Improvement**: 10-30% reduction in execution time
- **Success Rate**: 10-20% improvement in completion rate
- **Recovery**: 70%+ automatic recovery from transient failures
