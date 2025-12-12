# Azure MCP Workflow Examples

AI-powered Azure operations using Claude Code with Azure MCP integration.

## Scenario 1: Resource Discovery and Analysis

**User Request:** "Show me all my VMs and tell me which ones are oversized"

**Claude Code Workflow:**

1. Uses `azure_list_resources` MCP tool to get all VMs
2. Uses `azure_get_resource` for each VM to check metrics
3. Analyzes CPU/memory utilization
4. Recommends appropriate VM sizes
5. Calculates potential cost savings

**Example Interaction:**
```
User: Show me all my VMs and tell me which ones are oversized

Claude Code: I'll analyze your VMs for optimization opportunities.

[Uses azure_list_resources with resourceType="Microsoft.Compute/virtualMachines"]

Found 8 VMs across 3 resource groups:

Oversized VMs (< 10% avg CPU):
1. myVM-prod-1 (Standard_D8s_v3)
   - Average CPU: 6%
   - Recommendation: Downsize to Standard_D2s_v3
   - Potential savings: $450/month

2. myVM-dev-2 (Standard_D4s_v3)
   - Average CPU: 8%
   - Recommendation: Downsize to Standard_B2ms
   - Potential savings: $180/month

Appropriately sized VMs:
- myVM-app-1 (Standard_D4s_v3) - 45% avg CPU
- myVM-app-2 (Standard_D4s_v3) - 52% avg CPU
...

Total potential savings: $630/month

Would you like me to resize these VMs?
```

## Scenario 2: Compliance Audit

**User Request:** "Find all storage accounts without encryption enabled"

**Claude Code Workflow:**

1. Uses `azure_list_resources` to get all storage accounts
2. Uses `azure_get_resource` to check encryption settings
3. Identifies non-compliant resources
4. Offers to remediate

**Example:**
```
User: Find all storage accounts without encryption enabled

Claude Code: I'll check encryption settings for all storage accounts.

[Uses azure_list_resources with resourceType="Microsoft.Storage/storageAccounts"]
[Checks each storage account for encryption properties]

Non-Compliant Storage Accounts:
1. mystoragedev123 (dev-rg)
   - Blob encryption: Disabled
   - File encryption: Disabled

2. legacystorage456 (legacy-rg)
   - Blob encryption: Enabled
   - File encryption: Disabled

Compliant Storage Accounts: 5

Would you like me to enable encryption for the non-compliant accounts?
```

## Scenario 3: Cost Analysis

**User Request:** "What are my top 5 most expensive resources this month?"

**Claude Code Workflow:**

1. Uses `azure_query` with Resource Graph to get cost data
2. Aggregates and sorts by cost
3. Provides breakdown with recommendations

**Example:**
```
User: What are my top 5 most expensive resources this month?

Claude Code: [Uses azure_query for cost data]

Top 5 Most Expensive Resources (Current Month):

1. myVM-prod-large (Virtual Machine)
   - Cost: $1,245
   - Resource Group: production-rg
   - Size: Standard_D32s_v3
   - Recommendation: Review utilization, consider reserved instance

2. mysqlserver-prod (SQL Database)
   - Cost: $890
   - Resource Group: production-rg
   - Tier: Premium P2
   - Recommendation: Evaluate data usage patterns

3. aks-cluster-prod (Kubernetes Service)
   - Cost: $675
   - Resource Group: production-rg
   - Nodes: 8 (Standard_D4s_v3)
   - Recommendation: Enable auto-scaling

4. storage-prod-logs (Storage Account)
   - Cost: $432
   - Resource Group: production-rg
   - Type: Premium LRS
   - Recommendation: Move old logs to Cool tier

5. appgw-prod (Application Gateway)
   - Cost: $380
   - Resource Group: production-rg
   - SKU: WAF_v2
   - Status: Optimal

Total: $3,622 (78% of subscription spend)

Would you like detailed optimization recommendations?
```

## Scenario 4: Automated Cleanup

**User Request:** "Delete all dev resources older than 30 days"

**Claude Code Workflow:**

1. Uses `azure_query` to find old dev resources
2. Shows list for confirmation
3. Uses `azure_delete_resource` for each resource
4. Provides summary

