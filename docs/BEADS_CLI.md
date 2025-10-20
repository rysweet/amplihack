# Beads CLI Integration

Complete CLI integration for beads issue tracking in amplihack.

## Overview

The beads CLI integration provides command-line access to all beads functionality, enabling:

- Issue creation and management
- Ready work querying (issues with no blockers)
- Status tracking and updates
- Label and assignee filtering
- JSON output for programmatic usage

## Installation

First, install beads:

```bash
# Option 1: Homebrew (macOS)
brew install steveyegge/beads/beads

# Option 2: Direct download
# Visit https://github.com/steveyegge/beads
```

Verify installation:

```bash
amplihack beads status
```

## Commands

### `amplihack beads init`

Initialize beads in the current directory.

```bash
amplihack beads init
```

**Output:**

```
✓ Beads initialized successfully
  Location: .beads/issues.jsonl

You can now use beads commands:
  amplihack beads create --title 'Task name'
  amplihack beads ready
  amplihack beads list
```

**Requirements:**

- Beads must be installed
- Directory must not already be initialized

---

### `amplihack beads status`

Show beads setup status.

```bash
amplihack beads status
```

**Output:**

```
Beads Setup Status:
  Installed: ✓
  Initialized: ✓
  Version: 0.2.0
  Compatible: ✓
```

**Note:** This command works even if beads is not installed.

---

### `amplihack beads create`

Create a new issue.

```bash
amplihack beads create \
  --title "Implement user authentication" \
  --description "Add OAuth2 support with JWT tokens" \
  --labels "feature,auth,priority-high" \
  --assignee "alice" \
  --status "open"
```

**Options:**

- `--title` (required): Issue title
- `--description`: Issue description
- `--labels`: Comma-separated labels
- `--assignee`: Assignee name
- `--status`: Issue status (default: "open")
- `--json`: Output as JSON

**JSON Output:**

```json
{
  "id": "issue-abc123",
  "title": "Implement user authentication"
}
```

**Requirements:**

- Beads must be installed and initialized
- Title is required and cannot be empty

---

### `amplihack beads ready`

Show ready work (issues with no blockers).

```bash
# Show all ready work
amplihack beads ready

# Filter by labels
amplihack beads ready --labels "feature,priority-high"

# Filter by assignee
amplihack beads ready --assignee "alice"

# Limit results
amplihack beads ready --limit 5

# JSON output
amplihack beads ready --json
```

**Options:**

- `--labels`: Filter by labels (comma-separated)
- `--assignee`: Filter by assignee
- `--limit`: Max issues to show (default: 10)
- `--json`: Output as JSON

**Output:**

```
Ready Work (2 issues):

[issue-abc123] Implement user authentication
  Labels: feature, auth, priority-high
  Assignee: alice
  Description: Add OAuth2 support with JWT tokens

[issue-def456] Fix login bug
  Labels: bug, auth
  Assignee: bob
  Description: Users can't log in with special characters
```

**JSON Output:**

```json
[
  {
    "id": "issue-abc123",
    "title": "Implement user authentication",
    "labels": ["feature", "auth", "priority-high"],
    "assignee": "alice",
    "description": "Add OAuth2 support with JWT tokens"
  },
  {
    "id": "issue-def456",
    "title": "Fix login bug",
    "labels": ["bug", "auth"],
    "assignee": "bob",
    "description": "Users can't log in with special characters"
  }
]
```

---

### `amplihack beads list`

List issues with filtering.

```bash
# List open issues
amplihack beads list

# List closed issues
amplihack beads list --status closed

# List in-progress issues
amplihack beads list --status in_progress

# List all issues
amplihack beads list --status all

# Filter by labels
amplihack beads list --labels "bug,priority-high"

# Filter by assignee
amplihack beads list --assignee "alice"

# Limit results
amplihack beads list --limit 10

# JSON output
amplihack beads list --json
```

**Options:**

- `--status`: Filter by status (choices: open, closed, in_progress, blocked, all; default: open)
- `--labels`: Filter by labels (comma-separated)
- `--assignee`: Filter by assignee
- `--limit`: Max issues to show
- `--json`: Output as JSON

**Output:**

```
Issues (3):

[issue-abc123] Implement user authentication (open)
  Labels: feature, auth, priority-high
  Assignee: alice

[issue-def456] Fix login bug (in_progress)
  Labels: bug, auth
  Assignee: bob

[issue-ghi789] Update documentation (closed)
  Labels: docs
  Assignee: charlie
```

---

### `amplihack beads get`

Get issue details by ID.

```bash
# Human-readable output
amplihack beads get issue-abc123

# JSON output
amplihack beads get issue-abc123 --json
```

**Options:**

- `id` (positional, required): Issue ID
- `--json`: Output as JSON

**Output:**

```
Issue: issue-abc123
  Title: Implement user authentication
  Status: open
  Description: Add OAuth2 support with JWT tokens
  Labels: feature, auth, priority-high
  Assignee: alice
  Created: 2024-01-01T12:00:00Z
```

