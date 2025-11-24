# CI/CD Automation Workflows

Advanced CI/CD automation patterns using Azure DevOps CLI for build, test, and deployment workflows.

## Complete CI/CD Pipeline Automation

### End-to-End Pipeline Setup

```bash
#!/bin/bash
# Complete CI/CD pipeline setup for new project

PROJECT="MyProject"
REPO="myrepo"
PIPELINE_NAME="CI-CD-Pipeline"

# 1. Create repository
echo "Creating repository..."
az repos create --name "$REPO" --project "$PROJECT"

# 2. Create build pipeline from YAML
echo "Creating build pipeline..."
az pipelines create \
  --name "$PIPELINE_NAME" \
  --repository "$REPO" \
  --branch main \
  --yml-path azure-pipelines.yml \
  --project "$PROJECT"

# 3. Set up pipeline variables
echo "Configuring pipeline variables..."
az pipelines variable create \
  --name "BuildConfiguration" \
  --value "Release" \
  --pipeline-name "$PIPELINE_NAME"

az pipelines variable create \
  --name "Environment" \
  --value "Production" \
  --pipeline-name "$PIPELINE_NAME"

# 4. Create variable group for secrets
echo "Creating variable group..."
az pipelines variable-group create \
  --name "Production-Secrets" \
  --variables API_KEY="placeholder" DB_CONNECTION="placeholder" \  # pragma: allowlist secret
  --project "$PROJECT"

echo "CI/CD pipeline setup complete!"
echo "Update secrets in Azure DevOps UI for security"
```

## Multi-Environment Deployment

### Environment-Specific Pipeline Execution

```bash
#!/bin/bash
# Deploy to multiple environments with approval gates

PIPELINE_NAME="Deploy-Pipeline"
BRANCH="main"

deploy_to_environment() {
  local env=$1
  local require_approval=$2

  echo "Deploying to $env..."

  # Run pipeline with environment-specific variables
  RUN_ID=$(az pipelines run \
    --name "$PIPELINE_NAME" \
    --branch "$BRANCH" \
    --variables Environment="$env" \
    --query "id" -o tsv)

  echo "Deployment started: Run ID $RUN_ID"

  if [ "$require_approval" == "true" ]; then
    echo "Waiting for approval..."
    # Monitor for approval (polling)
    while true; do
      STATUS=$(az pipelines runs show --id "$RUN_ID" --query "status" -o tsv)
      if [ "$STATUS" == "completed" ]; then
        RESULT=$(az pipelines runs show --id "$RUN_ID" --query "result" -o tsv)
        echo "Deployment $RESULT"
        break
      fi
      sleep 30
    done
  fi

  return 0
}

# Deploy to dev (no approval)
deploy_to_environment "dev" "false"

# Deploy to staging (requires approval)
deploy_to_environment "staging" "true"

# Deploy to production (requires approval)
read -p "Deploy to production? (yes/no): " confirm
if [ "$confirm" == "yes" ]; then
  deploy_to_environment "production" "true"
fi
```

### Blue-Green Deployment Pattern

```bash
#!/bin/bash
# Blue-green deployment with automatic rollback

PIPELINE="Deploy-BlueGreen"
CURRENT_ENV="blue"
TARGET_ENV="green"

echo "Current environment: $CURRENT_ENV"
echo "Deploying to: $TARGET_ENV"

# Deploy to target environment
RUN_ID=$(az pipelines run \
  --name "$PIPELINE" \
  --variables DeploymentSlot="$TARGET_ENV" \
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

if [ "$RESULT" == "succeeded" ]; then
  echo "Deployment succeeded"
  echo "Run smoke tests on $TARGET_ENV..."

  # Smoke tests would go here
  SMOKE_TEST_PASSED=true

  if [ "$SMOKE_TEST_PASSED" == "true" ]; then
    echo "Switching traffic to $TARGET_ENV"
    # Traffic switch command would go here
  else
    echo "Smoke tests failed, keeping $CURRENT_ENV active"
  fi
else
  echo "Deployment failed, $CURRENT_ENV remains active"
fi
```

## Automated Testing Integration

### Test Execution and Reporting

