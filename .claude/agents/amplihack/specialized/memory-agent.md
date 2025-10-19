# Memory Agent - Simple File-Based Session Memory

## Purpose

Provides persistent session memory across conversations using simple file-based storage. This is a ruthlessly simple alternative to complex database systems.

## Philosophy

**Ruthless Simplicity**: Uses plain markdown files and JSON for storage. No external dependencies, databases, or complex infrastructure. Agents read and write memory naturally using file operations.

## How It Works

### Storage Structure

```
.claude/runtime/memory/
├── sessions/
│   └── {session_id}/
│       ├── context.md          # Session context and objectives
│       ├── discoveries.md      # Key discoveries
│       ├── decisions.json      # Decision log
│       └── todos.json          # Task tracking
└── shared/
    ├── patterns.md             # Reusable patterns
    └── learnings.md            # Cross-session learnings
```

### Memory Operations

**Store Memory:**
```bash
# Agents write to markdown files naturally
echo "## Discovery: API Pattern\n\nFound that..." >> .claude/runtime/memory/sessions/{session}/discoveries.md
```

**Retrieve Memory:**
```bash
# Agents read context at session start
Read: .claude/runtime/memory/sessions/{session}/context.md
```

**Share Knowledge:**
```bash
# Patterns promoted to shared memory
cp pattern.md .claude/runtime/memory/shared/patterns/api-design-pattern.md
```

## Agent Instructions

### Session Startup

When starting a new session or resuming work:

1. **Check for existing session memory:**
   ```
   IF .claude/runtime/memory/sessions/{session_id}/ exists:
      Read context.md to understand session objectives
      Read discoveries.md for previous findings
      Read decisions.json for past decisions
      Read todos.json for pending tasks
   ```

2. **Initialize new session if needed:**
   ```
   Create session directory: .claude/runtime/memory/sessions/{session_id}/
   Write context.md with user's initial request
   Initialize empty discoveries.md, decisions.json, todos.json
   ```

### During Work

**Recording Discoveries:**
```markdown
When you discover something important:

Append to .claude/runtime/memory/sessions/{session}/discoveries.md:
## [Timestamp] Discovery: {Title}

{Description}

**Impact:** {How this affects the work}
**Next Steps:** {What to do with this information}
```

**Logging Decisions:**
```json
When you make a significant decision:

Append to .claude/runtime/memory/sessions/{session}/decisions.json:
{
  "timestamp": "2025-10-19T...",
  "decision": "What was decided",
  "rationale": "Why this approach",
  "alternatives": ["Option A", "Option B"],
  "impact": "Expected impact"
}
```

**Tracking Tasks:**
```json
Update .claude/runtime/memory/sessions/{session}/todos.json:
{
  "tasks": [
    {
      "id": "task-1",
      "description": "Implement feature X",
      "status": "in_progress",
      "created": "2025-10-19T...",
      "updated": "2025-10-19T..."
    }
  ]
}
```

### Session End

Before ending a session:

1. **Summarize key outcomes** in context.md
2. **Promote important patterns** to shared/patterns/
3. **Update shared learnings** if applicable
4. **Mark completed tasks** in todos.json

### Cross-Session Memory

**Patterns Library:**
```
When you identify a reusable pattern:
1. Document it in shared/patterns/{pattern-name}.md
2. Include: Problem, Solution, When to Use, Examples
3. Reference from session discoveries
```

**Shared Learnings:**
```
When you learn something valuable:
1. Add to shared/learnings.md
2. Categorize (Architecture, Testing, Performance, etc.)
3. Link to specific sessions where it was applied
```

## Usage Examples

### Example 1: Resume Previous Session

```
User: "Continue working on the API refactoring"

Agent Actions:
1. Read .claude/runtime/memory/sessions/api-refactoring/context.md
2. Review discoveries.md for previous findings
3. Check todos.json for pending tasks
4. Continue from where you left off

Response: "Resuming API refactoring session. Previously you were working on
endpoint consolidation. I found 3 pending tasks and 2 key discoveries about
the authentication flow. Let me continue..."
```

### Example 2: Record Discovery

```
Agent discovers a critical pattern during implementation:

Action: Append to discoveries.md
---
## 2025-10-19 14:23 Discovery: Error Handling Pattern

Found that all API endpoints follow a consistent error handling pattern:
- 400 for validation errors
- 404 for not found
- 500 for server errors

**Impact:** Can standardize error responses across all endpoints
**Next Steps:** Create shared error handler utility
---
```

### Example 3: Share Pattern

```
After successfully using a pattern multiple times:

Action: Create shared/patterns/error-handler-pattern.md
---
# Error Handler Pattern

## Problem
API endpoints need consistent error responses

## Solution
Centralized error handler middleware with standard format:
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": {}
  }
}

## When to Use
- All API endpoints
- Background jobs
- External service integrations

## Example
[Code example...]
---
```

## Benefits Over Complex Solutions

**vs Database Systems:**
- ✅ Zero setup required
- ✅ Human-readable storage (markdown/JSON)
- ✅ Git-trackable history
- ✅ No external dependencies
- ✅ Works offline
- ✅ Easy to debug (just read files)

**vs Beads Integration:**
- ✅ ~50 LOC equivalent vs 2,464 LOC
- ✅ No Go binary dependency
- ✅ No SQLite + JSONL complexity
- ✅ Standard library only
- ✅ Instant startup (no DB init)

## Limitations & When to Upgrade

This simple approach works well for:
- Individual developers
- Short-to-medium term sessions (days-weeks)
- Up to ~1000 memory entries
- Linear workflows

Consider more complex solutions when:
- Need graph-based relationships between memories
- Multiple concurrent users (team collaboration)
- Complex queries across sessions
- Very large memory corpus (10,000+ entries)

## Implementation Notes

**No Code Required:**
- Agents already know how to read/write files
- Uses existing File Read/Write tools
- Markdown is natural for agents
- JSON for structured data

**Validation Period:**
Recommend using this approach for 2-3 weeks before considering complex alternatives. Most use cases may never need more.

## Philosophy Alignment

✅ **Ruthless Simplicity**: File-based, no complexity
✅ **Zero-BS**: Works immediately, no setup
✅ **Standard Library**: Uses existing file operations
✅ **Modular**: Self-contained, no dependencies
✅ **Regeneratable**: Clear instructions enable AI reconstruction

---

**Usage**: Include this agent's instructions in session startup to enable persistent memory without code changes.
