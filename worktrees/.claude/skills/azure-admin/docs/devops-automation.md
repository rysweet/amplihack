# DevOps Automation with Azure

Comprehensive guide to CI/CD pipelines, infrastructure as code, and GitOps workflows for Azure.

## Table of Contents

1. [Azure DevOps Pipelines](#azure-devops-pipelines)
2. [GitHub Actions Integration](#github-actions-integration)
3. [Infrastructure as Code in CI/CD](#infrastructure-as-code-in-cicd)
4. [Deployment Strategies](#deployment-strategies)
5. [GitOps Workflows](#gitops-workflows)
6. [Secrets Management](#secrets-management)

## Azure DevOps Pipelines

Azure DevOps provides comprehensive CI/CD capabilities with YAML-based pipelines.

### Basic Pipeline Structure

```yaml
# azure-pipelines.yml

trigger:
  branches:
    include:
      - main
      - develop
  paths:
    exclude:
      - docs/**
      - README.md

pool:
  vmImage: 'ubuntu-latest'

variables:
  azureSubscription: 'MyServiceConnection'
  resourceGroup: 'myapp-prod-rg'
  location: 'eastus'

stages:
  - stage: Build
    displayName: 'Build and Test'
    jobs:
      - job: BuildJob
        steps:
          - task: AzureCLI@2
            displayName: 'Validate Bicep Templates'
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                az bicep build --file infra/main.bicep

          - task: PublishBuildArtifacts@1
            inputs:
              pathToPublish: 'infra'
              artifactName: 'infrastructure'

  - stage: Deploy
    displayName: 'Deploy to Azure'
    dependsOn: Build
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
    jobs:
      - deployment: DeployInfrastructure
        environment: 'production'
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureResourceManagerTemplateDeployment@3
                  displayName: 'Deploy Infrastructure'
                  inputs:
                    azureResourceManagerConnection: $(azureSubscription)
                    subscriptionId: $(subscriptionId)
                    resourceGroupName: $(resourceGroup)
                    location: $(location)
                    templateLocation: 'Linked artifact'
                    csmFile: '$(Pipeline.Workspace)/infrastructure/main.bicep'
                    deploymentMode: 'Incremental'
```

### Multi-Stage Pipeline with Approvals

```yaml
# multi-stage-pipeline.yml

stages:
  - stage: Build
    jobs:
      - job: Build
        steps:
          - script: echo "Building application"
          - task: PublishBuildArtifacts@1

  - stage: DeployDev
    displayName: 'Deploy to Development'
    dependsOn: Build
    jobs:
      - deployment: DeployDev
        environment: 'development'
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureCLI@2
                  inputs:
                    azureSubscription: 'DevServiceConnection'
                    scriptType: 'bash'
                    scriptLocation: 'inlineScript'
                    inlineScript: |
                      az deployment group create \
                        --resource-group dev-rg \
                        --template-file $(Pipeline.Workspace)/infra/main.bicep \
                        --parameters environment=dev

  - stage: DeployProd
    displayName: 'Deploy to Production'
    dependsOn: DeployDev
    jobs:
      - deployment: DeployProd
        environment: 'production'  # Requires manual approval
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureCLI@2
                  inputs:
                    azureSubscription: 'ProdServiceConnection'
                    scriptType: 'bash'
                    scriptLocation: 'inlineScript'
                    inlineScript: |
                      az deployment group create \
                        --resource-group prod-rg \
                        --template-file $(Pipeline.Workspace)/infra/main.bicep \
                        --parameters environment=prod
```

### Pipeline with Testing

```yaml
stages:
  - stage: Test
    jobs:
      - job: InfrastructureTests
        steps:
          - task: AzureCLI@2
            displayName: 'Run Bicep Linting'
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                # Install bicep linter
                az bicep build --file infra/main.bicep

          - task: AzureCLI@2
            displayName: 'Validate Templates'
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                az deployment group validate \
                  --resource-group test-rg \
                  --template-file infra/main.bicep \
                  --parameters environment=test

          - task: AzureCLI@2
            displayName: 'Run What-If Analysis'
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                az deployment group what-if \
                  --resource-group test-rg \
                  --template-file infra/main.bicep \
                  --parameters environment=test

      - job: SecurityScanning
        steps:
          - task: AzureCLI@2
            displayName: 'Check for Sensitive Data'
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                # Check for hardcoded secrets
                if grep -r "password\|secret\|apikey" infra/; then
                  echo "##vso[task.logissue type=error]Found potential secrets in code"
                  exit 1
                fi
```

## GitHub Actions Integration

GitHub Actions provides native CI/CD for repositories hosted on GitHub.

### Basic Workflow

```yaml
# .github/workflows/deploy-azure.yml

name: Deploy to Azure

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:  # Manual trigger

env:
  AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
  RESOURCE_GROUP: myapp-prod-rg
  LOCATION: eastus

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Validate Bicep
        run: |
          az bicep build --file infra/main.bicep

      - name: Validate Deployment
        run: |
          az deployment group validate \
            --resource-group ${{ env.RESOURCE_GROUP }} \
            --template-file infra/main.bicep \
            --parameters environment=prod

  deploy:
    needs: validate
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy Infrastructure
        uses: azure/arm-deploy@v1
        with:
          subscriptionId: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          resourceGroupName: ${{ env.RESOURCE_GROUP }}
          template: ./infra/main.bicep
          parameters: environment=prod
          deploymentMode: Incremental
```

### Matrix Strategy for Multi-Environment

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [dev, staging, prod]
        include:
          - environment: dev
            resource_group: myapp-dev-rg
            approval_required: false
          - environment: staging
            resource_group: myapp-staging-rg
            approval_required: false
          - environment: prod
            resource_group: myapp-prod-rg
            approval_required: true

    environment:
      name: ${{ matrix.environment }}

    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy to ${{ matrix.environment }}
        uses: azure/arm-deploy@v1
        with:
          subscriptionId: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          resourceGroupName: ${{ matrix.resource_group }}
          template: ./infra/main.bicep
          parameters: environment=${{ matrix.environment }}
```

### Reusable Workflows

```yaml
# .github/workflows/reusable-deploy.yml

name: Reusable Azure Deployment

on:
  workflow_call:
    inputs:
      environment:
        required: true
        type: string
      resource_group:
        required: true
        type: string
    secrets:
      AZURE_CREDENTIALS:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy Infrastructure
        uses: azure/arm-deploy@v1
        with:
          subscriptionId: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
          resourceGroupName: ${{ inputs.resource_group }}
          template: ./infra/main.bicep
          parameters: environment=${{ inputs.environment }}
```

**Usage:**
```yaml
# .github/workflows/deploy-prod.yml

name: Deploy Production

on:
  push:
    branches: [main]

jobs:
  deploy-prod:
    uses: ./.github/workflows/reusable-deploy.yml
    with:
      environment: production
      resource_group: myapp-prod-rg
    secrets:
      AZURE_CREDENTIALS: ${{ secrets.AZURE_CREDENTIALS }}
```

## Infrastructure as Code in CI/CD

### Bicep Deployment Pipeline

```yaml
# Complete Bicep deployment pipeline

stages:
  - stage: Validate
    jobs:
      - job: ValidateBicep
        steps:
          - task: AzureCLI@2
            displayName: 'Bicep Build'
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                cd infra
                az bicep build --file main.bicep

          - task: AzureCLI@2
            displayName: 'Validate Template'
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                az deployment sub validate \
                  --location $(location) \
                  --template-file infra/main.bicep \
                  --parameters @infra/parameters/$(environment).json

          - task: AzureCLI@2
            displayName: 'What-If Analysis'
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: 'bash'
              scriptLocation: 'inlineScript'
              inlineScript: |
                az deployment sub what-if \
                  --location $(location) \
                  --template-file infra/main.bicep \
                  --parameters @infra/parameters/$(environment).json

  - stage: Deploy
    dependsOn: Validate
    jobs:
      - deployment: DeployBicep
        environment: $(environment)
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureCLI@2
                  displayName: 'Deploy Bicep Template'
                  inputs:
                    azureSubscription: $(azureSubscription)
                    scriptType: 'bash'
                    scriptLocation: 'inlineScript'
                    inlineScript: |
                      az deployment sub create \
                        --name $(Build.BuildNumber) \
                        --location $(location) \
                        --template-file $(Pipeline.Workspace)/infra/main.bicep \
                        --parameters @$(Pipeline.Workspace)/infra/parameters/$(environment).json

                - task: AzureCLI@2
                  displayName: 'Verify Deployment'
                  inputs:
                    azureSubscription: $(azureSubscription)
                    scriptType: 'bash'
                    scriptLocation: 'inlineScript'
                    inlineScript: |
                      # Check deployment status
                      STATUS=$(az deployment sub show \
                        --name $(Build.BuildNumber) \
                        --query properties.provisioningState -o tsv)

                      if [ "$STATUS" != "Succeeded" ]; then
                        echo "Deployment failed with status: $STATUS"
                        exit 1
                      fi

                      echo "✓ Deployment succeeded"
```

## Deployment Strategies

### Blue-Green Deployment

```yaml
# Blue-Green deployment with Azure App Service slots

jobs:
  - job: BlueGreenDeploy
    steps:
      - task: AzureCLI@2
        displayName: 'Deploy to Staging Slot (Green)'
        inputs:
          azureSubscription: $(azureSubscription)
          scriptType: 'bash'
          scriptLocation: 'inlineScript'
          inlineScript: |
            # Deploy to staging slot
            az webapp deployment source config-zip \
              --resource-group $(resourceGroup) \
              --name $(webAppName) \
              --slot staging \
              --src $(Build.ArtifactStagingDirectory)/app.zip

      - task: AzureCLI@2
        displayName: 'Warm Up Staging Slot'
        inputs:
          azureSubscription: $(azureSubscription)
          scriptType: 'bash'
          scriptLocation: 'inlineScript'
          inlineScript: |
            STAGING_URL="https://$(webAppName)-staging.azurewebsites.net"
            echo "Warming up $STAGING_URL"

            for i in {1..5}; do
              curl -f "$STAGING_URL" || exit 1
              sleep 2
            done

            echo "✓ Staging slot is healthy"

      - task: AzureCLI@2
        displayName: 'Swap Slots (Blue ↔ Green)'
        inputs:
          azureSubscription: $(azureSubscription)
          scriptType: 'bash'
          scriptLocation: 'inlineScript'
          inlineScript: |
            az webapp deployment slot swap \
              --resource-group $(resourceGroup) \
              --name $(webAppName) \
              --slot staging \
              --target-slot production

            echo "✓ Swap completed - Staging is now Production"

      - task: AzureCLI@2
        displayName: 'Verify Production'
        inputs:
          azureSubscription: $(azureSubscription)
          scriptType: 'bash'
          scriptLocation: 'inlineScript'
          inlineScript: |
            PROD_URL="https://$(webAppName).azurewebsites.net"
            curl -f "$PROD_URL" || {
              echo "Production health check failed - rolling back"
              az webapp deployment slot swap \
                --resource-group $(resourceGroup) \
                --name $(webAppName) \
                --slot staging \
                --target-slot production
              exit 1
            }

            echo "✓ Production is healthy"
```

### Canary Deployment

```yaml
# Canary deployment with gradual traffic shift

jobs:
  - job: CanaryDeploy
    steps:
      - task: AzureCLI@2
        displayName: 'Deploy Canary Version'
        inputs:
          azureSubscription: $(azureSubscription)
          scriptType: 'bash'
          scriptLocation: 'inlineScript'
          inlineScript: |
            # Deploy to canary slot
            az webapp deployment source config-zip \
              --resource-group $(resourceGroup) \
              --name $(webAppName) \
              --slot canary \
              --src $(Build.ArtifactStagingDirectory)/app.zip

      - task: AzureCLI@2
        displayName: 'Route 10% Traffic to Canary'
        inputs:
          azureSubscription: $(azureSubscription)
          scriptType: 'bash'
          scriptLocation: 'inlineScript'
          inlineScript: |
            az webapp traffic-routing set \
              --resource-group $(resourceGroup) \
              --name $(webAppName) \
              --distribution canary=10

            echo "✓ 10% traffic routed to canary"

      - task: ManualValidation@0
        displayName: 'Validate Canary Metrics'
        inputs:
          instructions: 'Check monitoring dashboards for canary performance and errors'

      - task: AzureCLI@2
        displayName: 'Increase to 50% Traffic'
        inputs:
          azureSubscription: $(azureSubscription)
          scriptType: 'bash'
          scriptLocation: 'inlineScript'
          inlineScript: |
            az webapp traffic-routing set \
              --resource-group $(resourceGroup) \
              --name $(webAppName) \
              --distribution canary=50

      - task: ManualValidation@0
        displayName: 'Final Validation'

      - task: AzureCLI@2
        displayName: 'Complete Canary Rollout'
        inputs:
          azureSubscription: $(azureSubscription)
          scriptType: 'bash'
          scriptLocation: 'inlineScript'
          inlineScript: |
            # Swap canary to production
            az webapp deployment slot swap \
              --resource-group $(resourceGroup) \
              --name $(webAppName) \
              --slot canary \
              --target-slot production

            # Clear traffic routing
            az webapp traffic-routing clear \
              --resource-group $(resourceGroup) \
              --name $(webAppName)
```

## GitOps Workflows

### ArgoCD with Azure

```yaml
# Flux CD configuration for Azure resources
# .flux/infrastructure.yaml

apiVersion: kustomize.toolkit.fluxcd.io/v1
kind: Kustomization
metadata:
  name: azure-infrastructure
  namespace: flux-system
spec:
  interval: 10m
  path: ./infrastructure/azure
  prune: true
  sourceRef:
    kind: GitRepository
    name: infrastructure
  validation: client
  healthChecks:
    - apiVersion: apps/v1
      kind: Deployment
      name: myapp
      namespace: production
```

## Secrets Management

### Using Azure Key Vault in Pipelines

```yaml
steps:
  - task: AzureKeyVault@2
    displayName: 'Retrieve Secrets from Key Vault'
    inputs:
      azureSubscription: $(azureSubscription)
      keyVaultName: 'myapp-keyvault'
      secretsFilter: '*'
      runAsPreJob: true

  - task: AzureCLI@2
    displayName: 'Use Secrets in Deployment'
    inputs:
      azureSubscription: $(azureSubscription)
      scriptType: 'bash'
      scriptLocation: 'inlineScript'
      inlineScript: |
        # Secrets available as pipeline variables
        az webapp config appsettings set \
          --resource-group $(resourceGroup) \
          --name $(webAppName) \
          --settings DatabasePassword=$(DatabasePassword)
```

### GitHub Actions with Key Vault

```yaml
steps:
  - name: Azure Login
    uses: azure/login@v1
    with:
      creds: ${{ secrets.AZURE_CREDENTIALS }}

  - name: Get Secrets from Key Vault
    uses: azure/get-keyvault-secrets@v1
    with:
      keyvault: 'myapp-keyvault'
      secrets: 'DatabasePassword, ApiKey'
    id: keyvault

  - name: Use Secrets
    run: |
      echo "Database password retrieved"
      # Use ${{ steps.keyvault.outputs.DatabasePassword }}
```

## Related Documentation

- @resource-management.md - Infrastructure as code fundamentals
- @cli-patterns.md - Scripting patterns for automation
- @troubleshooting.md - Pipeline debugging
- @../examples/environment-setup.md - Complete environment automation
