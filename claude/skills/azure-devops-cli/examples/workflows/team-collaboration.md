# Team Collaboration Workflows

Advanced team collaboration patterns using Azure DevOps CLI for sprint planning, code reviews, and team coordination.

## Sprint Planning and Management

### Sprint Setup Automation

```bash
#!/bin/bash
# Automated sprint setup

PROJECT="MyProject"
SPRINT_NAME="Sprint 42"
TEAM="MyTeam"
START_DATE="2025-12-01"
END_DATE="2025-12-14"

echo "Setting up $SPRINT_NAME..."

# 1. Create iteration
echo "Creating iteration..."
az boards iteration project create \
  --name "$SPRINT_NAME" \
  --start-date "$START_DATE" \
  --finish-date "$END_DATE" \
  --project "$PROJECT"

# 2. Add iteration to team
echo "Adding iteration to team..."
az boards iteration team add \
  --id "$SPRINT_NAME" \
  --team "$TEAM" \
  --project "$PROJECT"

# 3. Query backlog items
echo "Finding backlog items..."
BACKLOG_ITEMS=$(az boards query --wiql "
  SELECT [System.Id], [System.Title], [System.Priority]
  FROM WorkItems
  WHERE [System.State] = 'New'
    AND [System.WorkItemType] = 'User Story'
  ORDER BY [System.Priority] ASC
" --query "[].id" -o tsv)

# 4. Move top priority items to sprint
echo "Moving items to $SPRINT_NAME..."
ITEM_COUNT=0
MAX_ITEMS=10

for item_id in $BACKLOG_ITEMS; do
  if [ "$ITEM_COUNT" -ge "$MAX_ITEMS" ]; then
    break
  fi

  az boards work-item update \
    --id "$item_id" \
    --iteration "$PROJECT\\$SPRINT_NAME" \
    --state "Active"

  ITEM_COUNT=$((ITEM_COUNT + 1))
done

echo "Sprint setup complete: $ITEM_COUNT items added to $SPRINT_NAME"
```

### Sprint Capacity Planning

```bash
#!/bin/bash
# Calculate and display team capacity

PROJECT="MyProject"
SPRINT="Sprint 42"

echo "Team Capacity Report: $SPRINT"
echo "=================================="

# Get team members
TEAM_MEMBERS=$(az devops team list --project "$PROJECT" --query "[0].name" -o tsv)

# Sprint duration (working days)
SPRINT_DAYS=10
HOURS_PER_DAY=6  # Accounting for meetings, etc.

# Get current sprint work items
WORK_ITEMS=$(az boards query --wiql "
  SELECT [System.Id], [System.AssignedTo], [Microsoft.VSTS.Scheduling.RemainingWork]
  FROM WorkItems
  WHERE [System.IterationPath] = '$PROJECT\\$SPRINT'
    AND [System.State] != 'Closed'
" --output json)

# Calculate total capacity
TOTAL_CAPACITY=$((SPRINT_DAYS * HOURS_PER_DAY))

echo "Sprint Duration: $SPRINT_DAYS days"
echo "Hours per day: $HOURS_PER_DAY"
echo "Total Capacity: $TOTAL_CAPACITY hours per person"
echo ""

# Calculate allocated hours (would need to parse JSON)
echo "Current Allocation:"
echo "$WORK_ITEMS" | jq -r '
  group_by(.fields."System.AssignedTo".displayName) |
  map({
    user: .[0].fields."System.AssignedTo".displayName,
    hours: map(.fields."Microsoft.VSTS.Scheduling.RemainingWork" // 0) | add
  }) |
  .[] |
  "\(.user): \(.hours) hours"
'
```

### Daily Standup Report

