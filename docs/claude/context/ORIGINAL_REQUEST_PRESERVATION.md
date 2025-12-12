# Original Request Preservation

Ensures original user requirements are preserved and passed to all agents to prevent requirement loss during context compaction.

## Problem

Original user requests get lost during context compaction, leading to agents optimizing away explicit requirements.

## Solution

amplihack approach:

1. **Context Preservation**: Extract and preserve original requirements
2. **Agent Injection**: Include requirements in ALL agent prompts
3. **Conversation Export**: Export before compaction
4. **Validation**: Check preservation at key steps

## Core Components

- **context_preservation.py**: Extracts and structures requirements
- **pre_compact.py**: Exports conversation before compaction
- **Agent injection**: Include requirements in ALL agent prompts

## Agent Context Format

```markdown
## 🎯 ORIGINAL USER REQUEST - PRESERVE THESE REQUIREMENTS

**Target**: [User's stated goal]

**Requirements**: • [List user requirements]
**Constraints**: • [List user constraints]

**CRITICAL**: Do NOT optimize away explicit requirements.
```

## Key Rules

1. **Always include** original request context when invoking agents
2. **Never optimize away** explicit user requirements
3. **Validate preservation** at cleanup steps (6 & 14)
4. **Export conversations** before compaction

## File Locations

```
.claude/tools/amplihack/context_preservation.py
.claude/tools/amplihack/hooks/pre_compact.py
.claude/runtime/logs/<session_id>/ORIGINAL_REQUEST.md
```

## Golden Rule

**When in doubt, preserve the user's explicit requirements.**
