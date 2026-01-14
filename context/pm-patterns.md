# PM Cognitive Offloading Patterns

Patterns for using AI agents to reduce cognitive load on project managers and technical leads.

---

## The Cognitive Load Problem

Project managers and tech leads face constant context switching:
- Tracking multiple workstreams
- Remembering decisions and their rationale
- Maintaining project state across conversations
- Ensuring nothing falls through cracks

**AI agents can serve as external cognitive systems** that maintain state, track decisions, and surface relevant context at the right time.

---

## Pattern 1: Decision Journal

**Problem**: Decisions get made but rationale is forgotten. Same discussions repeat.

**Pattern**: Maintain a structured decision log that agents reference and update.

### Structure

```markdown
# Decision Journal

## [DATE] - Decision Title

**Status**: Proposed | Accepted | Superseded | Rejected

**Context**: Why this decision was needed

**Decision**: What was decided

**Alternatives Considered**:
1. [Option A] - [Why rejected]
2. [Option B] - [Why rejected]

**Consequences**:
- [Positive consequence]
- [Negative consequence / trade-off]

**Revisit When**: [Trigger for reconsidering]
```

### Agent Behavior

When a decision topic comes up, agent should:
1. Check decision journal for prior decisions
2. Surface relevant history: "We discussed this on [date]. Decision was [X] because [Y]."
3. Ask if circumstances have changed before re-deciding

### Template Command

```
"Before we decide on [topic], check if we've discussed this before."
```

---

## Pattern 2: Context Resurrection

**Problem**: Returning to a task after days/weeks, context is lost.

**Pattern**: Create "context packages" that can fully restore working state.

### Structure

```markdown
# Context Package: [Feature/Task Name]

## Last Active
Date: YYYY-MM-DD
Session: [link or ID]

## Current State
- What's done: [list]
- What's in progress: [list]
- What's blocked: [list]

## Key Files
- `path/to/main/file.py` - [what it does]
- `path/to/config.yaml` - [what to know]

## Active Questions
- [ ] [Unresolved question 1]
- [ ] [Unresolved question 2]

## Next Steps
1. [Immediate next action]
2. [Following action]

## Gotchas to Remember
- [Thing that tripped us up]
- [Non-obvious requirement]
```

### Agent Behavior

When resuming work on a feature:
1. Load the context package
2. Summarize state: "Last worked on [date]. [X] is done, [Y] is in progress."
3. Surface blockers: "There's an unresolved question about [Z]."
4. Suggest next action: "Ready to continue with [next step]?"

### Trigger Phrases

```
"Let's pick up [feature name] - what's the state?"
"Resume work on [task]"
"Where did we leave off with [project]?"
```

---

## Pattern 3: Stakeholder Briefing Generator

**Problem**: Need to communicate project status to different audiences with different concerns.

**Pattern**: Generate audience-appropriate summaries from single source of truth.

### Audience Templates

**Executive Summary** (for leadership):
```markdown
## [Project] Status - [Date]

**Health**: 🟢 On Track | 🟡 At Risk | 🔴 Blocked

**Key Metrics**:
- Timeline: [on schedule / X days behind]
- Scope: [100% / reduced by X%]
- Budget: [on budget / X% over]

**This Week**: [One sentence on progress]

**Risks**: [Top risk if any]

**Needs from Leadership**: [Ask if any]
```

**Technical Update** (for engineering):
```markdown
## [Project] Technical Update - [Date]

**Completed**:
- [Technical accomplishment 1]
- [Technical accomplishment 2]

**In Progress**:
- [Current technical work]

**Technical Decisions Made**:
- [Decision and brief rationale]

**Blockers**:
- [Technical blocker and what's needed]

**Code Locations**: [Key PRs, branches]
```

**Stakeholder Update** (for business):
```markdown
## [Project] Update - [Date]

**Progress**: [X]% complete

**What's Working**:
- [Business capability delivered]

**What's Next**:
- [Upcoming business capability]

**Timeline**: [Expected delivery date]

**Dependencies**: [What we need from stakeholders]
```

### Agent Behavior

```
User: "Generate status update for [audience]"
Agent: [Gathers current state, generates appropriate format]
```

---

## Pattern 4: Risk Radar

**Problem**: Risks emerge gradually and aren't noticed until they become problems.

**Pattern**: Continuously assess and surface potential risks.

### Risk Categories

| Category | Signals to Watch |
|----------|------------------|
| **Timeline** | Tasks taking longer than estimated, blockers accumulating |
| **Technical** | Increasing complexity, architectural concerns, tech debt |
| **Resource** | Key person dependencies, skill gaps, availability issues |
| **Scope** | Requirements changes, feature creep, unclear requirements |
| **External** | Dependency delays, API changes, vendor issues |

### Risk Entry Structure

