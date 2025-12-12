# Repository Operations Guide

Guide for working with Azure DevOps repositories using CLI tools.

## Listing Repositories

### Basic List

```bash
python .claude/scenarios/az-devops-tools/list_repos.py
```

### With Details

```bash
python .claude/scenarios/az-devops-tools/list_repos.py --include-details
```

This shows:
- Repository size
- Default branch
- Web URLs
- Clone URLs (HTTP/SSH)

### JSON Output

```bash
python .claude/scenarios/az-devops-tools/list_repos.py --format json
```

## Creating Pull Requests

### Basic PR

```bash
python .claude/scenarios/az-devops-tools/create_pr.py \
  --source feature/auth \
  --target main \
  --title "Add authentication"
```

### PR with Description from File

```bash
python .claude/scenarios/az-devops-tools/create_pr.py \
  --source feature/auth \
  --target main \
  --title "Add authentication" \
  --description @pr_description.md
```

### PR with Reviewers and Work Items

```bash
python .claude/scenarios/az-devops-tools/create_pr.py \
  --source feature/bug-fix \
  --target main \
  --title "Fix critical bug" \
  --reviewers "user1@domain.com,user2@domain.com" \
  --work-items "12345,12346"
```

### Draft PR

```bash
python .claude/scenarios/az-devops-tools/create_pr.py \
  --source feature/wip \
  --target main \
  --title "WIP: New feature" \
  --draft
```

### PR with Auto-Complete

```bash
python .claude/scenarios/az-devops-tools/create_pr.py \
  --source feature/done \
  --target main \
  --title "Complete feature" \
  --auto-complete \
  --delete-source-branch
```

## Common Workflows

### Feature Branch to Main

```bash
# Create feature branch (outside tool)
git checkout -b feature/new-feature main

# ... make changes, commit ...

# Push branch
git push -u origin feature/new-feature

# Create PR
python .claude/scenarios/az-devops-tools/create_pr.py \
  --source feature/new-feature \
  --target main \
  --title "Add new feature" \
  --description @feature_desc.md \
  --reviewers "team@domain.com"
```

### Bug Fix with Work Item Link

```bash
# Create bug fix branch
git checkout -b bugfix/issue-123 main

# ... fix bug, commit ...

# Push and create PR
git push -u origin bugfix/issue-123

python .claude/scenarios/az-devops-tools/create_pr.py \
  --source bugfix/issue-123 \
  --target main \
  --title "Fix: Issue #123 login button" \
  --work-items "123"
```

## Clone URLs

Repositories have two clone URL formats:

### HTTPS (Recommended)
```
https://dev.azure.com/ORG/PROJECT/_git/REPO
```

Best for most scenarios. Uses Azure DevOps credentials or PAT tokens.

### SSH
```
git@ssh.dev.azure.com:v3/ORG/PROJECT/REPO
```

Requires SSH key setup. Better for automation.

## Branch Management

### Branch Naming Conventions

Common patterns:
- `feature/feature-name` - New features
- `bugfix/issue-number` - Bug fixes
- `hotfix/critical-issue` - Production hotfixes
- `release/version` - Release branches

### Protected Branches

Main/master branches typically have policies:
- Require pull request reviews
- Require build validation
- Require work item linking

Use `create_pr.py` to work with protected branches.

## Repository Permissions

Common permission levels:
- **Reader** - Clone, pull, view code
- **Contributor** - Clone, pull, push, create branches
- **Project Administrator** - All permissions

## Tips and Best Practices

1. **Use feature branches** - Never commit directly to main
2. **Link work items** - Connect PRs to work items for traceability
3. **Write good PR titles** - Clear, concise description of changes
4. **Add reviewers early** - Get feedback during development
5. **Use draft PRs** - For work-in-progress that needs visibility

## Troubleshooting

### "Branch does not exist"

Verify branch exists:
```bash
git branch -a | grep branch-name
```

Push if local only:
```bash
git push -u origin branch-name
```

### "Pull request already exists"

Check existing PRs for these branches:
```bash
az repos pr list --source-branch feature/branch-name
```

### "Permission denied"

Verify you have Contributor access to the repository.

## See Also

- [Azure DevOps Repos](https://learn.microsoft.com/en-us/azure/devops/repos/)
- [Pull Request Overview](https://learn.microsoft.com/en-us/azure/devops/repos/git/pull-requests)
- [@work-items.md] - Link work items to PRs
