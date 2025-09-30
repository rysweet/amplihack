---
description: Manage user-specific preferences and customizations
argument-hint: <action> [preference] [value]
---

# User Customization Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/amplihack:customize <action> [preference] [value]`

## Actions

### set - Set a preference

`/amplihack:customize set <preference> <value>`

Sets or updates a user preference. Examples:

- `/amplihack:customize set verbosity concise`
- `/amplihack:customize set communication_style technical`
- `/amplihack:customize set priority_type bugs`

### show - Display current preferences

`/amplihack:customize show`

Shows all current user preferences and their values.

### reset - Reset preferences

`/amplihack:customize reset [preference]`

Resets a specific preference or all preferences to defaults.

- `/amplihack:customize reset verbosity` - resets verbosity to default
- `/amplihack:customize reset` - resets all preferences

### learn - Learn from feedback

`/amplihack:customize learn <feedback>`

Captures user feedback to improve future interactions.

- `/amplihack:customize learn "Always include unit tests when creating new functions"`
- `/amplihack:customize learn "Prefer async/await over callbacks"`

## Available Preferences

### verbosity

- **concise**: Brief, to-the-point responses
- **balanced**: Standard level of detail (default)
- **detailed**: Comprehensive explanations

### communication_style

- **formal**: Professional, structured communication
- **casual**: Conversational, friendly tone
- **technical**: Direct, code-focused responses (default)

### update_frequency

- **minimal**: Only essential updates
- **regular**: Standard progress updates (default)
- **frequent**: Detailed step-by-step updates

### priority_type

- **features**: Focus on new functionality
- **bugs**: Prioritize bug fixes
- **performance**: Emphasize optimization
- **security**: Security-first approach
- **balanced**: No specific priority (default)

### collaboration_style

- **independent**: Work autonomously, minimal interaction
- **interactive**: Regular check-ins and confirmations (default)
- **guided**: Step-by-step with user approval

### preferred_languages

Comma-separated list of preferred programming languages/frameworks
Example: `python,typescript,react`

### coding_standards

Custom coding standards or guidelines (can be multi-line)

### workflow_preferences

Custom workflow requirements or gates

## Implementation

This command is a prompt that instructs Claude Code to use its native tools (Read, Edit, Write) to manage the USER_PREFERENCES.md file.

When you invoke this command, follow these steps:

### For "set" action:

1. Use the Read tool to read `.claude/context/USER_PREFERENCES.md`
2. Validate the preference name and value against the available preferences list above
3. Use the Edit tool to update the preference section in USER_PREFERENCES.md:
   - Find the section matching the preference (e.g., "### Verbosity")
   - Replace the value on the next line with the new value
4. Use the Edit tool to update the "Last updated" timestamp at the bottom
5. Confirm the change to the user

Example for setting verbosity to concise:

```
Use Edit tool on .claude/context/USER_PREFERENCES.md:
  old_string: "### Verbosity\n\nbalanced"
  new_string: "### Verbosity\n\nconcise"

Then update timestamp:
  old_string: "_Last updated: [old timestamp]_"
  new_string: "_Last updated: [current timestamp]_"
```

### For "show" action:

1. Use the Read tool to read `.claude/context/USER_PREFERENCES.md`
2. Display the contents to the user in a formatted manner

### For "reset" action:

If resetting a specific preference:

1. Use the Read tool to read `.claude/context/USER_PREFERENCES.md`
2. Use the Edit tool to replace the preference value with its default
3. Update the timestamp

If resetting all preferences:

1. Use the Write tool to overwrite `.claude/context/USER_PREFERENCES.md` with the default template (see below)

Default template structure:

```markdown
# User Preferences

**MANDATORY ENFORCEMENT**: All agents and Claude Code MUST strictly follow these preferences. These are NOT advisory - they are REQUIRED behavior that CANNOT be optimized away or ignored.

This file contains user-specific preferences and customizations that persist across sessions.

## Core Preferences

### Verbosity

balanced

### Communication Style

technical

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

---

_Last updated: [current timestamp]_
```

### For "learn" action:

1. Use the Read tool to read `.claude/context/USER_PREFERENCES.md`
2. Extract the feedback text from the command arguments
3. Use the Edit tool to add the feedback to the "Learned Patterns" section:
   - Insert after the "<!-- User feedback... -->" comment
   - Format as: `### [timestamp]\n\n[feedback text]\n\n`
4. Update the "Last updated" timestamp

Example:

```
Use Edit tool on .claude/context/USER_PREFERENCES.md:
  old_string: "## Learned Patterns\n\n<!-- User feedback and learned behaviors will be added here -->"
  new_string: "## Learned Patterns\n\n<!-- User feedback and learned behaviors will be added here -->\n\n### [2025-09-29 10:30:00]\n\nAlways include unit tests when creating new functions\n"
```

## Validation Rules

Before making changes, validate:

1. **Preference names** must match exactly (case-insensitive matching is acceptable):
   - verbosity, communication_style, update_frequency, priority_type, collaboration_style, preferred_languages, coding_standards, workflow_preferences

2. **Enumerated values** must match allowed options:
   - verbosity: concise, balanced, detailed
   - communication_style: formal, casual, technical
   - update_frequency: minimal, regular, frequent
   - priority_type: features, bugs, performance, security, balanced
   - collaboration_style: independent, interactive, guided

3. **Free-form values** (preferred_languages, coding_standards, workflow_preferences) can be any non-empty string

4. If validation fails, provide clear error message and do NOT modify the file

## Error Handling

- If `.claude/context/USER_PREFERENCES.md` doesn't exist, create it with the default template
- If preference name is invalid, list valid preferences
- If value is invalid for enumerated preference, list valid values
- If file operations fail, report the error clearly
- Never leave the file in a partially edited state

## Integration

This command integrates with the project by:

1. Storing preferences in `.claude/context/USER_PREFERENCES.md`
2. Preferences are loaded via CLAUDE.md imports at session start
3. Agents and workflows reference these preferences (MANDATORY enforcement)
4. Learned patterns accumulate over time

## Priority Hierarchy

Preferences follow this priority hierarchy (highest to lowest):

1. **USER_PREFERENCES.md** (HIGHEST - MANDATORY)
2. Task-specific user instructions
3. Project philosophy (CLAUDE.md, PHILOSOPHY.md)
4. Default Claude Code behavior (LOWEST)

## Notes

- Preferences persist across sessions
- The preferences file is imported automatically in CLAUDE.md
- Agents MUST check preferences and apply them strictly
- Learned patterns help improve future interactions
- Use simple, direct tool invocations - no complex abstractions
