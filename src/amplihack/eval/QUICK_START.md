# Progressive Test Suite - Quick Start

## 30-Second Overview

Progressive test suite with 12 levels (L1-L12) testing agent learning from simple recall to far transfer across domains. Supports 4 SDK backends, 3-run median for stable benchmarks, and multi-vote grading for noise reduction.

**Current Scores** (3-run median, mini SDK):
L1: 83%, L2: 100%, L3: 88%, L4: 79%, L5: 95%, L6: 100%, L7: 84%, Overall: 97.5%

## Run Full Suite

```bash
cd /home/azureuser/src/amplihack5
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval
```

## Run Specific Levels

```bash
# Just L2 and L3
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval --levels L2 L3

# Just L6 (incremental learning)
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval --levels L6

# Advanced levels (metacognition, causal, counterfactual)
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval --advanced

# All levels
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval --levels L1 L2 L3 L4 L5 L6 L8 L9 L10 L11 L12
```

## 3-Run Median (Recommended)

Single runs are unreliable due to LLM stochasticity. Run 3 times and take medians:

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval_median --runs 3
```

## Multi-Vote Grading

Each answer graded N times, median score taken. Reduces noise on ambiguous answers:

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval_votes --grader-votes 3
```

## Choose an SDK

```bash
# Mini framework (default, fastest for iteration)
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval --sdk mini

# Claude Agent SDK
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval --sdk claude

# GitHub Copilot SDK
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval --sdk copilot

# Microsoft Agent Framework
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval --sdk microsoft
```

## Recommended: Final Benchmark

Combined 3-run median + 3-vote grading for stable, reliable results:

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval_final \
    --runs 3 \
    --grader-votes 3 \
    --sdk mini
```

## CLI Options Reference

| Option             | Description                                       | Default                  |
| ------------------ | ------------------------------------------------- | ------------------------ |
| `--output-dir`     | Directory for results                             | `./eval_progressive`     |
| `--agent-name`     | Agent name (memory isolation)                     | `progressive-test-agent` |
| `--levels`         | Specific levels to run (L1-L12)                   | L1-L6                    |
| `--advanced`       | Include L8-L10                                    | Off                      |
| `--memory-backend` | Memory backend                                    | `amplihack-memory-lib`   |
| `--parallel N`     | Run N times, report medians                       | Off                      |
| `--runs N`         | Alias for --parallel                              | Off                      |
| `--sdk`            | SDK type: mini, claude, copilot, microsoft        | `mini`                   |
| `--grader-votes N` | Grading votes per question (1=single, 3=majority) | 1                        |

## Check Results

```bash
cat /tmp/eval/summary.json
cat /tmp/eval/L1/scores.json
```

## The 12 Levels

| Level | Name                   | Tests                               | Current |
| ----- | ---------------------- | ----------------------------------- | ------- |
| L1    | Single Source Recall   | Basic memory retrieval              | 83%     |
| L2    | Multi-Source Synthesis | Combining multiple sources          | 100%    |
| L3    | Temporal Reasoning     | Tracking changes over time          | 88%     |
| L4    | Procedural Learning    | Learning step-by-step guides        | 79%     |
| L5    | Contradiction Handling | Detecting conflicts                 | 95%     |
| L6    | Incremental Learning   | Updating knowledge                  | 100%    |
| L7    | Teaching Transfer      | Teacher-student knowledge transfer  | 84%     |
| L8    | Metacognition          | Self-awareness of reasoning quality | --      |
| L9    | Causal Reasoning       | Identifying cause-and-effect        | --      |
| L10   | Counterfactual         | "What if" hypothetical analysis     | --      |
| L11   | Novel Skill            | Learning post-cutoff task formats   | --      |
| L12   | Far Transfer           | Applying patterns to new domains    | --      |

## What Each Level Tests

**L1**: "How many medals does Norway have?" (direct fact)
**L2**: "How does Italy 2026 compare to previous best?" (needs 2 sources)
**L3**: "How many medals between Day 7 and Day 9?" (compute difference)
**L4**: "Create weather_app with http package - what commands?" (apply procedure)
**L5**: "Two sources say 1.2B and 800M viewers - what's correct?" (handle conflict)
**L6**: "How many golds does Klaebo have?" after update article (must say 10, not 9)
**L7**: Teacher learns articles, teaches student, student is quizzed
**L8**: Agent evaluates its own confidence and knowledge gaps
**L9**: "What caused Italy to improve?" (identify root cause)
**L10**: "What if Klaebo hadn't competed?" (hypothetical reasoning)
**L11**: "Write a gh-aw workflow file" (learn from docs, generate config)
**L12**: "Which framework improved most from Q1 to Q2?" (apply reasoning to new domain)

## Multi-SDK Comparison

Compare all 4 SDKs with improvement loops:

```bash
# Compare 2 SDKs
PYTHONPATH=src python -m amplihack.eval.sdk_eval_loop \
    --sdks mini claude --loops 3

