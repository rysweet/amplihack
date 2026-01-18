# Example: Data Pipeline with Goal-Seeking Agents

## Scenario: Multi-Source Data Pipeline Automation

### Problem Statement

Manual data pipeline operations are:

- **Labor-intensive**: 2-3 hours to collect, transform, validate, and publish data
- **Source-dependent**: Different ingestion strategies for S3, databases, APIs
- **Fragile**: Source unavailability breaks entire pipeline
- **Quality-risky**: Data quality issues discovered late (after publishing)
- **Non-idempotent**: Re-running after failures causes duplicates

### Is Goal-Seeking Appropriate?

Apply the 5-question decision framework:

**Q1: Well-defined objective but flexible path?**

- **YES**: Objective is clear (ingest, transform, validate, publish data)
- Multiple paths:
  - All sources available: Parallel collection
  - Some sources unavailable: Partial collection with logging
  - Quality issues: Iterative cleansing
- Success criteria: Data in warehouse, quality thresholds met

**Q2: Multiple phases with dependencies?**

- **YES**: 4 phases with clear dependencies
  1. Data Collection (parallel: S3, database, API)
  2. Data Transformation (depends on collection)
  3. Quality Validation (depends on transformation)
  4. Data Publishing (depends on validation)

**Q3: Autonomous recovery valuable?**

- **YES**: Failures are common and recoverable
  - Source timeouts: Retry with backoff
  - Transformation errors: Log and skip bad records
  - Quality failures: Apply automated cleansing
  - Publishing errors: Retry with exponential backoff

**Q4: Context affects approach?**

- **YES**: Strategy varies by:
  - Data volume (100K vs 10M records)
  - Source availability (all vs partial)
  - Quality requirements (strict vs lenient)
  - Time constraints (daily batch vs real-time)

**Q5: Complexity justified?**

- **YES**: High-value automation
  - Frequency: Daily (365 times per year)
  - Manual time: 2-3 hours per run
  - Value: 730-1095 hours saved per year
  - Risk reduction: Fewer human errors

**Conclusion**: All 5 YES → Goal-seeking agent is appropriate

## Goal-Seeking Agent Design

### Goal Definition

```markdown
# Goal: Automate Multi-Source Data Pipeline

## Objective

Collect data from multiple sources (S3 buckets, PostgreSQL database, REST API),
transform to common schema, validate quality, and publish to data warehouse.

## Success Criteria

- All available sources successfully ingested (100% success or logged failures)
- Data transformed to target schema with < 2% transformation failure rate
- Quality checks pass: completeness ≥ 95%, accuracy ≥ 98%, consistency = 100%
- Data published to warehouse without duplicates
- Pipeline completes within 30 minutes

## Constraints

- Must handle source unavailability gracefully (log and continue)
- No data loss (failed records logged for manual review)
- Idempotent (safe to re-run without duplicates)
- Resource limits: 8GB RAM, 4 CPU cores
- Must preserve data lineage (track source → warehouse)

## Context

- Frequency: Daily (automated at 2 AM)
- Priority: High (blocking downstream analytics)
- Scale: Medium (100K-1M records per source)
- Sources: 3 (S3, PostgreSQL, REST API)
```

### Execution Plan

```python
from amplihack.goal_agent_generator import PromptAnalyzer, ObjectivePlanner

analyzer = PromptAnalyzer()
goal_def = analyzer.analyze_text(goal_text)

planner = ObjectivePlanner()
execution_plan = planner.generate_plan(goal_def)

# Result: 4-phase plan with parallel collection
```

**Phase 1: Data Collection** (15 minutes, parallel-safe)

- Collect from S3 (100K-500K records, parallel)
- Collect from PostgreSQL (50K-200K records, parallel)
- Collect from REST API (10K-100K records, parallel)
- Handle source failures gracefully
- Log collection metrics

Dependencies: None (all sources collected in parallel)
Success indicators:

- All sources attempted
- Successful collections logged
- Failed collections logged with reason
- Raw data stored in staging area

**Phase 2: Data Transformation** (15 minutes, depends on Phase 1)

- Parse raw data formats (JSON, CSV, Parquet)
- Transform to common schema
- Handle missing fields (apply defaults)
- Normalize data types
- Enrich with metadata

