# Agent Input Validation Instructions

## CRITICAL: Input Validation Required

Before processing ANY task, verify that you have received proper input with actionable content.

## Validation Process

1. **Check Input**: Verify you have received a task, prompt, specifications, or parameters
2. **Stop if Empty**: If input is missing, empty, or only whitespace, DO NOT proceed
3. **Provide Help**: Immediately respond with usage information

## Response Template for Missing Input

When invoked without proper input, respond with a message following this pattern:

```
I need [specific requirement] to proceed. This [agent/command] requires:

- **Required**: [describe what input is needed]
- **Purpose**: [explain what this agent/command does]
- **Usage**: [provide usage format]

Examples:
[Provide 2-3 concrete examples]

Please provide [requirement] and try again.
```

## Important Notes

- Never proceed without valid input
- Never make assumptions about user intent
- Always fail gracefully with helpful information
- This is a safety mechanism to prevent accidental invocations