```bash
#!/bin/bash
# Generate daily standup report

PROJECT="MyProject"
TEAM="MyTeam"
SPRINT="Sprint 42"

echo "Daily Standup Report: $(date +%Y-%m-%d)"
echo "========================================"
echo ""

# Yesterday's completed work
echo "✓ COMPLETED YESTERDAY:"
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

az boards query --wiql "
  SELECT [System.Id], [System.Title], [System.AssignedTo]
  FROM WorkItems
  WHERE [System.IterationPath] = '$PROJECT\\$SPRINT'
    AND [System.State] = 'Closed'
    AND [System.ChangedDate] >= '$YESTERDAY'
" --output table

echo ""

# Today's active work
echo "▶ IN PROGRESS TODAY:"
az boards query --wiql "
  SELECT [System.Id], [System.Title], [System.AssignedTo]
  FROM WorkItems
  WHERE [System.IterationPath] = '$PROJECT\\$SPRINT'
    AND [System.State] = 'In Progress'
" --output table

echo ""

# Blockers
echo "🚫 BLOCKED ITEMS:"
az boards query --wiql "
  SELECT [System.Id], [System.Title], [System.AssignedTo]
  FROM WorkItems
  WHERE [System.IterationPath] = '$PROJECT\\$SPRINT'
    AND [System.Tags] CONTAINS 'blocked'
" --output table

echo ""

# PRs waiting for review
echo "👀 PRs WAITING FOR REVIEW:"
az repos pr list --status active --output table

echo ""
echo "========================================"
```

### Sprint Retrospective Data

```bash
#!/bin/bash
# Generate sprint retrospective data

PROJECT="MyProject"
SPRINT="Sprint 42"
REPORT_FILE="retrospective-$SPRINT.md"

echo "# Sprint Retrospective: $SPRINT" > "$REPORT_FILE"
echo "Date: $(date +%Y-%m-%d)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Sprint goals (would be manually added)
echo "## Sprint Goals" >> "$REPORT_FILE"
echo "- Goal 1" >> "$REPORT_FILE"
echo "- Goal 2" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Velocity
echo "## Velocity" >> "$REPORT_FILE"
TOTAL_POINTS=$(az boards query --wiql "
  SELECT [System.Id]
  FROM WorkItems
  WHERE [System.IterationPath] = '$PROJECT\\$SPRINT'
" --output json | jq '[.[].fields."Microsoft.VSTS.Scheduling.StoryPoints" // 0] | add')

COMPLETED_POINTS=$(az boards query --wiql "
  SELECT [System.Id]
  FROM WorkItems
  WHERE [System.IterationPath] = '$PROJECT\\$SPRINT'
    AND [System.State] = 'Closed'
" --output json | jq '[.[].fields."Microsoft.VSTS.Scheduling.StoryPoints" // 0] | add')

echo "- Planned: $TOTAL_POINTS points" >> "$REPORT_FILE"
echo "- Completed: $COMPLETED_POINTS points" >> "$REPORT_FILE"
echo "- Completion Rate: $(awk "BEGIN {printf \"%.1f\", ($COMPLETED_POINTS/$TOTAL_POINTS)*100}")%" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Work item breakdown
echo "## Work Item Summary" >> "$REPORT_FILE"
az boards query --wiql "
  SELECT [System.WorkItemType], [System.State]
  FROM WorkItems
  WHERE [System.IterationPath] = '$PROJECT\\$SPRINT'
" --output json | jq -r '
  group_by(.fields."System.WorkItemType") |
  map({
    type: .[0].fields."System.WorkItemType",
    total: length,
    closed: [.[] | select(.fields."System.State" == "Closed")] | length
  }) |
  .[] |
  "- \(.type): \(.closed)/\(.total) completed"
' >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"

# PR statistics
echo "## Pull Request Statistics" >> "$REPORT_FILE"
TOTAL_PRS=$(az repos pr list --status all --output json | jq '[.[] | select(.creationDate >= "2025-12-01")] | length')
COMPLETED_PRS=$(az repos pr list --status completed --output json | jq '[.[] | select(.creationDate >= "2025-12-01")] | length')

echo "- Total PRs: $TOTAL_PRS" >> "$REPORT_FILE"
echo "- Merged: $COMPLETED_PRS" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Build statistics
echo "## Build Statistics" >> "$REPORT_FILE"
BUILD_STATS=$(az pipelines runs list --top 100 --output json | jq -r '
  group_by(.result) |
  map({result: .[0].result, count: length}) |
  .[] |
  "- \(.result): \(.count)"
')
echo "$BUILD_STATS" >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"
echo "## Action Items" >> "$REPORT_FILE"
echo "1. (Add action items here)" >> "$REPORT_FILE"

echo "Retrospective report generated: $REPORT_FILE"
cat "$REPORT_FILE"
```

## Code Review Automation

### Automated PR Assignment

