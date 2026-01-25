# Amplihack Benchmarking Suite

This directory contains benchmarking tools and reference examples for evaluating AI model performance in agentic coding workflows.

## Directory Structure

```
tests/benchmarks/
├── benchmark_suite_v3/        # ⭐ REFERENCE IMPLEMENTATION (Latest)
│   ├── BENCHMARK_REPORT_V3.md # Reference example of ideal benchmark report
│   ├── BENCHMARK_TASKS.md     # Task definitions for 4 complexity levels
│   └── run_benchmarks.py      # Automated benchmark runner
├── opus_vs_sonnet_v2/         # Previous version (workflow compliance focus)
└── results/                   # Historical benchmark results
```

## Benchmark Suite V3 (Current Reference)

**Location**: `benchmark_suite_v3/`

This is the canonical reference implementation for model evaluation benchmarks. It demonstrates:

- **4 Complexity Levels**: Simple → Medium → High → Very High
- **Comprehensive Metrics**: Duration, turns, cost, tool calls, subagent calls, tests, quality scores
- **Quality Assessment**: Code review by specialized agents with 5-point scoring
- **Workflow Analysis**: Full trace log analysis for tool/agent/skill usage
- **Production Standards**: GitHub issues, PRs, documentation, philosophy compliance

### Reference Report Format

See `benchmark_suite_v3/BENCHMARK_REPORT_V3.md` for the ideal benchmark report structure:

1. **Results Summary** - Aggregate metrics and quality score comparison
2. **Task-by-Task Analysis** - Detailed breakdown with quality assessments
3. **Tool Usage Analysis** - Tool call patterns and frequencies
4. **Subagent Orchestration** - Agent invocation patterns
5. **Skills Usage** - Skill activation analysis
6. **Workflow Adherence** - Step-by-step workflow compliance
7. **Key Findings** - Strategic recommendations and patterns

## Running Benchmarks

### Quick Start

```bash
cd tests/benchmarks/benchmark_suite_v3
python run_benchmarks.py --help
```

### Full Benchmark Suite

```bash
# Run all 8 benchmarks (4 tasks × 2 models)
python run_benchmarks.py --all

# Run specific model
python run_benchmarks.py --model opus
python run_benchmarks.py --model sonnet

# Run specific tasks
python run_benchmarks.py --tasks 1,2,3,4
```

### Results Location

- **Result Files**: `~/.amplihack/.claude/runtime/benchmarks/suite_v3/{model}_task{N}/result.json`
- **Trace Logs**: `worktrees/bench-{model}-task{N}/.claude-trace/*.jsonl`
- **Reports**: `tests/benchmarks/benchmark_suite_v3/BENCHMARK_REPORT_V3.md`

## Creating New Benchmarks

When creating new benchmark suites, use `benchmark_suite_v3` as your template:

1. **Task Definition** - Create `BENCHMARK_TASKS.md` with clear requirements
2. **Runner Script** - Implement automated execution (see `run_benchmarks.py`)
3. **Trace Analysis** - Capture and analyze claude-trace logs
4. **Quality Assessment** - Use reviewer agents for code quality scoring
5. **Report Generation** - Follow `BENCHMARK_REPORT_V3.md` structure

## Key Metrics to Track

### Efficiency Metrics

- Duration (wall-clock time)
- Turns (interaction count)
- Cost (API cost in USD)
- Tool calls (total tool invocations)

### Quality Metrics

- Test coverage (number of tests written)
- Code quality score (1-5 scale via reviewer agent)
- Philosophy compliance (simplicity, modularity)
- Bug detection (critical issues found)

### Workflow Metrics

- Subagent invocations (orchestration depth)
- Skills used (capability activation)
- Workflow adherence (step completion)
- GitHub artifacts (issues, PRs created)

## Historical Context

- **V1**: Initial workflow compliance benchmarks
- **V2**: Opus vs Sonnet workflow adherence comparison
- **V3**: Comprehensive model evaluation with quality assessment (CURRENT)

## Model Evaluation Skill

For automated reproduction of benchmark workflows, use:

```bash
/amplihack:model-evaluation-benchmark
```

See `~/.amplihack/.claude/skills/model-evaluation-benchmark/` for documentation.

## Contributing

When adding new benchmarks:

1. Follow the v3 reference structure
2. Document task requirements clearly
3. Automate execution where possible
4. Include comprehensive quality assessment
5. Generate reports in the v3 format
6. Update this README with your additions

---

**Last Updated**: 2025-11-26
**Current Reference**: Benchmark Suite V3
**Reference Report**: `benchmark_suite_v3/BENCHMARK_REPORT_V3.md`
