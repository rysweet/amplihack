# Stop Hook with Safe Reflection Analysis

## Overview

This stop hook provides safe session reflection without automatic issue creation, preventing the runaway loop problem while still providing valuable insights.

## Features

### Safe Analysis

- **No AI calls**: Uses simple heuristics to detect patterns
- **No automatic issues**: Never creates GitHub issues automatically
- **User control**: Provides commands for users to create issues manually
- **Silent by default**: Only shows messages when patterns are detected

### Pattern Detection

The hook analyzes sessions for:

- **Error patterns**: Multiple errors or failures
- **Workflow inefficiencies**: High tool use counts
- **User frustration**: Repeated attempts with errors
- **File operations**: Excessive file edits that could be batched
- **Tool failures**: Repeated tool_use_error occurrences

### User Prompts

When patterns are detected, provides clear next steps:

1. **Create Issue**: Manual `gh` command with repo and template
2. **Start PR**: `/ultrathink` command to begin work
3. **Quick Fixes**: `/fix` and `/improve` for immediate action

## Implementation

The hook is a Python script that:

1. Reads session messages from stdin
2. Performs safe pattern analysis (no AI, no external calls)
3. Formats findings for user display
4. Returns JSON with `systemMessage` field for visibility
5. Never blocks execution (always returns "approve")

## Installation

```bash
# Ensure hook is executable
chmod +x .claude/hooks/stop

# Hook location: .claude/hooks/stop in your project
```

## Testing

```bash
# Create test input
cat > test.json <<EOF
{
  "messages": [
    {"role": "user", "content": "test"},
    {"role": "assistant", "content": "error occurred"}
  ]
}
EOF

# Test the hook
CLAUDE_PROJECT_DIR=$(pwd) .claude/hooks/stop < test.json
```

## JSON Output Format

```json
{
  "decision": "approve",
  "systemMessage": "📊 Session Reflection Analysis...",
  "continue": true
}
```

## Key Safety Features

1. **No automatic GitHub operations**: All issue creation is manual
2. **No AI analysis**: Prevents infinite loops from AI-generated content
3. **Minimum message threshold**: Only analyzes sessions with 5+ messages
4. **Simple heuristics**: Pattern detection based on keyword matching
5. **User-initiated actions**: All improvements require explicit user commands

## Pattern Priority Levels

- **🔴 High**: Errors, tool failures, user frustration
- **🟡 Medium**: Workflow optimization, file operations
- **🟢 Low**: Minor improvements

## Troubleshooting

If the hook isn't showing messages:

1. Check it's executable: `chmod +x .claude/hooks/stop`
2. Verify Python 3 is available: `python3 --version`
3. Check logs: `.claude/runtime/logs/stop_reflection.log`
4. Test with sample input (see Testing section)

## Comparison to Original Reflection System

| Feature             | Original (Disabled)         | New Safe Version       |
| ------------------- | --------------------------- | ---------------------- |
| AI Analysis         | Yes (Claude SDK)            | No (heuristics only)   |
| Auto Issue Creation | Yes (caused 409 issues)     | No (manual only)       |
| Complexity          | High (state machine, locks) | Low (single function)  |
| User Visibility     | Poor                        | Good (systemMessage)   |
| Loop Prevention     | Failed (3 mechanisms)       | N/A (no automation)    |
| Interactive Prompts | Yes                         | No (just instructions) |

## Future Improvements

When ready to enhance (with proper testing):

1. Add opt-in AI analysis with strict rate limiting
2. Implement duplicate detection before showing prompts
3. Add session replay for debugging
4. Create `/reflect` command for on-demand analysis

## Safety First

This implementation prioritizes safety over features:

- No automatic actions that could loop
- No external API calls that could fail
- No complex state management
- User maintains full control

The goal is to provide helpful reflection without risk of runaway automation.
