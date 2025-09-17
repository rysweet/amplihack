# DISCOVERIES.md

This file documents non-obvious problems, solutions, and patterns discovered
during development. It serves as a living knowledge base that grows with the
project.

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

<!-- New discoveries will be added here as the project progresses -->

## Remember

- Document immediately while context is fresh
- Include specific error messages and stack traces
- Show actual code that fixed the problem
- Think about broader implications
- Update PATTERNS.md when a discovery becomes a reusable pattern
