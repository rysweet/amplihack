# Multi-Perspective Analyzer

Cross-discipline synthesis by deploying multiple analytical perspectives simultaneously.

## When to Use

- Complex decisions with multiple stakeholders
- Problems that span technical and non-technical domains
- Need to surface blind spots in thinking
- Keywords: "perspectives", "stakeholders", "cross-functional", "holistic view"

## Core Concept

Deploy 3-5 distinct perspectives on a problem simultaneously, then synthesize insights into a unified analysis that captures the full picture.

## Perspective Categories

### Technical Perspectives

| Perspective | Focus | Key Questions |
|-------------|-------|---------------|
| **Architect** | System design, scalability | "How does this fit the bigger picture?" |
| **Security** | Threats, vulnerabilities | "What could go wrong? Who might exploit this?" |
| **Performance** | Speed, efficiency, resources | "Will this scale? What are the bottlenecks?" |
| **Operations** | Deployment, monitoring, maintenance | "How do we run this in production?" |
| **Developer** | Implementation, maintainability | "How hard is this to build and change?" |

### Business Perspectives

| Perspective | Focus | Key Questions |
|-------------|-------|---------------|
| **Product** | User value, market fit | "Does this solve a real problem?" |
| **Business** | Revenue, cost, ROI | "Is this worth the investment?" |
| **User** | Experience, usability | "Would I want to use this?" |
| **Support** | Troubleshooting, documentation | "Can we help users when things break?" |

### Strategic Perspectives

| Perspective | Focus | Key Questions |
|-------------|-------|---------------|
| **Risk** | What could fail, mitigations | "What's our exposure?" |
| **Timeline** | Deadlines, dependencies | "When can we deliver?" |
| **Resource** | People, budget, tools | "Do we have what we need?" |
| **Opportunity** | Future possibilities | "What doors does this open?" |

## Workflow

### Step 1: Select Perspectives (3-5)

Choose perspectives based on the problem domain:

```markdown
## Perspective Selection

**Problem:** [Brief description]

**Selected Perspectives:**
1. [Perspective 1] - [Why relevant]
2. [Perspective 2] - [Why relevant]
3. [Perspective 3] - [Why relevant]
4. [Perspective 4] - [Why relevant] (optional)
5. [Perspective 5] - [Why relevant] (optional)
```

### Step 2: Deploy Perspectives

Analyze the problem from each perspective independently:

```markdown
### [Perspective Name] Analysis

**Key Observations:**
- [Observation 1]
- [Observation 2]

**Concerns:**
- [Concern 1]
- [Concern 2]

**Opportunities:**
- [Opportunity 1]

**Recommendation:** [What this perspective suggests]
```

### Step 3: Identify Patterns

```markdown
## Cross-Perspective Patterns

**Agreements (2+ perspectives align):**
- [Pattern]: [Which perspectives agree]

**Tensions (perspectives conflict):**
- [Tension]: [Perspective A] vs [Perspective B]

**Blind Spots (gaps in coverage):**
- [Gap]: [What no perspective addressed]
```

### Step 4: Resolve Conflicts

| Conflict Type | Resolution Strategy |
|---------------|---------------------|
| **Priority** | Rank by impact and urgency |
| **Approach** | Find middle ground or sequence |
| **Resource** | Trade-off analysis |
| **Risk** | Mitigate highest severity first |

```markdown
## Conflict Resolution

**Conflict:** [Description]
**Perspectives:** [A] vs [B]
**Resolution:** [How to reconcile]
**Rationale:** [Why this resolution]
```

### Step 5: Synthesize

```markdown
## Synthesis

**Unified Understanding:**
[Combined insight that honors all perspectives]

**Recommended Action:**
[What to do, informed by all perspectives]

**Key Trade-offs Accepted:**
- [Trade-off 1]: [What we gain] vs [What we sacrifice]

**Remaining Concerns:**
- [Concern]: [Mitigation plan]
```

## Output Format

```markdown
## Multi-Perspective Analysis: [Topic]

### Perspectives Deployed
1. [Perspective 1]
2. [Perspective 2]
3. [Perspective 3]

### Individual Analyses

#### [Perspective 1]
- Observations: [...]
- Concerns: [...]
- Recommendation: [...]

#### [Perspective 2]
[...]

### Synthesis

**Agreements:**
- [Point 1]

**Tensions:**
- [Tension 1]: Resolved by [...]

**Unified Recommendation:**
[Final recommendation with rationale]

**Confidence:** [High | Medium | Low]
**Key Assumptions:** [What must be true]
```

## Synthesis Patterns

### Complementary Insights
Perspectives reveal different aspects of the same truth.
*Strategy:* Combine into richer understanding.

### Competing Priorities
Perspectives have different optimization targets.
*Strategy:* Explicit trade-off decision with rationale.

### Sequential Dependencies
One perspective's concerns must be addressed before another's.
*Strategy:* Order recommendations by dependency.

### Hierarchical Override
One perspective's concerns trump others (e.g., security over features).
*Strategy:* Document override and ensure minimum viable for lower priorities.

## Anti-Patterns

- Using too many perspectives (analysis paralysis)
- Selecting only perspectives that agree (confirmation bias)
- Not resolving conflicts (leaving contradictions)
- Treating all perspectives as equal weight
- Forgetting to synthesize (just listing perspectives)
