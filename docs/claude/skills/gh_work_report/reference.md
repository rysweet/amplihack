# gh-work-report Reference

## Report Template

Use this structure for every report. Adapt section depth based on the volume of activity.

```markdown
# GitHub Activity Report: {START_DATE} → {END_DATE}

> **Generated**: {GENERATION_DATE}
> **Period**: {DAYS} days
> **Accounts**: {ACCOUNT_LIST}

## Executive Summary

{3-5 sentences highlighting the most important work, themes, and wins across all projects.}

## Activity Overview

### Contribution Summary

| Metric | Count |
|--------|-------|
| Projects active | {N} |
| PRs created | {N} |
| PRs merged | {N} |
| Issues opened | {N} |
| Releases published | {N} |

### Activity Timeline

```mermaid
gantt
    title Project Activity
    dateFormat YYYY-MM-DD
    section {Project1}
    PR: {title}  :done, {start}, {end}
    section {Project2}
    PR: {title}  :done, {start}, {end}
```

### PR Distribution by Project

```mermaid
pie title PRs by Project
    "{Project1}" : {count}
    "{Project2}" : {count}
    "{Project3}" : {count}
```

### Weekly Commit Activity

```mermaid
xychart-beta
    title "Commits per Day"
    x-axis ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    y-axis "Commits"
    bar [{n}, {n}, {n}, {n}, {n}, {n}, {n}]
```

## 🏆 Big Wins

{For each significant accomplishment:}

### {Win Title}

**Project**: [{repo}]({url})
**Impact**: {Brief description of why this matters}

{Optional: link to PR, release, or demo}

## 📋 Projects

{For each project with activity:}

### [{owner/repo}]({url})

{Short description from repo metadata. If a GitHub Pages site exists, link it.}

{If homepage URL exists:}
🌐 **Site**: [{homepageUrl}]({homepageUrl})

#### Pull Requests

| # | Title | Status | Created | Merged |
|---|-------|--------|---------|--------|
| [#{n}]({pr_url}) | {title} | {state} | {date} | {date or —} |

#### Notable Features & Updates

{For important PRs/features, write a short description with usage example:}

**{Feature Name}** — {What it does}

```{language}
// Quick example showing how to use this feature
{code snippet based on PR description and repo context}
```

{If docs exist:}
📖 **Docs**: [{link text}]({docs_url})

## 🔍 Themes

{Identify 3-5 themes across all projects. For each:}

### {Theme Name}

{2-3 sentences about this theme — what work fell into this category, why it matters, what direction it's heading.}

**Related PRs**: {list of PR links}

## 🆕 New Work

{Projects or repos that had their first activity in this period:}

- [{repo}]({url}) — {description}

## Appendix

### All Repositories ({N} total)

| Repository | Description | Last Push | Private |
|-----------|-------------|-----------|---------|
| [{repo}]({url}) | {desc} | {date} | {yes/no} |

### Account Summary

| Account | Host | PRs | Repos |
|---------|------|-----|-------|
| {user} | github.com | {n} | {n} |
```

## Mermaid Chart Guidelines

- **Gantt charts**: Use for showing PR timelines across projects. Limit to top 15 PRs to keep readable.
- **Pie charts**: Use for PR/commit distribution across projects. Collapse projects with < 3% into "Other".
- **XY charts**: Use for daily/weekly commit activity. Aggregate by day of week for short periods, by week for 30+ day periods.
- **Flowcharts**: Use sparingly — only to illustrate architecture changes when a project had significant structural work.

Keep chart data realistic — pull actual counts from the gathered data. **Never fabricate chart values.** Every number must trace back to real API data. If you don't have data for a chart, omit the chart entirely rather than estimating.

## gh CLI Command Patterns

### Date calculation

```bash
# Linux
START_DATE=$(date -d "$DAYS days ago" +%Y-%m-%d)
END_DATE=$(date +%Y-%m-%d)

# macOS fallback
START_DATE=$(date -v-${DAYS}d +%Y-%m-%d)
```

### Multi-account iteration

```bash
# Parse accounts from gh auth status
ACCOUNTS=$(gh auth status 2>&1 | grep -oP '(?<=account )\S+' || \
           gh auth status 2>&1 | grep -oP '✓ Logged in to .+ account \K\S+')

# Save current account
ORIGINAL=$(gh auth status 2>&1 | grep '✓ Logged in' | head -1 | grep -oP 'account \K\S+')

# Iterate
for ACCT in $ACCOUNTS; do
    gh auth switch --user "$ACCT"
    # ... gather data ...
done

# Restore
gh auth switch --user "$ORIGINAL"
```

### Handling rate limits

If a `gh api` call returns HTTP 403 or 429, the response includes `Retry-After` or `X-RateLimit-Reset` headers. Wait the indicated time before retrying. For `gh search` commands, GitHub's search API has a 30 requests/minute limit — add brief sleeps between calls if processing many repos.

### Pagination

Always use `--paginate` with `gh api graphql` for large result sets. For REST endpoints, use `--paginate` with `gh api`.

For `gh search prs`, the `--limit` flag controls result count (max 1000).

## Infrastructure Setup

When the user accepts the automation offer, create the following:

### 1. Create the private repo

```bash
# Determine the user's public GitHub account
PUBLIC_ACCOUNT=$(gh auth status 2>&1 | grep 'github.com' | grep -v 'ghe' | head -1 | grep -oP 'account \K\S+')
gh auth switch --user "$PUBLIC_ACCOUNT"

REPO_NAME="gh-work-reports"
gh repo create "$REPO_NAME" --private --description "Automated GitHub activity reports" --clone
cd "$REPO_NAME"
```

### 2. Set up directory structure

```
gh-work-reports/
├── .github/
│   └── workflows/
│       ├── weekly-report.yml
│       └── monthly-report.yml
├── docs/
│   ├── index.html          # Pages aggregation site
│   ├── style.css
│   └── reports/             # Individual reports go here
│       └── .gitkeep
├── scripts/
│   └── generate-report.sh   # Report generation script
└── README.md
```

### 3. GitHub Actions workflows

Copy the workflow templates from `templates/weekly-report.yml`. The workflows need:

- `GH_TOKEN` secret with `repo` scope for both accounts (if applicable)
- Scheduled triggers (cron) and manual dispatch
- The report generation script produces the markdown and commits it to `docs/reports/`

### 4. GitHub Pages

Enable Pages from the repo settings pointing to `docs/` on the `main` branch. The `index.html` template auto-discovers reports by listing markdown files in `docs/reports/`.

### 5. Script: generate-report.sh

The generation script should:

```bash
#!/usr/bin/env bash
set -euo pipefail

DAYS="${1:-7}"
START_DATE=$(date -d "$DAYS days ago" +%Y-%m-%d)
END_DATE=$(date +%Y-%m-%d)
REPORT_FILE="docs/reports/report-${START_DATE}-to-${END_DATE}.md"

# Use gh CLI to gather data (same commands as the skill workflow)
# Write the markdown report to $REPORT_FILE
# Rebuild the index page
# Commit and push
```

For the full GitHub Actions workflow, Claude should read and adapt `templates/weekly-report.yml`.

## Report File Naming

Use `gh-work-report-{START_DATE}-to-{END_DATE}.md` for standalone reports and `report-{START_DATE}-to-{END_DATE}.md` inside the automation repo's `docs/reports/` directory.

## Privacy Considerations

- Default to including private repo names but NOT their descriptions or PR details
- If the user says the report is for sharing publicly, strip private repo details
- Never include tokens, secrets, or authentication details in reports
