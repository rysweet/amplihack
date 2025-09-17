# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**Microsoft Hackathon 2025 - Agentic Coding Framework**

We are building an advanced agentic coding framework that leverages AI agents to accelerate software development through intelligent automation, code generation, and collaborative problem-solving.

## 🔴 CRITICAL: Decision Recording Requirements

**EVERY SESSION MUST MAINTAIN DECISION RECORDS**

### When to Record Decisions

Record a decision IMMEDIATELY when you:
- **Start any task** (using TodoWrite or otherwise)
- **Call any agent** (architect, builder, reviewer, etc.)
- **Make architectural choices** (approach, design, tools)
- **Encounter blockers** (errors, missing files, unclear requirements)
- **Complete major steps** (implementation done, tests passing)
- **Use /ultrathink** (record each phase)

### Session ID Generation

Generate session ID on FIRST action:
```
Format: YYYY-MM-DD-HHMMSS
Example: 2025-01-16-143022
```

### Decision Record Template

**Location**: `.claude/runtime/logs/{session_id}/DECISIONS.md`

```markdown
## [Timestamp] - [Component/Agent/Command]
**Decision**: What was decided
**Reasoning**: Why this approach
**Alternatives**: What else was considered
**Impact**: What this changes/affects
**Next Steps**: What happens next
---
```

### Example Decision Record

```markdown
## 2025-01-16 14:30:22 - /ultrathink
**Decision**: Use architect agent to analyze caching requirements
**Reasoning**: Complex architectural decision needs proper analysis
**Alternatives**: Direct implementation, use builder agent
**Impact**: Will create specifications before implementation
**Next Steps**: Call architect with problem context
---

## 2025-01-16 14:31:45 - Architect Agent
**Decision**: Implement file-based cache with TTL
**Reasoning**: Simplest solution, no external dependencies
**Alternatives**: Redis, in-memory cache, database cache
**Impact**: Creates new cache module in /modules/cache
**Next Steps**: Builder agent to implement specification
---
```

### Enforcement Checklist

- [ ] Session directory created on first action?
- [ ] Decision recorded for task start?
- [ ] Decision recorded for each agent call?
- [ ] Decision recorded for approach selection?
- [ ] Decision recorded for completion?

## Important Files to Import

When starting a session, import these files for context:

```
@.claude/context/PHILOSOPHY.md
@.claude/context/PROJECT.md
@.claude/context/PATTERNS.md
@.claude/context/USER_PREFERENCES.md
@.claude/agents/CATALOG.md
@DISCOVERIES.md
```

## Working Philosophy

### Critical Operating Principles

- **RECORD DECISIONS FIRST**: Before ANY action, record what you're about to do and why
- **Always think through a plan**: For any non-trivial task, break it down and use TodoWrite tool to manage a todo list
- **Use specialized agents**: Check `.claude/agents/CATALOG.md` for available agents and use them proactively
- **Ask for clarity**: If requirements are unclear, ask questions before proceeding
- **Document learnings**: Update DISCOVERIES.md with new insights

**Decision Recording Triggers**:
- TodoWrite usage → Record task breakdown decision
- Agent delegation → Record why this agent
- Error/blocker → Record pivot decision
- Completion → Record outcome and learnings

### Agent Delegation Strategy

**Always ask**: "What agents can help with this task?"

- **Architecture tasks** → Use architect agent
- **Implementation** → Use builder agent
- **Debugging/Review** → Use reviewer agent
- **Database work** → Use database agent
- **Security concerns** → Use security agent
- **External APIs** → Use integration agent

### Parallel Execution

**CRITICAL**: Always consider what can be done in parallel. Send ONE message with MULTIPLE tool calls.

Good:
```
"I'll analyze these files in parallel"
[Single message: Read file1.py, Read file2.py, Read file3.py]
```

Bad:
```
"Let me read the first file"
[Read file1.py]
"Now let me read the second file"
[Read file2.py]
```

## Development Principles

### Ruthless Simplicity
- Start with the simplest solution that works
- Add complexity only when justified
- Question every abstraction

### Modular Design (Bricks & Studs)
- **Brick** = Self-contained module with ONE responsibility
- **Stud** = Public contract others connect to
- **Regeneratable** = Can be rebuilt from specification

### Zero-BS Implementation
- No stubs or placeholders
- Every function must work or not exist
- Use files instead of external services initially

## Project Structure

```
.claude/
├── context/          # Philosophy, patterns, project info
├── agents/           # Specialized AI agents
├── commands/         # Slash commands (/ultrathink, /analyze, /improve)
├── tools/            # Hooks and utilities
└── runtime/          # Logs, metrics, analysis

Specs/               # Module specifications
```

## Key Commands

### /ultrathink <task>
Deep analysis mode using multiple agents
**AUTO-RECORDS**: Creates session and records phase decisions

### /analyze <path>
Comprehensive code review for philosophy compliance

### /improve [target]
Self-improvement and learning capture

## Testing & Validation

After code changes:
1. Run tests if available
2. Check philosophy compliance
3. Verify module boundaries
4. Update DISCOVERIES.md with learnings
5. **Record completion decision** in session log

## Common Patterns

See `.claude/context/PATTERNS.md` for:
- Claude Code SDK integration
- Resilient batch processing
- File I/O with retries
- Async context management
- Module regeneration structure

## Self-Improvement

The system should continuously improve:
- Track patterns in `.claude/context/PATTERNS.md`
- Document discoveries in `DISCOVERIES.md`
- Update agent definitions as needed
- Create new agents for repeated tasks

## Success Metrics

We measure success by:
- Code simplicity and clarity
- Module independence
- Agent effectiveness
- Knowledge capture rate
- Development velocity

## Getting Help

- Review `.claude/context/PHILOSOPHY.md` for principles
- Check `.claude/agents/CATALOG.md` for agent capabilities
- Look in `.claude/context/PATTERNS.md` for solutions
- Update `DISCOVERIES.md` with new learnings

---

Remember: You are the orchestrator working with specialized agents. Delegate liberally, execute in parallel, and continuously learn.