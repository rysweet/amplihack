---
name: INVESTIGATION_WORKFLOW
version: 1.0.0
description: 6-phase workflow for systematic investigation and knowledge excavation
steps: 6
phases:
  - scope-definition
  - exploration-strategy
  - parallel-deep-dives
  - verification
  - synthesis
  - knowledge-capture
success_criteria:
  - "All investigation questions answered"
  - "Understanding verified through testing"
  - "Knowledge documented in DISCOVERIES.md"
  - "Findings ready for implementation decisions"
philosophy_alignment:
  - principle: Analysis First
    application: Understand before building
  - principle: Parallel Execution
    application: Phase 3 uses parallel agent exploration
  - principle: Knowledge Capture
    application: All learnings documented for reuse
customizable: true
---

# Investigation Workflow

6-phase workflow optimized for exploration and understanding, not implementation.

## When This Workflow Applies

Keywords:
- "investigate", "explain", "understand", "how does", "why does"
- "analyze", "research", "explore", "examine", "study"

**Not for development tasks** - Use DEFAULT_WORKFLOW for "implement", "build", "create", "add feature".

## The 6 Phases

### Phase 1: Scope Definition

**Purpose:** Define investigation boundaries and success criteria before any exploration.

**Tasks:**
- Identify explicit user requirements - what specific questions must be answered?
- Use explorer agent to clarify investigation scope
- Define what counts as "understanding achieved"
- List specific questions that must be answered
- Set boundaries: What's in scope vs. out of scope

**Deliverables:**
- Investigation scope document with core questions, success criteria, scope boundaries

### Phase 2: Exploration Strategy

**Purpose:** Plan which agents to deploy and what to investigate.

**Tasks:**
- Use architect agent to design exploration strategy
- Identify key areas to explore (code paths, configurations, documentation)
- Select specialized agents for parallel deployment in Phase 3
- Create investigation roadmap with priorities

**Agent Selection Guidelines:**
- **For code understanding:** analyzer, explorer agents
- **For system architecture:** architect agents
- **For performance issues:** optimizer agents
- **For security concerns:** security agents
- **For integration flows:** integration agents

**Deliverables:**
- Exploration strategy document with agent deployment plan

### Phase 3: Parallel Deep Dives

**Purpose:** Deploy multiple exploration agents simultaneously.

**CRITICAL: This phase uses PARALLEL EXECUTION by default.**

**Tasks:**
- Deploy selected agents in PARALLEL based on Phase 2 strategy
- Each agent explores their assigned area independently
- Collect findings from all parallel explorations
- Identify connections and dependencies between findings

**Parallel Patterns:**
```
Investigation: "How does the auth system work?"
→ [analyzer(auth-module), security(auth), explorer(auth-docs)]

Investigation: "Why is CI failing?"
→ [analyzer(ci-config), explorer(github-actions), bug-hunter(ci-logs)]
```

**Deliverables:**
- Findings report from each parallel exploration

### Phase 4: Verification & Testing

**Purpose:** Test and validate understanding through practical application.

**Tasks:**
- Create hypotheses based on Phase 3 findings
- Design practical tests to verify understanding
- Run verification tests
- Identify gaps in understanding
- Refine hypotheses based on test results

**Deliverables:**
- Verification report with tests performed and results

### Phase 5: Synthesis

**Purpose:** Compile findings into coherent explanation.

**Tasks:**
- Synthesize findings from Phases 3-4 into coherent explanation
- Answer each question from Phase 1 scope definition
- Create visual artifacts (diagrams, flow charts) if helpful
- Note any assumptions or uncertainties remaining

**Synthesis Outputs:**
1. Executive Summary: 2-3 sentence answer to main question
2. Detailed Explanation: Complete explanation with evidence
3. Visual Aids: Diagrams showing system flow, architecture
4. Key Insights: Non-obvious discoveries or patterns
5. Remaining Unknowns: What's still unclear

**Deliverables:**
- Investigation report with all synthesis outputs

### Phase 6: Knowledge Capture

**Purpose:** Create durable documentation so investigation never needs repeating.

**Tasks:**
- Update DISCOVERIES.md with key insights
- Update PATTERNS.md if reusable patterns found
- Create or update relevant documentation files
- Ensure future investigators can find this knowledge easily

**Deliverables:**
- Updated DISCOVERIES.md
- Updated PATTERNS.md (if applicable)
- Investigation session log

## Transitioning to Development

After investigation completes, if implementation is needed:
1. Resume at DEFAULT_WORKFLOW Step 4 (Research and Design) with investigation knowledge
2. Use investigation findings from DISCOVERIES.md to inform design decisions
