# Meta-Analyst

Meta-cognitive reasoning for improving reasoning quality through self-reflection.

## When to Use

- After completing complex analysis
- When uncertain about conclusions
- Before presenting high-stakes recommendations
- Keywords: "check my reasoning", "am I missing something", "validate thinking"

## Core Purpose

Step outside the reasoning process to evaluate its quality, identify biases, surface assumptions, and validate the reasoning chain.

## Self-Reflection Framework

### Layer 1: Reasoning Quality Check

```markdown
## Reasoning Quality Assessment

**Clarity**
- [ ] Is the problem clearly defined?
- [ ] Are terms used consistently?
- [ ] Could someone else follow this reasoning?

**Completeness**
- [ ] Have all relevant factors been considered?
- [ ] Are there obvious gaps in the analysis?
- [ ] Were alternatives explored?

**Correctness**
- [ ] Does each step follow logically from the previous?
- [ ] Are facts accurate and verified?
- [ ] Are inferences justified?

**Quality Score:** [1-5] with rationale
```

### Layer 2: Bias Detection

| Bias Type | Signs | Mitigation |
|-----------|-------|------------|
| **Confirmation** | Only sought supporting evidence | Actively look for counter-evidence |
| **Anchoring** | First information dominates | Re-analyze without initial data |
| **Availability** | Recent/vivid examples overweighted | Seek base rates and statistics |
| **Sunk Cost** | Past investment influences future | Evaluate from fresh start |
| **Authority** | Accepted claims without scrutiny | Question sources, seek alternatives |
| **Groupthink** | Assumed consensus without testing | Steel-man opposing views |

```markdown
## Bias Scan

**Biases Detected:**
- [ ] Confirmation bias: [Evidence]
- [ ] Anchoring: [Evidence]
- [ ] Availability: [Evidence]
- [ ] Sunk cost: [Evidence]
- [ ] Authority: [Evidence]
- [ ] Groupthink: [Evidence]

**Mitigation Actions:**
- [Action taken to counter bias]
```

### Layer 3: Assumption Identification

```markdown
## Assumption Audit

### Explicit Assumptions (Stated)
| Assumption | Basis | Risk if Wrong |
|------------|-------|---------------|
| [Assumption] | [Why we believe this] | [Impact] |

### Implicit Assumptions (Unstated)
| Assumption | How Discovered | Validity |
|------------|----------------|----------|
| [Hidden assumption] | [What revealed it] | [Still valid?] |

### Critical Assumptions (Must Be True)
- [Assumption]: If wrong, [consequence]
```

### Layer 4: Reasoning Chain Validation

```markdown
## Reasoning Chain

### Forward Chain (Premises to Conclusion)
1. [Premise 1] - Verified: [Yes/No]
   ↓ (implies)
2. [Intermediate conclusion] - Sound: [Yes/No]
   ↓ (combined with)
3. [Premise 2] - Verified: [Yes/No]
   ↓ (therefore)
4. [Final conclusion]

### Weak Links
- Step [N] → Step [N+1]: [Why this link might fail]

### Alternative Conclusions
Given the same premises, could we conclude differently?
- [Alternative]: [Why/why not valid]
```

## Meta-Analysis Output Format

```markdown
## Meta-Analysis Report

### Original Conclusion
[The conclusion being analyzed]

### Reasoning Quality
**Score:** [1-5]
**Strengths:**
- [Strength 1]
**Weaknesses:**
- [Weakness 1]

### Bias Assessment
**Biases Found:** [None | List]
**Impact:** [How biases affected conclusion]
**Corrective Action:** [What was done]

### Assumption Check
**Critical Assumptions:**
1. [Assumption]: [Confidence level]

**Assumptions Needing Validation:**
- [Assumption]: [How to validate]

### Chain Validation
**Weakest Link:** [Step N → Step N+1]
**Confidence in Chain:** [High | Medium | Low]

### Revised Position
**Original Confidence:** [X%]
**Revised Confidence:** [Y%]
**Changes Made:** [If any]

### Remaining Uncertainties
- [Uncertainty 1]: [Impact on conclusion]
```

## Quick Meta-Check (5 Questions)

For rapid self-assessment:

1. **What would change my mind?** (Falsifiability)
2. **What am I not seeing?** (Blind spots)
3. **Why might I be wrong?** (Humility)
4. **Who would disagree and why?** (Opposition)
5. **What's the strongest counter-argument?** (Steel-man)

## Reasoning Red Flags

| Red Flag | Indicates | Action |
|----------|-----------|--------|
| "Obviously..." | Unexamined assumption | Question it |
| "Everyone knows..." | Possible groupthink | Verify independently |
| "It's always been..." | Status quo bias | Consider alternatives |
| High confidence + low evidence | Overconfidence | Seek more data |
| Emotional charge | Motivated reasoning | Step back, re-evaluate |
| Unable to articulate reasoning | Intuition without basis | Make reasoning explicit |

## Integration with Other Workflows

- **After Investigation:** Validate root cause reasoning
- **After Analysis:** Check for blind spots
- **Before Decision:** Ensure sound basis
- **After Implementation:** Retrospective on reasoning quality

## Anti-Patterns

- Meta-analysis paralysis (infinite recursion)
- Using meta-analysis to avoid commitment
- Superficial checklist completion without genuine reflection
- Over-correction (changing valid conclusions due to minor biases)
- Skipping meta-analysis for "obvious" conclusions
