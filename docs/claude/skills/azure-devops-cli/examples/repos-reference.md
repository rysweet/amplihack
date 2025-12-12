# Azure Repos Complete Command Reference

Complete reference for `az repos` command group covering Git repositories, pull requests, policies, and branch management.

## Repository Management

### List Repositories

```bash
# List all repositories
az repos list --project MyProject

# List as table
az repos list --output table

# Get repository details as JSON
az repos list --output json > repositories.json

# Filter by name
az repos list --query "[?contains(name, 'API')]" --output table
```

### Show Repository

```bash
# Show repository by name
az repos show --repository myrepo --project MyProject

# Show repository by ID
az repos show --repository REPO_ID

# Open repository in browser
az repos show --repository myrepo --open
```

### Create Repository

```bash
# Create repository
az repos create --name "newrepo" --project MyProject

# Create with initialization
az repos create --name "api-service" --project MyProject

# Create from template (requires API call)
az devops invoke --area git --resource repositories \
  --route-parameters project=MyProject \
  --http-method POST \
  --in-file repo-config.json
```

### Delete Repository

```bash
# Delete repository
az repos delete --id REPO_ID --yes

# Delete by name
az repos delete --name "oldrepo" --project MyProject --yes
```

### Update Repository

```bash
# Rename repository
az repos update --repository myrepo --name "newname" --project MyProject

# Update default branch
az repos update --repository myrepo --default-branch main
```

## Pull Requests

### List Pull Requests

```bash
# List all active pull requests
az repos pr list --repository myrepo --status active

# List all PRs (including completed)
az repos pr list --repository myrepo --status all

# List PRs created by me
az repos pr list --creator me@example.com

# List PRs assigned to me as reviewer
az repos pr list --reviewer me@example.com

# List PRs targeting specific branch
az repos pr list --target-branch main

# List PRs from source branch
az repos pr list --source-branch feature/new-feature

# List as table
az repos pr list --status active --output table

# Top N PRs
az repos pr list --top 10
```

### Show Pull Request

```bash
# Show PR by ID
az repos pr show --id 123

# Show PR and open in browser
az repos pr show --id 123 --open

# Get PR as JSON
az repos pr show --id 123 --output json
```

### Create Pull Request

```bash
# Create PR from current branch
az repos pr create --repository myrepo \
  --source-branch feature/new-feature \
  --target-branch main \
  --title "Add new feature" \
  --description "This PR adds the new feature"

# Create PR with reviewers
az repos pr create --repository myrepo \
  --source-branch feature/api \
  --target-branch main \
  --title "API updates" \
  --reviewers reviewer1@example.com reviewer2@example.com

# Create PR with work items linked
az repos pr create --repository myrepo \
  --source-branch bugfix/issue-123 \
  --target-branch main \
  --title "Fix bug #123" \
  --work-items 123 456

# Create PR and auto-complete
az repos pr create --repository myrepo \
  --source-branch feature/auto \
  --target-branch main \
  --title "Auto-merge feature" \
  --auto-complete true \
  --delete-source-branch true

# Create PR and open in browser
az repos pr create --repository myrepo \
  --source-branch feature/new \
  --target-branch main \
  --title "New feature" \
  --open
```

### Update Pull Request

```bash
# Update PR title
az repos pr update --id 123 --title "Updated title"

# Update PR description
az repos pr update --id 123 --description "Updated description"

# Update PR status
az repos pr update --id 123 --status completed

# Abandon PR
az repos pr update --id 123 --status abandoned

# Reactivate PR
az repos pr update --id 123 --status active

# Set auto-complete
az repos pr update --id 123 --auto-complete true

# Update draft status
az repos pr update --id 123 --draft false
```

### Pull Request Reviewers

```bash
# Add reviewers
az repos pr reviewer add --id 123 --reviewers dev1@example.com dev2@example.com

# List reviewers
az repos pr reviewer list --id 123

# Remove reviewer
az repos pr reviewer remove --id 123 --reviewers dev1@example.com
```

### Pull Request Work Items

```bash
# Add work items to PR
az repos pr work-item add --id 123 --work-items 456 789

# List work items linked to PR
az repos pr work-item list --id 123

# Remove work item from PR
az repos pr work-item remove --id 123 --work-items 456
```

### Set Pull Request Vote

```bash
# Approve PR
az repos pr set-vote --id 123 --vote approve

# Approve with suggestions
az repos pr set-vote --id 123 --vote approve-with-suggestions

# Wait for author
az repos pr set-vote --id 123 --vote wait-for-author

# Reject PR
az repos pr set-vote --id 123 --vote reject

# Reset vote
az repos pr set-vote --id 123 --vote reset
```

## Pull Request Policies

### List Policies