```bash
#!/bin/bash
# Run tests and generate reports

PIPELINE="Test-Pipeline"
TEST_BRANCH=$1

if [ -z "$TEST_BRANCH" ]; then
  TEST_BRANCH="main"
fi

echo "Running tests for branch: $TEST_BRANCH"

# Run test pipeline
RUN_ID=$(az pipelines run \
  --name "$PIPELINE" \
  --branch "$TEST_BRANCH" \
  --query "id" -o tsv)

echo "Test run started: $RUN_ID"

# Monitor test execution
while true; do
  STATUS=$(az pipelines runs show --id "$RUN_ID" --query "status" -o tsv)
  echo "Test status: $STATUS"

  if [ "$STATUS" == "completed" ]; then
    break
  fi

  sleep 15
done

# Get test results
RESULT=$(az pipelines runs show --id "$RUN_ID" --query "result" -o tsv)

echo "Test Result: $RESULT"

# Open test results in browser
az pipelines runs show --id "$RUN_ID" --open

if [ "$RESULT" == "succeeded" ]; then
  echo "All tests passed!"
  exit 0
else
  echo "Tests failed!"
  exit 1
fi
```

### Parallel Test Execution

```bash
#!/bin/bash
# Run multiple test suites in parallel

declare -a TEST_PIPELINES=(
  "Unit-Tests"
  "Integration-Tests"
  "E2E-Tests"
)

declare -a RUN_IDS=()

echo "Starting parallel test execution..."

# Start all test pipelines
for pipeline in "${TEST_PIPELINES[@]}"; do
  echo "Starting $pipeline..."
  RUN_ID=$(az pipelines run --name "$pipeline" --query "id" -o tsv)
  RUN_IDS+=("$RUN_ID")
  echo "  Run ID: $RUN_ID"
done

echo "Monitoring test execution..."

# Monitor all runs
ALL_COMPLETED=false
while [ "$ALL_COMPLETED" == "false" ]; do
  ALL_COMPLETED=true

  for i in "${!RUN_IDS[@]}"; do
    RUN_ID="${RUN_IDS[$i]}"
    STATUS=$(az pipelines runs show --id "$RUN_ID" --query "status" -o tsv)

    if [ "$STATUS" != "completed" ]; then
      ALL_COMPLETED=false
    fi
  done

  if [ "$ALL_COMPLETED" == "false" ]; then
    sleep 10
  fi
done

# Check results
echo "Test Results:"
ALL_PASSED=true

for i in "${!RUN_IDS[@]}"; do
  RUN_ID="${RUN_IDS[$i]}"
  PIPELINE="${TEST_PIPELINES[$i]}"
  RESULT=$(az pipelines runs show --id "$RUN_ID" --query "result" -o tsv)

  echo "  $PIPELINE: $RESULT"

  if [ "$RESULT" != "succeeded" ]; then
    ALL_PASSED=false
  fi
done

if [ "$ALL_PASSED" == "true" ]; then
  echo "All tests passed!"
  exit 0
else
  echo "Some tests failed!"
  exit 1
fi
```

## Build Artifact Management

### Artifact Publishing and Versioning

```bash
#!/bin/bash
# Build, version, and publish artifacts

FEED="build-artifacts"
PACKAGE="myapp"
BUILD_PIPELINE="Build-Pipeline"

# Generate semantic version
MAJOR=1
MINOR=0
PATCH=$(git rev-list --count HEAD)
VERSION="$MAJOR.$MINOR.$PATCH"

echo "Building version $VERSION..."

# Run build pipeline
RUN_ID=$(az pipelines run \
  --name "$BUILD_PIPELINE" \
  --variables BuildNumber="$VERSION" \
  --query "id" -o tsv)

# Wait for build
while true; do
  STATUS=$(az pipelines runs show --id "$RUN_ID" --query "status" -o tsv)
  if [ "$STATUS" == "completed" ]; then
    break
  fi
  sleep 10
done

RESULT=$(az pipelines runs show --id "$RUN_ID" --query "result" -o tsv)

if [ "$RESULT" == "succeeded" ]; then
  echo "Build succeeded!"

  # Download build artifacts
  az pipelines runs artifact download \
    --run-id "$RUN_ID" \
    --artifact-name "drop" \
    --path ./artifacts

  # Publish to Azure Artifacts
  az artifacts universal publish \
    --feed "$FEED" \
    --name "$PACKAGE" \
    --version "$VERSION" \
    --path ./artifacts/drop \
    --description "Build $VERSION from run $RUN_ID"

  echo "Published $PACKAGE:$VERSION to feed $FEED"

  # Tag the run
  az pipelines runs tag add --run-id "$RUN_ID" --tags "published" "v$VERSION"

else
  echo "Build failed!"
  exit 1
fi
```

