# Simple Memory Agent - Usage Guide

## Overview

The Simple Memory Agent provides persistent session memory using plain markdown files and JSON. No code, no databases, no external dependencies.

## Quick Start

### Enable for Your Session

Just mention the memory agent in your prompt:
```
@.claude/agents/amplihack/specialized/memory-agent.md

I need help building a new API. Please use session memory to track our progress.
```

That's it! The agent will automatically create and maintain memory files.

## What Gets Stored

### Session Directory Structure

```
.claude/runtime/memory/sessions/api-development-2025-10-19/
├── context.md          # What you're working on
├── discoveries.md      # Key findings
├── decisions.json      # Important decisions
└── todos.json          # Task tracking
```

### Example Memory Files

**context.md:**
```markdown
# API Development Session

## Objective
Build REST API for user management with authentication

## Current Phase
Implementing authentication endpoints

## Key Requirements
- JWT-based auth
- Password hashing with bcrypt
- Email verification flow
```

**discoveries.md:**
```markdown
## 2025-10-19 14:23 Discovery: Error Handling Pattern

All existing endpoints use consistent error format.
Can standardize across new API.

**Impact:** Reduces code duplication
**Next Steps:** Create shared error handler
```

**decisions.json:**
```json
{
  "decisions": [
    {
      "timestamp": "2025-10-19T14:30:00Z",
      "decision": "Use JWT for authentication",
      "rationale": "Stateless, scalable, industry standard",
      "alternatives": ["Sessions", "OAuth only"],
      "impact": "Enables microservices architecture"
    }
  ]
}
```

## Common Use Cases

### Resume Previous Work

```
User: "Continue the API work from yesterday"

Agent:
1. Reads .claude/runtime/memory/sessions/api-development-2025-10-18/
2. Reviews context, discoveries, and todos
3. Picks up exactly where you left off

Response: "Resuming API development. Yesterday we implemented
authentication. Found 3 pending tasks: email verification,
password reset, and rate limiting. Shall we start with email
verification?"
```

### Track Decisions

Memory agent automatically logs significant decisions:
- Architecture choices
- Library selections
- Design trade-offs
- Implementation approaches

### Share Knowledge

Promote valuable patterns to shared memory:

```
Agent discovers useful pattern → saves to session
Pattern proves valuable → promotes to shared/patterns/
Other agents reference shared patterns
```

## Benefits

### vs Complex Solutions

**Simple Memory Agent:**
- ✅ Zero setup - just reference the agent
- ✅ Human-readable files (markdown/JSON)
- ✅ Git-trackable history
- ✅ No external dependencies
- ✅ Works offline
- ✅ Instant debugging (cat memory.md)

**Complex Database Systems:**
- ❌ Installation required
- ❌ Binary formats
- ❌ External dependencies
- ❌ Network required
- ❌ Complex debugging

### Simplicity Comparison

| Feature | Simple Agent | Beads Integration | Database |
|---------|-------------|------------------|----------|
| Setup Time | 0 minutes | 30 minutes | Hours |
| LOC | 0 (markdown) | 2,464 | Varies |
| Dependencies | None | Beads CLI | DB server |
| Learning Curve | Instant | Days | Weeks |
| Maintenance | None | Medium | High |

## Advanced Features

### Cross-Session Patterns

```
.claude/runtime/memory/shared/patterns/
├── api-error-handling.md
├── authentication-flow.md
└── test-strategy.md
```

Agents automatically reference shared patterns when relevant.

### Session Linking

Link related sessions:

```markdown
# context.md
Related Sessions:
- [api-development-2025-10-18](../api-development-2025-10-18/)
- [auth-bug-fix-2025-10-17](../auth-bug-fix-2025-10-17/)
```

### Team Collaboration

Memory files are in `.claude/runtime/` (gitignored), but you can:
- Manually commit important discoveries to docs/
- Share session directories with teammates
- Export patterns to project documentation

## Limitations

**Works well for:**
- Individual developers
- Linear workflows
- Short-to-medium sessions (days-weeks)
- Up to ~1000 memory entries

**Consider upgrading when:**
- Need graph relationships (task dependencies)
- Multiple concurrent users
- Complex cross-session queries
- Very large corpus (10,000+ entries)

## Integration with Workflow

Memory agent integrates naturally with DEFAULT_WORKFLOW.md:

**Step 1 (Requirements):** Store requirements in context.md
**Step 4 (Design):** Log design decisions
**Step 5 (Implementation):** Track progress in todos.json
**Step 6 (Refactor):** Document discoveries
**Step 15 (Cleanup):** Summarize outcomes

## Philosophy Alignment

✅ **Ruthless Simplicity**: File-based, zero complexity
✅ **Zero-BS**: Works immediately, no setup
✅ **Standard Library**: Uses existing file operations
✅ **Modular**: Self-contained instructions
✅ **Regeneratable**: Clear docs enable recreation

## Validation Period

**Recommendation:** Use simple memory for 2-3 weeks before considering more complex solutions. Most use cases may never need more than this.

## Getting Started

1. Reference memory agent in your next session:
   ```
   @.claude/agents/amplihack/specialized/memory-agent.md
   ```

2. Work naturally - agent handles memory automatically

3. Review memory files to see what was captured:
   ```bash
   ls .claude/runtime/memory/sessions/
   cat .claude/runtime/memory/sessions/{your-session}/context.md
   ```

4. Use for a few sessions and assess if it meets your needs

## Support

Memory agent is self-documenting. Read `.claude/agents/amplihack/specialized/memory-agent.md` for complete instructions and examples.

---

**Created:** 2025-10-19
**Philosophy:** Ruthless Simplicity - 0 LOC implementation
