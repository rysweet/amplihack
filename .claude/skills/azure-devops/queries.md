# WIQL Query Guide

Work Item Query Language (WIQL) guide for querying Azure DevOps work items.

## Predefined Queries

Common queries are built-in to list_work_items.py:

### mine
Your assigned work items:
```bash
python .claude/scenarios/az-devops-tools/list_work_items.py --query mine
```

### unassigned
Open work items with no assignee:
```bash
python .claude/scenarios/az-devops-tools/list_work_items.py --query unassigned
```

### recent
Recently changed work items:
```bash
python .claude/scenarios/az-devops-tools/list_work_items.py --query recent
```

### active
Active work items:
```bash
python .claude/scenarios/az-devops-tools/list_work_items.py --query active
```

### team
Team's open work items:
```bash
python .claude/scenarios/az-devops-tools/list_work_items.py --query team
```

## Custom WIQL Queries

### Basic Syntax

```sql
SELECT [Field1], [Field2], [Field3]
FROM workitems
WHERE [Condition]
ORDER BY [Field] ASC/DESC
```

### Example: Active Tasks

```bash
python .claude/scenarios/az-devops-tools/list_work_items.py \
  --wiql "SELECT [System.Id], [System.Title] FROM workitems WHERE [System.WorkItemType] = 'Task' AND [System.State] = 'Active'"
```

### Example: High Priority Bugs

```bash
python .claude/scenarios/az-devops-tools/list_work_items.py \
  --wiql "SELECT [System.Id], [System.Title], [Microsoft.VSTS.Common.Priority] FROM workitems WHERE [System.WorkItemType] = 'Bug' AND [Microsoft.VSTS.Common.Priority] = 1"
```

### Example: Recently Created

```bash
python .claude/scenarios/az-devops-tools/list_work_items.py \
  --wiql "SELECT [System.Id], [System.Title] FROM workitems WHERE [System.CreatedDate] >= @Today - 7 ORDER BY [System.CreatedDate] DESC"
```

## Output Formats

### Table (Default)
```bash
python .claude/scenarios/az-devops-tools/list_work_items.py --query mine
```

### JSON
```bash
python .claude/scenarios/az-devops-tools/list_work_items.py --query mine --format json
```

### CSV
```bash
python .claude/scenarios/az-devops-tools/list_work_items.py --query mine --format csv > items.csv
```

### IDs Only
```bash
python .claude/scenarios/az-devops-tools/list_work_items.py --query mine --format ids-only
```

## Limit Results

```bash
python .claude/scenarios/az-devops-tools/list_work_items.py --query recent --limit 10
```

## Common Fields

### System Fields

- `[System.Id]` - Work item ID
- `[System.Title]` - Title
- `[System.WorkItemType]` - Type (Bug, Task, Story, etc.)
- `[System.State]` - State (New, Active, Closed, etc.)
- `[System.AssignedTo]` - Assigned user
- `[System.CreatedDate]` - Creation date
- `[System.ChangedDate]` - Last modified date
- `[System.AreaPath]` - Area path
- `[System.IterationPath]` - Sprint/iteration
- `[System.Tags]` - Tags

### Microsoft VSTS Fields

- `[Microsoft.VSTS.Common.Priority]` - Priority (1-4)
- `[Microsoft.VSTS.Common.Severity]` - Severity (1-4)
- `[Microsoft.VSTS.Common.StackRank]` - Backlog rank

## Operators

### Comparison
- `=` - Equals
- `<>` - Not equals
- `<` - Less than
- `>` - Greater than
- `<=` - Less than or equal
- `>=` - Greater than or equal

### Logical
- `AND` - Both conditions true
- `OR` - Either condition true
- `NOT` - Negate condition

### String
- `CONTAINS` - Field contains value
- `LIKE` - Pattern matching

### Special
- `IN` - Value in list
- `UNDER` - Under area/iteration path
- `@Me` - Current user
- `@Today` - Current date
- `@Project` - Current project

## Example Queries

### Find Bugs Assigned to Me
```bash
python .claude/scenarios/az-devops-tools/list_work_items.py \
  --wiql "SELECT [System.Id], [System.Title] FROM workitems WHERE [System.WorkItemType] = 'Bug' AND [System.AssignedTo] = @Me"
```

### Find Stories in Sprint
```bash
python .claude/scenarios/az-devops-tools/list_work_items.py \
  --wiql "SELECT [System.Id], [System.Title] FROM workitems WHERE [System.WorkItemType] = 'User Story' AND [System.IterationPath] = 'MyProject\\Sprint 1'"
```

### Find Items with Tag
```bash
python .claude/scenarios/az-devops-tools/list_work_items.py \
  --wiql "SELECT [System.Id], [System.Title] FROM workitems WHERE [System.Tags] CONTAINS 'security'"
```

### Find Items in Area
```bash
python .claude/scenarios/az-devops-tools/list_work_items.py \
  --wiql "SELECT [System.Id], [System.Title] FROM workitems WHERE [System.AreaPath] UNDER 'MyProject\\Platform'"
```

## Tips

1. Test queries in Azure DevOps web UI first
2. Use `--limit` for large result sets
3. Use `@Me`, `@Today`, `@Project` for dynamic queries
4. Escape single quotes in strings with two single quotes
5. Field names are case-sensitive

## See Also

- [WIQL Syntax Reference](https://learn.microsoft.com/en-us/azure/devops/boards/queries/wiql-syntax)
- [@work-items.md] - Work item operations
