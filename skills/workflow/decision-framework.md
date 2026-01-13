# Decision Framework

Structured decision-making for choices with significant consequences.

## When to Use

- Architecture or technology choices
- Trade-off decisions with multiple factors
- Irreversible or costly decisions
- Team decisions requiring buy-in
- Keywords: "decide", "choose", "which option", "trade-off", "should we"

## Decision Types

| Type | Characteristics | Approach |
|------|-----------------|----------|
| **Type 1** | Irreversible, high stakes | Full framework, seek input |
| **Type 2** | Reversible, lower stakes | Lightweight, bias to action |
| **Technical** | Objective criteria exist | Score-based evaluation |
| **Strategic** | Subjective, long-term | Scenario analysis |
| **Resource** | Allocation, trade-offs | Opportunity cost focus |

## Workflow

### Step 1: Frame the Decision

```markdown
## Decision Frame

**Decision Statement:** [Clear, specific question]
**Context:** [Why this decision now]
**Scope:** [What's included/excluded]
**Timeline:** [When decision needed]
**Decision Type:** [Type 1/2, Technical/Strategic/Resource]
**Decision Maker:** [Who has final say]
**Stakeholders:** [Who is affected]
```

### Step 2: Generate Options

Generate 3+ genuine options (not strawmen):

```markdown
## Options

### Option A: [Name]
**Description:** [What this option means]
**Pros:**
- [Pro 1]
- [Pro 2]
**Cons:**
- [Con 1]
- [Con 2]

### Option B: [Name]
[...]

### Option C: [Name]
[...]

### Option D: Do Nothing / Status Quo
[Always include this as baseline]
```

### Step 3: Define Criteria

```markdown
## Decision Criteria

| Criterion | Description | Weight | Type |
|-----------|-------------|--------|------|
| [Criterion 1] | [What it measures] | [1-5] | Must-have / Nice-to-have |
| [Criterion 2] | [...] | [...] | [...] |
| [Criterion 3] | [...] | [...] | [...] |

**Must-Have Criteria:** Options failing these are eliminated
**Weighted Criteria:** Used for scoring remaining options
```

### Step 4: Score Options

```markdown
## Option Scoring

| Criterion (Weight) | Option A | Option B | Option C |
|--------------------|----------|----------|----------|
| [C1] (5) | 4 (20) | 3 (15) | 5 (25) |
| [C2] (3) | 3 (9) | 4 (12) | 2 (6) |
| [C3] (2) | 5 (10) | 2 (4) | 4 (8) |
| **Total** | **39** | **31** | **39** |

**Score Notes:**
- Option A: [Why these scores]
- Option B: [Why these scores]
- Option C: [Why these scores]
```

### Step 5: Assess Reversibility

```markdown
## Reversibility Assessment

| Option | Reversibility | Cost to Reverse | Time to Reverse |
|--------|---------------|-----------------|-----------------|
| A | [Easy/Hard/Impossible] | [Low/Medium/High] | [Time] |
| B | [...] | [...] | [...] |
| C | [...] | [...] | [...] |

**Risk Tolerance:** [Low/Medium/High]
**Recommendation Based on Reversibility:** [If close scores, prefer reversible]
```

### Step 6: Document Decision

```markdown
## Decision Record

**Date:** [Date]
**Decision:** [What was decided]
**Option Selected:** [Which option]

**Rationale:**
[Why this option was chosen over others]

**Key Trade-offs Accepted:**
- [Trade-off 1]: Accepting [downside] for [upside]

**Dissenting Views:**
- [Stakeholder]: [Their concern]
- Response: [How addressed or why overridden]

**Success Criteria:**
- [Metric 1]: [Target]
- [Metric 2]: [Target]

**Review Date:** [When to revisit]
**Reversal Trigger:** [What would cause us to change course]
```

## Output Format

```markdown
## Decision: [Title]

### Summary
**Decision:** [One-line statement]
**Date:** [Date]
**Confidence:** [High/Medium/Low]

### Options Considered
1. **[Selected]** - [Brief description]
2. [Rejected] - [Why not]
3. [Rejected] - [Why not]

### Key Factors
- [Factor 1]: Favored [option] because [reason]
- [Factor 2]: [...]

### Trade-offs
- Accepting: [Downside accepted]
- Gaining: [Upside gained]

### Risks and Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk] | [L/M/H] | [L/M/H] | [Action] |

### Success Metrics
- [Metric]: [Target] by [Date]

### Review
- **Next Review:** [Date]
- **Reversal Trigger:** [Condition]
```

## Decision Quality Checklist

```markdown
## Decision Quality Check

**Process:**
- [ ] Clear decision statement
- [ ] Multiple genuine options considered
- [ ] Relevant criteria identified
- [ ] Stakeholders consulted
- [ ] Reversibility assessed

**Reasoning:**
- [ ] Criteria weights justified
- [ ] Scores defensible
- [ ] Trade-offs explicit
- [ ] Dissent captured

**Documentation:**
- [ ] Rationale recorded
- [ ] Success criteria defined
- [ ] Review date set
- [ ] Reversal triggers identified
```

## Quick Decisions (Type 2)

For reversible, lower-stakes decisions:

```markdown
## Quick Decision: [Topic]

**Options:** A vs B vs C
**Key Criterion:** [Most important factor]
**Choice:** [Selected option]
**Rationale:** [One sentence]
**Reversible:** Yes, by [how]
```

## Anti-Patterns

- Analysis paralysis on Type 2 decisions
- Insufficient analysis on Type 1 decisions
- Ignoring "do nothing" option
- Criteria chosen to justify preferred option (backwards reasoning)
- Not documenting rationale (unable to learn from outcomes)
- Treating all decisions as equally important
- Not defining reversal triggers
