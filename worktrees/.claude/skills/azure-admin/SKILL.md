# Azure Administration Skill

## Skill Metadata

```yaml
name: azure-admin
version: 1.0.0
category: cloud-infrastructure
auto_activate_keywords:
  - azure
  - az cli
  - azd
  - entra id
  - azure ad
  - rbac
  - azure resource
  - subscription
  - resource group
  - service principal
  - managed identity
  - azure devops
  - azure portal
  - arm template
  - bicep
  - azure policy
  - cost management
  - azure mcp
tags:
  - cloud
  - identity
  - access-management
  - devops
  - infrastructure
  - automation
prerequisites:
  - Azure subscription access
  - Azure CLI installed (az)
  - Basic understanding of cloud concepts
related_skills:
  - devops
  - security
  - infrastructure-as-code
```

## Overview

This skill provides comprehensive Azure administration capabilities, covering identity management, resource orchestration, CLI tooling, and DevOps automation. It integrates Microsoft's Azure ecosystem including Azure CLI (az), Azure Developer CLI (azd), Entra ID (formerly Azure AD), and Azure MCP (Model Context Protocol) for AI-powered workflows.

**Core Capabilities:**

- **Identity & Access Management**: User provisioning, RBAC, service principals, managed identities
- **Resource Management**: Subscriptions, resource groups, ARM templates, Bicep deployments
- **CLI & Tooling**: az CLI patterns, azd workflows, PowerShell integration
- **MCP Integration**: Azure MCP server for AI-driven Azure operations
- **DevOps Automation**: CI/CD pipelines, infrastructure as code, deployment strategies
- **Cost & Governance**: Budget management, policy enforcement, compliance

**Target Audience:**
- Cloud administrators managing Azure environments
- DevOps engineers automating Azure deployments
- Security teams implementing RBAC and compliance
- Developers using Azure services and MCP integration

**Philosophy Alignment:**
This skill follows amplihack principles: ruthless simplicity, working code only, clear module boundaries, and systematic workflows.

## Quick Reference Matrix

### Common Task Mapping

| Task | Primary Tool | Secondary Tools | Skill Doc Reference |
|------|--------------|----------------|---------------------|
| Create user account | az cli | Entra ID Portal | @docs/user-management.md |
| Assign RBAC role | az cli | Azure Portal | @docs/role-assignments.md |
| Deploy resource group | az cli, Bicep | ARM templates | @docs/resource-management.md |
| Setup service principal | az cli | Portal | @docs/user-management.md#service-principals |
| Enable managed identity | az cli | Portal | @docs/user-management.md#managed-identities |
| Create resource | az cli, azd | Portal, Terraform | @docs/resource-management.md |
| Query resources | az cli --query | JMESPath | @docs/cli-patterns.md#querying |
| Bulk user operations | az cli + bash | PowerShell | @examples/bulk-user-onboarding.md |
| Environment provisioning | azd | az cli, Bicep | @examples/environment-setup.md |
| Audit role assignments | az cli | Azure Policy | @examples/role-audit.md |
| Cost analysis | az cli, Portal | Cost Management API | @docs/cost-optimization.md |
| MCP integration | Azure MCP | az cli | @docs/mcp-integration.md |
| CI/CD pipeline | Azure DevOps | GitHub Actions | @docs/devops-automation.md |

### Command Pattern Reference

```bash
# Identity operations
az ad user create --display-name "Jane Doe" --user-principal-name jane@domain.com
az ad sp create-for-rbac --name myServicePrincipal --role Contributor

# Resource operations
az group create --name myResourceGroup --location eastus
az deployment group create --resource-group myRG --template-file main.bicep

# RBAC operations
az role assignment create --assignee user@domain.com --role Reader --scope /subscriptions/xxx
az role assignment list --assignee user@domain.com --all

# Query patterns
az vm list --query "[?powerState=='VM running'].{Name:name, RG:resourceGroup}"
az resource list --resource-type "Microsoft.Compute/virtualMachines" --query "[].{name:name, location:location}"

# Cost management
az consumption usage list --start-date 2025-01-01 --end-date 2025-01-31
az cost-management query --type Usage --dataset-aggregation totalCost=sum(PreTaxCost)

# Azure Developer CLI (azd)
azd init --template todo-nodejs-mongo
azd up  # provision + deploy
azd env list
azd down
```