```bash
#!/bin/bash
# Automatically assign reviewers based on code ownership

REPO="myrepo"
PR_ID=$1

if [ -z "$PR_ID" ]; then
  echo "Usage: $0 <pr-id>"
  exit 1
fi

echo "Assigning reviewers for PR #$PR_ID..."

# Get PR details
PR_SOURCE=$(az repos pr show --id "$PR_ID" --query "sourceRefName" -o tsv)
PR_AUTHOR=$(az repos pr show --id "$PR_ID" --query "createdBy.uniqueName" -o tsv)

# Get changed files
CHANGED_FILES=$(az repos pr show --id "$PR_ID" --output json | jq -r '.url' | sed 's|pullRequests.*|diffs?targetVersionType=branch\&targetVersion=main|')

# Simple code ownership rules (in production, use CODEOWNERS file)
declare -A CODE_OWNERS=(
  ["frontend/"]="frontend-team@example.com"
  ["backend/"]="backend-team@example.com"
  ["docs/"]="tech-writer@example.com"
  ["tests/"]="qa-team@example.com"
)

REVIEWERS=()

# Match changed files to owners
# (Simplified - would need actual file list from API)
for path in "${!CODE_OWNERS[@]}"; do
  REVIEWERS+=("${CODE_OWNERS[$path]}")
done

# Remove duplicates and author
UNIQUE_REVIEWERS=($(printf '%s\n' "${REVIEWERS[@]}" | sort -u | grep -v "$PR_AUTHOR"))

# Add reviewers to PR
for reviewer in "${UNIQUE_REVIEWERS[@]}"; do
  echo "Adding reviewer: $reviewer"
  az repos pr reviewer add --id "$PR_ID" --reviewers "$reviewer"
done

echo "Reviewers assigned successfully"
```

### PR Review Dashboard

```bash
#!/bin/bash
# Generate PR review dashboard for team

REPO="myrepo"
DASHBOARD_FILE="pr-dashboard-$(date +%Y%m%d).txt"

echo "PR Review Dashboard: $(date +%Y-%m-%d)" > "$DASHBOARD_FILE"
echo "========================================" >> "$DASHBOARD_FILE"
echo "" >> "$DASHBOARD_FILE"

# PRs waiting for review
echo "🔍 WAITING FOR REVIEW:" >> "$DASHBOARD_FILE"
az repos pr list --repository "$REPO" --status active \
  --query "[?reviewers[?vote==0]].{ID:pullRequestId, Title:title, Author:createdBy.displayName, Age:creationDate}" \
  --output table >> "$DASHBOARD_FILE"

echo "" >> "$DASHBOARD_FILE"

# PRs with requested changes
echo "⚠️ CHANGES REQUESTED:" >> "$DASHBOARD_FILE"
az repos pr list --repository "$REPO" --status active \
  --query "[?reviewers[?vote==-5]].{ID:pullRequestId, Title:title, Author:createdBy.displayName}" \
  --output table >> "$DASHBOARD_FILE"

echo "" >> "$DASHBOARD_FILE"

# Approved PRs waiting for merge
echo "✅ APPROVED (Ready to Merge):" >> "$DASHBOARD_FILE"
az repos pr list --repository "$REPO" --status active \
  --query "[?reviewers[?vote==10]].{ID:pullRequestId, Title:title, Author:createdBy.displayName}" \
  --output table >> "$DASHBOARD_FILE"

echo "" >> "$DASHBOARD_FILE"

# PRs by reviewer
echo "📊 REVIEW WORKLOAD:" >> "$DASHBOARD_FILE"
az repos pr list --repository "$REPO" --status active --output json | \
  jq -r '.[] | .reviewers[] | .displayName' | \
  sort | uniq -c | sort -rn | \
  awk '{print "  " $2 " " $3 ": " $1 " PRs"}' >> "$DASHBOARD_FILE"

cat "$DASHBOARD_FILE"
```

### Review Reminder Bot

