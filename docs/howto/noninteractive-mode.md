# How to Run amplihack in Non-Interactive / CI Mode

**Added:** March 2026 (PR #3066, #3067)

This guide explains how to run amplihack in environments that cannot handle
interactive prompts: CI pipelines, Docker containers, sandboxed test
environments, and automated scripts.

---

## When to Use This

Use non-interactive mode when amplihack is running in:

- GitHub Actions, GitLab CI, Azure Pipelines, or any CI system
- Docker containers with no TTY attached
- Automated test harnesses
- Sandboxed evaluation environments (e.g., amplihack's own eval system)
- Any context where `stdin` is not a real terminal

Without this mode, amplihack may hang indefinitely waiting for user input during
startup, blarify dependency installation, or prerequisite checks.

---

## How to Enable

Set the environment variable `AMPLIHACK_NONINTERACTIVE=1` before launching:

```bash
AMPLIHACK_NONINTERACTIVE=1 amplihack launch
```

Or export it for the duration of a script:

```bash
export AMPLIHACK_NONINTERACTIVE=1
amplihack launch
# ... other commands ...
```

In a CI YAML (GitHub Actions example):

```yaml
- name: Run amplihack
  env:
    AMPLIHACK_NONINTERACTIVE: "1"
  run: amplihack launch
```

---

## What Changes in Non-Interactive Mode

| Behaviour | Normal mode | Non-interactive mode |
|-----------|-------------|----------------------|
| Blarify dependency auto-installer | Runs on startup (may prompt) | Skipped entirely |
| Interactive prompts (e.g., "Install missing tool?") | Shown, waits for input | Skipped; defaults used |
| Prerequisite auto-install | Offered interactively | Disabled |
| Proxy connection retries | Open-ended retry loop | Bounded (max 3 retries, 10 s timeout) |
| Startup hang on missing TTY | Possible | Never |

---

## Verifying Non-Interactive Mode Works

With a restricted `PATH` (no network tools, no interactive tools), the launch
should exit within a few seconds:

```bash
# Simulate a restricted CI environment
PATH=/usr/bin:/bin AMPLIHACK_NONINTERACTIVE=1 amplihack launch
# Should exit in <5s with a clear error or success message — never hang
```

---

## Related Environment Variables

| Variable | Purpose |
|----------|---------|
| `AMPLIHACK_NONINTERACTIVE=1` | Disable all interactive prompts and auto-install |
| `AMPLIHACK_AUTO_INSTALL=1` | Enable automatic tool installation (interactive environments only) |
| `AMPLIHACK_USE_TRACE=0` | Disable claude-trace, use plain `claude` |

---

## Troubleshooting

**Problem:** amplihack still hangs in CI after setting `AMPLIHACK_NONINTERACTIVE=1`

Check whether the hang is happening before amplihack itself starts (e.g., in a
shell profile or pre-command hook). Run with `--verbose` to see which step is
blocking:

```bash
AMPLIHACK_NONINTERACTIVE=1 amplihack --verbose launch
```

**Problem:** blarify import errors in non-interactive mode

Blarify dependencies are skipped in non-interactive mode. If your use case
requires blarify (code graph features), install the dependencies manually in
your CI environment's Docker image:

```bash
pip install blarify networkx neo4j
```

---

## See Also

- [Prerequisites](../PREREQUISITES.md) — required tools including tmux
- [Troubleshooting hooks](troubleshoot-hooks.md) — hook configuration in CI