```markdown
### Risk: [Title]

**Category**: [Timeline/Technical/Resource/Scope/External]
**Likelihood**: High | Medium | Low
**Impact**: High | Medium | Low
**Status**: Active | Monitoring | Mitigated | Occurred

**Description**: [What might happen]

**Early Signals**: [How we'll know it's materializing]

**Mitigation**: [What we can do to prevent/reduce]

**Contingency**: [What we'll do if it happens]

**Owner**: [Who's watching this]
```

### Agent Behavior

During work, agents should:
1. Notice risk signals (delays, complexity, blockers)
2. Check if risk is already tracked
3. If new, suggest adding to risk radar
4. If existing, suggest updating status

```
"I notice [signal]. This might be related to the [risk] we identified. 
Should we update the risk assessment?"
```

---

## Pattern 5: Meeting Preparation

**Problem**: Going into meetings without full context leads to poor decisions.

**Pattern**: Auto-generate meeting prep based on agenda and project state.

### Prep Document Structure

```markdown
# Meeting Prep: [Meeting Title]

**Date**: [Date/Time]
**Attendees**: [List]
**Objective**: [What we need to accomplish]

## Agenda Items

### 1. [Agenda Item]

**Background**: [Relevant context]

**Current State**: [Where things stand]

**Open Questions**:
- [Question 1]
- [Question 2]

**Recommendation**: [If applicable]

**Decision Needed**: Yes/No - [What decision]

### 2. [Next Agenda Item]
...

## Reference Materials
- [Link to relevant doc]
- [Link to relevant PR/issue]

## Action Items from Last Meeting
- [ ] [Item] - [Status]
```

### Agent Behavior

```
User: "Prep me for the [meeting name] meeting"
Agent: 
1. Identify meeting agenda (from calendar, doc, or ask)
2. For each agenda item, gather relevant project context
3. Surface open questions and pending decisions
4. Note action items from previous meeting
```

---

## Pattern 6: Knowledge Handoff

**Problem**: When someone leaves or joins, knowledge transfer is incomplete.

**Pattern**: Maintain structured knowledge that can be transferred.

### Handoff Document Structure

```markdown
# Knowledge Handoff: [Area/Role]

## Overview
[What this area covers and why it matters]

## Key Responsibilities
1. [Responsibility] - [Frequency/Trigger]
2. [Responsibility] - [Frequency/Trigger]

## Regular Tasks
| Task | Frequency | How-To |
|------|-----------|--------|
| [Task] | [Daily/Weekly/etc] | [Brief instructions or link] |

## Key Relationships
| Who | Relationship | How to Work With |
|-----|--------------|------------------|
| [Person/Team] | [What they provide/need] | [Tips] |

## Systems & Access
| System | Purpose | Access Request |
|--------|---------|----------------|
| [System] | [What it's for] | [How to get access] |

## Tribal Knowledge
- [Thing that's not documented but important]
- [Gotcha that trips people up]
- [Historical context that explains current state]

## Current State
- [Active projects/initiatives]
- [Pending decisions]
- [Known issues]

## Where to Find Things
| Type | Location |
|------|----------|
| Documentation | [Path/Link] |
| Code | [Repo/Path] |
| Decisions | [Path to decision log] |
| Metrics | [Dashboard link] |
```

---

## Pattern 7: Async Standup Synthesis

**Problem**: Async updates scattered across channels, hard to get overall picture.

**Pattern**: Synthesize updates into coherent team status.

### Individual Update Format

```markdown
## [Name] - [Date]

**Yesterday**: 
- [What was accomplished]

**Today**:
- [What's planned]

**Blockers**:
- [Any blockers]

**FYI**:
- [Anything team should know]
```

### Team Synthesis Format

```markdown
# Team Status - [Date]

## Progress Highlights
- [Key accomplishment across team]
- [Key accomplishment across team]

## In Flight
- [Feature A]: [Status] - [Who]
- [Feature B]: [Status] - [Who]

## Blockers Requiring Action
- [Blocker]: [Who's blocked] - [What's needed]

## Cross-Team Dependencies
- [Dependency]: [Status]

## Calendar
- [Upcoming deadline or event]
```

---

## Implementation Guidance

### For Agents

1. **Recognize PM patterns**: When user asks PM-type questions, apply these patterns
2. **Maintain state**: Update relevant documents as work progresses
3. **Surface proactively**: Don't wait to be asked - surface relevant context
4. **Adapt format**: Adjust detail level to audience and situation

### For Users

1. **Establish documents**: Create the structured documents upfront
2. **Reference consistently**: Point agents to the right documents
3. **Review regularly**: Patterns work best when documents stay current
4. **Iterate on format**: Adapt templates to your actual needs

### Trigger Phrases

| Need | Say |
|------|-----|
| Record decision | "Let's log this decision..." |
| Resume work | "What's the state of [X]?" |
| Status update | "Generate [audience] update for [project]" |
| Risk check | "Any risks emerging on [project]?" |
| Meeting prep | "Prep me for [meeting]" |
| Handoff | "Create handoff doc for [area]" |
| Team status | "Synthesize today's updates" |
