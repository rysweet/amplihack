# Parallel Hypothesis Tester

Systematic hypothesis testing with parallel execution for efficient investigation.

## When to Use

- Debugging complex issues with multiple possible causes
- Scientific or analytical investigations
- When root cause is unclear
- Keywords: "could be", "might be", "investigate", "diagnose", "root cause"

## Core Concept

Generate multiple hypotheses upfront, then test them in parallel rather than sequentially. Eliminates bias toward first hypothesis and accelerates convergence.

## Workflow

### Step 1: Hypothesis Formation

Generate 3-5 hypotheses before testing any:

```markdown
## Hypothesis Set

**Observation:** [What we're trying to explain]

**H1:** [First hypothesis]
- Predicted evidence: [What we'd see if true]
- Disconfirming evidence: [What would rule this out]

**H2:** [Second hypothesis]
- Predicted evidence: [...]
- Disconfirming evidence: [...]

**H3:** [Third hypothesis]
- Predicted evidence: [...]
- Disconfirming evidence: [...]

**Prior Probabilities:**
- H1: [X%] - [Why]
- H2: [Y%] - [Why]
- H3: [Z%] - [Why]
```

### Step 2: Design Parallel Tests

Identify tests that can run simultaneously:

```markdown
## Test Design

### Independent Tests (Run in Parallel)
| Test | Hypothesis Targeted | Expected Result if True |
|------|---------------------|------------------------|
| T1 | H1, H2 | [Result] |
| T2 | H2, H3 | [Result] |
| T3 | H1 | [Result] |

### Dependent Tests (Run After)
| Test | Depends On | Condition |
|------|------------|-----------|
| T4 | T1 result | Only if T1 shows X |
```

### Step 3: Execute Tests

```markdown
## Test Execution

### Parallel Batch 1
| Test | Result | Duration |
|------|--------|----------|
| T1 | [Actual result] | [Time] |
| T2 | [Actual result] | [Time] |
| T3 | [Actual result] | [Time] |

### Conditional Batch 2
| Test | Triggered By | Result |
|------|--------------|--------|
| T4 | T1 = X | [Result or Skipped] |
```

### Step 4: Evidence Collection

```markdown
## Evidence Matrix

| Evidence | H1 | H2 | H3 | Source |
|----------|----|----|----|----|
| [E1] | ++ | - | 0 | T1 |
| [E2] | 0 | + | -- | T2 |
| [E3] | + | 0 | 0 | T3 |

Legend: ++ strong support, + support, 0 neutral, - against, -- strong against
```

### Step 5: Hypothesis Elimination

```markdown
## Elimination Analysis

**H1:** [Status: Active | Eliminated | Confirmed]
- Evidence for: [List]
- Evidence against: [List]
- Verdict: [Keep investigating | Ruled out | Most likely]

**H2:** [Status]
- Evidence for: [List]
- Evidence against: [List]
- Verdict: [...]

**H3:** [Status]
- [...]

**Remaining Hypotheses:** [H1, H3]
```

### Step 6: Confidence Scoring

```markdown
## Confidence Assessment

**Final Probabilities (Posterior):**
| Hypothesis | Prior | Posterior | Delta | Key Evidence |
|------------|-------|-----------|-------|--------------|
| H1 | 30% | 65% | +35% | E1, E3 |
| H2 | 40% | 5% | -35% | E2 ruled out |
| H3 | 30% | 30% | 0% | Inconclusive |

**Leading Hypothesis:** H1 (65%)
**Confidence Level:** [High | Medium | Low]
**Remaining Uncertainty:** [What's still unknown]
```

## Parallel Execution Strategy

### Maximize Parallelism

```
        ┌─── T1 ───┐
Start ──┼─── T2 ───┼─── Analyze ─── T4 (conditional) ─── Conclude
        └─── T3 ───┘
```

### Test Prioritization

| Priority | Criteria |
|----------|----------|
| **High** | Discriminates between multiple hypotheses |
| **Medium** | Tests single hypothesis definitively |
| **Low** | Provides incremental evidence |
| **Defer** | Expensive and only marginally useful |

### Parallelization Rules

1. **Independent tests first** - No dependencies, run together
2. **High-discrimination tests early** - Eliminate hypotheses quickly
3. **Cheap tests before expensive** - Quick wins first
4. **Conditional tests after triggers** - Only when needed

## Output Format

```markdown
## Hypothesis Testing Report

### Investigation
**Question:** [What we're investigating]
**Date:** [Timestamp]

### Hypotheses Tested
| ID | Hypothesis | Prior | Posterior | Status |
|----|------------|-------|-----------|--------|
| H1 | [Description] | 30% | 65% | Leading |
| H2 | [Description] | 40% | 5% | Eliminated |
| H3 | [Description] | 30% | 30% | Inconclusive |

### Key Evidence
1. [E1]: [Description] - Supports H1
2. [E2]: [Description] - Eliminates H2

### Tests Performed
- [T1]: [Description] - [Result]
- [T2]: [Description] - [Result]

### Conclusion
**Most Likely:** H1 - [Description]
**Confidence:** 65%
**Recommended Action:** [Next step]

### Remaining Questions
- [Q1]: Would increase confidence if answered
```

## Confidence Calibration

| Confidence Level | Meaning | Action |
|------------------|---------|--------|
| **>90%** | Near certain | Act on conclusion |
| **70-90%** | Likely | Act with monitoring |
| **50-70%** | Probable | Gather more evidence |
| **30-50%** | Uncertain | Cannot conclude |
| **<30%** | Unlikely | Look for alternatives |

## Anti-Patterns

- Testing hypotheses sequentially (slow, biased)
- Stopping at first confirmed hypothesis (may miss true cause)
- Not defining disconfirming evidence upfront (unfalsifiable)
- Ignoring evidence that contradicts favorite hypothesis
- Running expensive tests before cheap discriminating tests
- Not updating probabilities based on evidence (anchoring)
