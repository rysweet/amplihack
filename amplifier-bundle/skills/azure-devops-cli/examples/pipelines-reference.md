# Azure Pipelines Complete Command Reference

Complete reference for `az pipelines` command group covering build and release automation.

## Pipeline Management

### List Pipelines

```bash
# List all pipelines
az pipelines list --project MyProject

# List with specific name filter
az pipelines list --name "*API*" --output table

# List with top N results
az pipelines list --top 10

# Get pipeline details as JSON
az pipelines list --output json > pipelines.json
```

### Show Pipeline Details

```bash
# Show pipeline by name
az pipelines show --name "MyPipeline" --project MyProject

# Show pipeline by ID
az pipelines show --id 123

# Open pipeline in browser
az pipelines show --name "MyPipeline" --open
```

### Create Pipeline

```bash
# Create from YAML file in repository
az pipelines create --name "NewPipeline" \
  --repository myrepo \
  --branch main \
  --yml-path azure-pipelines.yml \
  --project MyProject

# Create with service connection
az pipelines create --name "Deploy-Pipeline" \
  --repository myrepo \
  --service-connection "AzureRM-Connection" \
  --yml-path deploy/azure-pipelines.yml

# Create and skip first run
az pipelines create --name "Test-Pipeline" \
  --repository myrepo \
  --yml-path test-pipeline.yml \
  --skip-first-run true
```

### Update Pipeline

```bash
# Update pipeline YAML path
az pipelines update --id 123 --yml-path new/path/azure-pipelines.yml

# Update pipeline name
az pipelines update --id 123 --new-name "RenamedPipeline"

# Update pipeline description
az pipelines update --id 123 --description "Updated description"
```

### Delete Pipeline

```bash
# Delete pipeline by ID
az pipelines delete --id 123 --yes

# Delete pipeline by name
az pipelines delete --name "OldPipeline" --yes --project MyProject
```

## Pipeline Runs

### List Runs

```bash
# List all runs
az pipelines runs list --project MyProject

# List runs for specific pipeline
az pipelines runs list --pipeline-ids 123

# List top 20 recent runs
az pipelines runs list --top 20

# List runs by status
az pipelines runs list --status completed
az pipelines runs list --status inProgress
az pipelines runs list --status failed

# List runs by result
az pipelines runs list --query-order FinishTimeDesc --top 10

# Filter runs with JMESPath
az pipelines runs list --query "[?result=='failed'].{ID:id, Pipeline:pipeline.name, Branch:sourceBranch}"
```

### Show Run Details

```bash
# Show run by ID
az pipelines runs show --id 456

# Show run and open in browser
az pipelines runs show --id 456 --open

# Get run as JSON for processing
az pipelines runs show --id 456 --output json
```

### Run Pipeline

```bash
# Run pipeline by name
az pipelines run --name "MyPipeline"

# Run specific branch
az pipelines run --name "MyPipeline" --branch feature/new-feature

# Run with parameters
az pipelines run --name "MyPipeline" --variables key1=value1 key2=value2

# Run and open in browser
az pipelines run --name "MyPipeline" --open

# Run specific pipeline ID
az pipelines run --id 123 --branch main

# Run with commit
az pipelines run --name "MyPipeline" --commit-id abc123def456
```

## Pipeline Variables

### List Variables

```bash
# List all pipeline variables
az pipelines variable list --pipeline-name "MyPipeline"

# List as JSON
az pipelines variable list --pipeline-id 123 --output json
```

### Create Variable

```bash
# Create pipeline variable
az pipelines variable create --name "API_KEY" --value "secret123" --pipeline-name "MyPipeline"

# Create secret variable
az pipelines variable create --name "PASSWORD" --value "secret" --secret true --pipeline-name "MyPipeline"

# Create variable with allow-override
az pipelines variable create --name "ENV" --value "dev" --allow-override true --pipeline-name "MyPipeline"
```

### Update Variable

```bash
# Update variable value
az pipelines variable update --name "API_KEY" --value "newsecret" --pipeline-name "MyPipeline"

# Update and make secret
az pipelines variable update --name "TOKEN" --secret true --pipeline-name "MyPipeline"
```

### Delete Variable

```bash
# Delete pipeline variable
az pipelines variable delete --name "OLD_VAR" --pipeline-name "MyPipeline" --yes
```

## Variable Groups

### List Variable Groups

```bash
# List all variable groups
az pipelines variable-group list --project MyProject

# List with specific name
az pipelines variable-group list --group-name "Production"

# List as table
az pipelines variable-group list --output table
```

### Create Variable Group

```bash
# Create variable group
az pipelines variable-group create --name "Production" --variables key1=value1 key2=value2

# Create with description
az pipelines variable-group create --name "Staging" \
  --variables ENV=staging API_URL=https://staging.api.com \
  --description "Staging environment variables"

# Create from JSON file
az pipelines variable-group create --name "Config" --variables @config.json
```

### Update Variable Group

