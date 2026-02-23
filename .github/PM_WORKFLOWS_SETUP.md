# PM Architect GitHub Actions Workflows - Setup Guide

This document explains how to configure and use the PM Architect GitHub Actions workflows for automated project management reporting.

## Overview

Three informational workflows are provided:

1. **Daily Status Report** (`pm-daily-status.yml`) - Runs daily at 9 AM UTC
2. **PR Triage** (`pm-pr-triage.yml`) - Triggers on PR opened events
3. **Weekly Roadmap Review** (`pm-roadmap-review.yml`) - Runs weekly on Monday at 8 AM UTC

**Security**: All workflows implement the 9 mandatory security mitigations from `Specs/PM_Architect_GitHub_Actions_SECURITY_ASSESSMENT.md`.

**Type**: Informational only - these workflows are read-only and do not modify repository state.

## Prerequisites

- Repository with PM Architect implementation
- GitHub repository with Actions enabled
- Anthropic API key for PM Architect
- Admin access to configure GitHub Secrets and Variables

## Configuration

### Step 1: Configure GitHub Secrets

Navigate to **Repository Settings → Secrets and variables → Actions → Secrets**

Add the following secret:

```
Name: ANTHROPIC_API_KEY
Value: [Your Anthropic API key]
```

**Security Notes**:

- Never commit API keys to the repository
- The workflows mask this key in logs using `::add-mask::`
- Key is scoped to workflow steps only
- Consider using environment-based scoping for additional isolation

**Where to find your API key**:

- Console: https://console.anthropic.com/settings/keys
- Local file: `~/.claude-msec-k` (if using amplihack CLI)

### Step 2: Configure GitHub Variables

Navigate to **Repository Settings → Secrets and variables → Actions → Variables**

Add the following variables:

```
Name: PM_STATUS_ISSUE_NUMBER
Value: [Issue number for daily status reports, e.g., 1509]

Name: PM_ROADMAP_ISSUE_NUMBER
Value: [Issue number for roadmap reviews, e.g., 1510]
```

**Note**: You must create these tracking issues first before setting the variables.

### Step 3: Create Tracking Issues

Create designated issues for workflow outputs:

```bash
# Create daily status tracking issue
gh issue create --title "PM Daily Status Reports" \
  --body "This issue tracks automated daily status reports from PM Architect." \
  --label "pm-automation"

# Create roadmap review tracking issue
gh issue create --title "PM Weekly Roadmap Reviews" \
  --body "This issue tracks automated weekly roadmap reviews from PM Architect." \
  --label "pm-automation"
```

Record the issue numbers and use them in Step 2 above.

## Testing Workflows

### Manual Trigger

Test workflows manually before relying on scheduled execution:

```bash
# Trigger daily status workflow
gh workflow run pm-daily-status.yml

# Trigger roadmap review workflow
gh workflow run pm-roadmap-review.yml

# PR triage workflow triggers automatically on PR creation
```

### Verify Configuration

1. Navigate to **Actions** tab in GitHub
2. Select the workflow you triggered
3. Check that it runs successfully
4. Verify output is posted to the designated issue
5. Check logs for any errors (API key should be masked as `***`)

## Security Mitigations

All workflows implement these security measures (reference: `Specs/PM_Architect_GitHub_Actions_SECURITY_ASSESSMENT.md`):

### M1.2: API Key Masking

```yaml
- name: Mask API key
  run: echo "::add-mask::${{ secrets.ANTHROPIC_API_KEY }}"
```

Prevents API key exposure in workflow logs.

### M2.1: Minimal Permissions

```yaml
# Base permissions (all PM workflows)
permissions:
  contents: read # Read repository contents only
  issues: write # Post reports to designated issue

  # Additional permissions (workflows using gh CLI for PR data)
  pull-requests: read # Required by gh pr list / gh api for PR metrics
```

Each workflow requests only the permissions it needs. Workflows that query PR data via `gh` CLI (daily status, roadmap review, PR triage) include `pull-requests: read`. Follows principle of least privilege.

### M2.2: GitHub Token Authentication for gh CLI

Workflows that use the `gh` CLI (for querying PRs, milestones, or the GitHub API) must pass `GH_TOKEN` as an environment variable:

```yaml
env:
  GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

`GITHUB_TOKEN` is auto-provisioned by GitHub Actions (short-lived, auto-rotated, scoped to the repository). No manual secret configuration is needed. Without `GH_TOKEN`, `gh` CLI commands fail with **exit code 4** (authentication error).

**Affected workflows**: `pm-daily-status.yml`, `pm-roadmap-review.yml`, `pm-pr-triage.yml`

### M3.2: Safe Command Construction

```yaml
env:
  ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  ISSUE_NUMBER: ${{ vars.PM_STATUS_ISSUE_NUMBER }}
  GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
run: |
  # Use environment variables, never string interpolation
```

Prevents command injection attacks.

### Timeout Limits

```yaml
timeout-minutes: 10
```

Prevents runaway execution.

### Error Handling

```yaml
- name: Handle errors
  if: failure()
  run: |
    echo "::error::Workflow failed. Check logs for details."