## Continuous Deployment Patterns

### Automated Deployment on Successful Build

```bash
#!/bin/bash
# Automatically deploy when build succeeds

BUILD_PIPELINE="Build-Pipeline"
DEPLOY_PIPELINE="Deploy-Pipeline"
BRANCH="main"

echo "Starting automated deployment workflow..."

# Run build
echo "Building..."
BUILD_RUN=$(az pipelines run \
  --name "$BUILD_PIPELINE" \
  --branch "$BRANCH" \
  --query "id" -o tsv)

# Monitor build
while true; do
  BUILD_STATUS=$(az pipelines runs show --id "$BUILD_RUN" --query "status" -o tsv)
  if [ "$BUILD_STATUS" == "completed" ]; then
    break
  fi
  echo "Build in progress..."
  sleep 10
done

BUILD_RESULT=$(az pipelines runs show --id "$BUILD_RUN" --query "result" -o tsv)

if [ "$BUILD_RESULT" == "succeeded" ]; then
  echo "Build succeeded! Starting deployment..."

  # Get build version
  BUILD_NUMBER=$(az pipelines runs show --id "$BUILD_RUN" --query "buildNumber" -o tsv)

  # Run deployment
  DEPLOY_RUN=$(az pipelines run \
    --name "$DEPLOY_PIPELINE" \
    --variables BuildNumber="$BUILD_NUMBER" \
    --query "id" -o tsv)

  echo "Deployment started: Run $DEPLOY_RUN"

  # Monitor deployment
  while true; do
    DEPLOY_STATUS=$(az pipelines runs show --id "$DEPLOY_RUN" --query "status" -o tsv)
    if [ "$DEPLOY_STATUS" == "completed" ]; then
      break
    fi
    echo "Deployment in progress..."
    sleep 15
  done

  DEPLOY_RESULT=$(az pipelines runs show --id "$DEPLOY_RUN" --query "result" -o tsv)
  echo "Deployment result: $DEPLOY_RESULT"

else
  echo "Build failed! Skipping deployment."
  exit 1
fi
```

### Scheduled Deployment Windows

```bash
#!/bin/bash
# Deploy only during maintenance windows

DEPLOY_PIPELINE="Production-Deploy"
MAINTENANCE_START="22:00"  # 10 PM
MAINTENANCE_END="02:00"    # 2 AM

is_maintenance_window() {
  current_hour=$(date +%H)
  current_minute=$(date +%M)
  current_time="${current_hour}:${current_minute}"

  # Simple time range check (works for same-day window)
  if [[ "$current_time" > "$MAINTENANCE_START" ]] || [[ "$current_time" < "$MAINTENANCE_END" ]]; then
    return 0  # True
  else
    return 1  # False
  fi
}

if is_maintenance_window; then
  echo "In maintenance window, proceeding with deployment..."
  az pipelines run --name "$DEPLOY_PIPELINE"
else
  echo "Outside maintenance window ($MAINTENANCE_START - $MAINTENANCE_END)"
  echo "Deployment not allowed at this time"
  exit 1
fi
```

## Pipeline Health Monitoring

### Build Success Rate Dashboard

```bash
#!/bin/bash
# Generate build health report

PIPELINE="Build-Pipeline"
DAYS=7
REPORT_FILE="build-health-$(date +%Y%m%d).txt"

echo "Build Health Report: $PIPELINE (Last $DAYS days)" > "$REPORT_FILE"
echo "Generated: $(date)" >> "$REPORT_FILE"
echo "=====================================================" >> "$REPORT_FILE"

# Get recent runs
SINCE_DATE=$(date -d "$DAYS days ago" +%Y-%m-%d)

# Total runs
TOTAL=$(az pipelines runs list \
  --pipeline-ids "$(az pipelines show --name "$PIPELINE" --query id -o tsv)" \
  --query "length([?finishTime>='$SINCE_DATE'])" -o tsv)

# Succeeded runs
SUCCEEDED=$(az pipelines runs list \
  --pipeline-ids "$(az pipelines show --name "$PIPELINE" --query id -o tsv)" \
  --result succeeded \
  --query "length([?finishTime>='$SINCE_DATE'])" -o tsv)

# Failed runs
FAILED=$(az pipelines runs list \
  --pipeline-ids "$(az pipelines show --name "$PIPELINE" --query id -o tsv)" \
  --result failed \
  --query "length([?finishTime>='$SINCE_DATE'])" -o tsv)

# Calculate success rate
if [ "$TOTAL" -gt 0 ]; then
  SUCCESS_RATE=$(awk "BEGIN {printf \"%.2f\", ($SUCCEEDED/$TOTAL)*100}")
else
  SUCCESS_RATE="0.00"
fi

echo "Total Runs: $TOTAL" >> "$REPORT_FILE"
echo "Succeeded: $SUCCEEDED" >> "$REPORT_FILE"
echo "Failed: $FAILED" >> "$REPORT_FILE"
echo "Success Rate: $SUCCESS_RATE%" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo "Recent Failed Builds:" >> "$REPORT_FILE"
az pipelines runs list \
  --pipeline-ids "$(az pipelines show --name "$PIPELINE" --query id -o tsv)" \
  --result failed \
  --query "[?finishTime>='$SINCE_DATE'].{ID:id, Branch:sourceBranch, Time:finishTime}" \
  --output table >> "$REPORT_FILE"

cat "$REPORT_FILE"
```