# Compare all 4 SDKs
PYTHONPATH=src python -m amplihack.eval.sdk_eval_loop --all-sdks --loops 3
```

## Self-Improvement Runner

Closed-loop: EVAL -> ANALYZE -> RESEARCH -> IMPROVE -> RE-EVAL -> DECIDE

```bash
PYTHONPATH=src python -m amplihack.eval.self_improve.runner \
    --sdk mini --iterations 3 --dry-run
```

## Long-Horizon Memory Eval

1000-turn memory stress test:

```bash
PYTHONPATH=src python -m amplihack.eval.long_horizon_memory \
    --turns 100 --questions 20
```

## Prerequisites

```bash
# Set API key for grading
export ANTHROPIC_API_KEY=your_key_here

# Verify memory backend
python -c "from amplihack_memory import MemoryConnector; print('OK')"
```

## Output Location

Results saved to the `--output-dir` directory:

```
eval_progressive/
  summary.json              # Overall scores
  L1/scores.json            # Level 1 detailed results
  L2/scores.json            # Level 2 detailed results
  ...
  L6/scores.json            # Level 6 detailed results
```

For parallel/multi-run:

```
eval_median/
  parallel_summary.json     # Median scores across all runs
  run_0/summary.json        # Run 0 results
  run_1/summary.json        # Run 1 results
  run_2/summary.json        # Run 2 results
```

## Common Issues

### ModuleNotFoundError: No module named 'amplihack.eval'

**Solution**: Set PYTHONPATH:

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite --output-dir /tmp/eval
```

### Agent subprocess fails

**Check**:

1. Memory backend is installed (`pip install -e amplihack-memory-lib/`)
2. No permission issues with temp directories

### Grading fails with API error

**Check**:

```bash
echo $ANTHROPIC_API_KEY  # Should not be empty
```

## Files

- **Test Data**: `src/amplihack/eval/test_levels.py`
- **Runner**: `src/amplihack/eval/progressive_test_suite.py`
- **Grader**: `src/amplihack/eval/grader.py` (multi-vote support)
- **Agent Subprocess**: `src/amplihack/eval/agent_subprocess.py` (SDK routing)
- **SDK Eval Loop**: `src/amplihack/eval/sdk_eval_loop.py` (multi-SDK comparison)
- **Self-Improvement**: `src/amplihack/eval/self_improve/runner.py`
- **Long-Horizon**: `src/amplihack/eval/long_horizon_memory.py`
- **Docs**: `src/amplihack/eval/PROGRESSIVE_TEST_SUITE.md`
- **Tests**: `tests/eval/test_progressive_suite.py`

## Next Steps After Running

1. Check `summary.json` for overall scores
2. Identify weakest level (lowest score)
3. Read detailed results in that level's `scores.json`
4. Run self-improvement loop to automatically fix weak areas
5. Re-run with `--runs 3` for stable comparison

## Related Documentation

- [Eval System Architecture](../../docs/EVAL_SYSTEM_ARCHITECTURE.md) - Complete eval system design
- [Goal-Seeking Agents](../../docs/GOAL_SEEKING_AGENTS.md) - End-to-end guide
- [SDK Adapters Guide](../../docs/SDK_ADAPTERS_GUIDE.md) - SDK details
