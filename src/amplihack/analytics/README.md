# Analytics Module

Subagent execution tracking and visualization for Amplihack.

## Overview

The analytics module provides tools to analyze subagent metrics, visualize execution patterns, detect performance issues, and generate comprehensive reports. It reads JSONL metrics files and builds execution trees with pattern detection.

## Features

- **JSONL Metrics Parsing**: Read and parse `subagent_start.jsonl` and `subagent_stop.jsonl` files
- **Execution Tree Building**: Build hierarchical agent execution trees
- **ASCII Art Visualization**: Generate ASCII art trees for terminal output
- **Pattern Detection**: Detect correlations, bottlenecks, and common sequences
- **Multiple Output Formats**: Text and JSON report generation
- **Performance Statistics**: Detailed agent execution statistics
- **CLI Interface**: Comprehensive command-line tool

## Installation

The analytics module is part of the Amplihack package:

```bash
pip install amplihack
```

## Usage

### CLI Tool

The primary interface is the command-line tool:

```bash
# Analyze current session
amplihack subagent-mapper

# Analyze specific session
amplihack subagent-mapper --session-id 20251102_143022

# Filter by agent
amplihack subagent-mapper --agent architect

# Export as JSON
amplihack subagent-mapper --output json

# Show performance statistics
amplihack subagent-mapper --stats

# List all available sessions
amplihack subagent-mapper --list-sessions

# Use custom metrics directory
amplihack subagent-mapper --metrics-dir /path/to/metrics
```

### Python API

Use the analytics module programmatically:

```python
from amplihack.analytics import MetricsReader, ReportGenerator

# Initialize reader
reader = MetricsReader()

# Get latest session
session_id = reader.get_latest_session_id()

# Build executions
executions = reader.build_executions(session_id=session_id)

# Generate report
generator = ReportGenerator(reader)
report = generator.generate_text_report(session_id=session_id)
print(report)

# Generate JSON report
json_report = generator.generate_json_report(session_id=session_id)
```

### Reading Metrics

```python
from amplihack.analytics import MetricsReader

reader = MetricsReader()

# Read all events
events = reader.read_events()

# Filter by session
events = reader.read_events(session_id="20251102_143022")

# Filter by event type
start_events = reader.read_events(event_type="start")
stop_events = reader.read_events(event_type="stop")

# Build complete executions (matched start/stop pairs)
executions = reader.build_executions()

# Get statistics
stats = reader.get_agent_stats(session_id="20251102_143022")
print(f"Total executions: {stats['total_executions']}")
print(f"Total duration: {stats['total_duration_ms'] / 1000}s")
```

### Building Execution Trees

```python
from amplihack.analytics import ExecutionTreeBuilder, AsciiTreeRenderer

# Build tree from executions
builder = ExecutionTreeBuilder(executions)
tree = builder.build()

# Render as ASCII art
renderer = AsciiTreeRenderer()
ascii_tree = renderer.render(tree)
print(ascii_tree)
```

### Pattern Detection

```python
from amplihack.analytics import PatternDetector

# Detect patterns
detector = PatternDetector(executions)
patterns = detector.detect_all()

for pattern in patterns:
    print(f"{pattern.pattern_type}: {pattern.description}")
    print(f"  Confidence: {pattern.confidence:.2%}")
    print(f"  Agents: {', '.join(pattern.agents)}")
```

## Output Examples

### Text Report

```
Subagent Execution Map - Session: 20251102_143022
================================================================

Agent Invocation Tree:
orchestrator
  ├─ architect (2 invocations, 45.0s total)
  │   └─ analyzer (1 invocation, 12.0s)
  ├─ builder (3 invocations, 120.0s total)
  │   ├─ reviewer (2 invocations, 30.0s)
  │   └─ tester (1 invocation, 15.0s)
  └─ ci-diagnostic (1 invocation, 60.0s)

Performance Summary:
  Total agents invoked: 8
  Total execution time: 282.0s
  Most used agent: builder (3 times)

Patterns Detected:
  - architect → analyzer (100% correlation)
```

### JSON Report

```json
{
  "session_id": "20251102_143022",
  "executions": [
    {
      "agent_name": "architect",
      "parent_agent": "orchestrator",
      "start_time": "2025-11-02T14:30:00+00:00",
      "duration_seconds": 45.0,
      "execution_id": "exec_001"
    }
  ],
  "tree": [
    {
      "name": "orchestrator",
      "invocation_count": 1,
      "total_duration_seconds": 282.0,
      "children": [...]
    }
  ],
  "stats": {
    "total_executions": 8,
    "total_duration_ms": 282000.0,
    "avg_duration_ms": 35250.0,
    "agents": {
      "architect": 2,
      "builder": 3
    }
  },
  "patterns": [
    {
      "type": "correlation",
      "description": "architect → analyzer (100% correlation)",
      "confidence": 1.0,
      "agents": ["architect", "analyzer"]
    }
  ]
}
```

