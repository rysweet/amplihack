# PM Automation Scripts

GitHub Actions scripts for automated project management reporting.

## Scripts

### `pm_daily_status.py` — Daily Status Report

Generates a daily project health report covering CI/CD status, open issues, open PRs, and actionable recommendations.

**Triggered by:** `.github/workflows/pm-daily-status.yml` (daily at 9 AM UTC, or manual dispatch)

**Output:** `status_report.md` — posted as a comment to the tracking issue configured in `vars.PM_STATUS_ISSUE_NUMBER`.

### `pm_roadmap_review.py` — Weekly Roadmap Review

Generates a weekly roadmap analysis covering velocity metrics, priority distribution, blockers, and strategic recommendations.

**Triggered by:** `.github/workflows/pm-roadmap-review.yml` (Mondays at 8 AM UTC, or manual dispatch)

**Output:** `roadmap_review.md` — posted as a comment to the tracking issue configured in `vars.PM_ROADMAP_ISSUE_NUMBER`.

---

## GitHub Token Compatibility

Both scripts use **only the regular GitHub REST API** via `gh` CLI commands (`gh issue list`, `gh pr list`, `gh run list`). They do **not** use the GitHub Search API.

This is a deliberate design choice. The `GITHUB_TOKEN` provided by GitHub Actions has limited scopes and does **not** support the Search API (used by `gh issue list --search` or `gh pr list --search`). Calling `--search` with a `GITHUB_TOKEN` fails with **exit code 4** (authentication/permission error).

### What we do instead

Instead of `--search 'created:>=DATE'`, the scripts:

1. Fetch a broad set of results with `--limit 200` (no `--search` flag)
2. Filter by date in Python using ISO 8601 string comparison

This works because:

- ISO 8601 timestamps (`2026-02-17T...`) sort lexicographically
- 200 items per query is sufficient for most repositories
- The regular Issues/PRs API only requires `issues: read` and `pull-requests: read` scopes, which `GITHUB_TOKEN` provides

### `_run_gh_command()` helper

Both scripts share the same error-handling pattern via a `_run_gh_command(args, description)` helper:

```python
def _run_gh_command(args: list[str], description: str) -> list[dict[str, Any]]:
    """Run a gh CLI command and return parsed JSON, or empty list on failure."""
```

**Behavior:**

- Runs `subprocess.run()` with list-form args (no shell injection risk)
- On non-zero exit code: logs a warning to stderr, returns `[]`
- On invalid JSON: logs a warning to stderr, returns `[]`
- The calling function continues with empty data rather than crashing

This ensures a single failed `gh` command never crashes the entire report. The report generates with whatever data is available.

---

## Workflow Permissions

### `pm-daily-status.yml`

```yaml
permissions:
  contents: read # Read repository contents
  issues: write # Post status report to tracking issue
  pull-requests: read # Read PR data for open PR counts
```

### `pm-roadmap-review.yml`

```yaml
permissions:
  contents: read # Read repository contents
  issues: write # Post roadmap review to tracking issue
  pull-requests: read # Read PR data for velocity metrics
```

No additional token scopes or PATs are required. The default `GITHUB_TOKEN` is sufficient.

---

## Configuration

| Variable                  | Where                          | Purpose                                              |
| ------------------------- | ------------------------------ | ---------------------------------------------------- |
| `PM_STATUS_ISSUE_NUMBER`  | Repository variables (`vars.`) | Issue number where daily status reports are posted   |
| `PM_ROADMAP_ISSUE_NUMBER` | Repository variables (`vars.`) | Issue number where weekly roadmap reviews are posted |

### Setup

1. Create a GitHub issue to receive daily status reports. Note its number.
2. Create a GitHub issue to receive weekly roadmap reviews. Note its number.
3. Set repository variables:
   - Go to **Settings > Secrets and variables > Actions > Variables**
   - Add `PM_STATUS_ISSUE_NUMBER` with the daily status issue number
   - Add `PM_ROADMAP_ISSUE_NUMBER` with the roadmap review issue number

---

## Troubleshooting

### Exit code 4 from `gh` CLI

**Cause:** The `--search` flag on `gh issue list` or `gh pr list` uses the GitHub Search API, which requires scopes that `GITHUB_TOKEN` does not provide.

**Fix:** Already applied. The scripts use `--limit 200` with Python-side date filtering instead of `--search`. If you see exit code 4 warnings in logs, a `gh` command failed gracefully and the report was generated with partial data.

### Missing `total` key in CI health analysis

**Cause:** Previous versions of `analyze_ci_health()` in `pm_daily_status.py` returned a dict without `"total": 0` when `workflow_runs` was empty, causing a `KeyError` in report generation.

**Fix:** Already applied. The empty-state return now includes all keys: `status`, `passing`, `failing`, `pending`, and `total`.

### Reports show empty data

If all sections show zeros or "No items," check:

1. The `GH_TOKEN` environment variable is set (should be `${{ secrets.GITHUB_TOKEN }}`)
2. The repository has issues/PRs/workflow runs to report on
3. Check the workflow run logs for warning messages from `_run_gh_command()`

### `--limit 200` is not enough

For repositories with more than 200 issues or PRs per week, increase the `--limit` value in the relevant `_run_gh_command()` call. The current limit is suitable for most projects.