## Topic 1: Identity & Access Management

### Overview

Azure identity management centers on Entra ID (formerly Azure AD) for authentication and authorization. Key components include users, groups, service principals, managed identities, and RBAC (Role-Based Access Control).

### Users and Groups

**User Lifecycle:**
1. **Creation**: Provision users via az CLI, Portal, or bulk CSV import
2. **Authentication**: Configure MFA, conditional access, password policies
3. **Authorization**: Assign roles and permissions via RBAC
4. **Offboarding**: Disable accounts, revoke tokens, remove assignments

**Best Practices:**
- Use groups for role assignments (not individual users)
- Implement least privilege principle
- Enable MFA for all administrative accounts
- Regular access reviews and audits

**Common Operations:**

```bash
# Create user
az ad user create \
  --display-name "Jane Doe" \
  --user-principal-name jane@contoso.com \
  --password "SecureP@ssw0rd!" \
  --force-change-password-next-sign-in true

# Create security group
az ad group create \
  --display-name "Engineering Team" \
  --mail-nickname "engineering"

# Add user to group
az ad group member add \
  --group "Engineering Team" \
  --member-id $(az ad user show --id jane@contoso.com --query id -o tsv)

# List group members
az ad group member list --group "Engineering Team" --query "[].userPrincipalName"
```

### Service Principals

Service principals enable applications and services to authenticate to Azure. Two types:
1. **Application service principal**: Represents an app registration
2. **Managed identity**: Azure-managed service principal (no credential management)

**Creating Service Principals:**

```bash
# Create with Contributor role at subscription scope
az ad sp create-for-rbac \
  --name "myAppServicePrincipal" \
  --role Contributor \
  --scopes /subscriptions/{subscription-id}

# Create with custom role at resource group scope
az ad sp create-for-rbac \
  --name "myCustomSP" \
  --role "Custom Role Name" \
  --scopes /subscriptions/{sub-id}/resourceGroups/{rg-name}

# Create without role assignment (assign later)
az ad sp create-for-rbac --name "myBasicSP" --skip-assignment
```

**Security Best Practices:**
- Use managed identities instead of service principals when possible
- Rotate credentials regularly (90 days maximum)
- Store credentials in Azure Key Vault
- Use certificate-based authentication over secrets
- Limit scope to minimum required resources

### Managed Identities

Managed identities eliminate credential management by providing Azure resources with an identity in Entra ID.

**Types:**
1. **System-assigned**: Tied to resource lifecycle, deleted with resource
2. **User-assigned**: Independent lifecycle, can be shared across resources

**Common Use Cases:**
- VM accessing Key Vault secrets
- Function App connecting to Azure SQL
- Container instance pulling from Container Registry
- Logic App calling Azure APIs

**Enabling Managed Identity:**

```bash
# Enable system-assigned identity on VM
az vm identity assign --name myVM --resource-group myRG

# Create user-assigned identity
az identity create --name myManagedIdentity --resource-group myRG

# Assign user-assigned identity to VM
az vm identity assign \
  --name myVM \
  --resource-group myRG \
  --identities /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/myManagedIdentity

# Grant Key Vault access to managed identity
az keyvault set-policy \
  --name myKeyVault \
  --object-id $(az vm show --name myVM --resource-group myRG --query identity.principalId -o tsv) \
  --secret-permissions get list
```

### RBAC Fundamentals

Azure RBAC controls access to Azure resources through role assignments. The model consists of:
- **Security principal**: User, group, service principal, or managed identity
- **Role definition**: Collection of permissions (Owner, Contributor, Reader, custom)
- **Scope**: Resource, resource group, subscription, or management group

