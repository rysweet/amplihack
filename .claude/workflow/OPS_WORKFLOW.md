---
name: OPS_WORKFLOW
version: 1.0.0
description: Direct execution workflow for administrative and operational tasks
steps: 1
phases:
  - direct-execution
success_criteria:
  - "Operation completed successfully"
  - "No unintended side effects"
philosophy_alignment:
  - principle: Ruthless Simplicity
    application: No unnecessary ceremony for simple operations
  - principle: Pragmatic Trust
    application: Execute directly without elaborate validation
  - principle: Present-moment focus
    application: Handle what's needed now
customizable: false
---

# Operations Workflow

Direct execution workflow for administrative, maintenance, and operational tasks that don't require structured development processes.

## When This Workflow Applies

Use OPS_WORKFLOW when the request is:

1. **Administrative tasks**: Disk cleanup, file organization, directory management
2. **Repository operations**: Git commands, branch cleanup, status checks
3. **System commands**: Running scripts, executing tools, checking versions
4. **Maintenance tasks**: Cleanup, organize, delete, move files
5. **Quick operations**: Single commands or simple sequences

### Keywords Suggesting Operations

- "run command..."
- "disk cleanup..."
- "clean up..."
- "delete old..."
- "organize files..."
- "git status"
- "check version"
- "list branches"
- "remove unused..."

### NOT Operations (Use Other Workflows)

- "Fix the login bug" → DEFAULT (requires analysis and testing)
- "How does authentication work?" → INVESTIGATION (requires exploration)
- "What files are in src/?" → Q&A (simple question)
- "Refactor the database module" → DEFAULT (code changes with testing)

## The Workflow: Direct Execution

**Step 1: Execute and Report**

Execute the requested operation and report results.

### Guidelines

1. **Understand the request**
   - What's the specific operation?
   - Are there any safety concerns?
   - What's the expected outcome?

2. **Execute directly**
   - Use the appropriate tool (bash, write_file, edit_file, etc.)
   - No elaborate planning for simple operations
   - Handle errors as they occur

3. **Report results**
   - What was done
   - What changed
   - Any errors or warnings

### Safety Considerations

**STOP and confirm with user if:**
- Deleting many files (>10) or large directories
- Running destructive commands (`rm -rf`, `git reset --hard`)
- Modifying critical configuration files
- Operations affecting production systems

**Safe to execute directly:**
- Listing files/directories
- Reading git status
- Checking versions
- Creating directories
- Moving/organizing files
- Cleaning temporary files

### Examples

#### Example 1: Disk Cleanup

**Request**: "Clean up old log files from .claude/runtime/logs/"

**Execution**:
```bash
find .claude/runtime/logs/ -name "*.log" -mtime +30 -delete
```

**Report**:
```
Cleaned up old log files:
- Removed 15 log files older than 30 days
- Freed 2.3 MB disk space
- .claude/runtime/logs/ now contains 8 recent logs
```

#### Example 2: Git Branch Cleanup

**Request**: "Delete local branches that are merged to main"

**Execution**:
```bash
git branch --merged main | grep -v "^\*" | grep -v "main" | xargs -r git branch -d
```

**Report**:
```
Cleaned up merged branches:
- Deleted: feature/old-work, fix/typo, feat/completed
- Kept: main (current branch), develop (unmerged)
- 3 branches removed, 2 active branches remain
```

#### Example 3: Repository Status Check

**Request**: "Show git status"

**Execution**:
```bash
git status
```

**Report**:
```
Repository status:
- Branch: main
- Uncommitted changes: 3 files modified
- Untracked files: 2 new files
- Status: Clean, ready to commit
```

## When to Escalate

If during execution you discover:

- **Complex dependencies**: "This cleanup requires understanding module interactions" → INVESTIGATION
- **Code changes needed**: "Need to update imports after moving files" → DEFAULT
- **System design required**: "This operation needs architectural planning" → DEFAULT

Then STOP and re-classify to the appropriate workflow.

## Workflow Comparison

| Workflow      | When to Use                     | Steps | Complexity |
| ------------- | ------------------------------- | ----- | ---------- |
| OPS           | Admin tasks, simple operations  | 1     | Minimal    |
| Q&A           | Simple questions                | 3     | Low        |
| INVESTIGATION | Understanding existing systems  | 6     | Medium     |
| DEFAULT       | Code changes, features, bugs    | 22    | High       |

## Philosophy Notes

Operations workflow embodies:

- **Wabi-sabi**: Execute what's needed without unnecessary embellishment
- **Occam's Razor**: The simplest path is to just do it
- **Pragmatic trust**: Trust the system enough to execute directly
- **Present-moment focus**: Handle this operation now, not hypothetical failures

This is the LIGHTEST workflow - when operations need planning, they're not operations anymore.