```

Fails gracefully without exposing secrets.

### Input Validation (M3.1, M3.4)

PM Architect scripts **must** sanitize user inputs and validate for prompt injection. Workflows document this requirement in comments.

## Workflow Details

### Daily Status Report

**Trigger**: Daily at 9 AM UTC + manual dispatch
**Purpose**: Generate comprehensive project status report
**Output**: Comment on tracking issue (PM_STATUS_ISSUE_NUMBER)

**Generated Report Includes**:

- Active workstreams status
- Blocked items
- Backlog summary
- Project health score
- Recommendations

### PR Triage

**Trigger**: Pull request opened event
**Purpose**: Analyze PRs for priority and complexity
**Output**: Comment on the PR itself

**Generated Analysis Includes**:

- Priority assessment
- Complexity estimation
- Suggested reviewer
- Estimated review time
- Changes overview

### Weekly Roadmap Review

**Trigger**: Weekly on Monday 8 AM UTC + manual dispatch
**Purpose**: Review roadmap alignment and goal progress
**Output**: Comment on tracking issue (PM_ROADMAP_ISSUE_NUMBER)

**Permissions**: `contents: read`, `issues: write`, `pull-requests: read`

**Environment Variables**:

- `ANTHROPIC_API_KEY` - Claude API key for analysis
- `ISSUE_NUMBER` - Target tracking issue
- `GH_TOKEN` - GitHub token for `gh pr list` and `gh api` calls (velocity metrics, milestone progress)

**Generated Review Includes**:

- Executive summary
- Goal progress tracking
- Velocity and capacity analysis (commits, PRs merged via `gh` CLI)
- Milestone progress (via `gh api`)
- Roadmap alignment assessment
- Strategic risks and opportunities
- Recommendations for next week

## Troubleshooting

### Workflow Fails with "API key not found"

**Solution**: Verify `ANTHROPIC_API_KEY` secret is configured in repository settings.

### Issue comment not posted

**Solution**: Verify tracking issue numbers are correct in Variables and issues exist.

### Workflow doesn't trigger on schedule

**Causes**:

- Repository has been inactive for 60+ days (GitHub disables scheduled workflows)
- GitHub Actions experiencing delays (check status.github.com)

**Solution**: Trigger manually via `workflow_dispatch` to keep workflows active.

### gh CLI fails with exit code 4

**Cause**: `GH_TOKEN` environment variable is not set in the workflow step, or the workflow is missing `pull-requests: read` permission.

**Solution**:

1. Add `GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}` to the `env:` block of the step that runs `gh` commands
2. Add `pull-requests: read` to the workflow's `permissions:` block
3. No manual secret setup is needed - `GITHUB_TOKEN` is auto-provisioned by GitHub Actions

**Example fix**:

```yaml
permissions:
  contents: read
  issues: write
  pull-requests: read # Required for gh pr list / gh api

steps:
  - name: Review roadmap
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }} # Required for gh CLI auth
    run: python .github/scripts/pm_roadmap_review.py
```

### "Permission denied" errors

**Solution**: Verify workflow has correct permissions. Should have `contents: read` + `issues: write` or `pull-requests: write`. Workflows using `gh` CLI for PR queries also need `pull-requests: read`.

## Disabling Workflows

To temporarily disable workflows:

1. Navigate to **Actions** tab
2. Select the workflow
3. Click **...** (more options)
4. Select **Disable workflow**

Or via CLI:

```bash
gh workflow disable pm-daily-status.yml
gh workflow disable pm-pr-triage.yml
gh workflow disable pm-roadmap-review.yml
```

## Advanced Configuration

### Environment-Based Secret Scoping

For additional security, scope secrets to specific environments:

1. Create environment: **Settings → Environments → New environment**
   - Name: `pm-automation`
   - Add `ANTHROPIC_API_KEY` secret to this environment
   - Optionally require reviewers for deployments

2. Update workflows to use environment:

```yaml
jobs:
  daily-status:
    environment: pm-automation # Add this line
    runs-on: ubuntu-latest
```

### Custom Schedules

Modify cron schedules in workflow files:

```yaml
on:
  schedule:
    - cron: "0 9 * * *" # Daily at 9 AM UTC
    # Change to your preferred time
```

**Cron Format**: `minute hour day-of-month month day-of-week`

Examples:

- Every 6 hours: `0 */6 * * *`
- Twice daily (9 AM, 5 PM UTC): `0 9,17 * * *`
- Weekdays only at 9 AM: `0 9 * * 1-5`

## References

- **Architecture Specification**: `Specs/PM_Architect_GitHub_Actions_Automation.md`
- **Security Assessment**: `Specs/PM_Architect_GitHub_Actions_SECURITY_ASSESSMENT.md`
- **GitHub Actions Documentation**: https://docs.github.com/en/actions
- **Anthropic API Documentation**: https://docs.anthropic.com/

## Support

For issues or questions:

1. Check workflow logs in Actions tab
2. Review this setup guide
3. Consult security assessment for security-related questions
4. Open an issue with `pm-automation` label

---

**Last Updated**: 2026-02-23
**Version**: 1.1.0
**Status**: Production (gh CLI authentication fix applied to all PM workflows)
