# Configure the Issue Classifier Workflow

How to maintain, extend, and troubleshoot the `issue-classifier` GitHub Actions workflow.

## Contents

- [Overview](#overview)
- [Permissions](#permissions)
- [Timeout Budget](#timeout-budget)
- [Modifying the Workflow](#modifying-the-workflow)
- [Recompiling the Lock File](#recompiling-the-lock-file)
- [Extending the Classifier](#extending-the-classifier)
- [Secret Redaction](#secret-redaction)
- [Error Handling and Retries](#error-handling-and-retries)
- [Validating Your Changes](#validating-your-changes)
- [Troubleshooting](#troubleshooting)

---

## Overview

The issue-classifier workflow automatically labels new issues as `bug`, `feature`, `enhancement`, or `documentation` using an AI agent step. It runs in strict mode — the agent **must** emit exactly one label; a no-output result is treated as a workflow failure.

Workflow source: [`../../.github/workflows/issue-classifier.md`](../../.github/workflows/issue-classifier.md)
Compiled lock file: `.github/workflows/issue-classifier.lock.yml`

The `.md` source is the authoritative definition; the `.lock.yml` is generated from it and is what GitHub Actions actually executes. Always edit the `.md` source and recompile — never edit the lock file directly.

---

## Permissions

The `agent` job requires these minimum permissions:

```yaml
permissions:
  contents: read
  issues: read
  pull-requests: read
```

| Permission | Reason |
|------------|--------|
| `contents: read` | Read repository files for context |
| `issues: read` | Fetch issue metadata and existing labels |
| `pull-requests: read` | Detect cross-references from issues to open PRs |

The top-level `permissions: {}` block denies all other permissions by default. Do **not** broaden the job permissions unless you add a step that genuinely requires it.

> **Security note:** The `GITHUB_TOKEN` fallback has broader scope than `GH_AW_GITHUB_TOKEN`. If `GH_AW_GITHUB_TOKEN` is unset, the workflow fails immediately rather than silently falling back to broader credentials.

---

## Timeout Budget

The `agent` job has a `timeout-minutes: 10` budget. This was raised from 5 minutes to accommodate:

- Rate-limit retry delays (60 s per retry, up to 3 retries)
- Network latency for large issue bodies
- Claude API response time under load

Do not lower the timeout below 10 minutes. The regression test `tests/unit/workflows/test_issue_classifier_workflow.py` enforces this floor.

---

## Modifying the Workflow

Edit `.github/workflows/issue-classifier.md`. The frontmatter controls runtime behavior:

```yaml
on:
  issues:
    types: [opened]
permissions:
  contents: read
  issues: read
  pull-requests: read
engine: claude
timeout-minutes: 10
strict: true
```

| Field | Description |
|-------|-------------|
| `engine` | AI engine to use (`claude` is the only supported value) |
| `timeout-minutes` | Per-job cap. Must be ≥ 10. |
| `strict` | When `true`, no output from the agent is a failure; the job does not silently succeed |

After editing, [recompile the lock file](#recompiling-the-lock-file) before committing.

### Safe output limits

The workflow enforces a `safe-outputs` constraint that restricts what the agent can write:

```yaml
safe-outputs:
  max-labels: 1
  allowed-labels:
    - bug
    - feature
    - enhancement
    - documentation
```

To add a new label category, add it to both `allowed-labels` here and the corresponding label in your GitHub repository. Then recompile.

---

## Recompiling the Lock File

After any change to `issue-classifier.md`, regenerate the lock file:

```bash
gh aw compile .github/workflows/issue-classifier.md \
  --output .github/workflows/issue-classifier.lock.yml
```

Requires `gh-aw` ≥ v0.56.2. Verify the installed version:

```bash
gh aw --version
```

Commit both files together. The regression test `test_lockfile_sync` fails if the lock file's `timeout-minutes` or `permissions` diverge from the source.

---

## Extending the Classifier

### Adding a new label

1. Create the label in the GitHub repository settings (or via `gh label create`).
2. Add it to `allowed-labels` in `issue-classifier.md`.
3. Update the agent prompt section in the `.md` source to describe when to apply the label.
4. Recompile the lock file.
5. Run `pytest tests/unit/workflows/test_issue_classifier_workflow.py` to confirm the regression tests still pass.

### Changing the trigger

The workflow currently runs on `issues: [opened]`. To also run on reopened issues:

```yaml
on:
  issues:
    types: [opened, reopened]
```

---

## Secret Redaction

The workflow includes a secret-redaction step that scrubs sensitive tokens from CI logs before any log retention:

```yaml
- name: Redact secrets from logs
  run: |
    sed -i 's/${{ secrets.ANTHROPIC_API_KEY }}/[REDACTED]/g' "$GITHUB_STEP_SUMMARY" || true
    sed -i 's/${{ secrets.GH_AW_GITHUB_TOKEN }}/[REDACTED]/g' "$GITHUB_STEP_SUMMARY" || true
```

This step runs unconditionally (even if prior steps fail). Do not remove it.

---

## Error Handling and Retries

The agent step uses a retry wrapper with:

- **Rate-limit retries:** 3 attempts, 60 s delay between attempts
- **Network failure backoff:** exponential backoff starting at 5 s, max 60 s

If all retries are exhausted, the job fails with exit code 1 and the last error message from the API response in the step output.

Common rate-limit indicators in the step log:

```
Error: 429 Too Many Requests — retrying in 60s (attempt 2/3)
```

If you see persistent rate-limit failures, consider adjusting your repository's issue volume or requesting a higher API rate tier.

---

## Validating Your Changes

Run the workflow regression tests locally before pushing:

```bash
pytest tests/unit/workflows/test_issue_classifier_workflow.py -v
```

Tests cover:

| Test | What it checks |
|------|---------------|
| `test_timeout_budget` | `timeout-minutes` in source ≥ 10 |
| `test_permissions_presence` | All three required permissions declared in source |
| `test_lockfile_sync` | Lock file `timeout-minutes` matches source |
| `test_lockfile_permissions` | Lock file grants same permissions as source |

All four tests must pass before merging any change to the workflow files.

---

## Troubleshooting

### Workflow fails with "no output from agent"

The agent returned no label. This is treated as a failure in strict mode. Common causes:

- Issue body is too short for the model to classify confidently
- The model exceeded the timeout before responding
- `GH_AW_GITHUB_TOKEN` is not set in repository secrets

Check the step log for `strict: true noop` or timeout messages.

### Lock file out of sync

```
AssertionError: lockfile timeout-minutes (5) != source timeout-minutes (10)
```

Recompile the lock file with `gh aw compile` and commit both files.

### `issues: read` permission denied

```
Error: Resource not accessible by integration
```

The `issues: read` permission is missing from the job's `permissions` block. Verify both the `.md` source and the compiled `.lock.yml` include `issues: read`.

### Agent applies wrong label

Check the prompt section in `issue-classifier.md`. The model's classification logic depends entirely on the instructions in that section. Update the prompt, recompile, and re-run on a test issue.

---

**See also:**

- [Issue Classifier Workflow source](../../.github/workflows/issue-classifier.md)
- [Rust Runner Execution Reference](../reference/rust-runner-execution.md)
- [CI Diagnostic Workflow](../claude/agents/amplihack/specialized/ci-diagnostic-workflow.md)
