# DISCOVERIES.md

This file documents non-obvious problems, solutions, and patterns discovered
during development. It serves as a living knowledge base that grows with the
project.

## Agent Priority Hierarchy Critical Flaw (2025-01-23)

### Issue

Agents were overriding explicit user requirements in favor of project
philosophy. Specifically, when user requested "ALL files" for UVX deployment,
cleanup/simplification agents reduced it to "essential files only", directly
violating user's explicit instruction.

### Root Cause

Agents had philosophy guidance but no explicit instruction that user
requirements override philosophy. The system prioritized simplicity principles
over user-specified constraints, creating a hierarchy where philosophy > user
requirements instead of user requirements > philosophy.

### Solution

Implemented comprehensive User Requirement Priority System:

1. **Created USER_REQUIREMENT_PRIORITY.md** with mandatory hierarchy:
   - EXPLICIT USER REQUIREMENTS (Highest - Never Override)
   - IMPLICIT USER PREFERENCES
   - PROJECT PHILOSOPHY
   - DEFAULT BEHAVIORS (Lowest)

2. **Updated Critical Agents** with requirement preservation:
   - cleanup.md: Added mandatory user requirement check before any removal
   - reviewer.md: User requirement compliance as first review criteria
   - improvement-workflow.md: User requirement analysis in Stage 1

3. **Enhanced Workflow Safeguards**:
   - DEFAULT_WORKFLOW.md: Multiple validation checkpoints
   - Step 1: Identify explicit requirements FIRST
   - Step 6: Cleanup within user constraints only
   - Step 14: Final requirement preservation check

### Key Learnings

- **User explicit requirements are sacred** - they override all other guidance
- **Philosophy guides HOW to implement** - not WHAT to implement
- **Simple instruction updates** are more effective than complex permission
  systems
- **Multiple validation points** prevent single-point-of-failure in requirement
  preservation
- **Clear priority hierarchy** must be communicated to ALL agents

### Prevention

- All agent instructions now include mandatory user requirement priority check
- Workflow includes explicit requirement capture and preservation steps
- CLAUDE.md updated with priority system as core principle
- Validation scenarios documented for testing agent behavior

### Pattern Recognition

**Trigger Signs of Explicit Requirements:**

- "ALL files", "include everything", "don't simplify X"
- Quoted specifications: "use this exact format"
- Numbered lists of requirements
- "Must have", "explicitly", "specifically"

**Agent Behavior Rule:** Before any optimization/simplification → Check: "Was
this explicitly requested by user?" If YES → Preserve completely regardless of
philosophy

## Format for Entries

Each discovery should follow this format:

```markdown
## [Brief Title] (YYYY-MM-DD)

### Issue

What problem or challenge was encountered?

### Root Cause

Why did this happen? What was the underlying issue?

### Solution

How was it resolved? Include code examples if relevant.

### Key Learnings

What insights were gained? What should be remembered?

### Prevention

How can this be avoided in the future?
```

---

## Project Initialization (2025-01-16)

### Issue

Setting up the agentic coding framework with proper structure and philosophy.

### Root Cause

Need for a well-organized, AI-friendly project structure that supports
agent-based development.

### Solution

Created comprehensive `.claude` directory structure with:

- Context files for philosophy and patterns
- Agent definitions for specialized tasks
- Command system for complex workflows
- Hook system for session tracking
- Runtime directories for metrics and analysis

### Key Learnings

1. **Structure enables AI effectiveness** - Clear organization helps AI agents
   work better
2. **Philosophy guides decisions** - Having written principles prevents drift
3. **Patterns prevent wheel reinvention** - Documented solutions save time
4. **Agent specialization works** - Focused agents outperform general approaches

### Prevention

Always start projects with clear structure and philosophy documentation.

---

## Anti-Sycophancy Guidelines Implementation (2025-01-17)

### Issue

Sycophantic behavior in AI agents erodes user trust. When agents always agree
with users ("You're absolutely right!"), their feedback becomes meaningless and
users stop believing them.

### Root Cause

Default AI training often optimizes for agreeability and user satisfaction,
leading to excessive validation and avoidance of disagreement. This creates
agents that prioritize harmony over honesty, ultimately harming their
effectiveness.

### Solution

Created `.claude/context/TRUST.md` with 7 simple anti-sycophancy rules:

1. Disagree When Necessary - Point out flaws clearly with evidence
2. Question Unclear Requirements - Never guess, always clarify
3. Propose Alternatives - Suggest better approaches when you see them
4. Acknowledge Limitations - Say "I don't know" when appropriate
5. Skip Emotional Validation - Focus on technical merit, not feelings
6. Challenge Assumptions - Question wrong premises
7. Be Direct - No hedging, state assessments plainly

Added TRUST.md to the standard import list in CLAUDE.md to ensure all agents
follow these principles.

### Key Learnings

1. **Trust comes from honesty, not harmony** - Users value agents that catch
   mistakes
2. **Directness builds credibility** - Clear disagreement is better than hedged
   agreement
3. **Questions show engagement** - Asking for clarity demonstrates critical
   thinking
4. **Alternatives demonstrate expertise** - Proposing better solutions shows
   value
5. **Simplicity in guidelines works** - 7 clear rules are better than complex
   policies

### Prevention

- Include TRUST.md in all agent initialization
- Review agent responses for sycophantic patterns
- Encourage disagreement when technically justified
- Measure trust through successful error detection, not user satisfaction scores

---

## Enhanced Agent Delegation Instructions (2025-01-17)

### Issue

The current CLAUDE.md had minimal guidance on when to use specialized agents,
leading to underutilization of available agent capabilities.

### Root Cause

Initial CLAUDE.md focused on basic delegation ("What agents can help?") without
specific triggers or scenarios, missing the orchestration-first philosophy from
the amplifier project.

