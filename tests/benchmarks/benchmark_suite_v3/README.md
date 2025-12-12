# Benchmark Suite V3 - Reference Implementation

**Status**: ⭐ **REFERENCE IMPLEMENTATION** for model evaluation benchmarks

This directory contains the canonical reference implementation for evaluating AI models in agentic coding workflows. Use this as your template when creating new benchmarks.

## What Makes This a Reference Implementation

1. **Comprehensive Metrics**: Tracks efficiency, quality, and workflow adherence
2. **Quality Assessment**: Automated code review by specialized agents with scoring
3. **Trace Analysis**: Full claude-trace log parsing for tool/agent/skill patterns
4. **Production Standards**: Real GitHub issues, PRs, documentation generation
5. **Clear Documentation**: Reproducible methodology with detailed reporting

## Files in This Directory

### Core Files

- **`BENCHMARK_REPORT_V3.md`** ⭐ - Reference example of ideal benchmark report structure
- **`BENCHMARK_TASKS.md`** - Task definitions for 4 complexity levels
- **`run_benchmarks.py`** - Automated benchmark runner script
- **`README.md`** (this file) - Reference implementation documentation

### Task Complexity Levels

| Level | Task | Description | Key Features |
|-------|------|-------------|--------------|
| 1 | Simple Greeting | Basic function + 1 test | Edge case handling |
| 2 | Config Manager | YAML + env vars + validation | Thread safety, 40+ tests |
| 3 | Plugin System | Abstract base + registry + decorator | SOLID design, security |
| 4 | REST API Client | Retry/backoff + rate limiting + mocks | Complex integration |

## Running This Benchmark

### Prerequisites

```bash
# Ensure you have:
- amplihack installed
- claude-trace available
- Git worktree support
- GitHub CLI (gh) configured
```

### Execution

```bash
cd tests/benchmarks/benchmark_suite_v3

# Run all benchmarks (4 tasks × 2 models = 8 total)
python run_benchmarks.py --all

# Run specific model only
python run_benchmarks.py --model opus
python run_benchmarks.py --model sonnet

# Run specific tasks
python run_benchmarks.py --tasks 1,2,3,4
```

### What Gets Measured

#### Efficiency Metrics
- **Duration**: Wall-clock time from start to completion
- **Turns**: Number of conversation turns (user + assistant messages)
- **Cost**: Total API cost in USD (broken down by model usage)
- **Tool Calls**: Total number of tool invocations

#### Quality Metrics
- **Code Quality Score**: 1-5 scale assessed by reviewer agent
  - Correctness: Does it work?
  - Error Handling: Edge cases covered?
  - Test Coverage: Comprehensive tests?
  - Documentation: Clear docstrings?
  - Style: Clean, maintainable code?
  - SOLID Principles: Good architecture?

#### Workflow Metrics
- **Subagent Invocations**: Count of specialized agent calls (architect, builder, reviewer, etc.)
- **Skills Used**: Which Claude Code skills were activated
- **Workflow Steps**: Which steps from DEFAULT_WORKFLOW.md were executed
- **GitHub Artifacts**: Issues and PRs created

## Results Location

After running benchmarks, results are stored in:

```
.claude/runtime/benchmarks/suite_v3/
├── opus_task1/
│   └── result.json       # Metrics for Opus on Task 1
├── opus_task2/
│   └── result.json
├── ...
└── sonnet_task4/
    └── result.json       # Metrics for Sonnet on Task 4

worktrees/
├── bench-opus-task1/
│   └── .claude-trace/
│       └── log-*.jsonl   # Full API trace for analysis
├── ...
└── bench-sonnet-task4/
    └── .claude-trace/
        └── log-*.jsonl
```

## Analyzing Results

### Generate Report

The reference report (`BENCHMARK_REPORT_V3.md`) was generated through:

1. **Read Result Files**: Parse all 8 `result.json` files for metrics
2. **Analyze Trace Logs**: Launch parallel reviewer agents to parse trace logs
3. **Quality Assessment**: Launch 8 parallel reviewer agents to score code quality
4. **Synthesize Findings**: Compile comprehensive markdown report
5. **Create GitHub Issue**: Publish report with artifact links

### Automated Analysis

