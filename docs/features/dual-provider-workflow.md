# Dual-Provider Workflow Support (GitHub + Azure DevOps)

**Provider-aware issue tracking and pull request creation in the default workflow recipe.**

> [Home](../index.md) > [Features](README.md) > Dual-Provider Workflow Support

## Quick Navigation

- [How to configure dual-provider workflow](../howto/configure-dual-provider-workflow.md)
- [Tutorial: running the default workflow on an ADO repo](../tutorials/dual-provider-workflow.md)
- [Dual-provider workflow reference](../reference/dual-provider-workflow.md)

---

## What This Feature Does

Before this feature, the `default-workflow` recipe failed immediately on Azure DevOps repositories because `step-03-create-issue` called `gh issue create`, which only works with GitHub remotes:

```
Step 'step-03-create-issue' failed: bash step failed: Command failed (exit 1):
none of the git remotes configured for this repository point to a known GitHub host.
```

Dual-provider workflow support makes two workflow steps provider-aware:

| Step                      | GitHub                 | Azure DevOps                             |
| ------------------------- | ---------------------- | ---------------------------------------- |
| `step-03-create-issue`    | `gh issue create`      | `az boards work-item create --type Task` |
| `step-16-create-draft-pr` | `gh pr create --draft` | `az repos pr create --draft`             |

Both steps now detect the git remote at runtime using a shared `detect_git_provider()` shell function and route to the correct CLI tool automatically. All other workflow steps are unchanged.

---

## How Provider Detection Works

```
git remote get-url origin
         │
         ▼
  contains "dev.azure.com"
  or "visualstudio.com"?
         │
    yes ─┤─ no
         │         │
       "ado"    "github"
```

The function is defined inline in each shell step that needs it:

```bash
detect_git_provider() {
  local remote_url
  remote_url=$(git remote get-url origin 2>/dev/null || echo '')
  if [[ "$remote_url" == *"dev.azure.com"* ]] || \
     [[ "$remote_url" == *"visualstudio.com"* ]]; then
    echo "ado"
  else
    echo "github"
  fi
}
```

"github" is the default, so self-hosted GitHub Enterprise remotes, SSH remotes, and any non-ADO remote follow the existing GitHub path unchanged.

---

## ADO Work Item Creation (step-03)

When `GIT_PROVIDER=ado`, step-03 creates an ADO **Task** work item using the Azure DevOps CLI:

```bash
az boards work-item create \
  --type "Task" \
  --title "<first 200 chars of task_description>" \
  --description "<full task body with requirements and acceptance criteria>" \
  --query id \
  -o tsv
```

The numeric work item ID is emitted as `_workitems/edit/<ID>` so that `step-03b-extract-issue-number` can parse it with its updated regex.

### Idempotency Guards

Two guards prevent duplicate work item creation on retry:

1. **Reference guard** — if `task_description` contains `#NNNN`, step-03 verifies that ADO work item `NNNN` exists and reuses it.
2. **Title search guard** — a WIQL query searches for an open work item with a matching title. If one is found, it is reused.

### Work Item Type

`Task` is used as the ADO equivalent of a GitHub issue for generic ADO projects. It is the closest general-purpose analog. Projects using a custom process model may adapt this via `--type`.

---

## ADO Pull Request Creation (step-16)

When `GIT_PROVIDER=ado`, step-16 creates a draft ADO pull request targeting `main`:

```bash
az repos pr create --draft \
  --title "<PR title>" \
  --description "<PR body with summary, issue link, checklist>" \
  --source-branch "<current branch>" \
  --target-branch "main" \
  --query url \
  -o tsv
```

An idempotency guard calls `az repos pr list --source-branch` first to detect an existing PR on the same branch before attempting creation.

The `--work-items` flag is not currently used. In the ADO workflow path `issue_number` is always the ADO work item ID (extracted from `_workitems/edit/<N>` by step-03b), but formal API linkage via `--work-items` is deferred to a future enhancement. The PR body contains `Closes #<issue_number>` as a prose reference, which is sufficient for most ADO board policies.

---

## step-03b Regex Update

`step-03b-extract-issue-number` parses the URL-like path emitted by step-03 to extract a numeric ID. The regex now matches both GitHub and ADO URL shapes:

| Pattern            | Example                                 |
| ------------------ | --------------------------------------- |
| GitHub             | `https://github.com/org/repo/issues/42` |
| ADO (emitted path) | `_workitems/edit/42`                    |

Both are matched by: `(issues|_workitems/edit)/[0-9]+`

---

## Security Fixes Included

Two security issues were corrected as part of this work:

| Severity | Location         | Fix                                                                                                                                          |
| -------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| Medium   | step-16 heredocs | Changed `<<EOFTASKDESC` to `<<'EOFTASKDESC'` (quoted delimiter prevents bash expansion of `$()` and backticks in recipe-substituted content) |
| Low      | ADO work item ID | Added `case '*[!0-9]*'` guard after `az boards work-item create` to reject non-numeric output before it is interpolated downstream           |

---

## What Is Not Covered

- **ADO organization/project inference** — the `az` CLI uses the default configured via `az devops configure`. There is no per-repository project map.
- **Label creation** — GitHub-only. Silently skipped on ADO (ADO does not have an exact label equivalent).
- **Pre-flight `az` auth check** — authentication failures propagate as `exit 1` from the `az` commands. Operators should verify `az account show` before running the workflow.
- **WIQL injection hardening** — the idempotency title search escapes single quotes but does not strip WIQL meta-operators. Titles with `[`, `]`, `CONTAINS`, or semicolons may produce unexpected query behavior.
