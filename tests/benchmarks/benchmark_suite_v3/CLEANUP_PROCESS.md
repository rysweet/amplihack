# Benchmark Cleanup Process

**CRITICAL**: After running benchmarks, ALWAYS clean up the test artifacts to avoid polluting the repository with temporary PRs and issues.

## What Gets Created During Benchmarks

Each benchmark task creates:

- **GitHub Issue** - Feature request for the task
- **Git Branch** - Feature branch for implementation
- **Pull Request** - PR with the implemented code
- **Worktree** - Isolated git worktree for execution
- **Trace Logs** - API traces in `.claude-trace/` (gitignored)
- **Result Files** - Metrics in `~/.amplihack/.claude/runtime/benchmarks/` (gitignored)

## Cleanup Checklist

### 1. Close Pull Requests

```bash
# Find benchmark PRs (created during benchmark window)
gh pr list --state open --limit 30

# Close each benchmark PR with reference to report
gh pr close <PR_NUMBER> --comment "Closing benchmark PR - created during benchmark suite v3. See #<REPORT_ISSUE> for full report."
```

### 2. Close GitHub Issues

```bash
# Find benchmark issues
gh issue list --state open --limit 30 | grep -E "greeting|ConfigManager|plugin|API client"

# Close each benchmark issue
gh issue close <ISSUE_NUMBER> --comment "Closing benchmark issue - created during benchmark suite v3. See #<REPORT_ISSUE> for full report."
```

### 3. Remove Git Worktrees

```bash
# List active worktrees
git worktree list

# Remove benchmark worktrees
git worktree remove worktrees/bench-opus-task1 --force
git worktree remove worktrees/bench-opus-task2 --force
git worktree remove worktrees/bench-opus-task3 --force
git worktree remove worktrees/bench-opus-task4 --force
git worktree remove worktrees/bench-sonnet-task1 --force
git worktree remove worktrees/bench-sonnet-task2 --force
git worktree remove worktrees/bench-sonnet-task3 --force
git worktree remove worktrees/bench-sonnet-task4 --force
```

### 4. Delete Git Branches (Optional)

```bash
# List benchmark branches
git branch --list | grep "benchmark/"

# Delete local benchmark branches
git branch -D benchmark/opus/task1
git branch -D benchmark/opus/task2
# ... etc for all 8 branches

# Delete remote benchmark branches (if pushed)
git push origin --delete benchmark/opus/task1
# ... etc
```

### 5. Archive Artifacts

```bash
# Create archive of trace logs and results
cd /tmp
mkdir -p benchmark_artifacts/results benchmark_artifacts/traces

# Copy results
cp -r /path/to/repo/.claude/runtime/benchmarks/suite_v3/* benchmark_artifacts/results/

# Copy trace logs
for dir in /path/to/repo/worktrees/bench-*-task*; do
    task=$(basename "$dir")
    cp "$dir"/.claude-trace/*.jsonl "benchmark_artifacts/traces/${task}.jsonl" 2>/dev/null || true
done

# Create archive
tar -czf benchmark_suite_v3_artifacts.tar.gz benchmark_artifacts

# Create GitHub release
gh release create benchmark-suite-v3-artifacts \
    --title "Benchmark Suite V3 - Trace Logs and Results" \
    --notes "Complete artifacts from benchmark. See issue #<REPORT_ISSUE>" \
    benchmark_suite_v3_artifacts.tar.gz
```

## Automated Cleanup Script

```bash
#!/bin/bash
# cleanup_benchmarks.sh - Automated benchmark cleanup

REPORT_ISSUE="$1"  # Pass report issue number as argument

if [ -z "$REPORT_ISSUE" ]; then
    echo "Usage: $0 <REPORT_ISSUE_NUMBER>"
    exit 1
fi

echo "Closing benchmark PRs and issues..."

# Close PRs
for pr in $(gh pr list --state open --json number --jq '.[].number' | grep -E "169[3-7]"); do
    gh pr close "$pr" --comment "Closing benchmark PR - created during benchmark suite v3. See #$REPORT_ISSUE for full report."
done

# Close issues
for issue in $(gh issue list --state open --json number --jq '.[].number' | grep -E "168[3-9]|169[0-7]"); do
    gh issue close "$issue" --comment "Closing benchmark issue - created during benchmark suite v3. See #$REPORT_ISSUE for full report."
done

echo "Removing worktrees..."
for wt in worktrees/bench-*-task*; do
    [ -d "$wt" ] && git worktree remove "$wt" --force
done

echo "Cleanup complete!"
echo "Remember to:"
echo "  1. Archive artifacts to GitHub release"
echo "  2. Update report issue with release link"
```

## Best Practices

### DO

✅ **Close artifacts immediately** after generating the report
✅ **Reference the report issue** in all cleanup comments
✅ **Archive trace logs** to a GitHub release for reproducibility
✅ **Document the cleanup** in the report issue comments
✅ **Verify cleanup** by checking `gh pr list` and `gh issue list`

### DON'T

❌ **Don't merge benchmark PRs** - they contain test code only
❌ **Don't delete artifacts before archiving** - they're needed for reproducibility
❌ **Don't leave worktrees** - they consume disk space
❌ **Don't commit trace logs** - they're huge and gitignored
❌ **Don't push benchmark branches** to origin (unless needed for review)

## Verification

After cleanup, verify:

```bash
# Should show no benchmark PRs
gh pr list --state open | grep -E "greeting|ConfigManager|plugin|API"

# Should show no benchmark issues (except report)
gh issue list --state open | grep -E "greeting|ConfigManager|plugin|API"

# Should show no benchmark worktrees
git worktree list | grep bench-

# Report issue should have artifacts comment
gh issue view <REPORT_ISSUE>
```

## Troubleshooting

### "Worktree removal failed"

```bash
# Force removal
rm -rf worktrees/bench-*-task*
git worktree prune
```

### "Branch still exists"

```bash
# Delete forcefully
git branch -D benchmark/opus/task1
```

### "Can't find benchmark PRs/issues"

```bash
# Search by date
gh pr list --state all --search "created:>2025-11-26" --json number,title,createdAt

gh issue list --state all --search "created:>2025-11-26" --json number,title,createdAt
```

---

**Remember**: Cleanup is a MANDATORY part of the benchmark process. Don't skip it!
