# Azure Boards Complete Command Reference

Complete reference for `az boards` command group covering work items, queries, sprints, and team collaboration.

## Work Item Management

### Create Work Items

```bash
# Create user story
az boards work-item create --type "User Story" \
  --title "Implement login feature" \
  --assigned-to me@example.com \
  --project MyProject

# Create bug with priority
az boards work-item create --type "Bug" \
  --title "Login button not working" \
  --assigned-to dev@example.com \
  --fields "System.Priority=1" "System.Severity=1 - Critical"

# Create task with parent
az boards work-item create --type "Task" \
  --title "Write unit tests" \
  --assigned-to me@example.com \
  --parent 123

# Create with description
az boards work-item create --type "User Story" \
  --title "Add user profile page" \
  --description "As a user, I want to view and edit my profile"

# Create with area and iteration
az boards work-item create --type "Feature" \
  --title "Payment integration" \
  --area "MyProject\\Backend" \
  --iteration "MyProject\\Sprint 1"

# Create with tags
az boards work-item create --type "Bug" \
  --title "Memory leak in API" \
  --fields "System.Tags=performance,critical"
```

### Show Work Item

```bash
# Show work item by ID
az boards work-item show --id 123

# Show as JSON
az boards work-item show --id 123 --output json

# Open work item in browser
az boards work-item show --id 123 --open

# Show specific fields
az boards work-item show --id 123 --fields "System.Title" "System.State" "System.AssignedTo"
```

### Update Work Items

```bash
# Update work item state
az boards work-item update --id 123 --state "In Progress"

# Update assigned to
az boards work-item update --id 123 --assigned-to newdev@example.com

# Update title
az boards work-item update --id 123 --title "Updated title"

# Update description
az boards work-item update --id 123 --description "New description"

# Update custom fields
az boards work-item update --id 123 --fields "System.Priority=2" "Microsoft.VSTS.Common.Severity=2 - High"

# Update area path
az boards work-item update --id 123 --area "MyProject\\Frontend"

# Update iteration
az boards work-item update --id 123 --iteration "MyProject\\Sprint 2"

# Add comment
az boards work-item update --id 123 --discussion "This is a comment"

# Update multiple fields at once
az boards work-item update --id 123 \
  --state "Resolved" \
  --assigned-to qa@example.com \
  --fields "System.Reason=Fixed"
```

### Delete Work Items

```bash
# Delete work item
az boards work-item delete --id 123 --yes

# Permanently delete (destroy)
az boards work-item delete --id 123 --destroy --yes
```

## Work Item Relations

### Add Relations

```bash
# Add parent-child relationship
az boards work-item relation add --id 456 \
  --relation-type parent \
  --target-id 123

# Add related work item
az boards work-item relation add --id 456 \
  --relation-type related \
  --target-id 789

# Add predecessor (dependency)
az boards work-item relation add --id 456 \
  --relation-type predecessor \
  --target-id 123
```

### Show Relations

```bash
# Show all relations for work item
az boards work-item relation show --id 123

# Show as JSON for processing
az boards work-item relation show --id 123 --output json
```

### Remove Relations

```bash
# Remove relation by target ID
az boards work-item relation remove --id 456 --target-id 123 --relation-type parent --yes
```

## Queries (WIQL)

### Basic Queries

```bash
# Query all active work items
az boards query --wiql "SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE [System.State] = 'Active'"

# Query work items assigned to me
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.AssignedTo] = @Me"

# Query by work item type
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.WorkItemType] = 'Bug'"

# Query with multiple conditions
az boards query --wiql "SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE [System.WorkItemType] = 'Bug' AND [System.State] = 'Active' AND [System.Priority] = 1"
```

### Advanced WIQL Queries

```bash
# Query by date range
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.CreatedDate] >= '2025-01-01' AND [System.CreatedDate] <= '2025-12-31'"

# Query by area path
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.AreaPath] UNDER 'MyProject\\Backend'"

# Query by iteration
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.IterationPath] = @CurrentIteration"

# Query with tags
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.Tags] CONTAINS 'critical'"

# Query changed in last 7 days
az boards query --wiql "SELECT [System.Id], [System.Title], [System.ChangedDate] FROM WorkItems WHERE [System.ChangedDate] >= @Today - 7"

# Query with ORDER BY
az boards query --wiql "SELECT [System.Id], [System.Title], [System.Priority] FROM WorkItems WHERE [System.State] = 'Active' ORDER BY [System.Priority] ASC, [System.CreatedDate] DESC"
```

