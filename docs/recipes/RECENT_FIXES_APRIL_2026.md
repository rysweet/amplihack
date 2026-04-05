# Recent Recipe Runner Fixes — April 2026

This document tracks bug fixes and improvements to the Recipe Runner released in
April 2026, following the [Diátaxis](https://diataxis.fr/) framework.

---

## ADO Provider Support for Steps 03 and 16 (PR #4205, 2026-04-03)

### Root Cause

`step-03-create-issue` and `step-16-create-draft-pr` unconditionally called
`gh issue create` and `gh pr create`, which are GitHub-only commands. When
`amplihack` was run against a repository whose remote URL pointed to Azure
DevOps (`dev.azure.com` or `*.visualstudio.com`), both steps exited 1 with
`gh: command requires a GitHub repository`.

`step-03b-extract-issue-number` used a regex of `issues/[0-9]+` that matched
GitHub issue URLs but not ADO work item URLs of the form
`_workitems/edit/NNNN`.

### Fix

A shared `detect_git_provider()` function was added to both `step-03` and
`step-16`. It inspects the `origin` remote URL and returns `github` or `ado`:

```bash
detect_git_provider() {
    local remote_url
    remote_url=$(git remote get-url origin 2>/dev/null || echo "")
    if echo "$remote_url" | grep -qE "dev\.azure\.com|\.visualstudio\.com"; then
        echo "ado"
    else
        echo "github"
    fi
}
GIT_PROVIDER=$(detect_git_provider)
```

Each step then branches on `$GIT_PROVIDER`:

| Step | GitHub path | ADO path |
|------|------------|---------|
| `step-03-create-issue` | `gh issue create` | `az boards work-item create --type Task` |
| `step-16-create-draft-pr` | `gh pr create --draft` | `az repos pr create --draft` |

**`step-03b-extract-issue-number`** regex updated from:

```
issues/[0-9]+
```

to:

```
(issues|_workitems/edit)/[0-9]+
```

This captures both GitHub issue URLs and ADO work item URLs, extracting the
numeric ID in both cases.

**Idempotency guards** were extended to both providers:

- Step-03: Reference guard (searching for `#NNNN` in `task_description`) works
  identically for both providers. Title-search guard uses `az boards
  work-item query` for ADO.
- Step-16: Existing PR check uses `az repos pr list` for ADO (previously
  `gh pr list`).

### Impact

- `default-workflow` now completes successfully on ADO-hosted repositories
  without modification.
- GitHub path is unchanged; no regression for existing GitHub users.
- The `detect_git_provider()` pattern is available for future steps that need
  provider-specific commands.

### Requirements

For ADO repos, the Azure CLI (`az`) must be installed and authenticated:

```bash
az login
az devops configure --defaults organization=https://dev.azure.com/YOUR_ORG project=YOUR_PROJECT
```

### Tests

`tests/recipes/test_ado_provider_support.py` — 25 tests covering:

- `detect_git_provider()` presence in step-03 and step-16
- `dev.azure.com` / `visualstudio.com` detection
- `az boards work-item create` path in step-03
- ADO URL regex in step-03b (`_workitems/edit/[0-9]+`)
- `az repos pr create` path in step-16
- GitHub path unchanged

---

## Heredoc Injection Fix in Step-16 (2026-04-03)

### Root Cause

`step-16-create-draft-pr` passed `TASK_DESC` and `PR_DESIGN` to the `gh pr
create` / `az repos pr create` command body using **unquoted** heredoc
delimiters:

```bash
gh pr create --body <<EOFTASKDESC
$TASK_DESC
EOFTASKDESC
```

When `TASK_DESC` or `PR_DESIGN` contained `$()` or backtick sequences (common
in PR descriptions that reference shell commands or code examples), bash
expanded them during heredoc substitution. This is the same class of injection
documented for step-03 in FIX #3045/#3076/#3117.

A secondary risk: `NEW_ITEM_ID` (the work item ID returned by
`az boards work-item create`) was used without numeric validation, so
unexpected CLI output (e.g., a warning line) could produce a
non-numeric value that silently broke downstream steps.

### Fix

Heredoc delimiters were changed to **quoted** form to suppress expansion:

```bash
# Before (vulnerable)
gh pr create --body <<EOFTASKDESC
$TASK_DESC
EOFTASKDESC

# After (safe)
gh pr create --body <<'EOFTASKDESC'
$TASK_DESC
'EOFTASKDESC'
```

A numeric guard was added after `az boards work-item create`:

```bash
NEW_ITEM_ID=$(az boards work-item create ... | jq -r '.id')
if ! [[ "$NEW_ITEM_ID" =~ ^[0-9]+$ ]]; then
    echo "ERROR: expected numeric work item ID, got: $NEW_ITEM_ID" >&2
    exit 1
fi
```

### Impact

- Task descriptions and PR design documents containing `$()`, backticks, or
  other shell metacharacters are passed verbatim to the PR creation command.
- Invalid `az` CLI output causes a clear, immediate failure rather than
  silently corrupting the workflow state.

### Pattern

This matches the `<<'EOF'` convention already established for step-03 (PR
#3117). All recipe bash steps that embed recipe-runner-substituted content in
heredocs should use quoted delimiters.

---

## Step-03 Idempotency Guards (PR #3952, merged 2026-04-03)

*Documented in [`step-03-idempotency.md`](step-03-idempotency.md). Summarised
here for completeness.*

`step-03-create-issue` now runs two deduplication guards before calling `gh
issue create` / `az boards work-item create`:

1. **Reference guard** — if `task_description` contains `#NNNN`, verify the
   issue exists and reuse it.
2. **Title-search guard** — search open issues/work items for a similar title
   and reuse if found.

These guards prevent duplicate issues on workflow re-runs and retries.

---

## See Also

- [`step-03-idempotency.md`](step-03-idempotency.md) — full guard contract,
  security analysis, and test reference
- [`RECENT_FIXES_MARCH_2026.md`](RECENT_FIXES_MARCH_2026.md) — prior fix cycle
- [`../RECIPE_RESILIENCE.md`](../RECIPE_RESILIENCE.md) — resilience pattern
  overview
