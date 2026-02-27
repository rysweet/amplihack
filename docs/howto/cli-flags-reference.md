# amplihack CLI Flags Reference

Complete reference for command-line flags across all amplihack commands following the Diátaxis framework (How-to Guide).

## Global Flags

These flags work across all amplihack commands:

### `--subprocess-safe`

**Added in:** v0.9.1 (PR #2571)

**Purpose:** Skip staging and environment updates when running as a subprocess delegate.

**Use Case:** Prevents concurrent write races on `~/.amplihack/.claude/` when multiple workstreams run in parallel.

**Example:**
```bash
# Multitask classic mode uses this automatically
amplihack claude --subprocess-safe -- -p "@TASK.md Execute autonomously"
```

**What It Skips:**
- Nesting detection checks
- `_ensure_amplihack_staged()` operations
- Power-steering synchronization
- Settings synchronization

**When To Use:**
- Running workstreams via `/multitask` in classic mode
- Manual parallel execution of multiple amplihack sessions
- Subprocess invocations where parent has already staged files

**When NOT To Use:**
- Normal interactive sessions
- First-run installations
- When you need framework file updates

## Evaluation Flags

### `--segment-size N`

**Added in:** v0.9.1 (PR #2573)

**Purpose:** Split long-horizon memory learning into subprocess segments to prevent OOM.

**Use Case:** Running evaluations with 5000+ turns where native memory (Kuzu C++, aiohttp) accumulates ~3MB/turn.

**Example:**
```bash
# 5000-turn eval in 100-turn segments (50 subprocesses)
python -m amplihack.eval.long_horizon_memory --turns 5000 --segment-size 100
```

**How It Works:**
1. Generate full dialogue once, save to JSON
2. For each segment: spawn subprocess with `--turns-slice START:END`
3. Each subprocess learns its slice, closes agent, exits (memory freed)
4. DB persists across segments on disk (Kuzu)
5. After all segments: run questions with `--skip-learning --load-db`

**Related Flags:**
- `--turns-slice START:END`: Internal flag for subprocess workers
- `--dialogue-json PATH`: Path to pre-generated dialogue JSON
- `--skip-questions`: Skip question phase (learning only)
- `--skip-learning`: Skip learning phase (questions only)

**When To Use:**
- Evaluations > 5000 turns
- Memory-constrained environments (< 4GB RAM)
- Large-scale stress testing

**When NOT To Use:**
- Standard 1000-turn evaluations (runs in-process by default)
- When debugging learning phase (subprocess isolation complicates debugging)

## Model Selection Flags

### `--model MODEL`

Select specific model to use:

```bash
amplihack amplifier --model claude-sonnet-4-20250514
amplihack amplifier --model gpt-4o --provider openai
```

### `--provider PROVIDER`

Select provider: `anthropic`, `openai`, `azure`

```bash
amplihack amplifier --provider openai
```

## Session Management Flags

### `--resume SESSION_ID`

Resume an existing session:

```bash
amplihack amplifier --resume abc123def456
```

### `--print`

Single response mode (no tool use, no conversation):

```bash
amplihack amplifier --print -- -p "What does this function do?"
```

## Auto Mode Flags

### `--auto`

Run in autonomous mode with task loop:

```bash
amplihack amplifier --auto
```

### `--max-turns N`

Maximum turns for auto mode (default: 10):

```bash
amplihack amplifier --auto --max-turns 20
```

## Installation Flags

### `--upgrade`

Upgrade existing installation:

```bash
amplihack plugin install --upgrade
```

### `--force`

Force reinstall even if up-to-date:

```bash
amplihack plugin install --force
```

### `--path PATH`

Install to custom path:

```bash
amplihack plugin install --path /custom/path
```

### `--from-git URL`

Install from git repository:

```bash
amplihack plugin install --from-git https://github.com/user/repo
```

### `--branch BRANCH`

Git branch to install from:

```bash
amplihack plugin install --from-git https://github.com/user/repo --branch develop
```

## Common Flags

### `--no-reflection`

Disable post-session reflection analysis:

```bash
amplihack amplifier --no-reflection
```

### `--verify`

Verify after installation (default: true):

```bash
amplihack plugin install --verify
```

## Flag Combinations

### Parallel Workstreams (Classic Mode)

```bash
# Each workstream automatically gets --subprocess-safe
/multitask --mode classic
- #123: Implement auth
- #124: Add logging
```

### Large-Scale Evaluation

```bash
# Combine subprocess segmentation with custom questions
python -m amplihack.eval.long_horizon_memory \
  --turns 5000 \
  --questions 200 \
  --segment-size 100 \
  --sdk claude
```

### Development Installation

```bash
# Install from development branch with verification
amplihack plugin install \
  --from-git https://github.com/rysweet/amplihack \
  --branch develop \
  --verify
```

## Troubleshooting

### `--subprocess-safe` Issues

**Problem:** "Framework files not found" when using `--subprocess-safe`

**Solution:** Ensure parent process has already staged files. Remove flag for first-run or standalone execution.

**Problem:** Concurrent write errors on `~/.amplihack/.claude/`

**Solution:** Add `--subprocess-safe` to all subprocess invocations. Used automatically in `/multitask` classic mode.

### `--segment-size` Issues

**Problem:** Out of memory even with segmentation

**Solution:** Reduce segment size further (try 50 or 25 turns per segment).

**Problem:** Segments failing midway

**Solution:** Check logs in `/tmp/amplihack-segments/`. Ensure DB path is writable.

## See Also

- [Plugin CLI Reference](../plugin/CLI_REFERENCE.md) - Plugin-specific commands
- [Amplifier Command Reference](../reference/amplifier-command.md) - Amplifier-specific options
- [Recipe CLI Commands](recipe-cli-commands.md) - Recipe Runner CLI
- [Multitask Skill](../../.claude/skills/multitask/SKILL.md) - Parallel execution patterns
- [Eval System Architecture](../EVAL_SYSTEM_ARCHITECTURE.md) - Evaluation internals