### Solution

Updated CLAUDE.md with comprehensive agent delegation instructions:

1. Added "GOLDEN RULE" emphasizing orchestration over implementation
2. Created specific delegation triggers mapping tasks to all 13 available agents
3. Included parallel execution examples for complex tasks
4. Added guidance for creating custom agents
5. Emphasized "ALWAYS IF POSSIBLE" for agent delegation

### Key Learnings

1. **Explicit triggers drive usage** - Listing specific scenarios for each agent
   increases delegation
2. **Orchestration mindset matters** - Positioning as orchestrator changes
   approach fundamentally
3. **Parallel patterns accelerate** - Showing concrete parallel examples
   encourages better execution
4. **Agent inventory awareness** - Must explicitly list all available agents to
   ensure usage
5. **Documentation drives behavior** - Clear instructions in CLAUDE.md shape AI
   behavior patterns

### Prevention

- Always compare CLAUDE.md files when porting functionality between projects
- Include specific usage examples for every agent created
- Regularly audit if available agents are being utilized
- Update delegation triggers when new agents are added

---

## Pre-commit Hooks Over-Engineering (2025-09-17)

### Issue

Initial pre-commit hooks implementation had 11+ hooks and 5 configuration files,
violating the project's ruthless simplicity principle.

### Root Cause

Common developer tendency to add "all the good tools" upfront rather than
starting minimal and adding complexity only when justified. The initial
implementation tried to solve problems that didn't exist yet.

### Solution

Simplified to only essential hooks:

```yaml
# From 11+ hooks down to 7 essential ones
repos:
  - pre-commit-hooks:
      check-merge-conflict, trailing-whitespace, end-of-file-fixer
  - ruff: format and basic linting
  - pyright: type checking
  - prettier: JS/TS/Markdown formatting
```

Deleted:

- Custom philosophy checker (arbitrary limits, no tests)
- detect-secrets (premature optimization)
- Complex pytest hook (fragile bash)
- Unused markdownlint config

### Key Learnings

1. **Start minimal, grow as needed** - Begin with 2-3 hooks, add others when
   problems arise
2. **Philosophy enforcement belongs in review** - Human judgment beats arbitrary
   metrics
3. **Dead code spreads quickly** - Commented configs and unused files multiply
4. **Automation can overcomplicate** - Sometimes IDE formatting is simpler than
   hooks
5. **Test your testing tools** - Custom hooks need tests too

### Prevention

- Always question: "What problem does this solve TODAY?"
- Count configuration files - more than 2-3 suggests over-engineering
- If a tool needs extensive configuration, it might be the wrong tool
- Prefer human review for subjective quality measures
- Remember: you can always add complexity, but removing it is harder

---

## CI Failure Resolution Process Analysis (2025-09-17)

### Issue

Complex CI failure resolution for PR 38 took 45 minutes involving version
mismatches, merge conflicts, and pre-commit hook failures. Need to optimize the
debugging process and create better diagnostic tools.

### Root Cause

Multiple compounding factors created a complex debugging scenario:

1. **Silent failures**: Merge conflicts blocked pre-commit hooks without clear
   error messages
2. **Environment mismatches**: Local (Python 3.12.10, ruff 0.12.7) vs CI (Python
   3.11, ruff 0.13.0)
3. **Missing diagnostic tools**: No automated environment comparison or pattern
   recognition
4. **Sequential investigation**: Manual step-by-step debugging instead of
   parallel diagnostics

### Solution

**Multi-agent orchestration approach**:

- Ultra-think coordination with architect, reviewer, and security agents
- Systematic investigation breaking problem into domains
- Persistent 45-minute effort identifying all root causes
- Complete resolution of 7 type errors, 2 unused variables, formatting issues,
  and merge conflict

**Key patterns identified**:

1. **CI Version Mismatch Pattern**: Local tests pass, CI fails on
   linting/formatting
2. **Silent Pre-commit Hook Failure Pattern**: Hooks appear to run but changes
   aren't applied

### Key Learnings

1. **Agent orchestration works for complex debugging**: Specialized agents
   (architect, reviewer, security) effectively decomposed the problem
2. **Silent failures need specialized detection**: Merge conflicts blocking
   tools require dedicated diagnostic capabilities
3. **Environment parity is critical**: Version mismatches cause significant
   investigation overhead (20-25 minutes)
4. **Pattern recognition accelerates resolution**: Known patterns should be
   automated
5. **Time-to-discovery varies by issue type**: Merge conflicts (10 min) vs
   version mismatches (25 min)
6. **Documentation discipline enables learning**: Having PHILOSOPHY.md,
   PATTERNS.md available accelerated analysis

### Prevention

**Immediate improvements needed**:

- **CI Diagnostics Agent**: Automated environment comparison and version
  mismatch detection
- **Silent Failure Detector Agent**: Pre-commit hook validation and merge
  conflict detection
- **Pattern Recognition Agent**: Automated matching to historical failure
  patterns

**Process improvements**:

- Environment comparison should be step 1 in CI failure debugging
- Check merge conflicts before running any diagnostic tools
- Use parallel agent execution for faster diagnosis
- Create pre-flight checks before CI submission

**New agent delegation triggers**:

- CI failures → CI Diagnostics Agent
- Silent tool failures → Silent Failure Detector Agent
- Recurring issues → Pattern Recognition Agent

**Target performance**: Reduce 45-minute complex debugging to 20-25 minutes
through automation and specialized agents.

---

<!-- New discoveries will be added here as the project progresses -->

## Remember

- Document immediately while context is fresh
- Include specific error messages and stack traces
- Show actual code that fixed the problem
- Think about broader implications
- Update PATTERNS.md when a discovery becomes a reusable pattern