```bash
#!/bin/bash
# Send reminders for stale PRs

REPO="myrepo"
STALE_DAYS=3

echo "Checking for stale PRs (older than $STALE_DAYS days)..."

CUTOFF_DATE=$(date -d "$STALE_DAYS days ago" +%Y-%m-%d)

az repos pr list --repository "$REPO" --status active --output json | \
  jq -r --arg cutoff "$CUTOFF_DATE" '
    .[] |
    select(.creationDate < $cutoff) |
    select(.reviewers | any(.vote == 0)) |
    "\(.pullRequestId)|\(.title)|\(.createdBy.uniqueName)|\(.creationDate)"
  ' | while IFS='|' read -r pr_id title author created_date; do

    echo "Stale PR #$pr_id: $title"
    echo "  Author: $author"
    echo "  Created: $created_date"

    # Get reviewers who haven't voted
    PENDING_REVIEWERS=$(az repos pr reviewer list --id "$pr_id" --output json | \
      jq -r '.[] | select(.vote == 0) | .uniqueName')

    echo "  Pending reviewers:"
    for reviewer in $PENDING_REVIEWERS; do
      echo "    - $reviewer"
      # Send reminder (implement notification mechanism)
      # Example: send email or Teams message
    done

    echo ""
done
```

## Team Coordination

### Work Distribution Report

```bash
#!/bin/bash
# Analyze work distribution across team

PROJECT="MyProject"
SPRINT="Sprint 42"

echo "Work Distribution Report: $SPRINT"
echo "=================================="
echo ""

# Get all active work items in sprint
WORK_ITEMS=$(az boards query --wiql "
  SELECT [System.Id], [System.AssignedTo], [Microsoft.VSTS.Scheduling.RemainingWork], [System.WorkItemType]
  FROM WorkItems
  WHERE [System.IterationPath] = '$PROJECT\\$SPRINT'
    AND [System.State] != 'Closed'
" --output json)

echo "Work Items by Assignee:"
echo "$WORK_ITEMS" | jq -r '
  group_by(.fields."System.AssignedTo".displayName // "Unassigned") |
  map({
    assignee: .[0].fields."System.AssignedTo".displayName // "Unassigned",
    count: length,
    hours: map(.fields."Microsoft.VSTS.Scheduling.RemainingWork" // 0) | add
  }) |
  sort_by(.hours) |
  reverse |
  .[] |
  "\(.assignee): \(.count) items, \(.hours) hours"
'

echo ""
echo "Work Items by Type:"
echo "$WORK_ITEMS" | jq -r '
  group_by(.fields."System.WorkItemType") |
  map({
    type: .[0].fields."System.WorkItemType",
    count: length
  }) |
  .[] |
  "  \(.type): \(.count)"
'

echo ""

# Identify unassigned work
UNASSIGNED=$(az boards query --wiql "
  SELECT [System.Id], [System.Title]
  FROM WorkItems
  WHERE [System.IterationPath] = '$PROJECT\\$SPRINT'
    AND [System.AssignedTo] = ''
    AND [System.State] != 'Closed'
" --query "length(@)" -o tsv)

if [ "$UNASSIGNED" -gt 0 ]; then
  echo "⚠️ Warning: $UNASSIGNED unassigned work items"
  az boards query --wiql "
    SELECT [System.Id], [System.Title], [System.WorkItemType]
    FROM WorkItems
    WHERE [System.IterationPath] = '$PROJECT\\$SPRINT'
      AND [System.AssignedTo] = ''
      AND [System.State] != 'Closed'
  " --output table
fi
```

### Team Velocity Tracking

```bash
#!/bin/bash
# Track team velocity over multiple sprints

PROJECT="MyProject"
NUM_SPRINTS=6

echo "Team Velocity Trend (Last $NUM_SPRINTS sprints)"
echo "==============================================="
echo ""

# Get recent iterations
ITERATIONS=$(az boards iteration project list --project "$PROJECT" \
  --query "reverse(sort_by([].{name:name, path:path}, &name)) | [0:$NUM_SPRINTS]" \
  --output json)

echo "Sprint | Planned | Completed | % Complete"
echo "-------|---------|-----------|------------"

echo "$ITERATIONS" | jq -r '.[] | .path' | while read iteration_path; do
  SPRINT_NAME=$(basename "$iteration_path")

  # Get total story points
  TOTAL=$(az boards query --wiql "
    SELECT [System.Id]
    FROM WorkItems
    WHERE [System.IterationPath] = '$iteration_path'
      AND [System.WorkItemType] = 'User Story'
  " --output json | jq '[.[].fields."Microsoft.VSTS.Scheduling.StoryPoints" // 0] | add')

  # Get completed story points
  COMPLETED=$(az boards query --wiql "
    SELECT [System.Id]
    FROM WorkItems
    WHERE [System.IterationPath] = '$iteration_path'
      AND [System.WorkItemType] = 'User Story'
      AND [System.State] = 'Closed'
  " --output json | jq '[.[].fields."Microsoft.VSTS.Scheduling.StoryPoints" // 0] | add')

  if [ "$TOTAL" -gt 0 ]; then
    PERCENT=$(awk "BEGIN {printf \"%.0f\", ($COMPLETED/$TOTAL)*100}")
  else
    PERCENT=0
  fi

  printf "%-15s | %7s | %9s | %10s%%\n" "$SPRINT_NAME" "$TOTAL" "$COMPLETED" "$PERCENT"
done
```

