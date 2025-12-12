# Pipeline Operations Guide

Guide for working with Azure DevOps pipelines and builds using CLI tools.

## Overview

Azure DevOps Pipelines provide CI/CD automation. Common operations include:

- Listing pipelines
- Queuing builds
- Checking build status
- Viewing logs
- Managing deployments

## Common Commands

### List Pipelines

```bash
az pipelines list --output table
```

### Show Pipeline Details

```bash
az pipelines show --id PIPELINE_ID
```

### Queue a Build

```bash
az pipelines run --id PIPELINE_ID
```

### Queue Build with Branch

```bash
az pipelines run --id PIPELINE_ID --branch feature/branch-name
```

### List Recent Builds

```bash
az pipelines build list --output table
```

### Get Build Status

```bash
az pipelines build show --id BUILD_ID
```

### Download Build Logs

```bash
az pipelines build logs download --id BUILD_ID --output-dir ./logs
```

## Pipeline Triggers

Pipelines can be triggered by:

### Push Triggers
Automatically run on push to specific branches:
```yaml
trigger:
  branches:
    include:
      - main
      - feature/*
```

### Pull Request Triggers
Run validation builds for PRs:
```yaml
pr:
  branches:
    include:
      - main
```

### Scheduled Triggers
Run on a schedule:
```yaml
schedules:
  - cron: "0 0 * * *"
    displayName: Daily midnight build
    branches:
      include:
        - main
```

### Manual Triggers
Queue builds manually via CLI or web portal.

## Build Variables

### Predefined Variables

Common system variables:
- `$(Build.SourceBranch)` - Source branch
- `$(Build.BuildNumber)` - Build number
- `$(Build.SourceVersion)` - Commit SHA
- `$(Build.Repository.Name)` - Repository name

### Custom Variables

Set in pipeline YAML:
```yaml
variables:
  buildConfiguration: 'Release'
  vmImage: 'ubuntu-latest'
```

Override at queue time:
```bash
az pipelines run --id PIPELINE_ID --variables buildConfiguration=Debug
```

## Build Artifacts

### Publish Artifacts

In pipeline:
```yaml
- task: PublishBuildArtifacts@1
  inputs:
    pathToPublish: '$(Build.ArtifactStagingDirectory)'
    artifactName: 'drop'
```

### Download Artifacts

```bash
az pipelines build artifacts download --id BUILD_ID --output-dir ./artifacts
```

## Monitoring Builds

### Check Build Status

```bash
# Get latest build for pipeline
az pipelines build list --pipeline-id PIPELINE_ID --top 1
```

### View Build Timeline

```bash
az pipelines build show --id BUILD_ID --open
```

This opens the build in your browser.

### Stream Build Logs

```bash
# Not directly supported - use polling:
while true; do
  az pipelines build show --id BUILD_ID --query status
  sleep 10
done
```

## Deployment Management

### List Releases

```bash
az pipelines release list --output table
```

### Create Release

```bash
az pipelines release create --definition-id RELEASE_DEF_ID
```

### Approve Deployment

```bash
az pipelines release approval approve --id APPROVAL_ID
```

## Common Workflows

### Trigger Build on PR Creation

When you create a PR, pipeline validation builds run automatically if configured.

```bash
# Create PR (automatically triggers build)
python .claude/scenarios/az-devops-tools/create_pr.py \
  --source feature/branch \
  --target main \
  --title "My feature"

# Check PR build status
az pipelines build list --branch refs/pull/PR_NUMBER/merge
```

### Manual Build with Custom Parameters

```bash
az pipelines run \
  --id PIPELINE_ID \
  --branch feature/branch-name \
  --variables buildConfiguration=Debug testEnabled=true
```

### Check If Build Passed

```bash
BUILD_STATUS=$(az pipelines build show --id BUILD_ID --query status -o tsv)
if [ "$BUILD_STATUS" = "completed" ]; then
  RESULT=$(az pipelines build show --id BUILD_ID --query result -o tsv)
  if [ "$RESULT" = "succeeded" ]; then
    echo "Build passed"
  else
    echo "Build failed"
  fi
fi
```

## Pipeline YAML Best Practices

1. **Use templates** - Reuse common steps
2. **Parameterize** - Use variables for flexibility
3. **Cache dependencies** - Speed up builds
4. **Run tests** - Validate changes
5. **Publish artifacts** - Make outputs available

## Tips

1. **Enable PR builds** - Catch issues before merge
2. **Set up notifications** - Get alerts on build failures
3. **Use build badges** - Show build status in README
4. **Review logs** - Understand failures quickly
5. **Clean up old builds** - Manage storage usage

## Troubleshooting

### "Pipeline not found"

List available pipelines:
```bash
az pipelines list
```

### "Build failed"

Download and review logs:
```bash
az pipelines build logs download --id BUILD_ID --output-dir ./logs
cat logs/*.log
```

### "Permission denied"

Verify you have Build Administrator or Contributor permissions.

## See Also

- [Azure Pipelines Docs](https://learn.microsoft.com/en-us/azure/devops/pipelines/)
- [YAML Schema](https://learn.microsoft.com/en-us/azure/devops/pipelines/yaml-schema)
- [Predefined Variables](https://learn.microsoft.com/en-us/azure/devops/pipelines/build/variables)