Dependencies: Phase 1 (needs collected data)
Success indicators:

- All records attempted transformation
- Success rate ≥ 98%
- Failed records logged
- Transformed data in staging schema

**Phase 3: Quality Validation** (5 minutes, depends on Phase 2)

- Completeness check (required fields present)
- Accuracy validation (data types, ranges, formats)
- Consistency verification (referential integrity)
- Duplicate detection
- Anomaly detection

Dependencies: Phase 2 (needs transformed data)
Success indicators:

- Completeness ≥ 95%
- Accuracy ≥ 98%
- Consistency = 100%
- Duplicates identified and removed
- Anomalies flagged

**Phase 4: Data Publishing** (10 minutes, depends on Phase 3)

- Load to data warehouse (bulk insert)
- Update metadata tables
- Create data lineage records
- Generate quality report
- Archive raw data

Dependencies: Phase 3 (only publish validated data)
Success indicators:

- All validated data in warehouse
- No duplicates
- Metadata updated
- Lineage tracked
- Report generated

**Total Duration**: 45 minutes (estimated with overhead)

### Implementation

```python
from amplihack.goal_agent_generator import (
    PromptAnalyzer,
    ObjectivePlanner,
    SkillSynthesizer,
    AgentAssembler,
    GoalAgentPackager,
)
from pathlib import Path
import asyncio
from datetime import datetime
from typing import List, Dict, Any

# Goal definition
goal_text = """
Automate multi-source data pipeline:
- Collect from S3, PostgreSQL, REST API (parallel)
- Transform to common schema
- Validate quality (completeness, accuracy, consistency)
- Publish to data warehouse
Handle source failures gracefully, ensure idempotency.
"""

# Create agent
analyzer = PromptAnalyzer()
goal_def = analyzer.analyze_text(goal_text)

planner = ObjectivePlanner()
execution_plan = planner.generate_plan(goal_def)

synthesizer = SkillSynthesizer()
skills = synthesizer.synthesize(execution_plan)

assembler = AgentAssembler()
agent_bundle = assembler.assemble(
    goal_definition=goal_def,
    execution_plan=execution_plan,
    skills=skills,
    bundle_name="multi-source-data-pipeline"
)

packager = GoalAgentPackager()
packager.package(
    bundle=agent_bundle,
    output_dir=Path(".claude/agents/goal-driven/data-pipeline")
)
```

### Adaptive Behavior

The agent adapts to different conditions:

**Scenario 1: All Sources Available** (optimal path)

```python
async def collect_all_sources():
    """Parallel collection when all sources available"""
    results = await asyncio.gather(
        collect_from_s3(),
        collect_from_postgresql(),
        collect_from_api(),
        return_exceptions=True  # Don't fail if one source fails
    )

    collected_data = []
    for source, result in zip(["S3", "PostgreSQL", "API"], results):
        if isinstance(result, Exception):
            log_source_failure(source, result)
        else:
            collected_data.append(result)

    return collected_data
```

**Scenario 2: Source Unavailable** (graceful degradation)

```python
async def collect_from_api_with_fallback():
    """Handle API unavailability"""
    try:
        # Try primary API endpoint
        data = await fetch_from_api(primary_endpoint)
        return data
    except ConnectionError:
        try:
            # Try fallback endpoint
            log_warning("Primary API unavailable, trying fallback")
            data = await fetch_from_api(fallback_endpoint)
            return data
        except ConnectionError:
            # Log failure and continue with partial data
            log_error("API completely unavailable")
            send_alert("Data pipeline: API source unavailable")
            return None  # Continue with S3 and PostgreSQL data
```

**Scenario 3: Large Data Volume** (resource optimization)

```python
def transform_data_adaptive(data: List[Dict], volume: int):
    """Adapt transformation strategy based on volume"""
    if volume < 100_000:
        # Small volume: In-memory transformation
        return transform_in_memory(data)
    elif volume < 1_000_000:
        # Medium volume: Chunked processing
        return transform_in_chunks(data, chunk_size=10_000)
    else:
        # Large volume: Distributed processing
        return transform_distributed(data, num_workers=4)
```

