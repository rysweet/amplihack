# Release Management Workflows

Advanced release management patterns using Azure DevOps CLI for version control, release automation, and deployment orchestration.

## Release Planning and Preparation

### Feature Freeze Workflow

```bash
#!/bin/bash
# Prepare repository for feature freeze before release

RELEASE_BRANCH="release/v2.0"
MAIN_BRANCH="main"
REPO="myrepo"

echo "Starting feature freeze workflow for $RELEASE_BRANCH..."

# 1. Create release branch
echo "Creating release branch from $MAIN_BRANCH..."
MAIN_SHA=$(az repos ref list \
  --repository "$REPO" \
  --filter "heads/$MAIN_BRANCH" \
  --query "[0].objectId" -o tsv)

az repos ref create \
  --name "refs/heads/$RELEASE_BRANCH" \
  --object-id "$MAIN_SHA" \
  --repository "$REPO"

# 2. Lock release branch (prevent direct commits)
echo "Locking release branch..."
az repos ref lock \
  --name "refs/heads/$RELEASE_BRANCH" \
  --repository "$REPO"

# 3. Create work item for release tracking
echo "Creating release tracking work item..."
az boards work-item create \
  --type "Epic" \
  --title "Release v2.0" \
  --assigned-to "release-manager@example.com" \
  --fields "System.Tags=release"

# 4. Query open PRs targeting main
echo "Checking for open PRs..."
OPEN_PRS=$(az repos pr list \
  --repository "$REPO" \
  --target-branch "$MAIN_BRANCH" \
  --status active \
  --query "length(@)")

echo "Open PRs targeting main: $OPEN_PRS"

if [ "$OPEN_PRS" -gt 0 ]; then
  echo "WARNING: There are $OPEN_PRS open PRs. Review before release."
  az repos pr list \
    --repository "$REPO" \
    --target-branch "$MAIN_BRANCH" \
    --status active \
    --output table
fi

echo "Feature freeze complete. Release branch: $RELEASE_BRANCH"
```

### Release Notes Generation

```bash
#!/bin/bash
# Generate release notes from commits and work items

REPO="myrepo"
PREVIOUS_TAG="v1.9.0"
CURRENT_TAG="v2.0.0"
RELEASE_NOTES_FILE="RELEASE_NOTES_${CURRENT_TAG}.md"

echo "Generating release notes: $PREVIOUS_TAG → $CURRENT_TAG"

# Get commit range
PREVIOUS_SHA=$(git rev-parse "$PREVIOUS_TAG")
CURRENT_SHA=$(git rev-parse "$CURRENT_TAG")

echo "# Release Notes: $CURRENT_TAG" > "$RELEASE_NOTES_FILE"
echo "" >> "$RELEASE_NOTES_FILE"
echo "Release Date: $(date +%Y-%m-%d)" >> "$RELEASE_NOTES_FILE"
echo "" >> "$RELEASE_NOTES_FILE"

# Get commits between tags
echo "## Changes" >> "$RELEASE_NOTES_FILE"
echo "" >> "$RELEASE_NOTES_FILE"
git log "$PREVIOUS_SHA..$CURRENT_SHA" --pretty=format:"- %s (%an)" >> "$RELEASE_NOTES_FILE"
echo "" >> "$RELEASE_NOTES_FILE"
echo "" >> "$RELEASE_NOTES_FILE"

# Extract work item IDs from commits
echo "## Work Items" >> "$RELEASE_NOTES_FILE"
echo "" >> "$RELEASE_NOTES_FILE"

git log "$PREVIOUS_SHA..$CURRENT_SHA" --pretty=format:"%s" | \
  grep -oP '#\K\d+' | sort -u | while read work_item_id; do
    TITLE=$(az boards work-item show --id "$work_item_id" --query "fields.'System.Title'" -o tsv 2>/dev/null)
    TYPE=$(az boards work-item show --id "$work_item_id" --query "fields.'System.WorkItemType'" -o tsv 2>/dev/null)

    if [ -n "$TITLE" ]; then
      echo "- **[$TYPE]** #$work_item_id: $TITLE" >> "$RELEASE_NOTES_FILE"
    fi
done

echo "" >> "$RELEASE_NOTES_FILE"
echo "## Contributors" >> "$RELEASE_NOTES_FILE"
echo "" >> "$RELEASE_NOTES_FILE"
git log "$PREVIOUS_SHA..$CURRENT_SHA" --pretty=format:"%an" | sort -u >> "$RELEASE_NOTES_FILE"

echo "Release notes generated: $RELEASE_NOTES_FILE"
cat "$RELEASE_NOTES_FILE"
```

## Version Management

### Semantic Version Bumping

