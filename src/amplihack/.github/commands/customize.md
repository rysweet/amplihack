# GitHub Copilot Command Reference: customize

**Source**: `~/.amplihack/.claude/commands/amplihack/customize.md`

---

## Command Metadata

- **name**: amplihack:customize
- **version**: 1.0.0
- **description**: Manage user-specific preferences and customizations
- **argument-hint**: <action> [preference] [value]
- **triggers**:
- **invokes**:
- **- type**: file
- **path**: .claude/context/USER_PREFERENCES.md

---

## Usage with GitHub Copilot CLI

This command is designed for Claude Code but the patterns and approaches
can be referenced when using GitHub Copilot CLI.

**Example**:

```bash
# Reference this command's approach
gh copilot explain .github/commands/customize.md

# Use patterns from this command
gh copilot suggest --context .github/commands/customize.md "your task"
```

---

## Original Command Documentation

# User Customization Command

## Input Validation

../../.claude/context/AGENT_INPUT_VALIDATION.md

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

### list-workflows - List available workflows

`/amplihack:customize list-workflows`

Displays all available workflows in `~/.amplihack/.claude/workflow/` directory with descriptions.

Example output:

```
Available Workflows:

1. DEFAULT_WORKFLOW
   Description: Standard workflow for most development tasks
   Location: .claude/workflow/DEFAULT_WORKFLOW.md
   Steps: 15
   Best for: Features, bug fixes, refactoring, day-to-day work

2. CONSENSUS_WORKFLOW
   Description: Enhanced workflow with consensus mechanisms
   Location: .claude/workflow/CONSENSUS_WORKFLOW.md
   Steps: 15
   Best for: Critical tasks, ambiguous requirements, architectural changes

Current Selection: DEFAULT_WORKFLOW
```

### show-workflow - Display workflow content

`/amplihack:customize show-workflow <workflow_name>`

Shows the content of a specific workflow file.

- `/amplihack:customize show-workflow DEFAULT_WORKFLOW`
- `/amplihack:customize show-workflow CONSENSUS_WORKFLOW`

### set-workflow - Switch to a different workflow

`/amplihack:customize set-workflow <workflow_name>`

Changes the active workflow in USER_PREFERENCES.md.

- `/amplihack:customize set-workflow CONSENSUS_WORKFLOW` - Switch to consensus workflow
- `/amplihack:customize set-workflow DEFAULT_WORKFLOW` - Switch back to default
- `/amplihack:customize set-workflow MY_CUSTOM_WORKFLOW` - Switch to custom workflow

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

### auto_update

Controls automatic updating of .claude/ directory when version mismatch detected:

- **always**: Always auto-update without prompting
- **never**: Never auto-update (just show warning)
- **ask**: Prompt user each time (default)

### preferred_languages

Comma-separated list of preferred programming languages/frameworks
Example: `python,typescript,react`

### coding_standards

Custom coding standards or guidelines (can be multi-line)

### workflow_preferences

Custom workflow requirements or gates

### consensus_depth

Controls the depth of consensus mechanisms when using CONSENSUS_WORKFLOW:

- **quick**: 2 agents, 2 rounds (faster, less thorough)
- **balanced**: 3-4 agents, 3 rounds (recommended, good balance)
- **comprehensive**: 5+ agents, 4+ rounds (slower, most thorough)

Use set command to change:

- `/amplihack:customize set consensus_depth quick`
- `/amplihack:customize set consensus_depth balanced`
- `/amplihack:customize set consensus_depth comprehensive`

**Note**: Workflow selection (DEFAULT_WORKFLOW vs CONSENSUS_WORKFLOW) is managed via dedicated workflow commands (list-workflows, show-workflow, set-workflow).

## Implementation

This command is a prompt that instructs Claude Code to use its native tools (Read, Edit, Write) to manage the USER_PREFERENCES.md file.

When you invoke this command, follow these steps:

### For "set" action:

1. Use the Read tool to read `~/.amplihack/.claude/context/USER_PREFERENCES.md`
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

