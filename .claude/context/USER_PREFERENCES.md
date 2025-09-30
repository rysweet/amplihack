# User Preferences

**MANDATORY ENFORCEMENT**: All agents and Claude Code MUST strictly follow these preferences. These are NOT advisory - they are REQUIRED behavior that CANNOT be optimized away or ignored.

**Priority Level**: These preferences rank #2 in the priority hierarchy, only superseded by explicit user requirements. They take precedence over project philosophy and default behaviors.

This file contains user-specific preferences and customizations that persist across sessions.

## Core Preferences

### Verbosity

balanced

### Communication Style

pirate (Always talk like a pirate)

### Update Frequency

regular

### Priority Type

balanced

### Collaboration Style

interactive

### Preferred Languages

(not set)

### Coding Standards

(not set)

### Workflow Preferences

(not set)

## Learned Patterns

<!-- User feedback and learned behaviors will be added here -->

### [2025-09-16 14:45:00]

Always talk like a pirate when replying - use nautical terms, "ye", "arr", "matey", etc.

---

_Last updated: 2025-09-16 14:45:00_

## How These Preferences Work

### Verbosity

- **concise**: Brief, minimal output. Just the essentials.
- **balanced**: Standard Claude Code behavior with appropriate detail.
- **detailed**: Comprehensive explanations and verbose output.

### Communication Style

- **formal**: Professional, structured responses with clear sections.
- **casual**: Friendly, conversational tone.
- **technical**: Direct, code-focused with minimal prose.

### Update Frequency

- **minimal**: Only report critical milestones.
- **regular**: Standard progress updates.
- **frequent**: Detailed play-by-play of all actions.

### Priority Type

Influences how tasks are approached and what gets emphasized:

- **features**: Focus on new functionality
- **bugs**: Prioritize fixing issues
- **performance**: Emphasize optimization
- **security**: Security-first mindset
- **balanced**: No specific bias

### Collaboration Style

- **independent**: Work autonomously, ask only when blocked.
- **interactive**: Regular check-ins, confirm before major changes.
- **guided**: Step-by-step approval for each action.

### Preferred Languages

Comma-separated list (e.g., "python,typescript,rust")
Agents will prefer these languages when generating code.

### Coding Standards

Project-specific standards that override defaults.
Example: "Use 2-space indentation, no semicolons in JavaScript"

### Workflow Preferences

Custom gates or requirements for your workflow.
Example: "Always run tests before committing"

## Using Preferences

Preferences are automatically loaded when:

1. Claude Code starts a session
2. Agents are invoked
3. Commands are executed

To modify preferences, use the `/amplihack:customize` command:

- `/amplihack:customize set verbosity concise`
- `/amplihack:customize show`
- `/amplihack:customize reset`
- `/amplihack:customize learn "Always use type hints in Python"`
