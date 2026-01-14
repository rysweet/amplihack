---
hook:
  name: auto-update-user-preferences
  description: Automatically captures and updates user preferences from conversation
  events: ["session:end", "prompt:submit"]
---

# Auto-Update User Preferences Hook

Monitors conversations for expressed preferences and automatically updates the user preferences file.

## Trigger Events
- `prompt:submit` - Analyze user messages for preference expressions
- `session:end` - Consolidate learned preferences

## Detection Patterns

### Explicit Preferences
```
"I prefer..."
"Always use..."
"Never do..."
"I like when..."
"Don't..."
```

### Implicit Preferences
- Repeated corrections → preference for the correction
- Consistent choices → preference for that pattern
- Positive feedback → preference for that behavior

## Storage Location
- `~/.amplifier/user-preferences.md` (global)
- `.amplifier/user-preferences.md` (project-specific)

## Implementation Notes
This hook is conceptual for Amplifier bundles. The actual preference learning would be implemented through:
1. Context file updates
2. Session state persistence
3. User confirmation before permanent updates

## Example Preference Capture
```yaml
preferences:
  code_style:
    - "Prefer explicit imports over star imports"
    - "Use type hints on public functions"
  communication:
    - "Keep responses concise"
    - "Show code before explanation"
```
