# Workflow Issue Extraction (Step 03b)

> [Home](../index.md) > Reference > Workflow Issue Extraction

Reference for the three-tier issue-number extraction logic in
`default-workflow` step `03b`.  This step resolves a GitHub issue number from
the workflow context so that downstream steps can link the working branch,
commit, and pull request to the correct issue.

## Contents

- [Overview](#overview)
- [Three-Tier Extraction](#three-tier-extraction)
  - [Tier 1 — Direct issue URL](#tier-1--direct-issue-url)
  - [Tier 2 — Pull request URL](#tier-2--pull-request-url)
  - [Tier 3 — Bare #N reference](#tier-3--bare-n-reference)
- [Output Contract](#output-contract)
- [Shell Security Constraints](#shell-security-constraints)
- [Configuration](#configuration)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)
- [Related](#related)

---

## Overview

Step `03b` accepts a free-form `task_description` string (e.g. a copied GitHub
issue URL, a PR URL, or a plain-text description containing `#123`) and
produces a canonical `issue_number` integer that the rest of the workflow uses.

```
task_description  ──►  03b extraction  ──►  issue_number (int | null)
                                             branch_prefix
                                             issue_title (str | null)
```

If no issue number can be resolved, `issue_number` is `null` and the workflow
continues with an anonymous branch name.

---

## Three-Tier Extraction

The tiers are evaluated in order; the first match wins.

### Tier 1 — Direct issue URL

**Pattern**: `https://github.com/<owner>/<repo>/issues/<N>`

When `task_description` contains a URL whose path component is
`/issues/<digits>`, the issue number is extracted directly from the URL without
any network call.

```
Input:  "Fix the crash described in https://github.com/rysweet/amplihack/issues/3960"
Match:  issues/3960
Output: issue_number=3960
```

This tier is purely regex-based and never calls `gh`.

---

### Tier 2 — Pull request URL

**Pattern**: `https://github.com/<owner>/<repo>/pull/<N>`

When `task_description` contains a PR URL, step `03b` calls `gh pr view` to
retrieve the list of issues that the PR closes:

```bash
gh pr view <N> \
    --repo <owner>/<repo> \
    --json closingIssuesReferences \
    --jq '.closingIssuesReferences[0].number'
```

The first closing issue reference is used.  If the PR closes no issues,
extraction falls through to Tier 3.

```
Input:  "Continue work on https://github.com/rysweet/amplihack/pull/4143"
gh call: closingIssuesReferences → [3960, 3983]
Output: issue_number=3960   (first reference)
```

**Timeout**: 60 seconds.  If `gh` does not respond within the timeout, Tier 2
is skipped and extraction falls through to Tier 3.

---

### Tier 3 — Bare `#N` reference

**Pattern**: `#<digits>` anywhere in `task_description`

When neither a direct issue URL nor a PR URL is found, step `03b` scans
`task_description` for bare `#N` patterns.  Each candidate is verified with:

```bash
gh issue view <N> --repo <owner>/<repo> --json number,title --jq '.number'
```

The first candidate that `gh issue view` confirms as an open issue is used.
Candidates that return a non-zero exit code (e.g. closed, non-existent, or
wrong repo) are skipped.

```
Input:  "Resume work on #3983 and #3960"
gh verify 3983 → 200 OK  →  issue_number=3983
```

**Timeout**: 60 seconds per candidate.

If no candidate passes verification, `issue_number` is `null`.

---

## Output Contract

After step `03b` completes, the workflow context contains:

| Field | Type | Description |
|-------|------|-------------|
| `issue_number` | `int \| null` | Resolved GitHub issue number, or `null` if unresolvable |
| `issue_title` | `str \| null` | Issue title fetched from GitHub, or `null` |
| `branch_prefix` | `str` | Branch prefix inferred from context (`fix`, `feat`, `docs`, …) |
| `extraction_tier` | `1 \| 2 \| 3 \| null` | Which tier produced the result (useful for debugging) |

### Example output (Tier 1)

```json
{
  "issue_number": 3960,
  "issue_title": "lock_tool: path-traversal via unsanitized session_id",
  "branch_prefix": "fix",
  "extraction_tier": 1
}
```

### Example output (no match)

```json
{
  "issue_number": null,
  "issue_title": null,
  "branch_prefix": "feat",
  "extraction_tier": null
}
```

---

## Shell Security Constraints

Step `03b` follows the same shell-security rules as the rest of the default
workflow:

| Constraint | Detail |
|------------|--------|
| **No `shell=True`** | All `gh` subprocess calls use a list-form argv; no shell interpolation |
| **Heredoc delimiter single-quoted** | The `EOFISSUECREATION` delimiter in the issue-creation heredoc is always single-quoted (`'EOFISSUECREATION'`) to prevent shell metacharacter expansion from `task_description` |
| **60-second timeout** | Every `gh` subprocess call carries `timeout=60`; hung subprocesses do not stall the workflow |
| **No credential logging** | `gh` output is captured in memory and never written to disk unredacted |

---

## Configuration

Step `03b` reads the following values from the workflow context:

| Context key | Required | Description |
|-------------|----------|-------------|
| `task_description` | Yes | Free-form string describing the task |
| `repo_path` | Yes | Absolute path used to derive `owner/repo` from `git remote get-url origin` |
| `expected_gh_account` | No | If set, `gh api /user` is checked before Tier 2/3 network calls |

No environment variables are specific to step `03b`; it relies on the
authenticated `gh` CLI configured in the user's shell.

---

## Examples

### Resolving from an issue URL

```yaml
# Recipe context snippet
task_description: |
  Fix path-traversal bug.
  See https://github.com/rysweet/amplihack/issues/3960
```

```
Tier 1 match: 3960
issue_number: 3960
issue_title:  "lock_tool: path-traversal via unsanitized session_id"
extraction_tier: 1
```

---

### Resolving from a PR URL

```yaml
task_description: "Resume https://github.com/rysweet/amplihack/pull/4143"
```

```
No issues/ URL found → Tier 2
gh pr view 4143 --json closingIssuesReferences
→ [3960, 3983]
issue_number: 3960
extraction_tier: 2
```

---

### Resolving from a bare `#N` pattern

```yaml
task_description: "Continue work on #3983"
```

```
No issues/ URL, no pull/ URL → Tier 3
gh issue view 3983 → open
issue_number: 3983
extraction_tier: 3
```

---

### No resolvable issue

```yaml
task_description: "Refactor the config module for clarity"
```

```
No URL, no #N → extraction_tier: null
issue_number: null
branch name falls back to slugified task_description
```

---

## Troubleshooting

**`gh: command not found`**

Install and authenticate the GitHub CLI: `gh auth login`.
Step `03b` degrades gracefully — Tier 1 (regex-only) still works without `gh`.

**Tier 2 returns no closing issues**

The PR may not use closing keywords (`Closes #N`, `Fixes #N`).  Add a closing
keyword to the PR description, or supply the issue URL directly in
`task_description`.

**Tier 3 skips a valid issue number**

The issue may be closed.  Step `03b` only accepts issues that `gh issue view`
returns successfully; closed issues return exit code 0 but the workflow checks
the `state` field and skips `CLOSED` issues.

**`extraction_tier` is `null` but a `#N` is present**

The `#N` pattern requires at least one digit.  Values like `#` alone or
`#abc` are not matched.  Check that the issue exists in the resolved repository.

---

## Related

- [Workflow Execution Guardrails Reference](./workflow-execution-guardrails.md)
  — canonical execution root and GitHub identity gate (also part of the default
  workflow)
- [How to Configure Workflow Execution Guardrails](../howto/configure-workflow-execution-guardrails.md)
- [Default Workflow](../claude/workflow/DEFAULT_WORKFLOW.md) — full step list
- [Lock Session ID Sanitization](../security/lock-session-id-sanitization.md)
  — the security fix delivered alongside this extraction improvement (PR #4143)
- Issues [#3960](https://github.com/rysweet/amplihack/issues/3960) and
  [#3983](https://github.com/rysweet/amplihack/issues/3983) — originating work
- PR [#4143](https://github.com/rysweet/amplihack/pull/4143) — implementation

---

**Metadata**

| Field | Value |
|-------|-------|
| Status | Implemented |
| Issues | #3960, #3983 |
| PR | #4143 |
| Recipe file | `amplifier-bundle/recipes/default-workflow.yaml` (step `03b`) |
| Test file | `amplifier-bundle/tools/test_default_workflow_fixes.py` |
| Gadugi spec | `tests/gadugi/lock-recovery-and-issue-extraction.yaml` |
