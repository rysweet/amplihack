# Background Indexing Prompt

Automatic code indexing with Blarify when starting Claude Code in unindexed projects.

## What It Does

When you start Claude Code in a project that hasn't been indexed, amplihack displays a prompt offering to index your codebase in the background. This indexes code while you work, making intelligent code context available to agents without blocking your workflow.

## The Startup Prompt

When you launch Claude Code in a project without an up-to-date Blarify index:

```
═══════════════════════════════════════════════════════════
📊 Code Indexing Available

This project hasn't been indexed yet. Would you like to
start background indexing now?

Estimated time: 2 minutes 30 seconds
  • Python files: ~45 seconds (150 files)
  • JavaScript files: ~1 minute 15 seconds (280 files)
  • TypeScript files: ~30 seconds (95 files)

Background indexing runs at low priority and won't slow
down your work. You can check progress anytime with:

  /blarify-status

[ Yes ]  [ No ]  [ Don't ask again for this project ]
═══════════════════════════════════════════════════════════
```

## Time Estimation

The prompt shows estimated indexing time based on:

- **File count** by language in your project
- **Average indexing speed** (300-600 files per minute with SCIP)
- **Historical performance** from previous indexing runs

### Example Estimates

| Project Size | Files | Languages      | Estimated Time |
| ------------ | ----- | -------------- | -------------- |
| Small        | 50    | Python         | 15 seconds     |
| Medium       | 500   | Python, JS     | 3 minutes      |
| Large        | 2000  | Multi-language | 10 minutes     |
| Very Large   | 10000 | Multi-language | 45 minutes     |

**Note**: Actual time varies based on code complexity and system resources.

## Response Options

### Yes - Start Indexing Now

Starts background indexing immediately:

```
✓ Background indexing started
  Process ID: 12345
  Check progress: /blarify-status
```

Indexing runs at low priority (nice 10) to minimize impact on your work.

### No - Skip This Time

Skips indexing for this session. You'll see the prompt again next time you start Claude Code in this project.

### Don't Ask Again for This Project

Creates a local preference file (`.amplihack/no-index-prompt`) that suppresses the prompt for this project. Indexing remains available via manual commands.

## Checking Progress

Use `/blarify-status` to check background indexing progress:

```
/blarify-status
```

Output while indexing:

```
═══════════════════════════════════════════════════════════
📊 Blarify Indexing Status

Status: RUNNING
Started: 2 minutes ago
Progress: 65% complete

Indexed so far:
  • Files: 325 / 500
  • Functions: 1,240
  • Classes: 180

Current language: JavaScript (280 files remaining)
Estimated completion: 1 minute

Background process: PID 12345 (nice 10)
═══════════════════════════════════════════════════════════
```

Output when complete:

```
═══════════════════════════════════════════════════════════
📊 Blarify Indexing Status

Status: COMPLETE ✓
Completed: 5 minutes ago
Total time: 3 minutes 15 seconds

Indexed:
  • Files: 500
  • Functions: 2,850
  • Classes: 340
  • Relationships: 4,120

Index location: .amplihack/blarify.db
Index size: 2.4 MB

Code context now available to all agents!
═══════════════════════════════════════════════════════════
```

## What Happens If Indexing Is Already Running

If you start Claude Code while background indexing is still running from a previous session:

```
═══════════════════════════════════════════════════════════
📊 Background Indexing In Progress

An indexing process is already running for this project.

Process ID: 12345
Started: 15 minutes ago
Progress: 82% complete

Use /blarify-status to check progress.
═══════════════════════════════════════════════════════════
```

amplihack detects the existing process and doesn't start a duplicate.

## Manual Indexing Commands

Even if you suppress the prompt, you can manually trigger indexing:

```bash
# Index entire project
/blarify-index

# Index specific directory
/blarify-index --path src/amplihack

# Force re-index (ignore existing index)
/blarify-index --force

# Incremental update (only changed files)
/blarify-index --incremental
```