**Scenario 4: Quality Issues** (iterative cleansing)

```python
def validate_and_cleanse(data: List[Dict]) -> List[Dict]:
    """Iterative quality improvement"""
    quality_score = calculate_quality(data)

    while quality_score < QUALITY_THRESHOLD:
        # Apply automated cleansing
        data = apply_cleansing_rules(data)

        # Recalculate quality
        quality_score = calculate_quality(data)

        if cleansing_iterations >= MAX_ITERATIONS:
            # Escalate if can't meet quality threshold
            escalate(
                reason="Quality threshold not met after cleansing",
                current_quality=quality_score,
                threshold=QUALITY_THRESHOLD,
                recommendation="Manual data review required"
            )
            break

    return data
```

### Error Recovery Strategies

**Strategy 1: Retry with Exponential Backoff** (transient errors)

```python
import time
from typing import Callable, Any

def retry_with_backoff(
    func: Callable[[], Any],
    max_attempts: int = 3,
    initial_delay: float = 1.0
) -> Any:
    """Retry function with exponential backoff"""
    for attempt in range(max_attempts):
        try:
            return func()
        except (ConnectionError, TimeoutError) as e:
            if attempt == max_attempts - 1:
                raise  # Last attempt, re-raise

            delay = initial_delay * (2 ** attempt)
            log_warning(f"Attempt {attempt + 1} failed, retrying in {delay}s")
            time.sleep(delay)

# Usage
s3_data = retry_with_backoff(
    lambda: collect_from_s3(),
    max_attempts=3,
    initial_delay=2.0
)
```

**Strategy 2: Partial Success** (continue with available data)

```python
def handle_partial_collection(results: List[Any]) -> Dict[str, Any]:
    """Process partial collection results"""
    successful_sources = [r for r in results if r is not None]
    failed_sources = [i for i, r in enumerate(results) if r is None]

    if not successful_sources:
        escalate("All data sources failed, cannot proceed")

    if failed_sources:
        log_warning(f"Partial collection: {len(successful_sources)}/{len(results)} sources")
        send_alert(f"Data pipeline: {len(failed_sources)} sources unavailable")

    # Continue with available data
    return {
        "data": successful_sources,
        "partial": len(failed_sources) > 0,
        "failed_sources": failed_sources
    }
```

**Strategy 3: Idempotent Execution** (safe re-runs)

```python
def publish_to_warehouse_idempotent(data: List[Dict], run_id: str):
    """Ensure idempotent publishing (no duplicates on re-run)"""
    # Check if this run already succeeded
    if check_run_completed(run_id):
        log_info(f"Run {run_id} already completed, skipping")
        return

    # Use transaction for atomicity
    with warehouse_transaction() as txn:
        # Delete any partial data from previous failed runs
        txn.execute(f"DELETE FROM target_table WHERE run_id = '{run_id}'")

        # Insert new data with run_id
        for record in data:
            record["run_id"] = run_id
            record["ingested_at"] = datetime.utcnow()
            txn.insert("target_table", record)

        # Mark run as completed
        txn.insert("pipeline_runs", {
            "run_id": run_id,
            "status": "completed",
            "record_count": len(data),
            "completed_at": datetime.utcnow()
        })

        txn.commit()
```

### Execution Example