### Query Output Formatting

```bash
# Output as table
az boards query --wiql "SELECT [System.Id], [System.Title], [System.State] FROM WorkItems" --output table

# Output as JSON for processing
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems" --output json > work-items.json

# Use JMESPath to filter results
az boards query --wiql "SELECT [System.Id], [System.Title], [System.State] FROM WorkItems" --output json | jq '.[] | select(.fields."System.State" == "Active")'
```

## Iterations (Sprints)

### List Iterations

```bash
# List all iterations for project
az boards iteration project list --project MyProject

# List iterations with depth
az boards iteration project list --depth 3

# List as table
az boards iteration project list --output table
```

### Show Iteration

```bash
# Show specific iteration
az boards iteration project show --id "Sprint 1" --project MyProject

# Show with children
az boards iteration project show --id "Sprint 1" --children true
```

### Create Iteration

```bash
# Create iteration
az boards iteration project create --name "Sprint 3" --project MyProject

# Create with dates
az boards iteration project create --name "Sprint 4" \
  --start-date "2025-12-01" \
  --finish-date "2025-12-14" \
  --project MyProject

# Create child iteration
az boards iteration project create --name "Sprint 5" \
  --path "MyProject\\2025" \
  --project MyProject
```

### Update Iteration

```bash
# Update iteration dates
az boards iteration project update --id "Sprint 3" \
  --start-date "2025-12-15" \
  --finish-date "2025-12-28" \
  --project MyProject

# Update iteration name
az boards iteration project update --id "Sprint 3" \
  --name "Sprint 3 Extended" \
  --project MyProject
```

### Delete Iteration

```bash
# Delete iteration
az boards iteration project delete --id "Sprint Old" --yes --project MyProject
```

## Team Iterations

```bash
# List team iterations
az boards iteration team list --team "MyTeam" --project MyProject

# Add iteration to team
az boards iteration team add --id "Sprint 1" --team "MyTeam" --project MyProject

# Show team iteration
az boards iteration team show --id "Sprint 1" --team "MyTeam" --project MyProject

# Remove iteration from team
az boards iteration team remove --id "Sprint 1" --team "MyTeam" --yes --project MyProject
```

## Area Paths

### List Areas

```bash
# List all areas for project
az boards area project list --project MyProject

# List with depth
az boards area project list --depth 3

# List as table
az boards area project list --output table
```

### Show Area

```bash
# Show specific area
az boards area project show --id "Backend" --project MyProject

# Show with children
az boards area project show --id "Backend" --children true
```

### Create Area

```bash
# Create area
az boards area project create --name "Mobile" --project MyProject

# Create child area
az boards area project create --name "iOS" \
  --path "MyProject\\Mobile" \
  --project MyProject
```

### Update Area

```bash
# Update area name
az boards area project update --id "Mobile" \
  --name "Mobile Apps" \
  --project MyProject
```

### Delete Area

```bash
# Delete area
az boards area project delete --id "OldArea" --yes --project MyProject
```

## Team Areas

```bash
# List team areas
az boards area team list --team "MyTeam" --project MyProject

# Add area to team
az boards area team add --path "MyProject\\Backend" --team "MyTeam" --project MyProject

# Update team area
az boards area team update --path "MyProject\\Backend" \
  --include-sub-areas true \
  --team "MyTeam" \
  --project MyProject

# Remove area from team
az boards area team remove --path "MyProject\\Backend" --team "MyTeam" --yes --project MyProject
```

## Scripting Examples

### Bulk Work Item Creation

```bash
#!/bin/bash
while IFS=, read -r type title assignee; do
  az boards work-item create --type "$type" --title "$title" --assigned-to "$assignee" --project MyProject
done < work-items.csv
```

### Sprint Report

