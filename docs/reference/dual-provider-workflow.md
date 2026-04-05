# Dual-Provider Workflow Reference

> [Home](../index.md) > Reference > Dual-Provider Workflow

Field-level contract for provider detection, ADO work item creation, ADO PR creation, and the updated issue-number extraction regex.

## Contents

- [Provider Detection Contract](#provider-detection-contract)
- [Affected Workflow Steps](#affected-workflow-steps)
- [step-03 ADO Path: Work Item Creation](#step-03-ado-path-work-item-creation)
- [step-03b Regex Contract](#step-03b-regex-contract)
- [step-16 ADO Path: PR Creation](#step-16-ado-path-pr-creation)
- [Security Invariants](#security-invariants)
- [Known Limitations](#known-limitations)
- [Environment Requirements](#environment-requirements)

---

## Provider Detection Contract

### Function: `detect_git_provider()`

Defined inline in each provider-aware bash step. Returns one of two string values.

| Return Value | Condition                                                                  |
| ------------ | -------------------------------------------------------------------------- |
| `ado`        | `git remote get-url origin` contains `dev.azure.com` or `visualstudio.com` |
| `github`     | All other cases, including empty remote, SSH remotes, GitHub Enterprise    |

#### Guarantees

- Never exits non-zero. If `git remote get-url origin` fails, the remote URL is treated as empty, and the function returns `github`.
- The check is substring-based, not regex. Both HTTPS (`https://dev.azure.com/org/...`) and SSH (`git@ssh.dev.azure.com:v3/...`) ADO remote formats are matched by the `dev.azure.com` pattern.
- The result is stored in `GIT_PROVIDER` and treated as read-only for the rest of the step.

---

## Affected Workflow Steps

| Step ID                         | Provider-Aware   | Change                                |
| ------------------------------- | ---------------- | ------------------------------------- |
| `step-03-create-issue`          | Yes              | ADO branch added                      |
| `step-03b-extract-issue-number` | Yes (regex only) | Regex extended to match ADO URL shape |
| `step-16-create-draft-pr`       | Yes              | ADO branch added                      |
| All other steps                 | No               | Unchanged                             |

---

## step-03 ADO Path: Work Item Creation

### Input Variables

| Variable             | Source                                    | Usage                                                  |
| -------------------- | ----------------------------------------- | ------------------------------------------------------ |
| `task_description`   | Recipe context (`{{task_description}}`)   | Work item title (first 200 chars) and description body |
| `final_requirements` | Recipe context (`{{final_requirements}}`) | Appended to description body                           |

### Idempotency Guards (evaluated in order)

#### Guard 1: Reference in task_description

If `task_description` matches `#[0-9]+`, the captured number is treated as an existing ADO work item ID.

- Calls `az boards work-item show --id <NUM> --query id -o tsv`
- If the work item exists: emits `_workitems/edit/<NUM>` and exits 0
- If not found: logs a warning and falls through to Guard 2

#### Guard 2: Title search (WIQL)

Searches for an open ADO work item with a title matching the first 100 characters of `ISSUE_TITLE`.

- Calls `az boards query --wiql "SELECT [System.Id] FROM WorkItems WHERE [System.Title] = '...' AND [System.State] <> 'Closed'"`
- Single quotes in the title are escaped to `''`
- If a match is found: emits `_workitems/edit/<ID>` and exits 0
- If no match: falls through to creation

### Creation

```bash
az boards work-item create \
  --type "Task" \
  --title "$ISSUE_TITLE" \
  --description "$ISSUE_BODY" \
  --query id \
  -o tsv
```

Uses the ADO defaults configured via `az devops configure --defaults`.

### Output

Emits one line to stdout: `_workitems/edit/<numeric-ID>`

### Exit Codes

| Code | Meaning                                                           |
| ---- | ----------------------------------------------------------------- |
| 0    | Work item created or idempotency guard matched; ID emitted        |
| 1    | `az boards work-item create` returned empty or non-numeric output |
| 1    | `az` exited non-zero                                              |

---

## step-03b Regex Contract

The regex used to extract a numeric issue number from the step-03 output:

```
(issues|_workitems/edit)/[0-9]+
```

| URL Shape                               | Matched Segment      | Extracted Number |
| --------------------------------------- | -------------------- | ---------------- |
| `https://github.com/org/repo/issues/42` | `issues/42`          | `42`             |
| `_workitems/edit/42`                    | `_workitems/edit/42` | `42`             |

The extracted number is the sequence of digits after the last `/`.

---

## step-16 ADO Path: PR Creation

### Input Variables

| Variable                       | Source          | Usage                                 |
| ------------------------------ | --------------- | ------------------------------------- |
| `worktree_setup.worktree_path` | step-04 output  | Working directory; branch name source |
| `task_description`             | Recipe context  | PR title (first 200 chars)            |
| `design_spec`                  | Recipe context  | PR description body                   |
| `issue_number`                 | step-03b output | Included as `Closes #<N>` in PR body  |

### Idempotency Guard

Before creating a PR, calls:

```bash
az repos pr list \
  --source-branch "$CURRENT_BRANCH" \
  --query '[0].url' \
  -o tsv
```

If a non-empty, non-`None` result is returned, the existing PR URL is emitted and the step exits 0.

### Creation

```bash
az repos pr create --draft \
  --title "$PR_TITLE" \
  --description "$PR_BODY" \
  --source-branch "$CURRENT_BRANCH" \
  --target-branch "main" \
  --query url \
  -o tsv
```

Timeout: 120 seconds (ADO REST API; slower than GitHub API).

### Output

Emits the ADO PR URL to stdout:

```
https://dev.azure.com/org/project/_git/repo/pullrequest/NNN
```

### Exit Codes

| Code   | Meaning                                                                                                |
| ------ | ------------------------------------------------------------------------------------------------------ |
| 0      | PR created or idempotency guard matched; URL emitted                                                   |
| 1      | `az repos pr create` returned empty or `None`                                                          |
| N (≠0) | `az repos pr create` exited non-zero; exit code propagated directly via `AZ_STATUS` (not clamped to 1) |
| 1      | `COMMITS_AHEAD` is 0 (pre-condition guard, not ADO-specific)                                           |
| 1      | `ISSUE_NUM` is not numeric (pre-condition guard, not ADO-specific)                                     |

---

## Security Invariants

| Invariant                                | Implementation                                                                                                                                 |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| Heredoc delimiters are quoted            | `<<'EOFTASKDESC'` and `<<'EOFDESIGN'` prevent bash from expanding `$()` and backticks in recipe-substituted content                            |
| ADO work item ID is validated as numeric | `case "$NEW_ITEM_ID" in ''`\|`*[!0-9]*)` exits 1 before any downstream interpolation; rejects empty, `None`, or non-numeric `az boards` output |
| `issue_number` is validated as numeric   | `case "$ISSUE_NUM" in ''`\|`*[!0-9]*)` exits 1 at the start of step-16 (pre-existing guard, not ADO-specific)                                  |

---

## Known Limitations

| Limitation                                                  | Impact                                                                                        | Workaround                                                                         |
| ----------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| ADO org/project not inferred from remote URL                | Wrong project used if `az devops configure` defaults point to a different project             | Set `az devops configure --defaults` explicitly per repository or per session      |
| WIQL title search escapes only single quotes                | Titles containing `[`, `]`, `CONTAINS`, semicolons may produce unexpected WIQL query behavior | Use `task_description` with simple alphanumeric titles on ADO                      |
| `CURRENT_BRANCH` not validated against a safe character set | Branches with unusual characters could produce unexpected `--source-branch` arguments         | Use standard branch names (`feat/`, `fix/`, `docs/`)                               |
| No pre-flight `az` auth check                               | Auth failures propagate as `exit 1` from `az` commands without a specific diagnostic message  | Run `az account show` before invoking the workflow                                 |
| `--work-items` flag not used in PR creation                 | ADO PR is not formally API-linked to the work item (prose `Closes #N` in description only)    | Future: add `--work-items "$ISSUE_NUM"` to `az repos pr create` for formal linkage |

---

## Environment Requirements

| Requirement              | Minimum Version | Check Command                                                        |
| ------------------------ | --------------- | -------------------------------------------------------------------- |
| Azure CLI                | 2.50.0          | `az --version`                                                       |
| azure-devops extension   | 0.26.0          | `az extension list --query "[?name=='azure-devops'].version" -o tsv` |
| Authenticated session    | —               | `az account show`                                                    |
| ADO organization default | —               | `az devops configure --list`                                         |
| ADO project default      | —               | `az devops configure --list`                                         |