## Project-Local Preference

The "don't ask again" preference is stored in:

```
.amplihack/no-index-prompt
```

This file contains:

```json
{
  "suppress_prompt": true,
  "suppressed_at": "2025-01-15T10:30:00Z",
  "reason": "user_choice"
}
```

### Re-enabling the Prompt

Delete the file to restore the prompt:

```bash
rm .amplihack/no-index-prompt
```

Or use the command:

```bash
/blarify-config --enable-prompt
```

## When Indexing Triggers

The background indexing prompt appears when:

1. **No index exists**: `.amplihack/blarify.db` is missing
2. **Index is stale**: Files modified since last index (threshold: 24 hours)
3. **Significant changes**: More than 10% of files changed

The prompt does NOT appear when:

- Index is up-to-date (modified within 24 hours, < 10% files changed)
- `.amplihack/no-index-prompt` exists
- `AMPLIHACK_NO_INDEX_PROMPT=1` environment variable is set
- Non-interactive session (CI/CD, scripts)

## Troubleshooting

### Prompt Doesn't Appear

**Check if prompt is suppressed:**

```bash
ls .amplihack/no-index-prompt
```

If file exists, delete it or use:

```bash
/blarify-config --enable-prompt
```

**Check environment variable:**

```bash
echo $AMPLIHACK_NO_INDEX_PROMPT
```

If set to `1`, unset it:

```bash
unset AMPLIHACK_NO_INDEX_PROMPT
```

**Check if index is up-to-date:**

```bash
/blarify-status
```

If index was recently updated, the prompt won't appear.

### Indexing Starts But Immediately Fails

**Check disk space:**

```bash
df -h .amplihack/
```

Indexing requires temporary space (typically 2x final database size).

**Check file permissions:**

```bash
ls -la .amplihack/
```

The directory must be writable.

**Check for SCIP installation:**

```bash
which scip-python
```

If not installed, indexing falls back to slower parsing (expect 10-50x longer).

Install SCIP for speed:

```bash
npm install -g @sourcegraph/scip-python
```

### Background Process Hangs

**Check process status:**

```bash
/blarify-status
```

If stuck (no progress for 5+ minutes):

```bash
# Kill the process
/blarify-cancel

# Restart indexing
/blarify-index
```

**Check system resources:**

```bash
top -p $(cat .amplihack/blarify.pid)
```

If process is consuming excessive CPU/memory, it may indicate:

- Very large or complex files
- Parsing errors in specific files
- System resource constraints

### Time Estimate Is Way Off

Time estimates improve over time as amplihack learns your project's characteristics. First-run estimates may be inaccurate.

**Manual calibration:**

After indexing completes, the system stores actual timing:

```
.amplihack/index-timing.json
```

Future estimates use this data for better accuracy.

### Can't Suppress Prompt

If "Don't ask again" doesn't work:

**Check write permissions:**

```bash
touch .amplihack/no-index-prompt
```

If this fails, the directory isn't writable.

**Alternative: Use environment variable:**

```bash
export AMPLIHACK_NO_INDEX_PROMPT=1
```

Add to your shell profile (`.bashrc`, `.zshrc`) to make permanent.

## Integration with CI/CD

In CI/CD pipelines, automatically suppress the prompt:

```bash
# In your CI script
export AMPLIHACK_NO_INDEX_PROMPT=1

# Or pre-create the file
mkdir -p .amplihack
echo '{"suppress_prompt": true, "reason": "ci"}' > .amplihack/no-index-prompt
```

For pre-indexed CI environments, run indexing during container build:

```dockerfile
# Dockerfile
RUN amplihack blarify-index --force
```

## See Also

- [Multi-Language Validation](./multi-language-validation.md) - Verify language support
- [Blarify Quickstart](../blarify_quickstart.md) - Complete setup guide
- [Blarify Architecture](../blarify_architecture.md) - How indexing works