```
Multi-Source Data Pipeline: Starting (run_id: 20251116_020000)

Phase 1: Data Collection [In Progress]
├── S3 Collection (parallel)...
│   ├── Bucket: data-lake/raw/2025/11/16
│   ├── Files: 15 Parquet files
│   └── Records: 250,000
│   └── Duration: 8 minutes
│   └── ✓ COMPLETED
├── PostgreSQL Collection (parallel)...
│   ├── Table: transactions_2025_11_16
│   ├── Query: SELECT * WHERE date = '2025-11-16'
│   └── Records: 75,000
│   └── Duration: 6 minutes
│   └── ✓ COMPLETED
└── API Collection (parallel)...
    ├── Endpoint: https://api.example.com/events?date=2025-11-16
    ├── Attempt 1: ✗ Timeout
    ├── Retry in 2s...
    ├── Attempt 2: ✓ Success
    └── Records: 15,000
    └── Duration: 4 minutes (1 retry)
    └── ✓ COMPLETED

Phase 1: ✓ COMPLETED
- Total records: 340,000
- Sources: 3/3 successful (1 retry)
- Duration: 10 minutes (parallel execution)

Phase 2: Data Transformation [In Progress]
├── Parsing formats...
│   ├── S3 (Parquet): ✓ 250,000 records parsed
│   ├── PostgreSQL (JSON): ✓ 75,000 records parsed
│   └── API (JSON): ✓ 15,000 records parsed
├── Schema transformation...
│   ├── Field mapping: ✓ All fields mapped
│   ├── Type conversion: ✓ Completed (12 type conversions)
│   ├── Default values: ✓ Applied to 2,500 records (0.7%)
│   └── Success rate: 98.5% (5,100 failures logged)
├── Data enrichment...
│   └── Metadata added: source, ingestion_time, run_id
└── Staging schema...
    └── ✓ 334,900 records in staging

Phase 2: ✓ COMPLETED
- Total transformed: 334,900 / 340,000 (98.5%)
- Failed transformations: 5,100 (logged to failed_records.log)
- Duration: 14 minutes

Phase 3: Quality Validation [In Progress]
├── Completeness check...
│   ├── Required fields: user_id, event_type, timestamp, amount
│   ├── Missing fields: 3,200 records (0.96%)
│   ├── Completeness: 99.04% ✓ (threshold: 95%)
│   └── ✓ PASS
├── Accuracy check...
│   ├── Data type validation: ✓ 100% correct types
│   ├── Range validation: ✗ 1,500 records out of range
│   │   └── Applying automated correction...
│   │   └── ✓ 1,200 corrected, 300 flagged
│   ├── Format validation: ✓ 100% correct formats
│   └── Accuracy: 99.91% ✓ (threshold: 98%)
├── Consistency check...
│   ├── Referential integrity: ✓ 100%
│   ├── No orphan records: ✓ Verified
│   └── ✓ PASS
├── Duplicate detection...
│   ├── Duplicate records found: 1,800
│   └── ✓ Duplicates removed
└── Anomaly detection...
    ├── Statistical outliers: 250 flagged
    └── ✓ Flagged for review

Phase 3: ✓ COMPLETED
- Final record count: 333,100 (after deduplication)
- Completeness: 99.04% ✓
- Accuracy: 99.91% ✓
- Consistency: 100% ✓
- Duration: 5 minutes

Phase 4: Data Publishing [In Progress]
├── Warehouse load...
│   ├── Target: warehouse.analytics.events
│   ├── Method: Bulk insert (batch size: 10,000)
│   ├── Records: 333,100
│   └── Duration: 6 minutes
│   └── ✓ COMPLETED
├── Metadata update...
│   ├── Table: pipeline_metadata
│   ├── Run ID: 20251116_020000
│   └── ✓ COMPLETED
├── Data lineage...
│   ├── Source → Warehouse mapping created
│   ├── Lineage records: 3 (S3, PostgreSQL, API)
│   └── ✓ COMPLETED
├── Quality report...
│   ├── File: reports/quality_20251116_020000.html
│   ├── Summary: 333,100 records published, 5,100 transformation failures
│   └── ✓ COMPLETED
└── Archive raw data...
    ├── Location: archive/2025/11/16/
    └── ✓ COMPLETED

Phase 4: ✓ COMPLETED (9 minutes)

Pipeline Execution: ✓ SUCCESS (38 minutes total)

Summary Report:
┌──────────────────────────────────────────────────────────────┐
│ Multi-Source Data Pipeline - Execution Summary               │
├──────────────────────────────────────────────────────────────┤
│ Run ID: 20251116_020000                                      │
│ Status: SUCCESS                                              │
│ Duration: 38 minutes                                         │
│                                                              │
│ Data Collection:                                             │
│ - S3: 250,000 records (8 min)                               │
│ - PostgreSQL: 75,000 records (6 min)                        │
│ - API: 15,000 records (4 min, 1 retry)                      │
│ - Total: 340,000 records                                     │
│                                                              │
│ Data Transformation:                                         │
│ - Transformed: 334,900 records (98.5%)                       │
│ - Failed: 5,100 records (1.5%, logged)                      │
│                                                              │
│ Quality Validation:                                          │
│ - Completeness: 99.04% ✓                                     │
│ - Accuracy: 99.91% ✓                                         │
│ - Consistency: 100% ✓                                        │
│ - Duplicates: 1,800 removed                                  │
│                                                              │
│ Data Publishing:                                             │
│ - Warehouse: 333,100 records                                 │
│ - Metadata: Updated                                          │
│ - Lineage: Tracked                                           │
│ - Report: Generated                                          │
│                                                              │
│ Issues:                                                      │
│ - API timeout (1 retry, resolved)                           │
│ - 5,100 transformation failures (logged)                     │
│ - 300 out-of-range values (flagged)                         │
│ - 250 anomalies (flagged for review)                        │
│                                                              │
│ Next Steps:                                                  │
│ - Review failed transformations (failed_records.log)         │
│ - Investigate out-of-range values                           │
│ - Review anomalies for false positives                      │
└──────────────────────────────────────────────────────────────┘
```