```bash
# Update variable group
az pipelines variable-group update --group-id 789 --name "NewName"

# Add/update variables in group
az pipelines variable-group variable create --group-id 789 --name "NEW_VAR" --value "value"

# Update variable in group
az pipelines variable-group variable update --group-id 789 --name "VAR" --value "newvalue"

# Delete variable from group
az pipelines variable-group variable delete --group-id 789 --name "OLD_VAR" --yes
```

### Delete Variable Group

```bash
# Delete variable group
az pipelines variable-group delete --group-id 789 --yes
```

## Advanced Pipeline Operations

### Pipeline Tags

```bash
# Add tag to run
az pipelines runs tag add --run-id 456 --tags "production" "release-1.0"

# List tags for run
az pipelines runs tag list --run-id 456

# Delete tag from run
az pipelines runs tag delete --run-id 456 --tag "old-tag"
```

### Pipeline Artifacts

```bash
# List artifacts for run
az pipelines runs artifact list --run-id 456

# Download artifact
az pipelines runs artifact download --run-id 456 --artifact-name "drop" --path ./download

# Upload artifact (typically done in pipeline YAML)
# This is usually handled by PublishPipelineArtifact task
```

### Pipeline Approval

```bash
# List pending approvals
az pipelines approval list --project MyProject

# Approve a deployment
az pipelines approval update --approval-id 123 --status approved --comments "Approved by CLI"

# Reject a deployment
az pipelines approval update --approval-id 123 --status rejected --comments "Failed validation"
```

## Query and Filtering Examples

### Complex JMESPath Queries

```bash
# Failed runs in last 7 days
az pipelines runs list --query "[?result=='failed' && finishTime>='2025-11-17'].{ID:id, Name:pipeline.name, Time:finishTime}"

# Running builds by branch
az pipelines runs list --status inProgress --query "[].{ID:id, Pipeline:pipeline.name, Branch:sourceBranch}" --output table

# Success rate calculation
az pipelines runs list --top 100 --query "length([?result=='succeeded'])"

# Get all build reasons
az pipelines runs list --query "[].{ID:id, Reason:reason}" --output table

# Filter by source branch
az pipelines runs list --query "[?sourceBranch=='refs/heads/main']" --output table
```

### Scripting Patterns

```bash
# Run all pipelines with specific name pattern
az pipelines list --query "[?contains(name, 'API')].id" -o tsv | while read id; do
  az pipelines run --id "$id"
done

# Get latest successful run for each pipeline
az pipelines list -o json | jq -r '.[].id' | while read id; do
  az pipelines runs list --pipeline-ids "$id" --result succeeded --top 1
done

# Monitor pipeline until completion
RUN_ID=$(az pipelines run --name "MyPipeline" --query "id" -o tsv)
while true; do
  STATUS=$(az pipelines runs show --id "$RUN_ID" --query "status" -o tsv)
  if [ "$STATUS" != "inProgress" ]; then
    echo "Build completed with status: $STATUS"
    break
  fi
  sleep 10
done
```

## Common Patterns

### Daily Build Report

```bash
#!/bin/bash
TODAY=$(date +%Y-%m-%d)
REPORT="build-report-$TODAY.txt"
echo "Build Report for $TODAY" > "$REPORT"
az pipelines runs list --query "[?startTime>='$TODAY'].{Pipeline:pipeline.name, Status:status, Result:result}" --output table >> "$REPORT"
az pipelines runs list --query "[?result=='failed' && startTime>='$TODAY'].{ID:id, Pipeline:pipeline.name}" --output table >> "$REPORT"
```

### Automated Pipeline Testing

```bash
#!/bin/bash
PIPELINE="MyPipeline"
BRANCHES=("main" "develop" "feature/test")
for branch in "${BRANCHES[@]}"; do
  az pipelines run --name "$PIPELINE" --branch "$branch"
done
```

### Environment-Specific Deployment

```bash
#!/bin/bash
case $1 in
  dev|staging) az pipelines run --name "Deploy-$1" --variables ENV=$1 ;;
  prod)
    read -p "Deploy to production? (yes/no): " confirm
    [ "$confirm" == "yes" ] && az pipelines run --name "Deploy-Prod" --variables ENV=prod ;;
  *) echo "Unknown environment: $1"; exit 1 ;;
esac
```

## Best Practices

- Use pipeline IDs (stable) over names
- Set default org/project
- JMESPath for filtering
- Tag runs for reporting
- Use variable groups
- Mark secrets with `--secret true`
- JSON for scripts, table for humans

## Troubleshooting

**Pipeline not found**: List all with `az pipelines list --output table`, use ID

**Run failures**: Check with `az pipelines runs show --id 456 --output json`

**Variables**: Verify with `az pipelines variable list --pipeline-name "MyPipeline"`

## References

- [Azure Pipelines CLI Reference](https://learn.microsoft.com/en-us/cli/azure/pipelines)
- [Pipeline YAML Schema](https://learn.microsoft.com/en-us/azure/devops/pipelines/yaml-schema)
- [JMESPath Tutorial](http://jmespath.org/tutorial.html)