**Key Built-in Roles:**
- **Owner**: Full access including ability to assign roles
- **Contributor**: Create and manage resources, cannot assign roles
- **Reader**: View resources only
- **User Access Administrator**: Manage user access, cannot manage resources

See @docs/role-assignments.md for detailed role assignment patterns and custom role creation.

## Topic 2: Resource Management

### Resource Hierarchy

Azure organizes resources in a hierarchical structure:

```
Management Groups (optional)
└── Subscriptions
    └── Resource Groups
        └── Resources (VMs, databases, storage, etc.)
```

**Scope Levels:**
- **Management Group**: Organize multiple subscriptions, apply policies at scale
- **Subscription**: Billing boundary, service limits, access control boundary
- **Resource Group**: Logical container, lifecycle management, shared location
- **Resource**: Individual service instance

### Resource Groups

Resource groups are fundamental containers for managing related resources.

**Best Practices:**
- Group resources by lifecycle (e.g., dev/test/prod)
- One resource group per application or workload
- All resources in a group should share the same lifecycle
- Use consistent naming conventions
- Apply tags for cost tracking and organization

**Common Operations:**

```bash
# Create resource group
az group create --name myResourceGroup --location eastus

# List resource groups
az group list --query "[].{Name:name, Location:location, State:properties.provisioningState}"

# Show resources in group
az resource list --resource-group myResourceGroup --output table

# Delete resource group (deletes all resources)
az group delete --name myResourceGroup --yes --no-wait

# Lock resource group to prevent deletion
az lock create --name DontDelete --resource-group myResourceGroup --lock-type CanNotDelete

# Tag resource group
az group update --name myResourceGroup --tags Environment=Production CostCenter=IT Department=Engineering
```

### ARM Templates and Bicep

Azure Resource Manager (ARM) templates and Bicep enable infrastructure as code.

**ARM Templates** (JSON):
- Declarative syntax
- Native Azure format
- Verbose but comprehensive

**Bicep** (DSL):
- Cleaner syntax, easier to read
- Transpiles to ARM templates
- Recommended for new projects

**Bicep Example:**

```bicep
param location string = resourceGroup().location
param vmName string = 'myVM'
param vmSize string = 'Standard_B2s'

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2023-05-01' = {
  name: '${vmName}-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: ['10.0.0.0/16']
    }
    subnets: [
      {
        name: 'default'
        properties: {
          addressPrefix: '10.0.1.0/24'
        }
      }
    ]
  }
}

resource vm 'Microsoft.Compute/virtualMachines@2023-07-01' = {
  name: vmName
  location: location
  properties: {
    hardwareProfile: {
      vmSize: vmSize
    }
    // ... additional configuration
  }
}
```

**Deployment Commands:**

```bash
# Deploy Bicep template
az deployment group create \
  --resource-group myRG \
  --template-file main.bicep \
  --parameters vmName=myVM vmSize=Standard_B2s

# Validate template before deployment
az deployment group validate \
  --resource-group myRG \
  --template-file main.bicep

# What-if analysis (preview changes)
az deployment group what-if \
  --resource-group myRG \
  --template-file main.bicep
```

### Resource Tagging Strategy

Tags enable organization, cost tracking, and automation.

**Common Tag Schemas:**
```json
{
  "Environment": "Production",
  "CostCenter": "Engineering",
  "Owner": "jane@contoso.com",
  "Application": "CustomerPortal",
  "Criticality": "High",
  "Compliance": "PCI-DSS",
  "BackupPolicy": "Daily",
  "ExpirationDate": "2025-12-31"
}
```

**Tagging Operations:**

```bash
# Tag resource
az resource tag \
  --tags Environment=Production CostCenter=Engineering \
  --ids /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/myVM

# Query resources by tag
az resource list --tag Environment=Production --query "[].{Name:name, Type:type, Location:location}"

# Apply tags at resource group level (inherited by resources)
az group update --name myRG --tags Department=IT Owner=admin@contoso.com
```