### Failure Scenario: Source Completely Unavailable

```
Phase 1: Data Collection [In Progress]
├── S3 Collection... ✓ COMPLETED (250,000 records, 8 min)
├── PostgreSQL Collection... ✓ COMPLETED (75,000 records, 6 min)
└── API Collection...
    ├── Attempt 1: ✗ Connection refused
    ├── Retry in 2s...
    ├── Attempt 2: ✗ Connection refused
    ├── Retry in 4s...
    ├── Attempt 3: ✗ Connection refused
    └── ✗ FAILED (all retries exhausted)
        └── Logging failure: API unavailable
        └── Sending alert: Data pipeline - API source down
        └── Continuing with partial data (S3 + PostgreSQL)

Phase 1: ⚠ COMPLETED WITH WARNINGS
- Total records: 325,000 (2/3 sources)
- Failed sources: API (connection refused)
- Duration: 10 minutes

[Pipeline continues with S3 + PostgreSQL data]

Summary Report:
┌──────────────────────────────────────────────────────────────┐
│ ⚠ PARTIAL SUCCESS                                            │
│                                                              │
│ Data collected from 2/3 sources (API unavailable)           │
│ Published: 318,500 records                                   │
│ Missing: ~15,000 records (API source)                       │
│                                                              │
│ Action Required:                                             │
│ - Investigate API connectivity                               │
│ - Re-run pipeline for API data once resolved                │
│ - Command: amplihack goal-agent-generator execute \         │
│            --agent data-pipeline \                           │
│            --source-filter API \                             │
│            --date 2025-11-16                                 │
└──────────────────────────────────────────────────────────────┘
```

## Lessons Learned

**Benefits Realized**:

1. **Time savings**: 38 minutes automated vs 2-3 hours manual
2. **Resilience**: Handles source failures gracefully (partial success)
3. **Quality**: Automated validation catches 99% of issues
4. **Idempotency**: Safe to re-run without duplicates
5. **Observability**: Detailed logging and quality reports

**Challenges Encountered**:

1. **Resource tuning**: Initial 8GB RAM insufficient for 1M records, increased to 12GB
2. **Quality thresholds**: Initial 100% completeness too strict, relaxed to 95%
3. **API reliability**: Frequent timeouts required fallback endpoint
4. **Duplicate detection**: Needed to add run_id for proper deduplication

**Philosophy Compliance**:

- **Ruthless simplicity**: 4 clear phases, no unnecessary steps
- **Single responsibility**: Each phase has one job (collect, transform, validate, publish)
- **Modularity**: Collectors (S3, PostgreSQL, API) are reusable
- **Regeneratable**: Can rebuild pipeline from goal definition

**When to Use This Pattern**:

- Multiple data sources with different collection strategies
- Quality validation is critical
- Source failures are common (need graceful handling)
- Idempotency is required (safe re-runs)
- High frequency (daily or more)

**When NOT to Use**:

- Single data source (simple script suffices)
- Real-time streaming (use streaming framework)
- No quality requirements (direct load acceptable)
- One-time data migration (script sufficient)
