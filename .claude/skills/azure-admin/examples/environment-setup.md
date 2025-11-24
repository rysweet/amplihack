# Complete Environment Setup with azd

Automated deployment of a complete Azure environment for a production web application using Azure Developer CLI (azd) and Bicep.

## Scenario

Deploy a production-ready environment for a Node.js web application with:

- Resource group with proper naming and tagging
- Virtual Network with subnets
- App Service Plan and App Service
- Azure SQL Database
- Azure Storage Account
- Application Insights
- Key Vault for secrets
- Proper networking and security configuration

## Prerequisites

- Azure CLI and azd installed
- Azure subscription with Contributor access
- Bicep CLI
- Git repository for infrastructure code

## Project Structure

```
myapp-infrastructure/
├── azure.yaml                 # azd configuration
├── infra/
│   ├── main.bicep            # Main infrastructure template
│   ├── modules/
│   │   ├── network.bicep     # Virtual network module
│   │   ├── app-service.bicep # App Service module
│   │   ├── database.bicep    # SQL Database module
│   │   ├── storage.bicep     # Storage Account module
│   │   └── keyvault.bicep    # Key Vault module
│   └── parameters/
│       ├── dev.json
│       ├── staging.json
│       └── prod.json
└── src/
    └── [application code]
```

## Step 1: Initialize azd Project

```bash
# Create new directory
mkdir myapp-infrastructure && cd myapp-infrastructure

# Initialize azd project
azd init --template minimal

# Or start from scratch
azd init
```

## Step 2: Configure azure.yaml

```yaml
# azure.yaml
name: myapp
metadata:
  template: myapp-infrastructure@0.0.1

services:
  web:
    project: ./src
    language: js
    host: appservice

infra:
  provider: bicep
  path: infra
  module: main
```

## Step 3: Create Main Bicep Template

```bicep
// infra/main.bicep
targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment (e.g., dev, staging, prod)')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('Resource tags')
param tags object = {}

// Generate unique resource names
var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

// Create resource group
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: '${abbrs.resourcesResourceGroups}${environmentName}-${resourceToken}'
  location: location
  tags: union(tags, {
    Environment: environmentName
    ManagedBy: 'azd'
  })
}

// Deploy network module
module network 'modules/network.bicep' = {
  name: 'network-deployment'
  scope: rg
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
  }
}

// Deploy app service module
module appService 'modules/app-service.bicep' = {
  name: 'app-service-deployment'
  scope: rg
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
    subnetId: network.outputs.appSubnetId
  }
}

// Deploy database module
module database 'modules/database.bicep' = {
  name: 'database-deployment'
  scope: rg
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
    subnetId: network.outputs.dataSubnetId
  }
}

// Deploy storage module
module storage 'modules/storage.bicep' = {
  name: 'storage-deployment'
  scope: rg
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
  }
}

// Deploy Key Vault module
module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault-deployment'
  scope: rg
  params: {
    location: location
    environmentName: environmentName
    resourceToken: resourceToken
    appServicePrincipalId: appService.outputs.identityPrincipalId
  }
}

// Outputs
output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_APP_SERVICE_NAME string = appService.outputs.appServiceName
output AZURE_DATABASE_CONNECTION_STRING string = database.outputs.connectionString
output AZURE_STORAGE_ACCOUNT_NAME string = storage.outputs.storageAccountName
output AZURE_KEY_VAULT_NAME string = keyVault.outputs.keyVaultName
```

## Step 4: Create Network Module

```bicep
// infra/modules/network.bicep
param location string
param environmentName string
param resourceToken string

var vnetName = 'vnet-${environmentName}-${resourceToken}'
var appSubnetName = 'subnet-app'
var dataSubnetName = 'subnet-data'

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: ['10.0.0.0/16']
    }
    subnets: [
      {
        name: appSubnetName
        properties: {
          addressPrefix: '10.0.1.0/24'
          delegations: [
            {
              name: 'appservice-delegation'
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
          serviceEndpoints: [
            {
              service: 'Microsoft.Storage'
            }
            {
              service: 'Microsoft.Sql'
            }
            {
              service: 'Microsoft.KeyVault'
            }
          ]
        }
      }
      {
        name: dataSubnetName
        properties: {
          addressPrefix: '10.0.2.0/24'
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output appSubnetId string = vnet.properties.subnets[0].id
output dataSubnetId string = vnet.properties.subnets[1].id
```

## Step 5: Deploy with azd

```bash
# Login to Azure
azd auth login

# Create new environment
azd env new dev

# Set environment variables
azd env set AZURE_LOCATION eastus

# Provision infrastructure
azd provision

# Deploy application
azd deploy

# Or do both in one command
azd up

# Monitor deployment
azd monitor --overview
```

## Step 6: Multi-Environment Deployment

```bash
# Development environment
azd env new development
azd env set AZURE_LOCATION eastus
azd up

# Staging environment
azd env new staging
azd env set AZURE_LOCATION westus
azd up

# Production environment
azd env new production
azd env set AZURE_LOCATION centralus
azd up

# List environments
azd env list

# Switch between environments
azd env select development
azd deploy

azd env select production
azd deploy
```

## Step 7: CI/CD Integration

```yaml
# .github/workflows/azure-dev.yml
name: Azure Dev

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    env:
      AZURE_CLIENT_ID: ${{ secrets.AZURE_CLIENT_ID }}
      AZURE_TENANT_ID: ${{ secrets.AZURE_TENANT_ID }}
      AZURE_SUBSCRIPTION_ID: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      AZURE_ENV_NAME: ${{ secrets.AZURE_ENV_NAME }}
      AZURE_LOCATION: ${{ secrets.AZURE_LOCATION }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Install azd
        uses: Azure/setup-azd@v0.1.0

      - name: Log in with Azure (Federated Credentials)
        run: |
          azd auth login \
            --client-id "$AZURE_CLIENT_ID" \
            --federated-credential-provider "github" \
            --tenant-id "$AZURE_TENANT_ID"

      - name: Provision Infrastructure
        run: azd provision --no-prompt

      - name: Deploy Application
        run: azd deploy --no-prompt
```

## Cleanup

```bash
# Delete all resources in an environment
azd down

# Delete specific environment
azd env select dev
azd down --purge

# List what will be deleted first
azd down --what-if
```

## Advanced: Custom Hooks

Create `.azd/hooks/preprovision.sh` for custom logic before provisioning:

```bash
#!/bin/bash
# .azd/hooks/preprovision.sh

set -e

echo "Running pre-provision validation..."

# Check required tools
command -v az >/dev/null 2>&1 || { echo "Azure CLI required"; exit 1; }
command -v bicep >/dev/null 2>&1 || { echo "Bicep CLI required"; exit 1; }

# Validate Bicep templates
echo "Validating Bicep templates..."
az bicep build --file infra/main.bicep

echo "✓ Pre-provision checks passed"
```

## Related Documentation

- @docs/resource-management.md - Bicep and ARM templates
- @docs/devops-automation.md - CI/CD pipelines
- @docs/cli-patterns.md - azd CLI patterns
- @../examples/mcp-workflow.md - MCP-powered environment management