### Automated Failure Notification

```bash
#!/bin/bash
# Monitor pipeline and send notifications on failure

PIPELINE="Critical-Pipeline"
NOTIFICATION_EMAIL="team@example.com"

# Get latest run
LATEST_RUN=$(az pipelines runs list \
  --pipeline-ids "$(az pipelines show --name "$PIPELINE" --query id -o tsv)" \
  --top 1 \
  --query "[0].id" -o tsv)

RESULT=$(az pipelines runs show --id "$LATEST_RUN" --query "result" -o tsv)

if [ "$RESULT" == "failed" ]; then
  echo "Pipeline $PIPELINE failed!"

  # Get failure details
  BUILD_NUMBER=$(az pipelines runs show --id "$LATEST_RUN" --query "buildNumber" -o tsv)
  SOURCE_BRANCH=$(az pipelines runs show --id "$LATEST_RUN" --query "sourceBranch" -o tsv)
  RUN_URL=$(az pipelines runs show --id "$LATEST_RUN" --query "_links.web.href" -o tsv)

  # Send notification (example using mail command)
  echo "Pipeline: $PIPELINE
Build: $BUILD_NUMBER
Branch: $SOURCE_BRANCH
Status: FAILED
URL: $RUN_URL" | mail -s "Build Failure: $PIPELINE" "$NOTIFICATION_EMAIL"

  echo "Notification sent to $NOTIFICATION_EMAIL"
fi
```

## Best Practices

1. **Idempotent Deployments**: Ensure deployments can be run multiple times safely
2. **Rollback Strategy**: Always have a rollback plan before deploying
3. **Smoke Tests**: Run basic health checks after deployment
4. **Deployment Slots**: Use staging slots for zero-downtime deployments
5. **Version Tagging**: Tag all deployments with version numbers
6. **Monitoring**: Implement health checks and alerting
7. **Audit Trail**: Log all deployment actions for compliance
8. **Security**: Use variable groups for secrets, never hardcode credentials

## Advanced Patterns

### Canary Deployment

```bash
#!/bin/bash
# Canary deployment with gradual rollout

DEPLOY_PIPELINE="Canary-Deploy"
TRAFFIC_PERCENTAGES=(10 25 50 100)

for percentage in "${TRAFFIC_PERCENTAGES[@]}"; do
  echo "Deploying canary with $percentage% traffic..."

  az pipelines run \
    --name "$DEPLOY_PIPELINE" \
    --variables TrafficPercentage="$percentage"

  echo "Monitoring canary at $percentage%..."
  sleep 300  # 5 minutes

  # Check metrics (error rate, latency, etc.)
  # If metrics are good, continue to next percentage
  # If metrics are bad, rollback

  read -p "Continue to next traffic percentage? (yes/no): " continue
  if [ "$continue" != "yes" ]; then
    echo "Rolling back canary deployment..."
    az pipelines run --name "$DEPLOY_PIPELINE" --variables TrafficPercentage="0"
    exit 1
  fi
done

echo "Canary deployment successful!"
```

## References

- [Azure Pipelines YAML Schema](https://learn.microsoft.com/en-us/azure/devops/pipelines/yaml-schema)
- [Deployment Strategies](https://learn.microsoft.com/en-us/azure/devops/pipelines/release/deployment-strategies)
- [Pipeline Triggers](https://learn.microsoft.com/en-us/azure/devops/pipelines/build/triggers)
