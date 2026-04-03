---
name: gh-work-report
description: >
  Generates comprehensive GitHub activity reports across all authenticated accounts.
  Gathers repos, PRs, features, and themes for configurable time periods (1/5/7/30/90 days).
  Produces shareable markdown with tables, mermaid charts, and executive summaries.
  Can create a private repo with GitHub Actions automation and GitHub Pages aggregation site.
  Use when: "github report", "work report", "activity summary", "what did I work on",
  "gh-work-report", "show my github activity".
auto_activate_keywords:
  - gh-work-report
  - github report
  - work report
  - activity summary
  - github activity
  - what did I work on
  - what have I been working on
---

# GitHub Work Report Skill

Generates rich GitHub activity reports across all authenticated `gh` accounts.

## Invocation

The user triggers this skill with phrases like:

- `/gh-work-report` (default: last 7 days)
- `/gh-work-report show me the last 30 days`
- `generate a github work report for the last 90 days`
- `what did I work on this week`

### Parse the time period

Extract the number of days from the user's message. Valid values: `1`, `5`, `7`, `30`, `90`. Default to `7` if not specified or if an invalid value is given.

## Workflow

Follow these steps in order. Check off each step as you complete it.

### Step 1: Detect accounts

```bash
gh auth status 2>&1
```

Parse the output to identify all authenticated accounts (e.g., `rysweet` on github.com, `rysweet_microsoft` on github.com). Store the list of `account` values and note which is currently active.

### Step 2: Gather data per account

For each account, switch to it and collect data:

```bash
gh auth switch --user <ACCOUNT>
```

Then gather:

#### 2a. Repositories with recent activity

```bash
# Get repos the user pushed to in the time window
gh api graphql --paginate -f query='
query($cursor: String) {
  viewer {
    repositories(first: 100, after: $cursor, orderBy: {field: PUSHED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        nameWithOwner
        url
        description
        pushedAt
        homepageUrl
        isPrivate
      }
    }
  }
}'
```

Filter to repos with `pushedAt` within the time window.

#### 2b. Pull requests

```bash
gh search prs --author=@me --created=">YYYY-MM-DD" --limit 200 --json number,title,repository,state,createdAt,url,mergedAt
```

Also gather PRs merged (not just created) in the window:

```bash
gh search prs --author=@me --merged=">YYYY-MM-DD" --limit 200 --json number,title,repository,state,createdAt,url,mergedAt
```

Deduplicate by URL.

#### 2c. Issues

```bash
gh search issues --author=@me --created=">YYYY-MM-DD" --limit 100 --json number,title,repository,state,createdAt,url
```

#### 2d. Releases

```bash
# For each active repo, check for releases
gh api repos/{owner}/{repo}/releases --jq '.[].tag_name' | head -5
```

### Step 3: Combine and deduplicate

Merge data from all accounts. Deduplicate repos by `nameWithOwner` and PRs by URL. Tag each item with the account that produced it.

### Step 4: Analyze and synthesize

This is where you add value beyond raw data:

1. **Identify themes**: Group repos/PRs by topic (e.g., "infrastructure", "security", "new features"). Use repo descriptions, PR titles, and any patterns you observe.
2. **Highlight big wins**: PRs with significant impact — large features merged, important bug fixes, new repos created.
3. **Extract usage examples**: For notable features, write a short "here's how to use this" snippet based on PR titles, descriptions, and repo READMEs.
4. **Spot new work**: Repos with first-ever commits in the time window.

### Step 5: Generate the report

Use the template structure from `reference.md`. The report must include:

- **Executive summary** (3-5 sentences)
- **Activity overview** with mermaid charts
- **Per-project sections** with PR tables
- **Themes and big wins**
- **Usage examples** for notable features
- **Appendix** with raw data links

Save the report as a markdown file named `gh-work-report-YYYY-MM-DD-to-YYYY-MM-DD.md`.

### Step 6: Restore original account

Switch back to the account that was active before the report started:

```bash
gh auth switch --user <ORIGINAL_ACCOUNT>
```

### Step 7: Offer automation infrastructure

After generating the report, ask the user:

> Would you like me to create a private GitHub repo with automated weekly/monthly reports and a GitHub Pages site to browse them?

If yes, follow the infrastructure setup in `reference.md` § Infrastructure Setup.

## Key Rules

- **Never hardcode usernames** — always detect from `gh auth status`
- **Never use fallbacks** — no silent defaults, no `2>/dev/null`, no hardcoded values. Errors must fail loud with descriptive messages.
- **All charts must be code-generated** — every number in every chart and table must come from actual API data. Never fabricate or estimate chart data.
- **4 query filters for complete PR coverage**: `created:>DATE` (new), `is:open` (all WIP), `merged:>DATE` (merged during window), `closed:>DATE` (closed during window). Deduplicate by URL.
- **Clamp chart timelines** — Gantt and timeline charts must be scoped to the report window. Clamp start dates to `max(pr_date, window_start)`.
- **Handle private repos gracefully** — note them but don't expose sensitive details unless the report itself is private
- **Date math**: Use `date -d "$DAYS days ago" +%Y-%m-%d` (Linux) for the start date
- **Rate limiting**: If `gh api` returns 403, wait and retry. Use `--paginate` for large result sets.
- **Empty results are fine** — if an account has no activity, say so briefly and move on

## Authentication & Automation

- **Local (multi-account)**: Use `./run.sh [days]` which leverages `gh auth switch` across all locally authenticated accounts. This is the recommended approach for users with multiple accounts (e.g., public + EMU).
- **GitHub Actions (single-account)**: Use the workflow templates with a PAT secret. A PAT is scoped to one identity and cannot cross accounts.
- **Two-PAT approach**: For Actions across two accounts, use separate PAT secrets (`ACCOUNT1_PAT`, `ACCOUNT2_PAT`) with explicit `--header "authorization: token $PAT"` per API call.
- **GitHub Pages is static only** — report generation must happen elsewhere (local script, Actions, gh-aw). Pages just serves the output.

## Reference Files

- `reference.md` — Report template, mermaid chart patterns, infrastructure setup guide
- `templates/weekly-report.yml` — GitHub Actions workflow for automated reports
- `templates/pages-index.html` — GitHub Pages aggregation site template