### Cross-Team Dependency Tracker

```bash
#!/bin/bash
# Track dependencies between teams

PROJECT="MyProject"

echo "Cross-Team Dependencies"
echo "======================="
echo ""

# Query work items with external dependencies tag
DEPENDENCIES=$(az boards query --wiql "
  SELECT [System.Id], [System.Title], [System.AssignedTo], [System.Tags]
  FROM WorkItems
  WHERE [System.Tags] CONTAINS 'dependency'
    AND [System.State] != 'Closed'
" --output json)

echo "Items with Dependencies:"
echo "$DEPENDENCIES" | jq -r '.[] | "\(.id): \(.fields."System.Title") (Assigned: \(.fields."System.AssignedTo".displayName // "Unassigned"))"'

echo ""
echo "Blocked Items:"
az boards query --wiql "
  SELECT [System.Id], [System.Title], [System.AssignedTo]
  FROM WorkItems
  WHERE [System.Tags] CONTAINS 'blocked'
    AND [System.State] != 'Closed'
" --output table
```

## Onboarding Automation

### New Team Member Setup

```bash
#!/bin/bash
# Automate new team member onboarding

NEW_MEMBER_EMAIL=$1
PROJECT="MyProject"
TEAM="MyTeam"

if [ -z "$NEW_MEMBER_EMAIL" ]; then
  echo "Usage: $0 <new-member-email>"
  exit 1
fi

echo "Onboarding new team member: $NEW_MEMBER_EMAIL"

# 1. Add to team (requires appropriate permissions)
echo "Adding to team..."
# az devops user add --email-id "$NEW_MEMBER_EMAIL"

# 2. Grant repository access
echo "Granting repository access..."
REPOS=$(az repos list --project "$PROJECT" --query "[].name" -o tsv)
for repo in $REPOS; do
  echo "  - $repo"
  # Permissions would be set via security commands
done

# 3. Add to relevant variable groups
echo "Configuring access to shared resources..."
# Variable group permissions

# 4. Create onboarding work item
echo "Creating onboarding checklist..."
az boards work-item create \
  --type "Task" \
  --title "Onboarding: $NEW_MEMBER_EMAIL" \
  --assigned-to "$NEW_MEMBER_EMAIL" \
  --description "
## Onboarding Checklist

- [ ] Complete Azure DevOps training
- [ ] Set up development environment
- [ ] Clone repositories
- [ ] Review coding standards
- [ ] Attend team standup
- [ ] Pair programming session
- [ ] Review architecture docs
  " \
  --fields "System.Tags=onboarding"

echo "Onboarding setup complete!"
echo "Checklist work item created for $NEW_MEMBER_EMAIL"
```

## Best Practices

1. **Daily Standups**: Automate status reports for efficiency
2. **Sprint Planning**: Use data-driven capacity planning
3. **Code Reviews**: Automate reviewer assignment based on code ownership
4. **Work Distribution**: Monitor and balance workload across team
5. **Retrospectives**: Generate data for informed discussions
6. **Dependencies**: Track and visualize cross-team dependencies
7. **Velocity**: Track team velocity for better planning
8. **Onboarding**: Standardize new team member setup

## References

- [Azure Boards Agile Process](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/guidance/agile-process)
- [Sprint Planning](https://learn.microsoft.com/en-us/azure/devops/boards/sprints/assign-work-sprint)
- [Code Review Best Practices](https://learn.microsoft.com/en-us/azure/devops/repos/git/review-code-with-pull-requests)
