---
name: github-branch-protection
version: 2.0.0
description: Configure server-side GitHub branch protection rules (Layer 3 of defense-in-depth)
auto_activate_keywords:
  - branch protection
  - github protection
  - protect branch
  - require pull request
  - branch protection rules
  - protect main
  - require reviews
  - status checks
  - prevent force push
tags:
  - github
  - security
  - branch-protection
  - ci-cd
  - git
authors:
  - amplihack
last_updated: 2026-02-12
---

# GitHub Branch Protection

## Overview

Configure **server-side GitHub branch protection** to prevent direct commits to protected branches. This is Layer 3 of amplihack's defense-in-depth strategy—the only layer that cannot be bypassed.

**Three layers of protection:**
1. **Client-side hook** - Fast local check (bypassable with `--no-verify`)
2. **Agent-side hook** - Prevents AI agents from using `--no-verify`
3. **Server-side rules** (this skill) - **Enforced by GitHub, cannot be bypassed**

## Quick Start

```bash
# Verify you have admin access
gh auth status && gh api repos/{owner}/{repo} | jq '.permissions.admin'

# Apply standard protection to main branch
gh api PUT repos/{owner}/{repo}/branches/main/protection \
  --input <(echo '{
    "required_pull_request_reviews": {"required_approving_review_count": 1},
    "required_status_checks": {"strict": false, "contexts": ["CI / Validate Code"]},
    "enforce_admins": false,
    "allow_force_pushes": false,
    "allow_deletions": false
  }')
```

Replace `{owner}/{repo}` with your repository (e.g., `rysweet/amplihack`).

## Core Settings

- **Require PR + Reviews**: Force pull request workflow with approvals
- **Require Status Checks**: Enforce CI passing before merge
- **Prevent Force Push/Deletion**: Protect history and branch existence
- **Enforce Admins**: Optional - apply rules to admins (use cautiously, may lock out during emergencies)

## Two Methods Available

1. **GitHub CLI** (`gh`) - Fast, scriptable, version-controllable
2. **GitHub Web UI** - Visual, discoverable, no CLI needed

See detailed walkthroughs in [reference/](reference/) directory.

## Prerequisites

- GitHub CLI authenticated (`gh auth login`)
- Admin permissions on target repository
- CI workflows configured and run at least once
- Know your CI check names (run `gh pr checks <PR_NUMBER>` on recent PR)

## Working Example

See [examples/amplihack-config.md](examples/amplihack-config.md) for the complete amplihack repository configuration with actual commands and output.

## Reference Documentation

### This Repository
- **CLI Method**: [reference/cli-walkthrough.md](reference/cli-walkthrough.md) - Step-by-step `gh` commands
- **UI Method**: [reference/ui-walkthrough.md](reference/ui-walkthrough.md) - GitHub web interface guide
- **Settings Deep Dive**: [reference/settings-reference.md](reference/settings-reference.md) - All options explained with trade-offs
- **Troubleshooting**: [reference/troubleshooting.md](reference/troubleshooting.md) - Common errors and solutions
- **Maintenance Guide**: [reference/maintenance.md](reference/maintenance.md) - How to update this skill

### Official GitHub Documentation
- [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Managing branch protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)
- [REST API: Branch protection](https://docs.github.com/en/rest/branches/branch-protection)

## Emergency Procedures

**To disable protection** (e.g., during CI failures blocking critical hotfix):

```bash
gh api -X DELETE repos/{owner}/{repo}/branches/main/protection
```

Document reason and re-enable after emergency resolved.

---

**Next Steps:** Choose your method and follow the appropriate walkthrough in the reference directory.
