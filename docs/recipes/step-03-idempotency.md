# step-03-create-issue: Idempotency Guards

`step-03-create-issue` is the issue-creation step in `default-workflow.yaml`.
It creates a GitHub issue to track the current workflow run. Since the
default-workflow is often re-run against the same task (e.g., when resuming
after an interruption, retrying a failed step, or running in a loop), the step
uses two idempotency guards to detect and reuse an existing issue instead of
creating a duplicate.

**Added in:** PR #3952 (merged 2026-04-03)
**Pattern source:** `step-16-create-draft-pr` idempotency guards (#3324)

---

## Quick Start

No configuration is required. The guards activate automatically every time
`step-03-create-issue` runs.

```bash
# Run the default workflow — step-03 handles deduplication transparently
amplihack recipe run default-workflow -c task_description="Fix login timeout bug in #4194" \
  -c repo_path="$(pwd)"
```

If a prior run already created an issue for this task, step-03 reuses it and
logs:

```
INFO: task_description references issue #4194 — verifying it exists
INFO: Reusing existing issue #4194 — skipping creation
```

---

## How It Works

The step runs three checks in priority order before creating a new issue:

```
input: task_description + ISSUE_TITLE
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Guard 1 — Reference Guard                                      │
│  Does task_description contain #NNNN?                           │
│  yes → gh issue view #NNNN (timeout 60s)                        │
│         issue found? → output URL, exit 0 (reuse)              │
│         not found   → fall through to Guard 2                   │
│  no  → fall through to Guard 2                                  │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Guard 2 — Title Search Guard                                   │
│  gh issue list --state open --search <first 100 chars of title> │
│         match found? → output URL, exit 0 (reuse)              │
│         no match    → fall through to creation                  │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Fallback — Create New Issue                                    │
│  gh issue create (original behavior, unchanged)                 │
└─────────────────────────────────────────────────────────────────┘
```

### Guard 1: Reference Guard

Triggered when `task_description` contains a GitHub issue reference in the form
`#NNNN` (e.g., `Fix the bug in #4194`).

1. Extracts the first `#NNNN` pattern using bash regex `[[ =~ \#([0-9]+) ]]`
2. Validates the extracted value is purely numeric (defense-in-depth)
3. Calls `gh issue view <N> --json url --jq '.url // ""'` with a 60-second timeout
4. If the issue exists: outputs its URL to stdout and exits 0 (reuse)
5. If the issue does not exist or the call fails: falls through to Guard 2

This guard is the cheapest and most specific. It requires zero search and makes
a single API call to a known issue number.

### Guard 2: Title Search Guard

Always runs when Guard 1 does not match. Uses `gh issue list` to search open
issues for a title similar to the current one.

1. Truncates the issue title to its first 100 characters (GitHub search limit)
2. Calls `gh issue list --state open --search "<query>"` with a 60-second timeout
3. If a matching open issue is found: outputs its URL to stdout and exits 0 (reuse)
4. If no match: falls through to issue creation

This guard catches the case where the workflow was re-run without explicitly
referencing an issue number — for example, when the task description is
re-submitted verbatim.

### Fallback: Create New Issue

If neither guard matches, the step creates a new issue using the same logic
as before the idempotency guards were added. This path is completely unchanged.

---

## Output Format

All three paths (both guards and the creation fallback) write a single GitHub
issue URL to stdout:

```
https://github.com/owner/repo/issues/123
```

The downstream step `step-03b-extract-issue-number` extracts the issue number
from this URL using:

```bash
grep -oE 'issues/[0-9]+' | grep -oE '[0-9]+' | head -1
```

This extraction works identically for guard output and newly-created issue
output, so `step-03b` requires no changes.

---

## Diagnostic Messages

All diagnostic output goes to **stderr** and is not captured by the recipe
runner's output pipeline. You can view it in the recipe's verbose log or by
redirecting stderr.

| Message                                                                      | When                             |
| ---------------------------------------------------------------------------- | -------------------------------- |
| `INFO: task_description references issue #N — verifying it exists`           | Guard 1 extracted a reference    |
| `INFO: Reusing existing issue #N — skipping creation`                        | Guard 1 matched and reused       |
| `WARN: Referenced issue #N not found — will search or create`                | Guard 1 fell through             |
| `INFO: Searching open issues for similar title`                              | Guard 2 running                  |
| `INFO: Found existing open issue matching title — skipping creation`         | Guard 2 matched and reused       |
| `INFO: No matching open issue found — proceeding to create`                  | Guard 2 fell through             |
| `WARN: Extracted issue reference is not numeric: <value> — skipping guard 1` | Guard 1 rejected an unsafe value |

---

## Error Handling

| Failure mode                           | Behavior                                                                                                                           |
| -------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `gh issue view` times out (> 60 s)     | `timeout` returns exit 124; `\|\| echo ''` catches it; guard falls through                                                         |
| `gh issue view` returns HTTP error     | `2>/dev/null` suppresses noise; `\|\| echo ''` falls through                                                                       |
| `gh issue list --search` times out     | Same as above                                                                                                                      |
| `gh issue list --search` returns empty | Empty string; guard falls through to creation                                                                                      |
| `gh` not authenticated                 | `2>/dev/null` and `\|\| echo ''` suppress; both guards fall through; creation proceeds normally (or fails with a clear auth error) |
| Non-numeric issue reference extracted  | Explicit `^[0-9]+$` validation skips guard 1 with a `WARN` message                                                                 |

The step uses `set -euo pipefail`. All expected-failure exit paths use
`|| echo ''` or `|| true` so the script does not abort unexpectedly.

---

## Security

### Command Injection Prevention

| Attack vector                                                      | Mitigation                                                                                                                                                                                                                     |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `#NNNN` in `task_description` contains shell metacharacters        | Bash regex `[[ =~ \#([0-9]+) ]]` captures only `[0-9]+`; `BASH_REMATCH[1]` contains only digits                                                                                                                                |
| Captured number contains semicolons, pipes, or other characters    | Explicit `^[0-9]+$` validation rejects anything non-numeric before it reaches `gh issue view "$REF_ISSUE_NUM"`                                                                                                                 |
| Long or special-character title passed to `gh issue list --search` | Double-quoted variable `"$SEARCH_QUERY"` prevents shell word-splitting; `gh` CLI handles API-level escaping                                                                                                                    |
| Template injection via `task_description` or `final_requirements`  | Both are captured via unquoted heredoc (`<<EOFTASKDESC`) into bash variables (`TASK_DESC`, `ISSUE_REQS`). The issue body is assembled with `printf` using double-quoted variable expansions — no `eval`, no unquoted expansion |

### Trusted Inputs

The recipe context variables `task_description` and `final_requirements` must
never contain secrets or authentication tokens. They are embedded verbatim in
the GitHub issue body, which is publicly visible on public repositories.

---

## Configuration

The guards require no configuration. They activate automatically on every
`step-03-create-issue` execution.

The only tuneable behaviour is the `condition: "not issue_number"` guard on
the step itself: if `issue_number` is already set in the recipe context (e.g.,
passed in explicitly via `-c issue_number=42`), the entire step is skipped.

```bash
# Skip step-03 entirely — use a pre-existing issue number
amplihack recipe run default-workflow \
  -c issue_number=42 \
  -c task_description="Fix login timeout" \
  -c repo_path="$(pwd)"
```

---

## Usage Examples

### Example 1: Re-running a workflow for the same task

A previous run created issue #4194. The next run's `task_description` still
references `#4194`.

```
task_description = "Fix login timeout bug described in #4194"
```

**Step-03 output (stderr):**

```
INFO: task_description references issue #4194 — verifying it exists
INFO: Reusing existing issue #4194 — skipping creation
```

**Step-03 output (stdout):**

```
https://github.com/myorg/myrepo/issues/4194
```

No duplicate issue created. Step-03b extracts `4194` as normal.

---

### Example 2: Re-running without an explicit issue reference

Previous run created issue #4200 with title `"Add user profile page"`. New run
has the same `task_description` but no `#NNNN` reference.

**Guard 1:** No `#NNNN` found — skips to Guard 2.

**Guard 2 search query:** `Add user profile page` (under 100 chars, no truncation)

**Step-03 output (stderr):**

```
INFO: Searching open issues for similar title
INFO: Found existing open issue matching title — skipping creation
```

**Step-03 output (stdout):**

```
https://github.com/myorg/myrepo/issues/4200
```

---

### Example 3: First run — no existing issue

No prior issues match. Both guards fall through; a new issue is created.

**Step-03 output (stderr):**

```
INFO: Searching open issues for similar title
INFO: No matching open issue found — proceeding to create
```

**Step-03 output (stdout):**

```
https://github.com/myorg/myrepo/issues/4201
```

---

### Example 4: Very long task description

`task_description` is 500 characters long. The issue title is truncated to 200
characters (recipe-level truncation). Guard 2's search query uses only the
first 100 characters of that title.

```bash
# Title: first 200 chars of task_description
# Search: first 100 chars of title
SEARCH_QUERY="${ISSUE_TITLE:0:100}"
```

This ensures the `gh` search API is not passed excessively long queries.

---

## Testing

The outside-in test suite covers all three code paths and all cross-cutting
concerns:

```bash
# Run the full test suite
gadugi-test run tests/gadugi/step-03-issue-creation-idempotency.yaml --verbose

# Validate the scenario YAML structure
gadugi-test validate tests/gadugi/step-03-issue-creation-idempotency.yaml
```

**Coverage (20 scenarios):**

| Area                                               | Scenarios |
| -------------------------------------------------- | --------- |
| Guard 1: `#NNNN` extraction                        | S11, S12  |
| Guard 1: numeric validation / injection prevention | S13       |
| Guard 2: title truncation                          | S14, S15  |
| Output URL compatibility with step-03b             | S16       |
| Both guards exit 0 on reuse                        | S10       |
| Guard ordering (1 before 2, creation last)         | S17       |
| API failure fallthrough (`\|\| echo ''`)           | S20       |
| `timeout 60` wrappers                              | S7        |
| Stderr routing                                     | S8        |
| `set -euo pipefail`                                | S19       |
| Pattern provenance (step-16 reference)             | S18       |
| YAML structure grep checks                         | S1–S9     |

---

## Known Limitations

**Guard 2 false positives.** `gh issue list --search` uses GitHub's full-text
search, which can match issues whose titles differ from the current one. When
this happens, step-03 reuses the matched issue instead of creating a new one.
This is intentional: a false-positive reuse is preferable to creating a
duplicate. The matched issue URL is passed downstream as normal, and the
workflow tracks progress there.

**TOCTOU race.** Between Guard 2's search and `gh issue create`, a concurrent
workflow run could create a matching issue. In that case, two issues would
exist — the same worst-case as before the guards were added. GitHub issue
creation is inherently non-atomic, so this is not mitigated.

**Guard 1 uses only the first `#NNNN` reference.** If `task_description`
contains multiple issue references, only the first one is checked. If that
issue was closed or deleted, Guard 1 falls through to Guard 2 even if a later
reference would have matched.

---

## Related

- `step-16-create-draft-pr` idempotency guards — pattern source (#3324)
- `step-03b-extract-issue-number` — downstream step that parses step-03 output
- `tests/gadugi/step-03-issue-creation-idempotency.yaml` — test suite
- `docs/investigations/step-03-idempotency-guards-analysis.md` — security analysis and implementation notes