**Example:**
```
User: Delete all dev resources older than 30 days

Claude Code: I'll find dev resources created more than 30 days ago.

[Uses azure_query with date filter and Environment=Dev tag]

Found 12 resources older than 30 days in dev environment:

VMs (4):
- myVM-dev-old1 (created: 45 days ago)
- myVM-dev-test2 (created: 38 days ago)
- myVM-dev-temp3 (created: 62 days ago)
- myVM-dev-experiment (created: 91 days ago)

Storage Accounts (3):
- devstorageold123 (created: 55 days ago)
- tempdevstg456 (created: 70 days ago)
- devstoragebak789 (created: 102 days ago)

SQL Databases (2):
- sqldb-dev-old (created: 48 days ago)
- testdb-dev (created: 67 days ago)

Other Resources (3):
- devnet-vnet (VNet, 88 days old)
- dev-nsg (NSG, 95 days old)
- dev-pip (Public IP, 101 days old)

Estimated monthly savings: $285

⚠️  This action is irreversible. Proceed with deletion? (yes/no)

User: yes

Claude Code: [Deletes each resource using azure_delete_resource]

Deletion Progress:
✓ myVM-dev-old1
✓ myVM-dev-test2
✓ myVM-dev-temp3
... (progress for all resources)

Summary:
- Total deleted: 12 resources
- Estimated monthly savings: $285
- Deletion time: 3m 42s
```

## Scenario 5: Access Review

**User Request:** "Show me all users with Owner access and when they last logged in"

**Claude Code Workflow:**

1. Uses `azure_list_role_assignments` with role filter
2. Uses `azure_get_user` for sign-in data
3. Highlights stale access

**Example:**
```
User: Show me all users with Owner access and when they last logged in

Claude Code: [Uses azure_list_role_assignments with roleDefinitionName="Owner"]
[Gets sign-in data for each user]

Owner Role Assignments (5):

Active Owners:
1. admin@contoso.com
   - Last sign-in: 2 hours ago
   - Scope: Subscription
   - Status: ✓ Active

2. jane.doe@contoso.com
   - Last sign-in: 1 day ago
   - Scope: /subscriptions/.../resourceGroups/production-rg
   - Status: ✓ Active

Potentially Stale:
3. john.smith@contoso.com
   - Last sign-in: 62 days ago
   - Scope: Subscription
   - Status: ⚠️ Review recommended

4. alice.johnson@contoso.com
   - Last sign-in: 95 days ago
   - Scope: /subscriptions/.../resourceGroups/legacy-rg
   - Status: ⚠️ Review recommended

Never signed in:
5. service-account@contoso.com
   - Last sign-in: Never
   - Scope: Subscription
   - Status: ⚠️ Investigation needed

Recommendations:
- Review access for users with 60+ days since last sign-in
- Remove Owner role from service-account@ (use managed identity instead)
- Consider using Privileged Identity Management (PIM) for just-in-time access

Would you like me to generate a detailed access review report?
```

## Scenario 6: Infrastructure Provisioning

**User Request:** "Create a complete dev environment for a Node.js app"

**Claude Code Workflow:**

1. Asks for clarification (region, naming, etc.)
2. Uses multiple MCP tools to create resources
3. Configures networking and security
4. Provides connection information

**Example:**
```
User: Create a complete dev environment for a Node.js app

Claude Code: I'll create a development environment. Let me ask a few questions:
- Preferred region? (default: eastus)
- App name prefix? (default: myapp)
- Include database? (yes/no)

User: eastus, nodeapp, yes

Claude Code: Creating development environment...

[Uses azure_create_resource for each component]

Progress:
✓ Resource Group: nodeapp-dev-rg (eastus)
✓ Virtual Network: nodeapp-dev-vnet (10.0.0.0/16)
✓ App Service Plan: nodeapp-dev-plan (B1)
✓ App Service: nodeapp-dev-app
✓ Azure SQL Database: nodeapp-dev-db (Basic)
✓ Storage Account: nodeappdevstg123
✓ Application Insights: nodeapp-dev-insights
✓ Key Vault: nodeapp-dev-kv

Configuration:
✓ VNet integration configured
✓ Managed identity enabled on App Service
✓ Key Vault access granted
✓ Database connection string stored in Key Vault
✓ Application Insights connected

Environment Details:
- Resource Group: nodeapp-dev-rg
- App Service URL: https://nodeapp-dev-app.azurewebsites.net
- Database Server: nodeapp-dev-server.database.windows.net
- Database Name: nodeapp-dev-db
- Key Vault: nodeapp-dev-kv.vault.azure.net

Next Steps:
1. Deploy your code: az webapp deploy --name nodeapp-dev-app --resource-group nodeapp-dev-rg
2. Configure connection string from Key Vault
3. Monitor via Application Insights

Total setup time: 4m 18s
Estimated monthly cost: $75

Would you like me to provide deployment instructions?
```

## Benefits of MCP-Powered Workflows

1. **Natural Language**: No need to remember complex CLI syntax
2. **Context Awareness**: Claude maintains context across operations
3. **Smart Recommendations**: AI analyzes data and suggests optimizations
4. **Error Prevention**: Validates operations before execution
5. **Automation**: Complex multi-step workflows automated
6. **Learning**: Explains what it's doing and why

## Related Documentation

- @docs/mcp-integration.md - MCP setup and tools
- @docs/cli-patterns.md - When to use CLI vs MCP
- @docs/user-management.md - Identity operations
- @docs/resource-management.md - Resource operations
