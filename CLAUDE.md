# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

**Microsoft Hackathon 2025 - Agentic Coding Framework**

We are building an advanced agentic coding framework that leverages AI agents to accelerate software development through intelligent automation, code generation, and collaborative problem-solving.

## Decision Recording

Record significant decisions in `.claude/runtime/logs/{session_id}/DECISIONS.md`
Format: Decision | Reasoning | Alternatives | Impact | Next Steps

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

- **Always think through a plan**: For any non-trivial task, break it down and use TodoWrite tool to manage a todo list
- **Use specialized agents**: Check `.claude/agents/amplihack/*.md` for available agents and use them proactively
- **Ask for clarity**: If requirements are unclear, ask questions before proceeding
- **Document learnings**: Update DISCOVERIES.md with new insights
- **Session Logs**: All interactions MUST be logged in .claude/runtime/logs/<session_id> where <session_id> is a unique identifier for the session based on the timestamp.
- **Decision records**: All Agents MUST log their decisions and reasoning in .claude/runtime/logs/<session_id>/DECISIONS.md

### Agent Delegation Strategy

**GOLDEN RULE**: You are an orchestrator, not an implementer. ALWAYS delegate to specialized agents when possible.

#### When to Use Agents (ALWAYS IF POSSIBLE)

**Immediate Delegation Triggers:**

- **System Design**: Use `architect.md` for specifications and problem decomposition
- **Implementation**: Use `builder.md` for code generation from specs
- **Code Review**: Use `reviewer.md` for philosophy compliance checks
- **Testing**: Use `tester.md` for test generation and validation
- **API Design**: Use `api-designer.md` for contract definitions
- **Performance**: Use `optimizer.md` for bottleneck analysis
- **Security**: Use `security.md` for vulnerability assessment
- **Database**: Use `database.md` for schema and query optimization
- **Integration**: Use `integration.md` for external service connections
- **Cleanup**: Use `cleanup.md` for code simplification
- **Pattern Recognition**: Use `patterns.md` to identify reusable solutions
- **Analysis**: Use `analyzer.md` for deep code understanding
- **Ambiguity**: Use `ambiguity.md` when requirements are unclear

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