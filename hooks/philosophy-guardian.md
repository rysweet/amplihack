---
hook:
  name: philosophy-guardian
  description: Ensures outputs align with project philosophy
  events: ["tool:after", "content_block:text"]
---

# Philosophy Guardian Hook

Monitors generated content for philosophy violations and provides warnings.

## Checked Principles

### Zero-BS Implementation
- No `TODO` comments in production code
- No `NotImplementedError` (except abstract methods)
- No placeholder implementations
- No `pass` statements (except structural)

### Ruthless Simplicity
- Flag overly complex abstractions
- Warn on deep nesting (>4 levels)
- Detect over-engineering patterns

### Modular Design
- Check for proper module boundaries
- Verify interface clarity
- Ensure regeneratable components

## Severity Levels
| Level | Action | Example |
|-------|--------|---------|
| Error | Block commit | `raise NotImplementedError` |
| Warning | Flag for review | TODO comment |
| Info | Log only | Long function |

## Integration
Works with `python_check` tool to provide comprehensive code quality enforcement.