```bash
#!/bin/bash
# Automated semantic version bumping

CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
BUMP_TYPE=${1:-patch}  # major, minor, patch

# Remove 'v' prefix if present
CURRENT_VERSION=${CURRENT_VERSION#v}

# Split version into components
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Bump version based on type
case $BUMP_TYPE in
  major)
    MAJOR=$((MAJOR + 1))
    MINOR=0
    PATCH=0
    ;;
  minor)
    MINOR=$((MINOR + 1))
    PATCH=0
    ;;
  patch)
    PATCH=$((PATCH + 1))
    ;;
  *)
    echo "Invalid bump type: $BUMP_TYPE (use: major, minor, patch)"
    exit 1
    ;;
esac

NEW_VERSION="v${MAJOR}.${MINOR}.${PATCH}"

echo "Current version: v$CURRENT_VERSION"
echo "Bump type: $BUMP_TYPE"
echo "New version: $NEW_VERSION"

# Create annotated tag
git tag -a "$NEW_VERSION" -m "Release $NEW_VERSION"

# Push tag
read -p "Push tag $NEW_VERSION to remote? (yes/no): " confirm
if [ "$confirm" == "yes" ]; then
  git push origin "$NEW_VERSION"
  echo "Tag $NEW_VERSION pushed to remote"
fi

echo "$NEW_VERSION"
```

### Multi-Repo Release Coordination

```bash
#!/bin/bash
# Coordinate releases across multiple repositories

declare -A REPOS=(
  ["api"]="api-service"
  ["frontend"]="web-app"
  ["backend"]="backend-service"
)

RELEASE_VERSION="v2.0.0"
PROJECT="MyProject"

echo "Coordinating release $RELEASE_VERSION across repositories..."

for key in "${!REPOS[@]}"; do
  repo="${REPOS[$key]}"
  echo "Processing $repo..."

  # Create release branch
  MAIN_SHA=$(az repos ref list \
    --repository "$repo" \
    --filter "heads/main" \
    --query "[0].objectId" -o tsv \
    --project "$PROJECT")

  az repos ref create \
    --name "refs/heads/release/$RELEASE_VERSION" \
    --object-id "$MAIN_SHA" \
    --repository "$repo" \
    --project "$PROJECT"

  echo "  Created release/$RELEASE_VERSION branch"

  # Create release work item
  az boards work-item create \
    --type "Task" \
    --title "Release $repo $RELEASE_VERSION" \
    --area "$PROJECT\\Release" \
    --fields "System.Tags=$RELEASE_VERSION,release" \
    --project "$PROJECT"

  echo "  Created tracking work item"
done

echo "Release coordination complete for $RELEASE_VERSION"
```

## Deployment Orchestration

### Multi-Stage Release Pipeline

```bash
#!/bin/bash
# Orchestrate multi-stage release deployment

RELEASE_PIPELINE="Multi-Stage-Release"
VERSION=$1

if [ -z "$VERSION" ]; then
  echo "Usage: $0 <version>"
  exit 1
fi

STAGES=("dev" "qa" "staging" "production")

echo "Starting multi-stage release for version $VERSION..."

for stage in "${STAGES[@]}"; do
  echo "============================================"
  echo "Deploying to: $stage"
  echo "============================================"

  # Run pipeline with stage-specific variables
  RUN_ID=$(az pipelines run \
    --name "$RELEASE_PIPELINE" \
    --variables Stage="$stage" Version="$VERSION" \
    --query "id" -o tsv)

  echo "Deployment started: Run $RUN_ID"

  # Monitor deployment
  while true; do
    STATUS=$(az pipelines runs show --id "$RUN_ID" --query "status" -o tsv)

    if [ "$STATUS" == "completed" ]; then
      RESULT=$(az pipelines runs show --id "$RUN_ID" --query "result" -o tsv)
      echo "Deployment result: $RESULT"

      if [ "$RESULT" != "succeeded" ]; then
        echo "Deployment to $stage failed! Stopping release."
        exit 1
      fi

      break
    fi

    sleep 15
  done

  # Stage-specific gates
  if [ "$stage" == "qa" ] || [ "$stage" == "staging" ]; then
    read -p "QA approval for $stage? (yes/no): " approval
    if [ "$approval" != "yes" ]; then
      echo "QA rejected deployment. Stopping release."
      exit 1
    fi
  fi

  if [ "$stage" == "production" ]; then
    read -p "FINAL APPROVAL for production? (yes/no): " approval
    if [ "$approval" != "yes" ]; then
      echo "Production deployment cancelled."
      exit 1
    fi
  fi

  echo "$stage deployment complete!"
  echo ""
done

echo "Multi-stage release complete for version $VERSION!"
```

### Phased Rollout Management

