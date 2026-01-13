# Planning Horizon

Multi-horizon planning for tasks, features, and architectural evolution.

## When to Use

- Starting new features or projects
- Sprint/iteration planning
- Architecture discussions
- Balancing immediate needs with future vision
- Keywords: "plan", "roadmap", "strategy", "phases", "timeline"

## Planning Horizons

| Horizon | Scope | Timeframe | Focus |
|---------|-------|-----------|-------|
| **H1: Immediate** | This task | Hours-Days | Execution |
| **H2: Near-term** | This sprint/feature | Days-Weeks | Delivery |
| **H3: Medium-term** | This quarter | Weeks-Months | Capability |
| **H4: Long-term** | Architecture evolution | Months-Years | Vision |

## Workflow

### Step 1: Establish Context

```markdown
## Planning Context

**Current Task:** [What triggered this planning]
**Current Position:** [Where we are now]
**Constraints:**
- Time: [Deadlines]
- Resources: [People, budget]
- Technical: [Limitations]
- Dependencies: [Blockers, prerequisites]
```

### Step 2: Plan Each Horizon

#### Horizon 1: Immediate (This Task)

```markdown
## H1: Immediate Plan

**Goal:** [What to accomplish now]
**Timebox:** [Hours/days]

**Tasks:**
1. [ ] [Task 1] - [Duration]
2. [ ] [Task 2] - [Duration]
3. [ ] [Task 3] - [Duration]

**Definition of Done:**
- [ ] [Criterion 1]
- [ ] [Criterion 2]

**Blockers:**
- [Blocker]: [Resolution path]
```

#### Horizon 2: Near-term (This Sprint/Feature)

```markdown
## H2: Near-term Plan

**Goal:** [Feature/sprint objective]
**Timeline:** [Start - End]

**Milestones:**
| Milestone | Target Date | Criteria |
|-----------|-------------|----------|
| M1: [Name] | [Date] | [What's done] |
| M2: [Name] | [Date] | [What's done] |

**Dependencies:**
| Dependency | Type | Status | Owner |
|------------|------|--------|-------|
| [Dep 1] | [Blocking/Informing] | [Status] | [Who] |

**Risks:**
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk] | [L/M/H] | [L/M/H] | [Action] |
```

#### Horizon 3: Medium-term (This Quarter)

```markdown
## H3: Medium-term Plan

**Goal:** [Quarterly objective]
**Timeline:** [Quarter]

**Key Outcomes:**
1. [Outcome 1] - [Success metric]
2. [Outcome 2] - [Success metric]
3. [Outcome 3] - [Success metric]

**Capability Building:**
- [Capability]: [Why needed for future]

**Technical Debt:**
| Item | Priority | Planned Sprint |
|------|----------|----------------|
| [Debt 1] | [P1/P2/P3] | [When] |

**Learning Goals:**
- [Skill/knowledge to acquire]
```

#### Horizon 4: Long-term (Architecture Evolution)

```markdown
## H4: Long-term Vision

**Target State:** [Where we want to be]
**Timeline:** [6-18 months]

**Evolution Path:**
```
Current State → Phase 1 → Phase 2 → Target State
    [Now]       [+3mo]     [+6mo]     [+12mo]
```

**Architectural Decisions:**
| Decision | Options | Direction | Rationale |
|----------|---------|-----------|-----------|
| [Decision] | [A, B, C] | [Leaning] | [Why] |

**Technology Radar:**
| Technology | Status | Notes |
|------------|--------|-------|
| [Tech 1] | Adopt/Trial/Assess/Hold | [Why] |

**Principles Guiding Evolution:**
1. [Principle 1]
2. [Principle 2]
```

### Step 3: Map Dependencies

```markdown
## Dependency Map

### Across Horizons
```
H4 Vision
    ↑ informs
H3 Capabilities
    ↑ enables
H2 Features
    ↑ contributes
H1 Tasks
```

### Blocking Dependencies
| From | To | Dependency | Critical Path? |
|------|----|------------|----------------|
| [H1 Task] | [H2 Milestone] | [What] | [Yes/No] |

### Information Dependencies
| From | To | Information Needed |
|------|----|-------------------|
| [H3 Decision] | [H2 Design] | [What info] |
```

### Step 4: Align Horizons

```markdown
## Horizon Alignment Check

**Does H1 work contribute to H2 goals?**
[Yes/No - explanation]

**Does H2 delivery enable H3 outcomes?**
[Yes/No - explanation]

**Does H3 build toward H4 vision?**
[Yes/No - explanation]

**Misalignments Found:**
- [Misalignment]: [How to resolve]

**Adjustments Needed:**
- [Adjustment to horizon X]
```

## Output Format

```markdown
## Multi-Horizon Plan: [Context]

### Overview
| Horizon | Goal | Timeline | Status |
|---------|------|----------|--------|
| H1 | [Immediate goal] | [Days] | [Status] |
| H2 | [Sprint goal] | [Weeks] | [Status] |
| H3 | [Quarter goal] | [Months] | [Status] |
| H4 | [Vision] | [Year+] | [Direction] |

### H1: Immediate
[Detailed task list]

### H2: Near-term
[Milestones and dependencies]

### H3: Medium-term
[Outcomes and capabilities]

### H4: Long-term
[Vision and evolution path]

### Critical Dependencies
[Key blockers and paths]

### Alignment
[How horizons connect]
```

## Horizon Interaction Patterns

### Top-Down (Vision-Driven)
H4 vision shapes H3 outcomes, which define H2 features, which break into H1 tasks.

### Bottom-Up (Reality-Driven)
H1 learnings inform H2 adjustments, which reshape H3 priorities, which may shift H4 direction.

### Middle-Out (Delivery-Driven)
H2 delivery focus with H1 task breakdown and H3 context awareness.

## Planning Cadence

| Horizon | Review Frequency | Revision Frequency |
|---------|------------------|-------------------|
| H1 | Daily | As needed |
| H2 | Weekly | Sprint boundaries |
| H3 | Monthly | Quarterly |
| H4 | Quarterly | Annually |

## Anti-Patterns

- Planning only H1 (reactive, no direction)
- Planning only H4 (visionary, no execution)
- Misaligned horizons (work doesn't ladder up)
- Over-detailed long-term plans (false precision)
- Ignoring dependencies (surprised by blockers)
- Static plans (not adapting to learnings)