See @docs/resource-management.md for advanced patterns including move operations, locks, and multi-region deployments.

## Topic 3: CLI & Tooling

### Azure CLI (az)

The Azure CLI is the primary command-line tool for Azure management.

**Installation:**
```bash
# macOS (Homebrew)
brew install azure-cli

# Linux
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Verify installation
az --version
```

**Authentication:**
```bash
# Interactive login
az login

# Login with service principal
az login --service-principal \
  --username {app-id} \
  --password {password-or-cert} \
  --tenant {tenant-id}

# Login with managed identity (from Azure VM/Container)
az login --identity

# Set active subscription
az account set --subscription "My Subscription Name"

# Show current context
az account show
```

### Query Patterns with JMESPath

Azure CLI uses JMESPath for output filtering and transformation.

**Essential Query Patterns:**

```bash
# Basic filtering
az vm list --query "[?powerState=='VM running']"

# Projection (select specific fields)
az vm list --query "[].{Name:name, RG:resourceGroup, Location:location}"

# Sorting
az vm list --query "sort_by([],&name)"

# Contains filter
az resource list --query "[?contains(name, 'prod')]"

# Multiple conditions
az vm list --query "[?powerState=='VM running' && location=='eastus']"

# Nested queries
az vm list --query "[].{Name:name, OS:storageProfile.osDisk.osType}"

# Count results
az vm list --query "length([])"
```

See @docs/cli-patterns.md for advanced query patterns, batch operations, and scripting best practices.

### Azure Developer CLI (azd)

The Azure Developer CLI (azd) streamlines development workflows and environment management.

**Core Concepts:**
- **Templates**: Pre-built application architectures
- **Environments**: Named deployment targets (dev, test, prod)
- **Infrastructure**: Bicep files in `infra/` directory
- **Services**: Application code in `src/` directory

**Common Workflows:**

```bash
# Initialize new project from template
azd init --template todo-nodejs-mongo

# Provision infrastructure and deploy code
azd up

# Deploy code only (skip infrastructure)
azd deploy

# Provision infrastructure only
azd provision

# Manage environments
azd env new development
azd env select production
azd env list
azd env get-values

# Monitor application
azd monitor --overview
azd monitor --logs

# Clean up resources
azd down
```

**Custom Templates:**
Create your own azd templates with this structure:
```
my-template/
├── azure.yaml           # azd configuration
├── infra/
│   ├── main.bicep      # Infrastructure definition
│   └── main.parameters.json
└── src/
    └── [application code]
```

### PowerShell Integration

Azure PowerShell provides cmdlet-based management.

```powershell
# Install Azure PowerShell module
Install-Module -Name Az -Repository PSGallery -Force

# Connect to Azure
Connect-AzAccount

# Get VMs
Get-AzVM | Select-Object Name, ResourceGroupName, Location

# Create resource group
New-AzResourceGroup -Name "myRG" -Location "eastus"
```

## Topic 4: MCP Integration

### Azure MCP Overview

Azure MCP (Model Context Protocol) enables AI applications to interact with Azure services through a standardized interface. The Azure MCP server provides tools for resource management, identity operations, and data retrieval.

**Key Capabilities:**
- List and manage Azure resources
- Query resource properties and metadata
- Execute Azure CLI commands through MCP
- Integrate with Claude Code and other AI workflows

### Installation and Setup

**Prerequisites:**
- Node.js 18+ installed
- Azure CLI installed and authenticated
- Active Azure subscription

**Installation:**

```bash
# Install Azure MCP server
npm install -g @modelcontextprotocol/server-azure

# Or install locally in project
npm install @modelcontextprotocol/server-azure
```

**Configuration for Claude Code:**

Add to your MCP settings file (`~/.config/claude-code/mcp.json`):