## Module Structure

```
analytics/
├── __init__.py                  # Public API
├── README.md                    # This file
├── metrics_reader.py            # JSONL parsing and metrics reading
├── visualization.py             # Tree building and pattern detection
├── subagent_mapper.py           # CLI tool
└── tests/
    ├── __init__.py
    ├── test_metrics_reader.py   # 12 tests
    ├── test_visualization.py    # 8 tests
    └── test_subagent_mapper.py  # 15 tests
```

## Public API

### Core Classes

- **MetricsReader**: Read and parse JSONL metrics files
- **SubagentEvent**: Single subagent execution event (start or stop)
- **SubagentExecution**: Complete execution record (matched start/stop pair)

### Visualization

- **ReportGenerator**: Generate text and JSON reports
- **ExecutionTreeBuilder**: Build agent execution trees
- **PatternDetector**: Detect execution patterns
- **AsciiTreeRenderer**: Render trees as ASCII art
- **AgentNode**: Node in execution tree
- **Pattern**: Detected execution pattern

### CLI

- **main**: CLI entry point

## Pattern Types

### Correlation Patterns

Detects agent pairs that frequently execute together (≥80% correlation):

```
architect → analyzer (100% correlation)
```

### Bottleneck Patterns

Identifies agents with unusually long execution times (>2x mean):

```
slow_agent averages 55.0s (5.5x slower than mean)
```

### Sequence Patterns

Finds common agent execution sequences:

```
Common sequence: orchestrator → architect → builder (appears 5 times)
```

## Performance

- **Report Generation**: < 0.01s for 100 executions (< 3s requirement)
- **Memory Efficient**: Streams JSONL files line-by-line
- **Scalable**: Handles thousands of executions efficiently

## Metrics File Format

The module reads JSONL files from `.claude/runtime/metrics/`:

### subagent_start.jsonl

```json
{
  "event": "start",
  "agent_name": "architect",
  "session_id": "20251102_143022",
  "timestamp": "2025-11-02T14:30:00.000Z",
  "parent_agent": "orchestrator",
  "execution_id": "exec_001"
}
```

### subagent_stop.jsonl

```json
{
  "event": "stop",
  "agent_name": "architect",
  "session_id": "20251102_143022",
  "timestamp": "2025-11-02T14:30:45.000Z",
  "execution_id": "exec_001",
  "duration_ms": 45000.0
}
```

## Testing

Run the test suite:

```bash
# Run all tests
pytest src/amplihack/analytics/tests/

# Run specific test file
pytest src/amplihack/analytics/tests/test_metrics_reader.py -v

# Run with coverage
pytest src/amplihack/analytics/tests/ --cov=src/amplihack/analytics

# Run performance test
python test_performance.py
```

Test coverage:

- **test_metrics_reader.py**: 12 tests covering JSONL parsing, event handling, and statistics
- **test_visualization.py**: 8 tests covering tree building, ASCII rendering, and pattern detection
- **test_subagent_mapper.py**: 15 tests covering CLI interface and argument parsing

Total: 35 tests (60% unit, 30% integration, 10% E2E)

## Dependencies

- Python 3.8+
- Standard library only (no external dependencies)
- pytest (for testing only)

## Error Handling

The module gracefully handles:

- **Missing metrics files**: Returns empty results
- **Malformed JSONL**: Skips invalid lines
- **Incomplete executions**: Handles orphaned start/stop events
- **Missing timestamps**: Uses current time as fallback

## Future Enhancements

Potential future features:

- [ ] HTML report generation with interactive visualizations
- [ ] Real-time monitoring mode
- [ ] Metrics aggregation across multiple sessions
- [ ] Performance trend analysis
- [ ] Export to external analytics platforms
- [ ] Custom pattern detection rules

## Contributing

When contributing to the analytics module:

1. Follow the project's philosophy (ruthless simplicity, zero-BS)
2. Add tests for all new functionality
3. Update README with usage examples
4. Verify performance requirements (< 3s for report generation)
5. Ensure all code is self-contained and regeneratable

## License

Part of the Amplihack framework (Microsoft Hackathon 2025).
