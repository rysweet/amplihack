# Memory A/B Test - Quick Reference

**One-page guide for running memory effectiveness tests**

---

## Quick Commands

```bash
# Install dependencies
pip install scipy statsmodels numpy

# Run full test suite (all phases)
python scripts/memory_test_harness.py --full

# Run specific phase
python scripts/memory_test_harness.py --phase baseline
python scripts/memory_test_harness.py --phase sqlite
python scripts/memory_test_harness.py --phase neo4j

# Analyze existing results
python scripts/memory_test_harness.py --analyze

# Custom output directory
python scripts/memory_test_harness.py --full --output-dir my_results
```

---

## Test Phases

| Phase           | Command            | Duration | Decision                    |
| --------------- | ------------------ | -------- | --------------------------- |
| **1. Baseline** | `--phase baseline` | ~8 hours | None                        |
| **2. SQLite**   | `--phase sqlite`   | ~8 hours | Proceed if >20% improvement |
| **3. Neo4j**    | `--phase neo4j`    | ~8 hours | Only if Phase 2 succeeds    |
| **4. Report**   | Automatic          | ~1 hour  | Final recommendation        |

---

## Success Criteria Checklist

### For SQLite (Phase 2 → Phase 3)

- [ ] Statistical significance: p < 0.05
- [ ] Effect size: Cohen's d > 0.5
- [ ] Time reduction: > 20%
- [ ] No major errors

**Decision**: Proceed to Neo4j testing? **YES** / NO

### For Neo4j (Phase 3 → Production)

- [ ] Statistical significance vs SQLite: p < 0.05
- [ ] Meaningful improvement: > 15% over SQLite
- [ ] Benefit justifies complexity
- [ ] Scale warrants graph database

**Decision**: Deploy Neo4j? YES / **NO** (start with SQLite)

---

## Expected Results

### Memory vs No Memory (Phase 2)

| Metric              | Expected         | Action if Below       |
| ------------------- | ---------------- | --------------------- |
| Time reduction      | **-20% to -35%** | Investigate scenarios |
| Error reduction     | **-50% to -70%** | Check memory quality  |
| Quality improvement | **+25% to +40%** | Review metrics        |

### Neo4j vs SQLite (Phase 3)

| Metric         | Expected         | Action if Below       |
| -------------- | ---------------- | --------------------- |
| Time reduction | **-5% to -15%**  | Stick with SQLite     |
| Query speed    | **-10% to -30%** | Scale not reached yet |

---

## Results Files

```
test_results/
├── baseline_results.json            # Phase 1: Control data
├── sqlite_results.json              # Phase 2: SQLite data
├── neo4j_results.json               # Phase 3: Neo4j data
├── baseline_vs_sqlite_comparison.json
├── sqlite_vs_neo4j_comparison.json
└── final_report.md                  # Phase 4: Final recommendation
```

---

## Quick Troubleshooting

### Test Taking Too Long

```bash
# Run with fewer iterations (3 instead of 5)
# Edit memory_test_harness.py:
# Change: for iteration in range(5)
# To:     for iteration in range(3)
```

### Memory System Not Available

```bash
# Check SQLite memory
python -c "from amplihack.memory import MemoryManager; print('OK')"

# Check Neo4j memory
python -c "from amplihack.memory.neo4j import Neo4jConnector; print('OK')"
```

### Statistical Analysis Fails

```bash
# Install required packages
pip install scipy statsmodels numpy matplotlib seaborn

# Verify installation
python -c "import scipy.stats; import statsmodels; print('OK')"
```

---

## Interpreting Results

### P-Value (Statistical Significance)

- **p < 0.001**: Extremely strong evidence ✅✅✅
- **p < 0.01**: Strong evidence ✅✅
- **p < 0.05**: Moderate evidence ✅
- **p > 0.05**: Insufficient evidence ❌

### Effect Size (Practical Significance)

- **d > 0.8**: Large effect (major improvement) ✅✅
- **d > 0.5**: Medium effect (substantial improvement) ✅
- **d > 0.2**: Small effect (minor improvement) ~
- **d < 0.2**: Negligible effect (not worth it) ❌