```bash
#!/bin/bash
SPRINT="Sprint 1"
echo "Sprint Report: $SPRINT"
az boards query --wiql "SELECT [System.Id] FROM WorkItems WHERE [System.IterationPath] = '$SPRINT'" --output json | jq 'length'
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.IterationPath] = '$SPRINT' AND [System.State] = 'Closed'" --output table
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.IterationPath] = '$SPRINT' AND [System.Tags] CONTAINS 'blocked'" --output table
```

### Work Item State Transition

```bash
#!/bin/bash
FROM_STATE="New"; TO_STATE="Active"
az boards query --wiql "SELECT [System.Id] FROM WorkItems WHERE [System.State] = '$FROM_STATE'" --output json | jq -r '.[].id' | while read id; do
  az boards work-item update --id "$id" --state "$TO_STATE"
done
```

### Team Velocity Report

```bash
#!/bin/bash
# Calculate team velocity

SPRINTS=("Sprint 1" "Sprint 2" "Sprint 3")

for sprint in "${SPRINTS[@]}"; do
  echo "Velocity for $sprint:"
  az boards query --wiql "SELECT [System.Id], [Microsoft.VSTS.Scheduling.StoryPoints] FROM WorkItems WHERE [System.IterationPath] = '$sprint' AND [System.State] = 'Closed'" --output json | jq '[.[].fields."Microsoft.VSTS.Scheduling.StoryPoints" // 0] | add'
done
```

### Assigned Work Items Dashboard

```bash
#!/bin/bash
# Show work items assigned to current user

USER="me@example.com"

echo "Work Items Dashboard for $USER"
echo "================================="

echo -e "\nActive Work:"
az boards query --wiql "SELECT [System.Id], [System.Title], [System.WorkItemType] FROM WorkItems WHERE [System.AssignedTo] = '$USER' AND [System.State] = 'Active'" --output table

echo -e "\nIn Progress:"
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.AssignedTo] = '$USER' AND [System.State] = 'In Progress'" --output table

echo -e "\nBlocked:"
az boards query --wiql "SELECT [System.Id], [System.Title] FROM WorkItems WHERE [System.AssignedTo] = '$USER' AND [System.Tags] CONTAINS 'blocked'" --output table
```

## Best Practices

- WIQL for complex queries
- Use macros: @Me, @CurrentIteration
- Set area/iteration defaults
- Tag work items for organization
- Parent-child relationships for hierarchy
- Query before bulk updates
- JSON for scripting
- Save frequent WIQL queries

## WIQL Reference

### Common Fields

- `[System.Id]` - Work item ID
- `[System.Title]` - Work item title
- `[System.State]` - Current state
- `[System.WorkItemType]` - Type (Bug, User Story, Task, etc.)
- `[System.AssignedTo]` - Assigned user
- `[System.CreatedBy]` - Creator
- `[System.CreatedDate]` - Creation date
- `[System.ChangedDate]` - Last modified date
- `[System.AreaPath]` - Area path
- `[System.IterationPath]` - Iteration path
- `[System.Tags]` - Tags
- `[System.Priority]` - Priority (1-4)
- `[Microsoft.VSTS.Common.Severity]` - Severity
- `[Microsoft.VSTS.Scheduling.StoryPoints]` - Story points

### Operators

- `=` - Equals
- `<>` - Not equals
- `>`, `<`, `>=`, `<=` - Comparison
- `CONTAINS` - String contains
- `UNDER` - Area/iteration path hierarchy
- `IN` - Value in list
- `AND`, `OR` - Logical operators

### Macros

- `@Me` - Current user
- `@Today` - Today's date
- `@CurrentIteration` - Current iteration
- `@Project` - Current project

## Troubleshooting

**Not found**: Verify with `az boards work-item show --id 123` or search by title

**WIQL errors**: Field names are case-sensitive, use brackets `[Field.Name]`, proper escaping

**Permissions**: Verify with `az devops project show --project MyProject`

## References

- [Azure Boards CLI Reference](https://learn.microsoft.com/en-us/cli/azure/boards)
- [WIQL Syntax](https://learn.microsoft.com/en-us/azure/devops/boards/queries/wiql-syntax)
- [Work Item Fields](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/guidance/work-item-field)