```bash
# From the benchmark_suite_v3 directory:
python analyze_results.py

# This will:
# 1. Read all result.json files
# 2. Parse trace logs for tool/agent/skill usage
# 3. Launch quality assessment agents
# 4. Generate markdown report
# 5. Create GitHub issue with findings
```

## Report Structure (Reference Format)

See `BENCHMARK_REPORT_V3.md` for the canonical report structure:

```markdown
# Benchmark Report: [Title]

## Results Summary
- Core Metrics Comparison (aggregate table)
- Quality Score Summary (per-task breakdown)

## Task-by-Task Analysis
For each task:
- Requirements summary
- Metrics table (duration, turns, cost, quality score)
- Notable features/differences
- Quality Assessment table (6 dimensions)
- Verdict (recommendation and insights)

## Tool Usage Analysis
- Tool call frequency breakdown
- Pattern analysis

## Subagent Orchestration
- Agent invocation patterns
- Parallel vs sequential execution

## Skills Usage
- Which skills were activated
- Context and frequency

## Workflow Adherence
- Step-by-step workflow compliance
- Deviations and reasons

## Key Findings
- Speed vs Quality tradeoffs
- Complexity-dependent patterns
- Cost-benefit analysis
- Strategic recommendations
```

## Using This as a Template

When creating new benchmarks, copy this structure:

1. **Define Tasks** - Create clear, unambiguous task definitions with acceptance criteria
2. **Automate Execution** - Build runner script that handles worktrees, models, trace logs
3. **Capture Metrics** - Save structured JSON results with all key metrics
4. **Enable Trace Analysis** - Use claude-trace for API-level observability
5. **Assess Quality** - Use reviewer agents to objectively score implementations
6. **Generate Report** - Follow the v3 markdown structure for consistency
7. **Publish Findings** - Create GitHub issue with artifacts and recommendations

## Key Learnings from V3

### Quality vs Speed Tradeoffs

- **Simple Tasks**: Workflow overhead may exceed value (Opus 2.4/5 → Sonnet 4.8/5 but 10x time)
- **Medium Tasks**: Quality converges (both 4.1-4.3/5) - Opus delivers faster
- **High Tasks**: Excellent design on both (4.7-4.8/5) - Opus 11x faster
- **Very High Tasks**: Subtle bugs emerge (Opus 3.7/5 vs Sonnet 4.5/5) - quality gap widens

### Workflow Adherence Patterns

- **Opus**: SIMPLE session classification, skips workflow steps, minimal subagents
- **Sonnet**: Full 22-step workflow, extensive subagent orchestration, comprehensive artifacts

### Cost-Benefit Analysis

- **Fast Development**: Opus delivers 10x speed, 55-80% cost savings on medium/high complexity
- **Production Quality**: Sonnet catches subtle bugs, worth 1.7-2x cost premium for critical systems

## Reproducing This Benchmark

### Manual Reproduction

```bash
# 1. Set up environment
export AMPLIHACK_USE_TRACE=1

# 2. For each task (1-4) and model (opus, sonnet):
git worktree add worktrees/bench-{model}-task{N} -b benchmark/{model}/task{N}
cd worktrees/bench-{model}-task{N}

# 3. Run benchmark with specific model
amplihack --model {model} "/amplihack:ultrathink {task_prompt}"

# 4. Collect results
cp .claude-trace/*.jsonl ../../.claude/runtime/benchmarks/suite_v3/{model}_task{N}/
# Save metrics to result.json

# 5. Clean up
cd ../..
git worktree remove worktrees/bench-{model}-task{N}
```

### Automated Reproduction

Use the model-evaluation-benchmark skill:

```bash
/amplihack:model-evaluation-benchmark --tasks 1,2,3,4 --models opus,sonnet
```

## Contributing Improvements

When enhancing this benchmark:

1. Maintain backward compatibility with v3 structure
2. Document all changes in git commit messages
3. Update this README with new features
4. Regenerate `BENCHMARK_REPORT_V3.md` if metrics change
5. Create GitHub issue with findings

---

**Created**: 2025-11-26
**Last Benchmark Run**: 2025-11-26 06:16-08:48 UTC
**Report**: `BENCHMARK_REPORT_V3.md`
**GitHub Issue**: [#1698](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1698)