### Confidence Interval

- **Negative CI**: Performance degraded ❌
- **Crosses zero**: Uncertain benefit ⚠️
- **Positive CI**: Confirmed improvement ✅

---

## Decision Matrix

| p-value | Effect Size | Action                  |
| ------- | ----------- | ----------------------- |
| < 0.05  | > 0.8       | **STRONG PROCEED** ✅✅ |
| < 0.05  | 0.5-0.8     | **PROCEED** ✅          |
| < 0.05  | 0.2-0.5     | **CONSIDER** ~          |
| < 0.05  | < 0.2       | **STOP** ❌             |
| > 0.05  | Any         | **STOP** ❌             |

---

## Common Scenarios

### Scenario 1: SQLite Shows Strong Benefit

```
Phase 2 Results:
- p-value: 0.001 ✅
- Effect size: 0.85 ✅
- Time reduction: -32% ✅

Decision: PROCEED to Phase 3 (test Neo4j)
```

### Scenario 2: SQLite Shows Marginal Benefit

```
Phase 2 Results:
- p-value: 0.04 ✅
- Effect size: 0.35 ~
- Time reduction: -12% ~

Decision: STOP - benefit too small to justify
```

### Scenario 3: Neo4j Shows No Additional Benefit

```
Phase 3 Results (Neo4j vs SQLite):
- p-value: 0.45 ❌
- Effect size: 0.15 ~
- Time reduction: -3% ~

Decision: Deploy SQLite, skip Neo4j
```

---

## Timeline

### Week 1-2: Implementation

- Implement scenario execution
- Integrate with agents
- Validate test harness

### Week 3: Phase 1

```bash
python scripts/memory_test_harness.py --phase baseline
# Wait ~8 hours
# Review baseline_results.json
```

### Week 4: Phase 2 + Decision

```bash
python scripts/memory_test_harness.py --phase sqlite
# Wait ~8 hours
# Review baseline_vs_sqlite_comparison.json
# DECISION GATE: Proceed to Phase 3?
```

### Week 5: Phase 3 (conditional)

```bash
# Only if Phase 2 successful
python scripts/memory_test_harness.py --phase neo4j
# Wait ~8 hours
# Review sqlite_vs_neo4j_comparison.json
```

### Week 6: Final Decision

- Review all results
- Generate final report
- Make deployment decision

---

## Emergency Stops

### Stop Testing If:

1. **Test harness errors**: Fix bugs before continuing
2. **Metrics look wrong**: Validate collection logic
3. **Results highly variable**: Increase iterations
4. **Clear negative impact**: Stop immediately

---

## Contact / Questions

- **Test Design**: `docs/memory/EFFECTIVENESS_TEST_DESIGN.md`
- **Implementation**: `scripts/memory_test_harness.py`
- **Results**: `test_results/` directory

---

## Cheat Sheet

```python
# Quick analysis of results
import json
import numpy as np

# Load results
with open('test_results/baseline_results.json') as f:
    baseline = json.load(f)
with open('test_results/sqlite_results.json') as f:
    sqlite = json.load(f)

# Extract execution times
baseline_times = [r['time']['execution_time'] for r in baseline]
sqlite_times = [r['time']['execution_time'] for r in sqlite]

# Calculate improvement
baseline_mean = np.mean(baseline_times)
sqlite_mean = np.mean(sqlite_times)
improvement = ((sqlite_mean - baseline_mean) / baseline_mean) * 100

print(f"Baseline: {baseline_mean:.1f}s")
print(f"SQLite: {sqlite_mean:.1f}s")
print(f"Improvement: {improvement:.1f}%")

# Quick decision
from scipy.stats import ttest_rel
t_stat, p_value = ttest_rel(baseline_times, sqlite_times)
print(f"p-value: {p_value:.4f}")
print(f"Significant: {p_value < 0.05}")
```

---

**Status**: Ready for Use
**Updated**: 2025-11-03
