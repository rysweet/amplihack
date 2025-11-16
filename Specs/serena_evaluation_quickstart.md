# Serena Evaluation Framework - Quick Start

**Full Specification**: `Specs/serena_evaluation_framework.md`

## TL;DR

Measure Serena MCP's impact on amplihack with 3 focused coding tests, comparing quality + efficiency metrics between baseline (no Serena) and Serena-enabled approaches.

## Three Tests

1. **Cross-File Refactoring**: Rename function across 6 files (18 instances)
   - Tests: Symbol tracking vs grep-based search
   - Expected: Fewer file reads, better completeness

2. **API Usage Analysis**: Find all callers + analyze patterns
   - Tests: Direct navigation vs exploratory reading
   - Expected: Token reduction, better accuracy

3. **Error Handling Insertion**: Add try/except to 10 functions
   - Tests: Precise insertion vs manual editing
   - Expected: Faster execution, perfect placement

## Key Metrics

**Quality** (must not regress):
- Correctness: % of requirements met
- Completeness: % of problem space covered
- Code Quality: 1-10 score by reviewers

**Efficiency** (expect major gains):
- Token Usage: Total tokens consumed
- Time Taken: Seconds to complete
- File Reads: Number of files accessed
- Tool Operations: Number of tool calls

## Quick Execution

```bash
# 1. Setup (30 min)
cd eval-tests
./setup_tests.sh

# 2. Baseline runs (3 hours)
export SERENA_MCP_ENABLED=false
./run_evaluation.sh test1 test2 test3

# 3. Serena runs (3 hours)
export SERENA_MCP_ENABLED=true
./run_evaluation.sh test1 test2 test3

# 4. Generate report (30 min)
python3 scripts/generate_report.py --output report.md
```

## Expected Findings

Based on Serena's design:
- **40-50% token reduction** (fewer file reads)
- **50%+ time reduction** (targeted operations)
- **60%+ file read reduction** (symbol navigation)
- **Equal or better quality** (LSP accuracy)

## Report Deliverable

Comprehensive markdown report with:
- Executive summary (recommend/don't recommend)
- Test-by-test results with statistical significance
- Overall performance comparison
- Detailed recommendations and caveats
- Reproducible test artifacts

## Philosophy Alignment

**Ruthless Simplicity**: 3 tests, 7 metrics, clear protocol
**Zero-BS**: Complete working evaluation, real measurements
**Modular Design**: Each test is independent brick
**Trust in Emergence**: Simple metrics reveal profound patterns

## Files Created

- `Specs/serena_evaluation_framework.md` (7,500 lines) - Complete specification
- `Specs/serena_evaluation_quickstart.md` (this file) - Quick reference

## Next Actions

1. Review framework with team
2. Create test repositories
3. Execute evaluation (2 days)
4. Make integration decision based on data
