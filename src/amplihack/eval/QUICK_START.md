# Progressive Test Suite - Quick Start

## 30-Second Overview

Progressive test suite with 6 levels (L1-L6) testing agent learning from simple recall to complex reasoning.

**Current Status**: L1 passing at 100%, L2-L6 expected ~30-40% average.
**Target**: L2-L6 at ~75% average after agent improvements.

## Run Full Suite

```bash
cd /home/azureuser/src/amplihack5
python examples/run_progressive_eval.py
```

## Run Specific Levels

```bash
# Just L2 and L3
python examples/run_progressive_eval.py --levels L2 L3

# Just L6 (incremental learning)
python examples/run_progressive_eval.py --levels L6
```

## Check Results

```bash
cat eval_progressive_example/summary.json
cat eval_progressive_example/L1/scores.json
```

## The 6 Levels

| Level | Name                     | Tests                          | Target |
|-------|--------------------------|--------------------------------|--------|
| L1    | Single Source Recall     | Basic memory retrieval         | 100%   |
| L2    | Multi-Source Synthesis   | Combining multiple sources     | 90%    |
| L3    | Temporal Reasoning       | Tracking changes over time     | 75%    |
| L4    | Procedural Learning      | Learning step-by-step guides   | 65%    |
| L5    | Contradiction Handling   | Detecting conflicts            | 60%    |
| L6    | Incremental Learning     | Updating knowledge             | 70%    |

## What Each Level Tests

**L1**: "How many medals does Norway have?" (direct fact)
**L2**: "How does Italy 2026 compare to previous best?" (needs 2 sources)
**L3**: "How many medals between Day 7 and Day 9?" (compute difference)
**L4**: "Create weather_app with http package - what commands?" (apply procedure)
**L5**: "Two sources say 1.2B and 800M viewers - what's correct?" (handle conflict)
**L6**: "How many golds does Klaebo have?" after update article (must say 10, not 9)

## Prerequisites

```bash
# Set API key for grading
export ANTHROPIC_API_KEY=your_key_here

# Verify memory backend
python -c "from amplihack_memory import MemoryConnector; print('OK')"
```

## Output Location

Results saved to: `eval_progressive_example/`

```
eval_progressive_example/
├── summary.json           # Overall scores
├── L1/scores.json         # Level 1 detailed results
├── L2/scores.json         # Level 2 detailed results
├── ...
└── L6/scores.json         # Level 6 detailed results
```

## Quick Test Infrastructure

```bash
# Verify test data structure
pytest tests/eval/test_progressive_suite.py -v

# Should see 15 tests pass
```

## Common Issues

### ModuleNotFoundError: No module named 'amplihack.eval'

**Solution**: Use the example script which handles paths:
```bash
python examples/run_progressive_eval.py
```

### Agent subprocess fails

**Check**:
1. Memory backend is installed (`amplihack-memory-lib`)
2. Agent subprocess implementation exists (`agent_subprocess.py`)
3. No permission issues with temp directories

### Grading fails with API error

**Check**:
```bash
echo $ANTHROPIC_API_KEY  # Should not be empty
```

## Files

- **Test Data**: `src/amplihack/eval/test_levels.py`
- **Runner**: `src/amplihack/eval/progressive_test_suite.py`
- **Docs**: `src/amplihack/eval/PROGRESSIVE_TEST_SUITE.md`
- **Example**: `examples/run_progressive_eval.py`
- **Tests**: `tests/eval/test_progressive_suite.py`

## Next Steps After Running

1. Check `summary.json` for overall scores
2. Identify weakest level (lowest score)
3. Read detailed results in that level's `scores.json`
4. Improve agent for that specific cognitive skill
5. Re-run suite and measure improvement

## Getting Help

**Full Documentation**: `src/amplihack/eval/PROGRESSIVE_TEST_SUITE.md`
**Implementation Details**: `src/amplihack/eval/IMPLEMENTATION_SUMMARY.md`
**Test Data**: Look at `test_levels.py` to see exact questions/content

## Expected Timeline

**Current (pre-improvement)**: ~30-40% average L2-L6
**After improvements**: ~75% average L2-L6
**Represents**: 135% improvement in learning capability

---

**Quick Check**: Can you answer these without the docs?
1. Which level tests contradiction handling? (L5)
2. Which level tests temporal reasoning? (L3)
3. What's the baseline level that should always pass? (L1 at 100%)

If yes, you're ready to run the suite!