```bash
#!/bin/bash
# Manage phased rollout with monitoring

DEPLOY_PIPELINE="Phased-Deploy"
VERSION=$1
PHASES=(5 15 30 50 100)  # Percentage of users

if [ -z "$VERSION" ]; then
  echo "Usage: $0 <version>"
  exit 1
fi

echo "Starting phased rollout for version $VERSION..."

for phase in "${PHASES[@]}"; do
  echo "=========================================="
  echo "Phase: $phase% of users"
  echo "=========================================="

  # Deploy to percentage of users
  RUN_ID=$(az pipelines run \
    --name "$DEPLOY_PIPELINE" \
    --variables Version="$VERSION" RolloutPercentage="$phase" \
    --query "id" -o tsv)

  # Wait for deployment
  while true; do
    STATUS=$(az pipelines runs show --id "$RUN_ID" --query "status" -o tsv)
    if [ "$STATUS" == "completed" ]; then
      break
    fi
    sleep 10
  done

  RESULT=$(az pipelines runs show --id "$RUN_ID" --query "result" -o tsv)

  if [ "$RESULT" != "succeeded" ]; then
    echo "Deployment failed at $phase% phase!"
    echo "Rolling back..."
    # Rollback logic here
    exit 1
  fi

  echo "Phase $phase% deployed successfully"

  # Monitoring period (longer for early phases)
  if [ "$phase" -lt 50 ]; then
    MONITOR_TIME=1800  # 30 minutes
  else
    MONITOR_TIME=900   # 15 minutes
  fi

  echo "Monitoring for $((MONITOR_TIME / 60)) minutes..."

  # Simulate monitoring (replace with actual monitoring)
  sleep 10

  # Check for issues (error rate, latency, etc.)
  ISSUES_DETECTED=false

  if [ "$ISSUES_DETECTED" == "true" ]; then
    echo "Issues detected during monitoring!"
    echo "Rolling back version $VERSION..."
    # Rollback logic here
    exit 1
  fi

  echo "No issues detected, proceeding to next phase"
  echo ""
done

echo "Phased rollout complete! Version $VERSION at 100%"
```

## Rollback and Recovery

### Automated Rollback

```bash
#!/bin/bash
# Automated rollback to previous version

DEPLOY_PIPELINE="Deploy-Pipeline"
FEED="production-artifacts"
PACKAGE="myapp"

echo "Initiating rollback..."

# Get current version
CURRENT_VERSION=$(az artifacts universal list \
  --feed "$FEED" \
  --query "[?name=='$PACKAGE'] | [0].versions[0].version" -o tsv)

echo "Current version: $CURRENT_VERSION"

# Get previous version
PREVIOUS_VERSION=$(az artifacts universal list \
  --feed "$FEED" \
  --query "[?name=='$PACKAGE'] | [0].versions[1].version" -o tsv)

if [ -z "$PREVIOUS_VERSION" ]; then
  echo "No previous version found to rollback to!"
  exit 1
fi

echo "Rolling back to: $PREVIOUS_VERSION"

read -p "Confirm rollback to $PREVIOUS_VERSION? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
  echo "Rollback cancelled"
  exit 0
fi

# Deploy previous version
RUN_ID=$(az pipelines run \
  --name "$DEPLOY_PIPELINE" \
  --variables Version="$PREVIOUS_VERSION" IsRollback="true" \
  --query "id" -o tsv)

echo "Rollback deployment started: Run $RUN_ID"

# Monitor rollback
while true; do
  STATUS=$(az pipelines runs show --id "$RUN_ID" --query "status" -o tsv)
  if [ "$STATUS" == "completed" ]; then
    RESULT=$(az pipelines runs show --id "$RUN_ID" --query "result" -o tsv)
    echo "Rollback result: $RESULT"

    if [ "$RESULT" == "succeeded" ]; then
      echo "Rollback successful! Now running $PREVIOUS_VERSION"

      # Tag the run
      az pipelines runs tag add --run-id "$RUN_ID" --tags "rollback"

      # Create incident work item
      az boards work-item create \
        --type "Bug" \
        --title "Rollback: $CURRENT_VERSION → $PREVIOUS_VERSION" \
        --description "Automated rollback executed" \
        --fields "System.Tags=rollback,incident"

      exit 0
    else
      echo "Rollback failed!"
      exit 1
    fi
  fi
  sleep 10
done
```

### Emergency Hotfix Workflow