```bash
# List all policies for repository
az repos policy list --repository-id REPO_ID --project MyProject

# List policies for specific branch
az repos policy list --branch main --repository-id REPO_ID
```

### Approver Count Policy

```bash
# Create minimum approver count policy
az repos policy approver-count create \
  --allow-downvotes false \
  --blocking true \
  --enabled true \
  --minimum-approver-count 2 \
  --creator-vote-counts false \
  --repository-id REPO_ID \
  --branch main

# Update approver count policy
az repos policy approver-count update \
  --id POLICY_ID \
  --minimum-approver-count 3

# Show approver count policy
az repos policy approver-count show --id POLICY_ID
```

### Build Policy

```bash
# Create build validation policy
az repos policy build create \
  --blocking true \
  --enabled true \
  --build-definition-id BUILD_ID \
  --display-name "CI Build" \
  --manual-queue-only false \
  --queue-on-source-update-only true \
  --repository-id REPO_ID \
  --branch main

# Update build policy
az repos policy build update \
  --id POLICY_ID \
  --blocking true

# Show build policy
az repos policy build show --id POLICY_ID
```

### Comment Resolution Policy

```bash
# Create comment resolution policy
az repos policy comment-required create \
  --blocking true \
  --enabled true \
  --repository-id REPO_ID \
  --branch main

# Update comment required policy
az repos policy comment-required update \
  --id POLICY_ID \
  --enabled false
```

### File Size Policy

```bash
# Create file size policy
az repos policy file-size create \
  --blocking true \
  --enabled true \
  --maximum-git-blob-size 10 \
  --repository-id REPO_ID \
  --use-uncompressed-size true

# Update file size policy
az repos policy file-size update \
  --id POLICY_ID \
  --maximum-git-blob-size 5
```

### Work Item Linking Policy

```bash
# Create work item linking policy
az repos policy work-item-linking create \
  --blocking true \
  --enabled true \
  --repository-id REPO_ID \
  --branch main

# Update work item linking policy
az repos policy work-item-linking update \
  --id POLICY_ID \
  --enabled false
```

## Branches

### List Branches

```bash
# List all branches
az repos ref list --repository myrepo --project MyProject

# Filter branches only
az repos ref list --repository myrepo --filter heads

# List tags only
az repos ref list --repository myrepo --filter tags
```

### Create Branch

```bash
# Create branch
az repos ref create \
  --name refs/heads/feature/new \
  --object-id COMMIT_SHA \
  --repository myrepo

# Create branch from main
MAIN_SHA=$(az repos ref list --repository myrepo --filter heads/main --query "[0].objectId" -o tsv)
az repos ref create \
  --name refs/heads/feature/branch \
  --object-id "$MAIN_SHA" \
  --repository myrepo
```

### Delete Branch

```bash
# Delete branch
az repos ref delete \
  --name refs/heads/old-feature \
  --object-id COMMIT_SHA \
  --repository myrepo
```

### Lock/Unlock Branch

```bash
# Lock branch
az repos ref lock \
  --name refs/heads/main \
  --repository myrepo

# Unlock branch
az repos ref unlock \
  --name refs/heads/main \
  --repository myrepo
```

## Imports

### Import Repository

```bash
# Import from Git URL
az repos import create \
  --git-url https://github.com/username/repo.git \
  --repository myrepo \
  --project MyProject

# Import with authentication
az repos import create \
  --git-url https://github.com/username/private-repo.git \
  --repository myrepo \
  --user-name username \
  --git-service-endpoint-id SERVICE_ID
```

## Scripting Examples

### Batch PR Creation

```bash
#!/bin/bash
az repos ref list --repository myrepo --filter heads --query "[?contains(name, 'feature/')].name" -o tsv | while read branch; do
  az repos pr create --repository myrepo --source-branch "${branch#refs/heads/}" --target-branch main --title "Auto PR: ${branch#refs/heads/}"
done
```

### PR Status Dashboard

```bash
#!/bin/bash
echo "Pull Request Dashboard"
az repos pr list --repository myrepo --status active --output table
az repos pr list --repository myrepo --status active --query "[?reviewers[?vote==0]].{ID:pullRequestId, Title:title}" --output table
az repos pr list --repository myrepo --status active --query "[?reviewers[?vote==10]].{ID:pullRequestId, Title:title}" --output table
```

### Auto-Approve Automated PRs

```bash
#!/bin/bash
az repos pr list --repository myrepo --creator "automation@example.com" --status active --query "[].pullRequestId" -o tsv | while read pr_id; do
  az repos pr set-vote --id "$pr_id" --vote approve
done
```

### Clone All Repositories

