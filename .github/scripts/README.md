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
def _run_gh_command(args: list[str], description: str) -> Optional[list[dict[str, Any]]]:
    """Run a gh CLI command and return parsed JSON, or None on failure."""
```

**Behavior:**

- Runs `subprocess.run()` with list-form args (no shell injection risk)
- On non-zero exit code: logs error to stderr and stdout, returns `None`
- On invalid JSON: logs error to stderr and stdout, returns `None`
- Returns `None` to indicate failure (not empty list `[]`)

This ensures:

- **Failures are explicit** - `None` is clearly different from empty data `[]`
- **Reports show warnings** - Failed fetches displayed as "⚠️ Data fetch failed"
- **Workflows fail** - Exit code 1 when any fetch fails (visible in GitHub Actions)
- **No silent degradation** - Users always know when data is missing

### Failure Visibility

When data fetches fail, reports explicitly show warnings:

**Example report with failures:**

```markdown
## PM Daily Status - 2026-02-24

### ⚠️ INCOMPLETE DATA - SOME FETCHES FAILED

This report contains partial data. The following information could not be fetched:

- Issue count
- CI/CD status

**Action Required**: Check workflow logs for details: `gh run view --log`

---

### Open Items

**Open Issues**: ⚠️ Data fetch failed
**Open PRs**: 5 (3 ready, 2 draft)

### Recommendations

- ⚠️ Verify data manually - some metrics unavailable
```

The workflow will exit with code 1 (fail) when any fetch fails, making issues immediately visible in the GitHub Actions UI.

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

### Workflow fails with "Data fetch failed" warnings

**Cause:** One or more `gh` CLI commands failed (exit code 4 = auth error, other codes = API/network issues).

**What happens:**

- Report is still generated showing which data is missing
- Report includes "⚠️ Data fetch failed" for failed sections
- Workflow exits with code 1 (fail) to make issue visible
- ERROR messages logged to stdout and stderr

**Common causes:**

1. **Exit code 4**: `--search` flag requires Search API scope (we don't use this anymore)
2. **Exit code 1**: API rate limit, network timeout, or GitHub API outage
3. **Invalid JSON**: `gh` CLI version mismatch or API format change

**Fix:**

1. Check workflow logs: `gh run view --log`
2. Look for "ERROR: fetch <operation> failed" messages
3. Verify `GITHUB_TOKEN` has required permissions (issues:read, pull-requests:read)
4. For transient errors, re-run the workflow

### Reports show "⚠️ Data fetch failed"

**This is expected behavior** when `gh` commands fail. The report explicitly shows:

- Banner: "⚠️ INCOMPLETE DATA - SOME FETCHES FAILED"
- List of what couldn't be fetched
- "⚠️ Data fetch failed" for each missing metric

**This is NOT a bug** - it's designed to prevent silent degradation where you see zeros and think "no issues" when actually the fetch failed.

### Missing `total` key in CI health analysis

**Cause:** Previous versions of `analyze_ci_health()` in `pm_daily_status.py` returned a dict without `"total": 0` when `workflow_runs` was empty, causing a `KeyError` in report generation.

**Fix:** Already applied. The empty-state return now includes all keys: `status`, `passing`, `failing`, `pending`, and `total`.

### `--limit 200` is not enough

For repositories with more than 200 issues or PRs per week, increase the `--limit` value in the relevant `_run_gh_command()` call. The current limit is suitable for most projects.