```json
{
  "mcpServers": {
    "azure": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-azure"],
      "env": {
        "AZURE_SUBSCRIPTION_ID": "your-subscription-id"
      }
    }
  }
}
```

### MCP Tools Reference

The Azure MCP server exposes these tools:

**Resource Management:**
- `azure_list_resources`: List resources in subscription or resource group
- `azure_get_resource`: Get detailed information about a specific resource
- `azure_create_resource`: Create a new Azure resource
- `azure_delete_resource`: Delete an existing resource

**Identity Operations:**
- `azure_list_users`: List Entra ID users
- `azure_get_user`: Get user details
- `azure_list_service_principals`: List service principals
- `azure_list_role_assignments`: List RBAC assignments

**Query Operations:**
- `azure_query`: Execute Azure Resource Graph queries
- `azure_cli`: Execute arbitrary az CLI commands

### Usage Patterns

**Example: List VMs through MCP**

When Azure MCP is configured, you can ask Claude Code:

"Show me all running VMs in my subscription"

Claude Code will use the `azure_list_resources` MCP tool:
```json
{
  "tool": "azure_list_resources",
  "parameters": {
    "resourceType": "Microsoft.Compute/virtualMachines",
    "filter": "powerState eq 'VM running'"
  }
}
```

**Example: Query cost information**

"What are my top 5 most expensive resources this month?"

Claude Code combines MCP tools to:
1. Query cost data with `azure_query`
2. Aggregate and sort results
3. Present formatted output

See @docs/mcp-integration.md for complete MCP tool reference and integration patterns.

## Topic 5: DevOps Automation

### CI/CD with Azure DevOps

Azure DevOps provides end-to-end DevOps capabilities including pipelines, repos, boards, and artifacts.

**Pipeline Types:**
- **Build pipelines**: Compile code, run tests, create artifacts
- **Release pipelines**: Deploy artifacts to environments
- **YAML pipelines**: Infrastructure as code for CI/CD

**Basic YAML Pipeline:**

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  azureSubscription: 'myServiceConnection'
  resourceGroup: 'myRG'

stages:
  - stage: Build
    jobs:
      - job: BuildJob
        steps:
          - task: AzureCLI@2
            inputs:
              azureSubscription: $(azureSubscription)
              scriptType: bash
              scriptLocation: inlineScript
              inlineScript: |
                az --version
                az group list

  - stage: Deploy
    dependsOn: Build
    jobs:
      - deployment: DeployInfra
        environment: production
        strategy:
          runOnce:
            deploy:
              steps:
                - task: AzureResourceManagerTemplateDeployment@3
                  inputs:
                    azureResourceManagerConnection: $(azureSubscription)
                    resourceGroupName: $(resourceGroup)
                    location: eastus
                    templateLocation: Linked artifact
                    csmFile: $(Pipeline.Workspace)/infra/main.bicep
```

### GitHub Actions Integration

GitHub Actions can deploy to Azure using service principal authentication.

```yaml
name: Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Deploy Bicep
        uses: azure/arm-deploy@v1
        with:
          subscriptionId: ${{ secrets.AZURE_SUBSCRIPTION }}
          resourceGroupName: myRG
          template: ./infra/main.bicep
          parameters: environment=production
```

### Infrastructure as Code Best Practices

1. **Version Control**: Store all IaC in Git
2. **Modularity**: Create reusable Bicep modules
3. **Parameter Files**: Separate config per environment
4. **State Management**: Use Azure or Terraform state backends
5. **Testing**: Validate templates before deployment
6. **Documentation**: Document architecture decisions

See @docs/devops-automation.md for advanced pipeline patterns, blue-green deployments, and GitOps workflows.

## Topic 6: Cost & Governance

### Cost Management

Azure Cost Management provides visibility into spending and optimization recommendations.

**Cost Analysis Commands:**

```bash
# View current month costs by resource group
az costmanagement query \
  --type ActualCost \
  --dataset-aggregation name=Cost,function=Sum \
  --dataset-grouping name=ResourceGroup,type=Dimension \
  --timeframe MonthToDate