**JSON Output:**

```json
{
  "id": "issue-abc123",
  "title": "Implement user authentication",
  "status": "open",
  "description": "Add OAuth2 support with JWT tokens",
  "labels": ["feature", "auth", "priority-high"],
  "assignee": "alice",
  "created_at": "2024-01-01T12:00:00Z"
}
```

---

### `amplihack beads update`

Update issue fields.

```bash
# Update status
amplihack beads update issue-abc123 --status in_progress

# Update title
amplihack beads update issue-abc123 --title "New title"

# Update description
amplihack beads update issue-abc123 --description "New description"

# Update assignee
amplihack beads update issue-abc123 --assignee "bob"

# Update labels
amplihack beads update issue-abc123 --labels "bug,priority-high,urgent"

# Update multiple fields
amplihack beads update issue-abc123 \
  --status in_progress \
  --assignee "bob" \
  --labels "feature,in-progress"

# JSON output
amplihack beads update issue-abc123 --status closed --json
```

**Options:**

- `id` (positional, required): Issue ID
- `--status`: New status
- `--title`: New title
- `--description`: New description
- `--assignee`: New assignee
- `--labels`: New labels (comma-separated)
- `--json`: Output as JSON

**Output:**

```
✓ Updated issue: issue-abc123
  status: in_progress
  assignee: bob
```

**JSON Output:**

```json
{
  "success": true,
  "id": "issue-abc123"
}
```

---

### `amplihack beads close`

Close an issue.

```bash
# Close with default resolution
amplihack beads close issue-abc123

# Close with custom resolution
amplihack beads close issue-abc123 --resolution "wont-fix"

# JSON output
amplihack beads close issue-abc123 --json
```

**Options:**

- `id` (positional, required): Issue ID
- `--resolution`: Closure resolution (default: "completed")
- `--json`: Output as JSON

**Output:**

```
✓ Closed issue: issue-abc123
  Resolution: completed
```

**JSON Output:**

```json
{
  "success": true,
  "id": "issue-abc123",
  "resolution": "completed"
}
```

---

## Common Workflows

### Create and Track a Feature

```bash
# 1. Create issue
amplihack beads create \
  --title "Add user profile page" \
  --description "Users need a profile page with avatar, bio, and settings" \
  --labels "feature,ui,priority-medium" \
  --assignee "alice"

# 2. Start work
amplihack beads update issue-abc123 --status in_progress

# 3. Complete work
amplihack beads close issue-abc123
```

### Find Ready Work

```bash
# Show all ready work for current user
amplihack beads ready --assignee "alice"

# Show high-priority ready work
amplihack beads ready --labels "priority-high"

# Show ready bugs
amplihack beads ready --labels "bug" --limit 5
```

### Review Status

```bash
# Check beads installation
amplihack beads status

# List all open issues
amplihack beads list --status open

# List in-progress issues
amplihack beads list --status in_progress

# Get details for specific issue
amplihack beads get issue-abc123
```

### Programmatic Usage

```bash
# Create issue and capture ID
ISSUE_ID=$(amplihack beads create \
  --title "Task" \
  --description "Description" \
  --json | jq -r '.id')

# Get ready work as JSON
amplihack beads ready --json | jq '.[] | select(.labels[] == "bug")'

# List all issues as JSON
amplihack beads list --status all --json | jq length
```

---

## Error Handling

### Beads Not Installed

```bash
$ amplihack beads ready
Error: Beads CLI not found

Installation instructions:
  Visit: https://github.com/steveyegge/beads
  Or run: brew install steveyegge/beads/beads
```

### Beads Not Initialized

```bash
$ amplihack beads create --title "Task"
Error: Beads not initialized in this directory
Run: amplihack beads init
```

### Invalid Input

```bash
$ amplihack beads create --title ""
Error: Invalid input: Title cannot be empty
```

### Issue Not Found

```bash
$ amplihack beads get invalid-id
Error: Issue not found: invalid-id
```

---

## Exit Codes

- `0`: Success
- `1`: Error (installation, initialization, validation, or operation failure)

---

## Integration with Beads Infrastructure

The CLI integrates with the comprehensive beads infrastructure:

- **BeadsAdapter**: Safe subprocess wrapper for `bd` command
- **BeadsMemoryProvider**: Memory provider bridge
- **BeadsPrerequisites**: Installation and setup verification
- **Input Validation**: Security controls for all inputs
- **Error Handling**: Graceful degradation and helpful messages

---

## Testing

Verify CLI integration:

```bash
python verify_beads_cli.py
```

This runs comprehensive tests for all commands.

---

## See Also

- [Beads Infrastructure Documentation](../src/amplihack/memory/README.md)
- [Beads CLI GitHub](https://github.com/steveyegge/beads)
- [PR #944 - Beads Infrastructure](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/944)
