# Decision Recording Quick Reference

## WHEN to Record (IMMEDIATELY)
- **Task Start**: First thing when you begin any work
- **Agent Call**: Before delegating to any agent
- **Design Choice**: When selecting an approach
- **Blocker Hit**: When encountering errors/issues
- **Task Complete**: When finishing any work

## WHERE to Record
```
.claude/runtime/logs/{session_id}/DECISIONS.md
```
Session ID Format: `YYYY-MM-DD-HHMMSS` (e.g., `2025-01-16-143022`)

## WHAT to Record (Copy This)
```markdown
## [Timestamp] - [Component]
**Decision**: What was decided
**Reasoning**: Why this approach
**Alternatives**: What else was considered
**Impact**: What this changes
**Next Steps**: What happens next
---
```

## Quick Examples

### Starting Work
```markdown
## 2025-01-16 14:30:22 - Task Start
**Decision**: Implement caching for API responses
**Reasoning**: Performance issues with repeated API calls
**Alternatives**: Rate limiting, request batching
**Impact**: New cache module, reduced API load
**Next Steps**: Use architect agent to design cache
---
```

### Calling Agent
```markdown
## 2025-01-16 14:31:45 - Architect Agent
**Decision**: Use architect to design cache system
**Reasoning**: Complex requirements need proper analysis
**Alternatives**: Direct implementation, builder agent
**Impact**: Will get specifications before coding
**Next Steps**: Provide requirements to architect
---
```

### Making Choice
```markdown
## 2025-01-16 14:35:10 - Technical Decision
**Decision**: Use file-based cache with TTL
**Reasoning**: Simple, no external dependencies
**Alternatives**: Redis, memory cache, database
**Impact**: Creates /cache directory, adds TTL logic
**Next Steps**: Builder agent to implement spec
---
```

## Decision Triggers Checklist
- [ ] Starting TodoWrite? → Record task breakdown
- [ ] Calling agent? → Record why this agent
- [ ] Choosing approach? → Record selection
- [ ] Hit error? → Record pivot strategy
- [ ] Task done? → Record completion

## Common Commands & Decisions

| Command | Decision to Record |
|---------|-------------------|
| `/ultrathink` | Analysis approach, agent sequence |
| `/analyze` | What to review, criteria used |
| `/improve` | What to enhance, metrics targeted |
| `TodoWrite` | Task breakdown reasoning |
| Agent call | Why this agent, what to achieve |

## Quality Checks
✅ **Good**: "Use Redis for session storage due to horizontal scaling needs"
❌ **Bad**: "Use Redis"

✅ **Good**: "Call architect agent to analyze complex auth requirements"
❌ **Bad**: "Call architect"

✅ **Good**: "Switch from REST to GraphQL to reduce over-fetching"
❌ **Bad**: "Change API"

## Remember
**RECORD FIRST, ACT SECOND** - Your future self will thank you!