# Get consumption usage
az consumption usage list \
  --start-date 2025-01-01 \
  --end-date 2025-01-31 \
  --query "[].{Date:usageStart, Service:meterName, Cost:pretaxCost}"
```

**Cost Optimization Strategies:**
1. **Right-size resources**: Use appropriate VM sizes
2. **Reserved instances**: Commit to 1-3 year terms for 30-70% savings
3. **Spot instances**: Use for fault-tolerant workloads
4. **Auto-shutdown**: Schedule VM shutdowns during off-hours
5. **Storage tiering**: Move cold data to Archive tier
6. **Delete unused resources**: Regular cleanup audits

### Azure Policy

Azure Policy enforces organizational standards and compliance.

**Built-in Policies:**
- Require tags on resources
- Allowed resource locations
- Allowed VM SKUs
- Require encryption at rest

**Assigning Policies:**

```bash
# List built-in policies
az policy definition list --query "[?policyType=='BuiltIn'].{Name:displayName, ID:name}" --output table

# Assign policy to resource group
az policy assignment create \
  --name "require-tag-environment" \
  --policy "require-tag-on-resources" \
  --params '{"tagName":{"value":"Environment"}}' \
  --resource-group myRG
```

See @docs/cost-optimization.md for budgets, alerts, and detailed optimization patterns.

## Troubleshooting

### Common Issues and Solutions

**Authentication Errors:**
```bash
# Clear cached credentials
az logout
az login --use-device-code

# Verify tenant and subscription
az account show
az account tenant list
```

**Permission Denied:**
- Verify RBAC role assignments: `az role assignment list --assignee {user-or-sp}`
- Check resource provider registration: `az provider list --query "[?registrationState=='NotRegistered']"`
- Ensure proper scope (subscription vs resource group)

**Resource Not Found:**
- Verify subscription context: `az account show`
- Check resource group: `az group exists --name {rg-name}`
- Search across subscriptions: `az resource list --name {resource-name}`

**Quota Exceeded:**
```bash
# Check current quotas
az vm list-usage --location eastus --output table

# Request quota increase through portal or support ticket
```

**CLI Tool Issues:**
- Update to latest version: `az upgrade`
- Clear cache: `rm -rf ~/.azure/`
- Reinstall extensions: `az extension list-available`

See @docs/troubleshooting.md for comprehensive debugging guide including network issues, deployment failures, and performance problems.

## Certification Path

**Azure Administrator Associate (AZ-104):**
- Prerequisites: 6 months hands-on Azure experience
- Domains: Identity, governance, storage, compute, networking, monitoring
- Study Resources: @references/az-104-guide.md
- Hands-on Practice: Azure free account, Microsoft Learn labs

**Next Steps:**
- Azure Solutions Architect Expert (AZ-305)
- Azure DevOps Engineer Expert (AZ-400)
- Azure Security Engineer Associate (AZ-500)

## Further Learning

**Documentation:**
- @docs/user-management.md - Complete user and identity operations
- @docs/role-assignments.md - RBAC patterns and custom roles
- @docs/resource-management.md - Advanced resource operations
- @docs/mcp-integration.md - MCP tools and workflows
- @docs/cli-patterns.md - Advanced CLI scripting
- @docs/devops-automation.md - CI/CD and GitOps
- @docs/cost-optimization.md - Cost management strategies
- @docs/troubleshooting.md - Debugging and resolution

**Examples:**
- @examples/bulk-user-onboarding.md - Automated user provisioning
- @examples/environment-setup.md - Complete environment deployment
- @examples/role-audit.md - RBAC compliance auditing
- @examples/mcp-workflow.md - AI-powered Azure operations

**References:**
- @references/microsoft-learn.md - Official learning paths
- @references/az-104-guide.md - Certification preparation
- @references/api-references.md - API and SDK documentation
