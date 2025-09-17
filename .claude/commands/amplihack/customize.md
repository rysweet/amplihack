---
description: Manage user-specific preferences and customizations
argument-hint: <action> [preference] [value]
---

# User Customization Command

## Usage
`/customize <action> [preference] [value]`

## Actions

### set - Set a preference
`/customize set <preference> <value>`

Sets or updates a user preference. Examples:
- `/customize set verbosity concise`
- `/customize set communication_style technical`
- `/customize set priority_type bugs`

### show - Display current preferences
`/customize show`

Shows all current user preferences and their values.

### reset - Reset preferences
`/customize reset [preference]`

Resets a specific preference or all preferences to defaults.
- `/customize reset verbosity` - resets verbosity to default
- `/customize reset` - resets all preferences

### learn - Learn from feedback
`/customize learn <feedback>`

Captures user feedback to improve future interactions.
- `/customize learn "Always include unit tests when creating new functions"`
- `/customize learn "Prefer async/await over callbacks"`

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

```bash
# Parse the command arguments
ACTION="$1"
PREFERENCE="$2"
VALUE="$3"

PREFS_FILE=".claude/context/USER_PREFERENCES.md"

# Ensure preferences file exists
if [ ! -f "$PREFS_FILE" ]; then
    echo "Creating user preferences file..."
    !mkdir -p .claude/context
    !cat > "$PREFS_FILE" << 'EOF'
# User Preferences

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
*Last updated: $(date)*
EOF
fi

case "$ACTION" in
    "set")
        if [ -z "$PREFERENCE" ] || [ -z "$VALUE" ]; then
            echo "Usage: /customize set <preference> <value>"
            exit 1
        fi

        echo "Setting $PREFERENCE to $VALUE..."

        # Update the preference in the file
        case "$PREFERENCE" in
            "verbosity")
                if [[ "$VALUE" =~ ^(concise|balanced|detailed)$ ]]; then
                    @Edit $PREFS_FILE "### Verbosity\n.*" "### Verbosity\n$VALUE"
                    echo "✓ Verbosity set to: $VALUE"
                else
                    echo "Invalid value. Options: concise, balanced, detailed"
                fi
                ;;
            "communication_style")
                if [[ "$VALUE" =~ ^(formal|casual|technical)$ ]]; then
                    @Edit $PREFS_FILE "### Communication Style\n.*" "### Communication Style\n$VALUE"
                    echo "✓ Communication style set to: $VALUE"
                else
                    echo "Invalid value. Options: formal, casual, technical"
                fi
                ;;
            "update_frequency")
                if [[ "$VALUE" =~ ^(minimal|regular|frequent)$ ]]; then
                    @Edit $PREFS_FILE "### Update Frequency\n.*" "### Update Frequency\n$VALUE"
                    echo "✓ Update frequency set to: $VALUE"
                else
                    echo "Invalid value. Options: minimal, regular, frequent"
                fi
                ;;
            "priority_type")
                if [[ "$VALUE" =~ ^(features|bugs|performance|security|balanced)$ ]]; then
                    @Edit $PREFS_FILE "### Priority Type\n.*" "### Priority Type\n$VALUE"
                    echo "✓ Priority type set to: $VALUE"
                else
                    echo "Invalid value. Options: features, bugs, performance, security, balanced"
                fi
                ;;
            "collaboration_style")
                if [[ "$VALUE" =~ ^(independent|interactive|guided)$ ]]; then
                    @Edit $PREFS_FILE "### Collaboration Style\n.*" "### Collaboration Style\n$VALUE"
                    echo "✓ Collaboration style set to: $VALUE"
                else
                    echo "Invalid value. Options: independent, interactive, guided"
                fi
                ;;
            "preferred_languages")
                @Edit $PREFS_FILE "### Preferred Languages\n.*" "### Preferred Languages\n$VALUE"
                echo "✓ Preferred languages set to: $VALUE"
                ;;
            "coding_standards")
                @Edit $PREFS_FILE "### Coding Standards\n.*" "### Coding Standards\n$VALUE"
                echo "✓ Coding standards updated"
                ;;
            "workflow_preferences")
                @Edit $PREFS_FILE "### Workflow Preferences\n.*" "### Workflow Preferences\n$VALUE"
                echo "✓ Workflow preferences updated"
                ;;
            *)
                echo "Unknown preference: $PREFERENCE"
                echo "Available preferences: verbosity, communication_style, update_frequency, priority_type, collaboration_style, preferred_languages, coding_standards, workflow_preferences"
                ;;
        esac

        # Update timestamp
        @Edit $PREFS_FILE "*Last updated:.*" "*Last updated: $(date)*"
        ;;

    "show")
        echo "Current user preferences:"
        echo ""
        @Read $PREFS_FILE
        ;;

    "reset")
        if [ -z "$PREFERENCE" ]; then
            echo "Resetting all preferences to defaults..."
            @Write $PREFS_FILE "# User Preferences

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
*Last updated: $(date)*"
            echo "✓ All preferences reset to defaults"
        else
            echo "Resetting $PREFERENCE to default..."
            case "$PREFERENCE" in
                "verbosity")
                    @Edit $PREFS_FILE "### Verbosity\n.*" "### Verbosity\nbalanced"
                    ;;
                "communication_style")
                    @Edit $PREFS_FILE "### Communication Style\n.*" "### Communication Style\ntechnical"
                    ;;
                "update_frequency")
                    @Edit $PREFS_FILE "### Update Frequency\n.*" "### Update Frequency\nregular"
                    ;;
                "priority_type")
                    @Edit $PREFS_FILE "### Priority Type\n.*" "### Priority Type\nbalanced"
                    ;;
                "collaboration_style")
                    @Edit $PREFS_FILE "### Collaboration Style\n.*" "### Collaboration Style\ninteractive"
                    ;;
                "preferred_languages"|"coding_standards"|"workflow_preferences")
                    @Edit $PREFS_FILE "### ${PREFERENCE//_/ }\n.*" "### ${PREFERENCE//_/ }\n(not set)"
                    ;;
                *)
                    echo "Unknown preference: $PREFERENCE"
                    exit 1
                    ;;
            esac
            echo "✓ $PREFERENCE reset to default"
        fi
        ;;

    "learn")
        if [ -z "$ARGUMENTS" ] || [ "$ARGUMENTS" = "learn" ]; then
            echo "Usage: /customize learn <feedback>"
            exit 1
        fi

        FEEDBACK="${ARGUMENTS#learn }"
        echo "Learning from feedback: $FEEDBACK"

        # Add to learned patterns section
        TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
        @Edit $PREFS_FILE "## Learned Patterns\n\n<!-- User feedback and learned behaviors will be added here -->" "## Learned Patterns\n\n<!-- User feedback and learned behaviors will be added here -->\n\n### [$TIMESTAMP]\n$FEEDBACK"

        echo "✓ Feedback captured and stored"
        ;;

    *)
        echo "Unknown action: $ACTION"
        echo ""
        echo "Available actions:"
        echo "  set    - Set a preference value"
        echo "  show   - Display current preferences"
        echo "  reset  - Reset preferences to defaults"
        echo "  learn  - Capture feedback for learning"
        echo ""
        echo "Example: /customize set verbosity concise"
        ;;
esac
```

## Integration

This command integrates with the project by:
1. Storing preferences in `.claude/context/USER_PREFERENCES.md`
2. Preferences are loaded via CLAUDE.md imports
3. Agents and workflows reference these preferences
4. Learned patterns accumulate over time

## Notes

- Preferences persist across sessions
- The preferences file is imported automatically in CLAUDE.md
- Agents should check preferences when determining behavior
- Learned patterns help improve future interactions