```bash
#!/bin/bash
# Clone all repositories from project

OUTPUT_DIR="./repos"
mkdir -p "$OUTPUT_DIR"

az repos list --project MyProject --query "[].{Name:name, URL:remoteUrl}" -o tsv | while IFS=$'\t' read -r name url; do
  echo "Cloning $name..."
  git clone "$url" "$OUTPUT_DIR/$name"
done
```

### PR Merge Automation

```bash
#!/bin/bash
# Merge approved PRs automatically

az repos pr list --repository myrepo --status active --output json | jq -r '.[] | select(.reviewers | all(.vote == 10)) | .pullRequestId' | while read pr_id; do
  echo "Merging approved PR $pr_id"
  az repos pr update --id "$pr_id" --status completed --delete-source-branch true
done
```

### Branch Cleanup

```bash
#!/bin/bash
# Delete merged feature branches

# Get merged branches
git branch -r --merged origin/main | grep 'origin/feature/' | sed 's|origin/||' | while read branch; do
  echo "Deleting merged branch: $branch"
  COMMIT_SHA=$(az repos ref list --repository myrepo --filter "heads/$branch" --query "[0].objectId" -o tsv)
  az repos ref delete --name "refs/heads/$branch" --object-id "$COMMIT_SHA" --repository myrepo
done
```

### PR Quality Check

```bash
#!/bin/bash
# Check PR quality before approval

PR_ID=$1

echo "Checking PR $PR_ID..."

# Check for work items
WI_COUNT=$(az repos pr work-item list --id "$PR_ID" --output json | jq 'length')
if [ "$WI_COUNT" -eq 0 ]; then
  echo "WARNING: No work items linked"
fi

# Check for description
DESC=$(az repos pr show --id "$PR_ID" --query "description" -o tsv)
if [ -z "$DESC" ]; then
  echo "WARNING: No description"
fi

# Check for reviewers
REVIEWER_COUNT=$(az repos pr reviewer list --id "$PR_ID" --output json | jq 'length')
if [ "$REVIEWER_COUNT" -lt 2 ]; then
  echo "WARNING: Less than 2 reviewers"
fi

# Check build status (if applicable)
echo "Build status check would go here"
```

## Best Practices

- PR templates in `.azuredevops/pull_request_template.md`
- Link work items for traceability
- Branch policies enforce quality
- Auto-complete with caution
- Delete source branches after merge
- Review all changes
- Draft PRs for WIP
- Tag relevant reviewers

## Advanced Patterns

### Custom PR Workflow

```bash
#!/bin/bash
# Custom PR creation with validation

SOURCE_BRANCH=$(git branch --show-current)
TARGET_BRANCH="main"

# Check if branch follows naming convention
if [[ ! "$SOURCE_BRANCH" =~ ^(feature|bugfix|hotfix)/ ]]; then
  echo "Error: Branch must start with feature/, bugfix/, or hotfix/"
  exit 1
fi

# Extract work item from branch name (e.g., feature/123-description)
WORK_ITEM=$(echo "$SOURCE_BRANCH" | grep -oP '\d+' | head -1)

if [ -z "$WORK_ITEM" ]; then
  echo "Error: Branch name must include work item number"
  exit 1
fi

# Create PR with work item linked
az repos pr create \
  --repository myrepo \
  --source-branch "$SOURCE_BRANCH" \
  --target-branch "$TARGET_BRANCH" \
  --title "$(git log -1 --pretty=%B)" \
  --work-items "$WORK_ITEM" \
  --open
```

### Repository Sync

```bash
#!/bin/bash
# Sync repository state across organizations

SOURCE_ORG="https://dev.azure.com/source-org"
TARGET_ORG="https://dev.azure.com/target-org"
PROJECT="MyProject"
REPO="myrepo"

# Get source repo info
az devops configure --defaults organization="$SOURCE_ORG" project="$PROJECT"
SOURCE_POLICIES=$(az repos policy list --repository-id REPO_ID --output json)

# Create policies in target
az devops configure --defaults organization="$TARGET_ORG" project="$PROJECT"
echo "$SOURCE_POLICIES" | jq -c '.[]' | while read policy; do
  # Parse and recreate policy
  echo "Creating policy: $(echo $policy | jq -r '.type.displayName')"
done
```

## Troubleshooting

**PR creation fails**: Verify branch with `az repos ref list`, check conflicts, verify permissions

**Policy issues**: Check with `az repos pr show --id 123 --query "mergeStatus"`

**Reference errors**: Use fully qualified refs `refs/heads/branch-name`, not `branch-name`

## References

- [Azure Repos CLI Reference](https://learn.microsoft.com/en-us/cli/azure/repos)
- [Pull Request Documentation](https://learn.microsoft.com/en-us/azure/devops/repos/git/pull-requests)
- [Branch Policies](https://learn.microsoft.com/en-us/azure/devops/repos/git/branch-policies)
