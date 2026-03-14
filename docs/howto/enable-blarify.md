# How to Enable Blarify Code Indexing

Blarify is an optional code-graph indexer that imports your codebase into a Kuzu embedded database, enabling memory-aware queries over code structure. It is **disabled by default** and never activates automatically in non-interactive environments such as CI pipelines.

## Contents

- [Prerequisites](#prerequisites)
- [Enable Blarify](#enable-blarify)
- [What Happens at Launch](#what-happens-at-launch)
- [Consent and the "Don't Ask Again" Cache](#consent-and-the-dont-ask-again-cache)
- [Non-Interactive Mode](#non-interactive-mode)
- [Staleness Detection](#staleness-detection)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

1. Install the `blarify` Python package:
   ```bash
   pip install blarify
   ```
2. Optionally install `scip-python` for a ~330× indexing speed increase:
   ```bash
   npm install -g @sourcegraph/scip-python
   ```

---

## Enable Blarify

Set the `AMPLIHACK_ENABLE_BLARIFY` environment variable to `1` when launching:

```bash
AMPLIHACK_ENABLE_BLARIFY=1 amplihack launch
```

Without this variable, the blarify prompt is never shown and indexing never runs, regardless of any other configuration.

To always enable blarify in your shell, add the export to your profile:

```bash
# In ~/.bashrc or ~/.zshrc
export AMPLIHACK_ENABLE_BLARIFY=1
```

---

## What Happens at Launch

When `AMPLIHACK_ENABLE_BLARIFY=1` is set and the session is interactive, amplihack:

1. **Checks staleness** — queries the Kuzu database to determine whether the index is current.
2. **Estimates time** — measures the codebase and estimates how long indexing will take (e.g. `~30 seconds`).
3. **Prompts the user** — asks whether to index now, offering a "don't ask again" option.
4. **Runs the orchestrator** — if the user consents, runs `Orchestrator` and `PrerequisiteChecker` to import the codebase.

If the index is already fresh, step 3 is skipped and no prompt is shown.

---

## Consent and the "Don't Ask Again" Cache

When you answer the blarify prompt, you can choose to cache your decision for this project. amplihack stores the consent in a per-project cache file:

```
~/.amplihack/blarify_consent/<project-hash>.json
```

On subsequent launches in the same project, the prompt is skipped and the log records:

```
[blarify] Consent cached — don't ask again for this project.
```

To reset the cache and be prompted again, delete the cache file:

```bash
rm ~/.amplihack/blarify_consent/<project-hash>.json
```

Or delete all cached consents:

```bash
rm -rf ~/.amplihack/blarify_consent/
```

---

## Non-Interactive Mode

In non-interactive environments — shells without a TTY, CI runners, scripts using pipes — blarify is **always skipped**, even when `AMPLIHACK_ENABLE_BLARIFY=1` is set. No prompt is shown and no indexing runs.

amplihack detects non-interactive mode via `_is_noninteractive()`, which checks for an attached TTY. This is intentional: indexing during automated runs would block pipelines and fail silently on machines without blarify installed.

```bash
# This will NOT run blarify — stdin is a pipe, not a terminal
echo "" | AMPLIHACK_ENABLE_BLARIFY=1 amplihack launch

# This WILL run blarify — stdin is an interactive terminal
AMPLIHACK_ENABLE_BLARIFY=1 amplihack launch
```

---

## Staleness Detection

Before prompting, amplihack calls `check_index_status()` to determine whether the existing Kuzu index matches the current codebase state. The returned status has an `is_stale` flag:

| `is_stale` | Behavior |
|-----------|---------|
| `True` | Prompt is shown; user can choose to re-index. |
| `False` | Prompt is skipped; the fresh index is used as-is. |

Staleness is based on file modification times and content hashes stored in the index. A newly created project always reports `is_stale = True`.

---

## Troubleshooting

### Blarify prompt never appears

Check that all three conditions are met:

```bash
# 1. Variable must be set to '1' (not 'true', not 'yes')
echo $AMPLIHACK_ENABLE_BLARIFY   # Should print: 1

# 2. Session must be interactive
[ -t 0 ] && echo "interactive" || echo "non-interactive"

# 3. blarify package must be importable
python3 -c "import blarify; print('ok')"
```

### Indexing fails with "PrerequisiteChecker error"

```bash
# Run the prerequisite check standalone to see the failure reason
python3 -c "
from amplihack.memory.kuzu.indexing.prerequisite_checker import PrerequisiteChecker
checker = PrerequisiteChecker()
result = checker.check()
print(result)
"
```

### Index is always stale

Delete the index and re-run to force a clean build:

```bash
rm -rf ~/.amplihack/.claude/runtime/kuzu/
AMPLIHACK_ENABLE_BLARIFY=1 amplihack launch
```

---

## See Also

- [Blarify Integration Overview](../blarify_integration.md) — architecture, node types, schema
- [Blarify Quick Start](../blarify_quickstart.md) — first-time setup with Neo4j
- [CLI Reference](../reference/cli.md) — `AMPLIHACK_ENABLE_BLARIFY` environment variable
