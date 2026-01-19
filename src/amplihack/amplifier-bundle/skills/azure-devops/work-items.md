# Work Item Management Guide

Complete guide to creating and managing work items with Azure DevOps CLI tools.

## Work Item Types

Standard types in most projects:

- **Epic** - Large body of work (months)
- **Feature** - Shippable functionality (weeks)
- **User Story** - User-facing feature (days)
- **Task** - Technical work (hours/days)
- **Bug** - Defect or issue

Check available types in your project:

```bash
python .claude/scenarios/az-devops-tools/list_types.py
```

## Creating Work Items

### Basic Creation

```bash
python .claude/scenarios/az-devops-tools/create_work_item.py \
  --type "User Story" \
  --title "Implement user login"
```

### With Description (Markdown Auto-Converted)

```bash
python .claude/scenarios/az-devops-tools/create_work_item.py \
  --type "User Story" \
  --title "User authentication" \
  --description "# Story

As a user, I want to log in with my credentials.

## Acceptance Criteria
- User can enter email/password
- System validates credentials
- Invalid login shows error message"
```

### With All Options

```bash
python .claude/scenarios/az-devops-tools/create_work_item.py \
  --type Bug \
  --title "Login button not responding" \
  --description "Button click does nothing" \
  --assigned-to user@example.com \
  --area "MyProject\\Frontend" \
  --iteration "MyProject\\Sprint 1" \
  --tags "ui,critical,login" \
  --fields "Microsoft.VSTS.Common.Priority=1" \
  --fields "Microsoft.VSTS.Common.Severity=1-Critical"
```

### With Parent Link

```bash
# Creates Task and links to Story #1234
python .claude/scenarios/az-devops-tools/create_work_item.py \
  --type Task \
  --title "Write unit tests" \
  --parent 1234
```

## Linking Work Items

Create parent-child relationships:

```bash
# Link Task #5678 to Story #1234
python .claude/scenarios/az-devops-tools/link_parent.py \
  --child 5678 \
  --parent 1234
```

Valid relationships:

- Task → User Story, Bug, Feature, Epic
- Bug → Feature, Epic
- User Story → Feature, Epic
- Feature → Epic

## Updating Work Items

Update state, assignments, or other fields:

```bash
# Update state
python .claude/scenarios/az-devops-tools/update_work_item.py --id 12345 --state "Active"

# Reassign work item
python .claude/scenarios/az-devops-tools/update_work_item.py --id 12345 --assign-to "user@domain.com"

# Update multiple fields with comment
python .claude/scenarios/az-devops-tools/update_work_item.py --id 12345 --state "Resolved" --comment "Fixed issue"
```

## Querying Work Items

List and filter work items:

```bash
# List my active work items
python .claude/scenarios/az-devops-tools/list_work_items.py --state Active --assigned-to @me

# List all bugs
python .claude/scenarios/az-devops-tools/list_work_items.py --type Bug

# Use predefined query
python .claude/scenarios/az-devops-tools/list_work_items.py --query mine
```

## Common Workflows

### Create Epic with Features

```bash
# Create Epic
epic_output=$(python .claude/scenarios/az-devops-tools/create_work_item.py \
  --type Epic \
  --title "Authentication System")
epic_id=$(echo "$epic_output" | grep "ID:" | awk '{print $2}')

# Create Features under Epic
for feature in "OAuth Integration" "Session Management" "RBAC"; do
  python .claude/scenarios/az-devops-tools/create_work_item.py \
    --type Feature \
    --title "$feature" \
    --parent "$epic_id"
done
```

### Create Story with Tasks

```bash
# Create Story
story_output=$(python .claude/scenarios/az-devops-tools/create_work_item.py \
  --type "User Story" \
  --title "Implement login UI")
story_id=$(echo "$story_output" | grep "ID:" | awk '{print $2}')

# Create Tasks
for task in "Design mockup" "Implement form" "Add validation" "Write tests"; do
  python .claude/scenarios/az-devops-tools/create_work_item.py \
    --type Task \
    --title "$task" \
    --parent "$story_id"
done
```

## Field Reference

### Common System Fields

- `System.Title` - Work item title (required)
- `System.Description` - HTML description
- `System.State` - Current state (New, Active, Closed, etc.)
- `System.AssignedTo` - Assigned user (email or display name)
- `System.AreaPath` - Area path (format: Project\\Team\\Area)
- `System.IterationPath` - Sprint/iteration
- `System.Tags` - Comma-separated tags

### Microsoft VSTS Fields

- `Microsoft.VSTS.Common.Priority` - 1 (highest) to 4 (lowest)
- `Microsoft.VSTS.Common.Severity` - 1-Critical, 2-High, 3-Medium, 4-Low
- `Microsoft.VSTS.Common.StackRank` - Backlog ordering

### Discover All Fields

```bash
# Show fields for specific type
python .claude/scenarios/az-devops-tools/list_types.py --type "User Story"

# Show all fields including system
python .claude/scenarios/az-devops-tools/list_types.py --type Bug --all-fields
```

## Tips and Best Practices

1. **Use markdown descriptions** - Auto-converted to HTML for better formatting
2. **Set area path** - Helps with team organization and queries
3. **Link work items early** - Easier to track relationships
4. **Use tags** - Improves searchability
5. **Validate types first** - Use list_types before creating

## Troubleshooting

### "Invalid work item type"

Check available types:

```bash
python .claude/scenarios/az-devops-tools/list_types.py
```

### "Work item type with spaces"

Use quotes:

```bash
--type "User Story"  # Correct
--type User Story    # Wrong
```

### "Parent link failed"

Verify both IDs exist and relationship is valid.

## See Also

- [@queries.md] - WIQL query patterns
- [@html-formatting.md] - Rich text formatting
- [MS Learn: Work Items](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/)
