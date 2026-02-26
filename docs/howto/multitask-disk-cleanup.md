# How to Manage Disk Space When Using Multitask

> **Diátaxis Category**: How-To Guide (Problem-solving)
> **Goal**: Prevent disk space exhaustion from multitask workstream clones
> **Time**: 10 minutes

## Problem

The `/multitask` skill creates temporary git clones in `/tmp` for each parallel workstream. If you run many tasks or forget to clean up, these can consume significant disk space (e.g., 49GB in reported cases).

## Solution Overview

Use the built-in disk management features in multitask:

1. **Monitor** disk usage with startup warnings and final reports
2. **Cleanup** merged workstreams automatically with `--cleanup` flag
3. **Prevent** buildup with regular maintenance

## Quick Reference

````bash
# Check disk usage before starting
df -h /tmp

# Run multitask with automatic cleanup
/multitask --cleanup workstreams.json

# Dry-run to see what would be deleted
/multitask --cleanup --dry-run workstreams.json

# Manual cleanup of all workstreams
rm -rf /tmp/multitask-workstreams-*

# Calculate current usage
du -sh /tmp/multitask-workstreams-*
````

## When to Use Each Approach

### Automatic Cleanup (Recommended)

**Use when**:
- PRs have been merged to main
- You're finished with the workstream
- You want safe, automated cleanup

**Command**:

````bash
/multitask --cleanup workstreams.json
````

**What happens**:
- Checks each PR status using `gh pr view`
- Deletes only **merged** PR workstreams
- Preserves open/draft PRs (safe!)
- Reports what was deleted

### Dry-Run Preview

**Use when**:
- You want to see what would be deleted
- You're unsure which workstreams are safe to remove
- You want to verify before actual deletion

**Command**:

````bash
/multitask --cleanup --dry-run workstreams.json
````

**Example output**:

````
Disk Cleanup (dry-run mode - no actual deletion):

Would delete (merged PRs):
  #123 feat/add-auth (4.2 GB) - merged 2 days ago
  #124 fix/memory-leak (1.8 GB) - merged yesterday

Would preserve (not merged):
  #125 feat/new-feature (3.1 GB) - open
  #126 docs/update (0.5 GB) - draft

Total space to reclaim: 6.0 GB
````

### Manual Cleanup

**Use when**:
- You want to delete **everything** (even open PRs)
- Multitask automated cleanup isn't working
- You need immediate space recovery

**Commands**:

````bash
# Delete all workstreams (DESTRUCTIVE!)
rm -rf /tmp/multitask-workstreams-*

# Or delete specific workstream
rm -rf /tmp/multitask-workstreams-123-feat-add-auth
````

**⚠️ Warning**: This deletes **all** workstreams, including open PRs!

## Monitoring Disk Usage

### Startup Warning

Multitask automatically checks disk space at startup:

````
⚠️  Warning: Low disk space
Available: 8.2 GB
Recommended: 10+ GB

This session will create ~12 GB of workstream clones.
Consider running cleanup before proceeding.

Run: /multitask --cleanup workstreams.json
````

### Final Report

After task completion, multitask shows disk statistics:

````
=== Multitask Summary ===

Workstreams: 4 total
- Completed: 3
- Failed: 1

Disk Usage:
- Workstreams: 15.3 GB
- Available: 4.2 GB

Cleanup suggestion:
  # Safe cleanup (merged PRs only)
  /multitask --cleanup workstreams.json

  # Full cleanup (all workstreams)
  rm -rf /tmp/multitask-workstreams-*
````

## Step-by-Step: Safe Cleanup Workflow

### Step 1: Check Current Disk Usage

````bash
# Total usage by all workstreams
du -sh /tmp/multitask-workstreams-*

# Detailed breakdown
du -h /tmp/multitask-workstreams-* | sort -h
````

**Example output**:

````
1.2G    /tmp/multitask-workstreams-123-feat-auth
3.4G    /tmp/multitask-workstreams-124-fix-bug
5.6G    /tmp/multitask-workstreams-125-refactor
````

### Step 2: Identify Which PRs Are Merged

````bash
# Check PR status
gh pr view 123 --json state,mergedAt
gh pr view 124 --json state,mergedAt
gh pr view 125 --json state,mergedAt
````

### Step 3: Preview Cleanup (Dry-Run)

````bash
# See what would be deleted
/multitask --cleanup --dry-run workstreams.json
````

Review the output carefully. Ensure you're comfortable deleting those workstreams.

### Step 4: Execute Cleanup

````bash
# Actually delete merged PRs
/multitask --cleanup workstreams.json
````

### Step 5: Verify Space Reclaimed

````bash
# Check disk space after cleanup
df -h /tmp

# Verify workstreams remaining
ls -la /tmp/multitask-workstreams-*
````

## Prevention Strategies

### Regular Cleanup Routine

Create a habit of cleaning up after each multitask session:

````bash
# After all PRs merged
/multitask --cleanup workstreams.json

# Then verify
df -h /tmp
````

### Monitoring Script

Add to your shell profile for ongoing monitoring:

````bash
# Add to ~/.bashrc or ~/.zshrc
alias multitask-disk='du -sh /tmp/multitask-workstreams-* 2>/dev/null | sort -h'
alias multitask-cleanup='cd ~/.amplihack && /multitask --cleanup'
````

**Usage**:

````bash
# Check disk usage anytime
multitask-disk

# Quick cleanup
multitask-cleanup workstreams.json
````

### Disk Space Alerts

Set up a pre-flight check before starting multitask:

````bash
#!/bin/bash
# File: ~/bin/multitask-preflight

AVAILABLE=$(df /tmp | tail -1 | awk '{print $4}')
THRESHOLD=10485760  # 10GB in KB

if [ "$AVAILABLE" -lt "$THRESHOLD" ]; then
    echo "⚠️  Low disk space: $(($AVAILABLE / 1024 / 1024)) GB available"
    echo "Run cleanup before continuing:"
    echo "  /multitask --cleanup workstreams.json"
    exit 1
fi

echo "✅ Disk space OK: $(($AVAILABLE / 1024 / 1024)) GB available"
````

**Make executable and use**:

````bash
chmod +x ~/bin/multitask-preflight
multitask-preflight && /multitask workstreams.json
````

## Understanding the Cleanup Logic

### What Gets Deleted

**Safe for deletion**:
- Workstreams where PR is **merged**
- Verified via `gh pr view` status check
- Only directories matching pattern `/tmp/multitask-workstreams-{PR}-*`

**Preserved**:
- Open PRs
- Draft PRs
- PRs under review
- Failed clone directories (no PR number)

### How It Works

````python
# Simplified logic
for workstream in workstreams:
    if workstream.pr_merged():
        workstream.delete()
    else:
        workstream.preserve()
````

Full implementation in `.claude/skills/multitask/orchestrator.py`.

## Troubleshooting

### Cleanup Not Working

**Symptom**: `--cleanup` reports 0 deletions but workstreams exist

**Causes**:

1. PRs not actually merged
2. `gh` CLI not authenticated
3. PR numbers don't match directories

**Fix**:

````bash
# Verify gh CLI works
gh auth status

# Check actual PR status
gh pr view 123

# Manual cleanup if needed
rm -rf /tmp/multitask-workstreams-123-*
````

### "Permission Denied" Errors

**Symptom**: Cannot delete workstream directories

**Causes**:
- Processes still running in workstream
- File permissions issues

**Fix**:

````bash
# Check for running processes
lsof +D /tmp/multitask-workstreams-123-*

# Kill processes if found
pkill -f multitask-workstreams-123

# Force delete (may need sudo)
sudo rm -rf /tmp/multitask-workstreams-123-*
````

### Disk Full During Multitask

**Symptom**: Task fails with "No space left on device"

**Immediate action**:

````bash
# Stop multitask
Ctrl+C

# Emergency cleanup (deletes everything!)
rm -rf /tmp/multitask-workstreams-*

# Verify space recovered
df -h /tmp
````

**Prevention**: Run pre-flight check before starting multitask.

## Advanced: Custom Cleanup Scripts

### Delete Older Than N Days

````bash
#!/bin/bash
# Delete workstreams older than 7 days

find /tmp/multitask-workstreams-* -maxdepth 0 -type d -mtime +7 -exec rm -rf {} \;
````

### Delete by Size

````bash
#!/bin/bash
# Delete workstreams larger than 5GB

for dir in /tmp/multitask-workstreams-*; do
    size=$(du -s "$dir" | awk '{print $1}')
    if [ "$size" -gt 5242880 ]; then  # 5GB in KB
        echo "Deleting large workstream: $dir ($(($size / 1024 / 1024)) GB)"
        rm -rf "$dir"
    fi
done
````

### Cleanup by PR State

````bash
#!/bin/bash
# Delete only closed (not merged) PRs

for dir in /tmp/multitask-workstreams-*; do
    pr=$(basename "$dir" | grep -oP '\d+' | head -1)
    state=$(gh pr view "$pr" --json state --jq .state)

    if [ "$state" = "CLOSED" ]; then
        echo "Deleting closed PR workstream: $dir"
        rm -rf "$dir"
    fi
done
````

## Related Documentation

- [Multitask Skill Reference](.claude/skills/multitask/SKILL.md) - Complete skill documentation
- [Multitask Examples](.claude/skills/multitask/examples.md) - Usage examples
- [GitHub CLI Reference](https://cli.github.com/manual/) - gh command documentation

## Summary

**Key takeaways**:

✅ Use `--cleanup` flag for safe automated cleanup
✅ Always preview with `--dry-run` first
✅ Monitor disk usage with startup warnings and final reports
✅ Clean up after each multitask session
✅ Use manual cleanup only when necessary

**Best practice workflow**:

````bash
# 1. Check space before starting
df -h /tmp

# 2. Run multitask
/multitask workstreams.json

# 3. After PRs merged, cleanup
/multitask --cleanup workstreams.json

# 4. Verify space recovered
df -h /tmp
````

---

**Problem solved!** You now know how to prevent and resolve disk space issues with multitask.