```bash
#!/bin/bash
# Emergency hotfix workflow

REPO="myrepo"
PRODUCTION_TAG="v2.0.5"
HOTFIX_BRANCH="hotfix/critical-bug"

echo "Starting emergency hotfix workflow..."

# 1. Create hotfix branch from production tag
echo "Creating hotfix branch from $PRODUCTION_TAG..."
TAG_SHA=$(git rev-parse "$PRODUCTION_TAG")

az repos ref create \
  --name "refs/heads/$HOTFIX_BRANCH" \
  --object-id "$TAG_SHA" \
  --repository "$REPO"

echo "Hotfix branch created: $HOTFIX_BRANCH"

# 2. Create PR for hotfix
echo "Create PR for your hotfix changes to $HOTFIX_BRANCH"
echo "When ready, the PR will be auto-deployed to production"

# 3. Monitor for merged PR
echo "Monitoring for merged hotfix PR..."

# (This would typically be triggered by a webhook or scheduled job)
# For demo purposes, we'll wait for user confirmation

read -p "Has the hotfix PR been merged? (yes/no): " merged

if [ "$merged" == "yes" ]; then
  # 4. Deploy hotfix immediately
  echo "Deploying hotfix..."

  # Bump patch version
  NEW_VERSION="v2.0.6"

  # Create tag
  git tag -a "$NEW_VERSION" -m "Hotfix: $NEW_VERSION"
  git push origin "$NEW_VERSION"

  # Deploy
  az pipelines run \
    --name "Hotfix-Deploy" \
    --variables Version="$NEW_VERSION" \
    --branch "$HOTFIX_BRANCH"

  echo "Hotfix deployed: $NEW_VERSION"

  # 5. Backport to main
  echo "Create PR to backport hotfix to main branch"

  az repos pr create \
    --repository "$REPO" \
    --source-branch "$HOTFIX_BRANCH" \
    --target-branch "main" \
    --title "Backport hotfix: $NEW_VERSION" \
    --description "Backporting emergency hotfix from production"
fi
```

## Release Validation

### Pre-Release Checklist Automation

```bash
#!/bin/bash
# Automated pre-release checklist validation

RELEASE_VERSION="v2.0.0"
REPO="myrepo"
PROJECT="MyProject"

echo "Pre-Release Checklist for $RELEASE_VERSION"
echo "==========================================="

PASS_COUNT=0
FAIL_COUNT=0

check_item() {
  local description=$1
  local command=$2

  echo -n "Checking: $description... "

  if eval "$command" > /dev/null 2>&1; then
    echo "✓ PASS"
    PASS_COUNT=$((PASS_COUNT + 1))
    return 0
  else
    echo "✗ FAIL"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return 1
  fi
}

# Checklist items
check_item "All PRs merged" \
  "[ $(az repos pr list --repository '$REPO' --target-branch main --status active --query 'length(@)' -o tsv) -eq 0 ]"

check_item "Latest build succeeded" \
  "[ $(az pipelines runs list --pipeline-ids $(az pipelines show --name 'Build-Pipeline' --query id -o tsv) --top 1 --query '[0].result' -o tsv) == 'succeeded' ]"

check_item "All tests passing" \
  "[ $(az pipelines runs list --pipeline-ids $(az pipelines show --name 'Test-Pipeline' --query id -o tsv) --top 1 --query '[0].result' -o tsv) == 'succeeded' ]"

check_item "No critical bugs open" \
  "[ $(az boards query --wiql \"SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = 'Bug' AND [System.State] = 'Active' AND [System.Priority] = 1\" --query 'length(@)' -o tsv) -eq 0 ]"

check_item "Release notes generated" \
  "[ -f 'RELEASE_NOTES_${RELEASE_VERSION}.md' ]"

check_item "Security scan completed" \
  "[ $(az pipelines runs list --pipeline-ids $(az pipelines show --name 'Security-Scan' --query id -o tsv) --top 1 --query '[0].result' -o tsv) == 'succeeded' ]"

echo ""
echo "==========================================="
echo "Results: $PASS_COUNT passed, $FAIL_COUNT failed"

if [ "$FAIL_COUNT" -eq 0 ]; then
  echo "✓ All checks passed! Ready for release."
  exit 0
else
  echo "✗ Some checks failed. Fix issues before release."
  exit 1
fi
```

## Best Practices

1. **Release Branches**: Create dedicated branches for each release
2. **Semantic Versioning**: Follow semver (MAJOR.MINOR.PATCH) strictly
3. **Release Notes**: Auto-generate from commits and work items
4. **Approval Gates**: Require manual approval for production
5. **Phased Rollouts**: Gradually increase traffic to new version
6. **Monitoring**: Watch metrics closely during rollout
7. **Rollback Plan**: Always have a tested rollback procedure
8. **Hotfix Process**: Maintain fast-track process for critical issues
9. **Changelog**: Keep detailed changelog for audit trail
10. **Communication**: Notify stakeholders at each stage

## References

- [Release Strategies](https://learn.microsoft.com/en-us/azure/devops/pipelines/release/)
- [Semantic Versioning](https://semver.org/)
- [Deployment Patterns](https://learn.microsoft.com/en-us/azure/devops/pipelines/release/deployment-strategies)