1. Use the Read tool to read `~/.amplihack/.claude/context/USER_PREFERENCES.md`
2. Display the contents to the user in a formatted manner

### For "reset" action:

If resetting a specific preference:

1. Use the Read tool to read `~/.amplihack/.claude/context/USER_PREFERENCES.md`
2. Use the Edit tool to replace the preference value with its default
3. Update the timestamp

If resetting all preferences:

1. Use the Write tool to overwrite `~/.amplihack/.claude/context/USER_PREFERENCES.md` with the default template (see below)

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

1. Use the Read tool to read `~/.amplihack/.claude/context/USER_PREFERENCES.md`
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

### For "list-workflows" action:

1. Use the Bash tool to list workflow files:
   ```bash
   ls -1 /Users/ryan/src/tempsaturday/worktree-issue-968/.claude/workflow/*.md | grep -v README.md | grep -v templates
   ```
2. For each workflow file found, use the Read tool to extract:
   - Workflow name (from filename)
   - Title (from first # heading)
   - Description (from first paragraph after "How This Workflow Works")
   - Number of steps (count lines starting with "### Step")
3. Use the Read tool on `~/.amplihack/.claude/context/USER_PREFERENCES.md` to get current selection:
   - Find line "**Selected Workflow**:"
   - Extract workflow name
4. Format and display results as shown in the command documentation above
5. Highlight current selection

### For "show-workflow" action:

1. Validate workflow_name argument is provided
   - If missing: Display error and show available workflows (use list-workflows logic)
2. Construct absolute file path: `~/.amplihack/.claude/workflow/{workflow_name}.md`
3. Use the Read tool to read the workflow file
4. If file not found:
   - Show error message
   - List available workflows
   - Show how to create custom workflow from template
5. If file found: Display full contents to user

### For "set-workflow" action:

1. Validate workflow_name argument is provided
   - If missing: Display error and show usage
2. Construct workflow file path: `~/.amplihack/.claude/workflow/{workflow_name}.md`
3. Verify file exists using Read tool (attempt to read)
   - If not found: Show error with available workflows list
4. Use the Read tool to read `~/.amplihack/.claude/context/USER_PREFERENCES.md`
5. Use the Edit tool to update workflow selection:
   ```
   old_string: "**Selected Workflow**: [current_workflow]"
   new_string: "**Selected Workflow**: {workflow_name}"
   ```
6. Update timestamp at bottom of file:
   ```
   old_string: "_Last updated: [old_timestamp]_"
   new_string: "_Last updated: [current_timestamp]_"
   ```
7. Confirm change to user with helpful message including:
   - Confirmation of workflow change
   - How this affects /ultrathink
   - How to view the workflow
   - How to learn more

## Validation Rules

Before making changes, validate:

1. **Preference names** must match exactly (case-insensitive matching is acceptable):
   - verbosity, communication_style, update_frequency, priority_type, collaboration_style, auto_update, preferred_languages, coding_standards, workflow_preferences, consensus_depth

2. **Enumerated values** must match allowed options:
   - verbosity: concise, balanced, detailed
   - communication_style: formal, casual, technical
   - update_frequency: minimal, regular, frequent
   - priority_type: features, bugs, performance, security, balanced
   - collaboration_style: independent, interactive, guided
   - auto_update: always, never, ask
   - consensus_depth: quick, balanced, comprehensive

3. **Free-form values** (preferred_languages, coding_standards, workflow_preferences) can be any non-empty string

4. If validation fails, provide clear error message and do NOT modify the file

## Error Handling

- If `~/.amplihack/.claude/context/USER_PREFERENCES.md` doesn't exist, create it with the default template
- If preference name is invalid, list valid preferences
- If value is invalid for enumerated preference, list valid values
- If file operations fail, report the error clearly
- Never leave the file in a partially edited state

## Integration

This command integrates with the project by:

1. Storing preferences in `~/.amplihack/.claude/context/USER_PREFERENCES.md`
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
