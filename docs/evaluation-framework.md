# Memory Backend Evaluation Framework

This document explains how to evaluate and compare memory backends fer quality, performance, and reliability.

## Overview

The evaluation framework measures backends across three dimensions:

1. **Quality Metrics**: How relevant are retrieved memories?
   - Relevance scoring (0-1)
   - Precision (% retrieved that are relevant)
   - Recall (% of relevant retrieved)
   - NDCG (ranking quality)

2. **Performance Metrics**: How fast is the backend?
   - Storage latency (ms)
   - Retrieval latency (ms)
   - Throughput (operations/second)
   - Scalability (performance vs database size)

3. **Reliability Metrics**: How robust is the backend?
   - Data integrity (can retrieve what was stored?)
   - Concurrent safety (multi-thread safe?)
   - Error recovery (handles failures gracefully?)

## Quick Start

### Using the CLI

```bash
# Compare all backends
amplihack memory evaluate

# Evaluate specific backend
amplihack memory evaluate --backend sqlite

# Save report to file
amplihack memory evaluate --output report.md

# Custom database path
amplihack memory evaluate --backend sqlite --db-path /tmp/memory.db
```

### Using Python API

```python
import asyncio
from amplihack.memory.evaluation import run_evaluation

# Evaluate all backends
async def main():
    report = await run_evaluation()
    print(report)

asyncio.run(main())
```

## Detailed Usage

### Quality Evaluation

Measures retrieval quality using test queries with ground truth:

```python
from amplihack.memory.backends import create_backend
from amplihack.memory.coordinator import MemoryCoordinator
from amplihack.memory.evaluation import QualityEvaluator

# Create coordinator
backend = create_backend(backend_type="sqlite")
coordinator = MemoryCoordinator(backend=backend)

# Create evaluator
evaluator = QualityEvaluator(coordinator)

# Create test set (50 memories, 3+ queries)
test_queries = await evaluator.create_test_set(num_memories=50)

# Run evaluation
metrics = await evaluator.evaluate(test_queries)

print(f"Precision: {metrics.precision:.2f}")
print(f"Recall: {metrics.recall:.2f}")
print(f"NDCG: {metrics.ndcg_score:.2f}")
```

**Quality Metrics Explained:**

- **Relevance**: Average relevance of retrieved memories (0-1)
  - Higher is better
  - 0.8+ is excellent

- **Precision**: What % of retrieved memories are relevant?
  - Few false positives = high precision
  - 0.7+ is good

- **Recall**: What % of relevant memories were retrieved?
  - Few false negatives = high recall
  - 0.7+ is good

- **NDCG**: Are most relevant memories ranked first?
  - 1.0 = perfect ranking
  - 0.8+ is excellent

### Performance Evaluation

Measures speed and throughput:

```python
from amplihack.memory.evaluation import PerformanceEvaluator

evaluator = PerformanceEvaluator(coordinator)

# Run benchmark (100 operations)
metrics = await evaluator.evaluate(num_operations=100)

print(f"Storage: {metrics.storage_latency_ms:.2f}ms")
print(f"Retrieval: {metrics.retrieval_latency_ms:.2f}ms")
print(f"Throughput: {metrics.storage_throughput:.1f} ops/sec")

# Check performance contracts
contracts = evaluator.check_performance_contracts(metrics)
if contracts["storage_latency_ok"]:
    print("✅ Storage meets <500ms contract")
if contracts["retrieval_latency_ok"]:
    print("✅ Retrieval meets <50ms contract")
```

**Performance Contracts:**

- Storage: Must complete under 500ms
- Retrieval: Must complete under 50ms
- Storage throughput: At least 2 operations/second
- Retrieval throughput: At least 20 queries/second

**Scalability Testing:**

```python
# Test at multiple scales
results = await evaluator.evaluate_scalability(scales=[100, 1000, 10000])

for scale, metrics in results.items():
    print(f"Scale {scale}:")
    print(f"  Storage: {metrics.storage_latency_ms:.2f}ms")
    print(f"  Retrieval: {metrics.retrieval_latency_ms:.2f}ms")
```

### Reliability Evaluation

Measures robustness and data integrity:

```python
from amplihack.memory.evaluation import ReliabilityEvaluator

evaluator = ReliabilityEvaluator(coordinator)

# Run stress tests
metrics = await evaluator.evaluate()

print(f"Data Integrity: {metrics.data_integrity_score:.2f}")
print(f"Concurrent Safety: {metrics.concurrent_safety_score:.2f}")
print(f"Error Recovery: {metrics.error_recovery_score:.2f}")
```

**Reliability Metrics Explained:**

- **Data Integrity**: Can retrieve what was stored?
  - Tests special characters, unicode, long text
  - 0.95+ is excellent

- **Concurrent Safety**: Multi-thread safe?
  - Tests 10 concurrent operations
  - 0.9+ is excellent

- **Error Recovery**: Handles failures gracefully?
  - Tests invalid IDs, empty queries, etc.
  - 0.8+ is good

### Backend Comparison

Compare multiple backends:

```python
from amplihack.memory.evaluation import BackendComparison

comparison = BackendComparison()

# Evaluate multiple backends
await comparison.evaluate_backend("sqlite")
await comparison.evaluate_backend("kuzu")

# Generate report
report = comparison.generate_markdown_report()
print(report)
```

## Interpreting Results

### Overall Score

The overall score (0-1) is a weighted average:

- Quality: 40% (most important - are results relevant?)
- Performance: 30% (is it fast enough?)
- Reliability: 30% (is it robust?)

**Score Interpretation:**

- 0.8+ : Excellent
- 0.6-0.8 : Good
- 0.4-0.6 : Acceptable
- <0.4 : Needs improvement

### Use Case Recommendations

The framework generates recommendations based on metrics:

**High Quality (precision/recall > 0.8)**:

- Good for knowledge-intensive tasks
- Use when retrieval accuracy is critical

**High Performance (latency < 50ms)**:

- Good for real-time queries
- Use when response time is critical

**High Reliability (integrity > 0.95)**:

- Good for critical data
- Use when data loss is unacceptable

### Backend Comparison

**SQLite**:

- Pros: Fast, reliable, simple deployment
- Cons: Single-process only, no graph queries
- Best for: Simple deployments, single-user systems

**Kùzu**:

- Pros: Graph queries, relationship traversal
- Cons: More complex setup, newer technology
- Best for: Complex relationships, graph analytics

**Neo4j**:

- Pros: Large-scale analytics, multi-user access
- Cons: Requires separate server, more overhead
- Best for: Production systems, distributed access

## Example Reports

See `examples/evaluate_backends.py` for complete working examples.

Sample output:

```
=== Performance Evaluation ===

Backend: sqlite
Storage Latency: 0.49ms ✅
Retrieval Latency: 0.75ms ✅
Storage Throughput: 2030.8 ops/sec
Retrieval Throughput: 1340.0 ops/sec

Performance Contracts:
  ✅ storage_latency_ok
  ✅ retrieval_latency_ok
  ✅ storage_throughput_ok
  ✅ retrieval_throughput_ok
```

## API Reference

### QualityEvaluator

```python
class QualityEvaluator:
    async def evaluate(test_queries: list[QueryTestCase]) -> QualityMetrics
    async def create_test_set(num_memories: int) -> list[QueryTestCase]
```

### PerformanceEvaluator

```python
class PerformanceEvaluator:
    async def evaluate(num_operations: int) -> PerformanceMetrics
    async def evaluate_scalability(scales: list[int]) -> dict[int, PerformanceMetrics]
    def check_performance_contracts(metrics: PerformanceMetrics) -> dict[str, bool]
```

### ReliabilityEvaluator

```python
class ReliabilityEvaluator:
    async def evaluate() -> ReliabilityMetrics
```

### BackendComparison

```python
class BackendComparison:
    async def evaluate_backend(backend_type: str, **config) -> ComparisonReport
    async def compare_all() -> dict[str, ComparisonReport]
    def generate_markdown_report() -> str
```

### Convenience Function

```python
async def run_evaluation(backend_type: str | None = None, **config) -> str
```

## Philosophy

The evaluation framework follows amplihack's core philosophy:

- **Evidence-based**: Real benchmark data, not guesswork
- **Comprehensive**: All three evaluation dimensions
- **Fair comparison**: Same test data for all backends
- **Actionable**: Clear recommendations for use cases
- **Zero-BS**: All metrics measure real behavior

## Next Steps

1. Run evaluations on your backends
2. Compare results across different configurations
3. Choose the backend that fits your use case
4. Document your decision and tradeoffs
