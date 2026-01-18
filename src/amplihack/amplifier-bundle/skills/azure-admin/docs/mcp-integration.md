# Azure MCP Integration

Guide to integrating Azure MCP (Model Context Protocol) server with Claude Code for AI-powered Azure operations.

## Table of Contents

1. [Overview](#overview)
2. [Installation and Setup](#installation-and-setup)
3. [Available Tools](#available-tools)
4. [Usage Patterns](#usage-patterns)
5. [Advanced Workflows](#advanced-workflows)
6. [Troubleshooting](#troubleshooting)

## Overview

Azure MCP provides a standardized interface for AI applications to interact with Azure services. It exposes Azure management operations as MCP tools that Claude Code can invoke directly.

### Benefits

- **Natural language Azure operations**: "Show me all VMs" instead of complex CLI commands
- **Contextual awareness**: MCP maintains session context across multiple operations
- **Error handling**: Automatic retry and fallback mechanisms
- **Type safety**: Validated inputs and structured outputs
- **Multi-operation workflows**: Compose complex operations from simple tools

### Architecture

```
Claude Code
    ↓
MCP Protocol
    ↓
Azure MCP Server
    ↓
Azure CLI / SDK
    ↓
Azure APIs
```

## Installation and Setup

### Prerequisites

```bash
# Verify Node.js 18+ installed
node --version  # Should be >= 18.0.0

# Verify Azure CLI authenticated
az account show
```

### Install Azure MCP Server

```bash
# Global installation (recommended)
npm install -g @modelcontextprotocol/server-azure

# Verify installation
npx @modelcontextprotocol/server-azure --version
```

### Configure Claude Code

Add to `~/.config/claude-code/mcp.json`:

```json
{
  "mcpServers": {
    "azure": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-azure"],
      "env": {
        "AZURE_SUBSCRIPTION_ID": "your-subscription-id",
        "AZURE_TENANT_ID": "your-tenant-id"
      }
    }
  }
}
```

### Get Subscription and Tenant IDs

```bash
# Get subscription ID
az account show --query id -o tsv

# Get tenant ID
az account show --query tenantId -o tsv

# List all subscriptions
az account list --query "[].{Name:name, ID:id, TenantID:tenantId}" --output table
```

### Verify MCP Configuration

Restart Claude Code and test:

```
List all my Azure resource groups
```

If MCP is configured correctly, Claude Code will use the `azure_list_resources` tool instead of running `az` commands directly.

## Available Tools

### Resource Management Tools

**azure_list_resources**

- **Purpose**: List resources in subscription or resource group
- **Parameters**:
  - `resourceGroup` (optional): Filter by resource group
  - `resourceType` (optional): Filter by resource type
  - `location` (optional): Filter by location
  - `tags` (optional): Filter by tags

**Example usage:**

```
Show all VMs in my subscription
Show storage accounts in resource group "production-rg"
List all resources tagged with Environment=Production
```

**azure_get_resource**

- **Purpose**: Get detailed information about a specific resource
- **Parameters**:
  - `resourceId`: Full resource ID or resource name
  - `resourceGroup`: Resource group name (if using resource name)
  - `resourceType`: Resource type (if using resource name)

**Example usage:**

```
Show details for VM named "myVM" in resource group "myRG"
Get information about resource ID /subscriptions/.../virtualMachines/myVM
```

**azure_create_resource**

- **Purpose**: Create a new Azure resource
- **Parameters**:
  - `resourceGroup`: Target resource group
  - `resourceType`: Type of resource to create
  - `name`: Resource name
  - `location`: Azure region
  - `properties`: Resource-specific properties (JSON)

**Example usage:**

```
Create a storage account named "mystorageaccount" in resource group "myRG" in eastus
Create a virtual network named "myVNet" with address space 10.0.0.0/16
```

**azure_delete_resource**

- **Purpose**: Delete an existing resource
- **Parameters**:
  - `resourceId`: Full resource ID
  - `noWait` (optional): Don't wait for deletion to complete

**Example usage:**

```
Delete the VM named "testVM" in resource group "dev-rg"
Remove all resources tagged with Environment=Temporary
```

### Identity and Access Tools

**azure_list_users**

- **Purpose**: List Entra ID users
- **Parameters**:
  - `filter` (optional): OData filter expression
  - `top` (optional): Limit results

**Example usage:**

```
List all users in Entra ID
Show users in the Engineering department
Find users with email starting with "john"
```

**azure_get_user**

- **Purpose**: Get detailed user information
- **Parameters**:
  - `userId`: User principal name or object ID

**Example usage:**

```
Show details for user jane@contoso.com
Get information about user with ID 12345678-1234-1234-1234-123456789012
```

**azure_list_service_principals**

- **Purpose**: List service principals
- **Parameters**:
  - `filter` (optional): OData filter expression

**Example usage:**

```
List all service principals
Show service principals for my application
```

**azure_list_role_assignments**

- **Purpose**: List RBAC role assignments
- **Parameters**:
  - `scope` (optional): Limit to specific scope
  - `principalId` (optional): Filter by principal
  - `roleDefinitionName` (optional): Filter by role

**Example usage:**

```
List all role assignments in my subscription
Show role assignments for user jane@contoso.com
Find all Owner role assignments
```

### Query Tools

**azure_query**

- **Purpose**: Execute Azure Resource Graph queries
- **Parameters**:
  - `query`: KQL (Kusto Query Language) query string

**Example usage:**

```
Query all VMs with their power state
Find resources created in the last 7 days
Show cost by resource group for this month
```

**azure_cli**

- **Purpose**: Execute arbitrary az CLI commands
- **Parameters**:
  - `command`: CLI command to execute (without "az" prefix)

**Example usage:**

```
Run: az vm list --query "[?powerState=='VM running']"
Execute: az account show
```

## Usage Patterns

### Pattern 1: Resource Discovery

```
# Natural language → MCP tool invocation
User: "Show me all my storage accounts"

Claude Code uses azure_list_resources:
{
  "tool": "azure_list_resources",
  "parameters": {
    "resourceType": "Microsoft.Storage/storageAccounts"
  }
}

# Response formatted for user
Found 3 storage accounts:
- mystorageaccount (eastus, Standard_LRS)
- prodstorageaccount (westus, Premium_LRS)
- backupstorage (centralus, Standard_GRS)
```

### Pattern 2: Multi-Step Operations

```
User: "Create a new VM in resource group 'dev-rg' and assign me Reader access"

Step 1: azure_create_resource (create VM)
Step 2: azure_list_users (find user)
Step 3: azure_cli (assign role)

Complete workflow automated by Claude Code
```

### Pattern 3: Compliance Checking

```
User: "Find all storage accounts without encryption enabled"

Step 1: azure_list_resources (get all storage accounts)
Step 2: azure_get_resource (check each for encryption property)
Step 3: Format results showing non-compliant accounts
```

### Pattern 4: Cost Analysis

```
User: "What are my top 5 most expensive resources this month?"

Step 1: azure_query (Resource Graph query for cost data)
Step 2: Aggregate and sort by cost
Step 3: Present formatted table with costs
```

## Advanced Workflows

### Automated Resource Tagging

```python
# Claude Code can compose this workflow using MCP tools

# 1. Get all untagged resources
untagged_resources = azure_list_resources(filter="tags eq null")

# 2. For each resource, infer tags based on naming convention
for resource in untagged_resources:
    tags = infer_tags_from_name(resource.name)

# 3. Apply tags
    azure_cli(f"resource tag --tags {tags} --ids {resource.id}")

# 4. Generate report
print(f"Tagged {len(untagged_resources)} resources")
```

### Automated Access Review

```python
# Complete access review workflow

# 1. List all role assignments
assignments = azure_list_role_assignments()

# 2. For each Owner/Contributor role
high_privilege = [a for a in assignments if a.role in ['Owner', 'Contributor']]

# 3. Check last sign-in for each user
for assignment in high_privilege:
    user = azure_get_user(assignment.principalId)
    if days_since_last_signin(user) > 90:
        # Flag for review
        report_stale_access(assignment)

# 4. Generate compliance report
```

### Environment Provisioning

```
User: "Setup a complete dev environment for the new project"

Claude Code orchestrates:
1. azure_create_resource: Resource group
2. azure_create_resource: Virtual network
3. azure_create_resource: Storage account
4. azure_create_resource: App Service Plan
5. azure_create_resource: App Service
6. azure_create_resource: SQL Database
7. azure_create_resource: Key Vault
8. azure_cli: Configure networking
9. azure_cli: Apply tags
10. azure_list_role_assignments: Grant team access

Complete environment ready in minutes
```

### Resource Cleanup

```
User: "Delete all dev resources older than 30 days"

Claude Code workflow:
1. azure_query: Find dev resources by tag and creation date
2. Confirm with user (list resources to delete)
3. azure_delete_resource: Delete each resource (parallel)
4. Report: Resources deleted, estimated cost savings
```

## Troubleshooting

### MCP Server Not Responding

**Symptom**: Claude Code doesn't use Azure MCP tools

**Solutions**:

```bash
# 1. Verify MCP server installation
npx @modelcontextprotocol/server-azure --version

# 2. Check MCP configuration file
cat ~/.config/claude-code/mcp.json

# 3. Verify Azure CLI authentication
az account show

# 4. Check subscription ID in config matches current subscription
az account show --query id -o tsv

# 5. Restart Claude Code
```

### Authentication Errors

**Symptom**: "Authentication failed" or "Unauthorized"

**Solutions**:

```bash
# Re-authenticate Azure CLI
az logout
az login

# Verify subscription access
az account list --output table

# Check environment variables in MCP config
echo $AZURE_SUBSCRIPTION_ID
echo $AZURE_TENANT_ID

# Update MCP config with correct values
```

### Permission Denied

**Symptom**: "Insufficient privileges" errors

**Solutions**:

```bash
# Check your role assignments
az role assignment list \
  --assignee $(az ad signed-in-user show --query id -o tsv) \
  --all

# Verify you have at least Reader role at subscription level
# Request appropriate access from subscription administrator
```

### Tool Not Found

**Symptom**: "Tool azure_list_resources not found"

**Solutions**:

1. Verify MCP server version: `npm list -g @modelcontextprotocol/server-azure`
2. Update to latest: `npm update -g @modelcontextprotocol/server-azure`
3. Check MCP server logs for errors
4. Restart Claude Code

### Slow Performance

**Symptom**: MCP operations take a long time

**Optimizations**:

1. **Use filters**: Always filter queries to reduce data transfer
2. **Cache results**: MCP maintains session cache automatically
3. **Parallel operations**: Request multiple resources simultaneously
4. **Specific queries**: Use Resource Graph queries instead of listing all resources

```
# Slow
"List all resources and find VMs"

# Fast
"List all VMs" (uses resourceType filter)
```

### Debugging MCP Requests

Enable debug logging:

```json
{
  "mcpServers": {
    "azure": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-azure"],
      "env": {
        "AZURE_SUBSCRIPTION_ID": "your-subscription-id",
        "AZURE_TENANT_ID": "your-tenant-id",
        "DEBUG": "mcp:*"
      }
    }
  }
}
```

View logs in Claude Code console.

## Best Practices

1. **Use natural language**: Let Claude Code translate to MCP tools
2. **Be specific**: "VMs in production-rg" vs "show me stuff"
3. **Confirm destructive operations**: MCP will ask before deleting
4. **Leverage multi-step workflows**: Combine operations for complex tasks
5. **Use filters**: Narrow results for faster responses
6. **Check permissions first**: Verify access before attempting operations

## Related Documentation

- @user-management.md - Identity operations via MCP
- @role-assignments.md - RBAC through MCP tools
- @resource-management.md - Resource lifecycle with MCP
- @cli-patterns.md - When to use CLI vs MCP
- @../examples/mcp-workflow.md - Complete MCP workflow examples
