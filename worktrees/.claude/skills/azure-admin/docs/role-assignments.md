# Role Assignments and RBAC in Azure

Comprehensive guide to Role-Based Access Control (RBAC) in Azure, including built-in roles, custom roles, scope management, and access reviews.

## Table of Contents

1. [RBAC Fundamentals](#rbac-fundamentals)
2. [Built-in Roles](#built-in-roles)
3. [Role Assignment Operations](#role-assignment-operations)
4. [Custom Roles](#custom-roles)
5. [Scope Management](#scope-management)
6. [Access Reviews and Auditing](#access-reviews-and-auditing)
7. [Troubleshooting](#troubleshooting)

## RBAC Fundamentals

Azure RBAC is an authorization system that provides fine-grained access management for Azure resources.

### Core Components

**Security Principal** (Who):
- User: Individual with Entra ID account
- Group: Collection of users
- Service Principal: Identity for applications/services
- Managed Identity: Azure-managed service principal

**Role Definition** (What):
- Collection of permissions (actions and data actions)
- Examples: Owner, Contributor, Reader, custom roles

**Scope** (Where):
- Management Group: Multiple subscriptions
- Subscription: Billing boundary
- Resource Group: Logical container
- Resource: Individual service

### RBAC Assignment Formula

```
Security Principal + Role Definition + Scope = Role Assignment
```

Example:
```
jane@contoso.com + Contributor + /subscriptions/{sub}/resourceGroups/myRG
= Jane has Contributor access to myRG resource group
```

### Permission Model

**Actions**: Control plane operations (management operations)
```
Microsoft.Compute/virtualMachines/read
Microsoft.Compute/virtualMachines/write
Microsoft.Compute/virtualMachines/delete
```

**DataActions**: Data plane operations (data access)
```
Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read
Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write
```

**NotActions**: Excluded from allowed actions
**NotDataActions**: Excluded from allowed data actions

## Built-in Roles

Azure provides 100+ built-in roles. Here are the most commonly used:

### Fundamental Roles

**Owner**
- Full access to all resources
- Can assign roles to others
- Scope: All levels
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role Owner \
  --scope /subscriptions/{subscription-id}
```

**Contributor**
- Create and manage all types of resources
- Cannot assign roles
- Cannot manage Microsoft Entra directory
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role Contributor \
  --scope /subscriptions/{subscription-id}/resourceGroups/myRG
```

**Reader**
- View all resources
- No modification permissions
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role Reader \
  --scope /subscriptions/{subscription-id}
```

**User Access Administrator**
- Manage user access to Azure resources
- Cannot manage resources themselves
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "User Access Administrator" \
  --scope /subscriptions/{subscription-id}
```

### Compute Roles

**Virtual Machine Contributor**
- Manage VMs but not access to them
- Cannot manage virtual network or storage account
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "Virtual Machine Contributor" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}
```

**Virtual Machine Administrator Login**
- View VMs in portal and login as administrator
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "Virtual Machine Administrator Login" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{vm}
```

**Virtual Machine User Login**
- View VMs and login as regular user
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "Virtual Machine User Login" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/{vm}
```

### Storage Roles

**Storage Account Contributor**
- Manage storage accounts (control plane)
- Cannot access data
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "Storage Account Contributor" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{storage}
```

**Storage Blob Data Contributor**
- Read, write, delete blob containers and data
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "Storage Blob Data Contributor" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{storage}
```

**Storage Blob Data Reader**
- Read blob containers and data
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "Storage Blob Data Reader" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{storage}
```

### Networking Roles

**Network Contributor**
- Manage networks but not access to them
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "Network Contributor" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}
```

### Database Roles

**SQL DB Contributor**
- Manage SQL databases but not access to them
- Cannot manage security policies
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "SQL DB Contributor" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Sql/servers/{server}
```

**SQL Security Manager**
- Manage security policies of SQL servers and databases
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "SQL Security Manager" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Sql/servers/{server}
```

### Security Roles

**Security Admin**
- View and update security policies
- View security alerts and recommendations
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "Security Admin" \
  --scope /subscriptions/{subscription-id}
```

**Security Reader**
- View security recommendations and alerts
- Cannot update security policies
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "Security Reader" \
  --scope /subscriptions/{subscription-id}
```

### Key Vault Roles

**Key Vault Administrator**
- Perform all data plane operations (keys, secrets, certificates)
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "Key Vault Administrator" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{vault}
```

**Key Vault Secrets User**
- Read secret contents
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "Key Vault Secrets User" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.KeyVault/vaults/{vault}
```

## Role Assignment Operations

### Creating Role Assignments

**Assign to user:**
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role Contributor \
  --scope /subscriptions/{sub}/resourceGroups/myRG
```

**Assign to group:**
```bash
# Get group object ID
GROUP_ID=$(az ad group show --group "Engineering Team" --query id -o tsv)

az role assignment create \
  --assignee "$GROUP_ID" \
  --role Contributor \
  --scope /subscriptions/{sub}/resourceGroups/myRG
```

**Assign to service principal:**
```bash
az role assignment create \
  --assignee {app-id} \
  --role Reader \
  --scope /subscriptions/{sub}
```

**Assign to managed identity:**
```bash
# Get managed identity principal ID
PRINCIPAL_ID=$(az vm show --name myVM --resource-group myRG --query identity.principalId -o tsv)

az role assignment create \
  --assignee "$PRINCIPAL_ID" \
  --role "Storage Blob Data Reader" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{storage}
```

### Listing Role Assignments

**List all assignments for a user:**
```bash
az role assignment list --assignee jane@contoso.com --all --output table
```

**List assignments at specific scope:**
```bash
az role assignment list --scope /subscriptions/{sub}/resourceGroups/myRG --output table
```

**List assignments for a resource:**
```bash
az role assignment list \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/myVM \
  --output table
```

**List assignments including inherited:**
```bash
az role assignment list \
  --scope /subscriptions/{sub}/resourceGroups/myRG \
  --include-inherited \
  --output table
```

**Query specific role:**
```bash
az role assignment list \
  --role Contributor \
  --query "[].{Principal:principalName, Scope:scope}" \
  --output table
```

**List with classic administrators:**
```bash
az role assignment list --all --include-classic-administrators --output table
```

### Deleting Role Assignments

**Delete specific assignment:**
```bash
az role assignment delete \
  --assignee jane@contoso.com \
  --role Contributor \
  --scope /subscriptions/{sub}/resourceGroups/myRG
```

**Delete by assignment ID:**
```bash
# Get assignment ID
ASSIGNMENT_ID=$(az role assignment list \
  --assignee jane@contoso.com \
  --role Contributor \
  --scope /subscriptions/{sub}/resourceGroups/myRG \
  --query "[0].id" -o tsv)

az role assignment delete --ids "$ASSIGNMENT_ID"
```

**Bulk delete (remove user from all roles):**
```bash
az role assignment list --assignee jane@contoso.com --all --query "[].id" -o tsv | \
  xargs -I {} az role assignment delete --ids {}
```

## Custom Roles

Create custom roles when built-in roles don't meet your specific requirements.

### Creating Custom Roles

**Define role in JSON file** (`custom-role.json`):
```json
{
  "Name": "Virtual Machine Operator",
  "IsCustom": true,
  "Description": "Can monitor and restart virtual machines",
  "Actions": [
    "Microsoft.Compute/*/read",
    "Microsoft.Compute/virtualMachines/start/action",
    "Microsoft.Compute/virtualMachines/restart/action",
    "Microsoft.Resources/subscriptions/resourceGroups/read",
    "Microsoft.Insights/alertRules/*",
    "Microsoft.Support/*"
  ],
  "NotActions": [],
  "DataActions": [],
  "NotDataActions": [],
  "AssignableScopes": [
    "/subscriptions/{subscription-id}"
  ]
}
```

**Create role:**
```bash
az role definition create --role-definition custom-role.json
```

### Custom Role Examples

**Storage Account Key Reader:**
```json
{
  "Name": "Storage Account Key Reader",
  "IsCustom": true,
  "Description": "Read storage account keys",
  "Actions": [
    "Microsoft.Storage/storageAccounts/read",
    "Microsoft.Storage/storageAccounts/listkeys/action"
  ],
  "NotActions": [],
  "AssignableScopes": [
    "/subscriptions/{subscription-id}"
  ]
}
```

**VM Snapshot Creator:**
```json
{
  "Name": "VM Snapshot Creator",
  "IsCustom": true,
  "Description": "Create and manage VM snapshots",
  "Actions": [
    "Microsoft.Compute/disks/read",
    "Microsoft.Compute/snapshots/*",
    "Microsoft.Resources/subscriptions/resourceGroups/read"
  ],
  "NotActions": [],
  "AssignableScopes": [
    "/subscriptions/{subscription-id}/resourceGroups/production-rg"
  ]
}
```

**Cost Reader with Export:**
```json
{
  "Name": "Cost Management Analyst",
  "IsCustom": true,
  "Description": "View costs and export data",
  "Actions": [
    "Microsoft.CostManagement/*/read",
    "Microsoft.CostManagement/exports/*",
    "Microsoft.Consumption/*/read"
  ],
  "NotActions": [],
  "AssignableScopes": [
    "/subscriptions/{subscription-id}"
  ]
}
```

### Managing Custom Roles

**List custom roles:**
```bash
az role definition list --custom-role-only true --output table
```

**Show role definition:**
```bash
az role definition list --name "Virtual Machine Operator"
```

**Update custom role:**
```bash
# Modify the JSON file, then:
az role definition update --role-definition custom-role.json
```

**Delete custom role:**
```bash
az role definition delete --name "Virtual Machine Operator"
```

### Custom Role Best Practices

1. **Start with built-in role** - Clone and modify
2. **Use wildcards sparingly** - Be explicit with permissions
3. **Document thoroughly** - Clear description and purpose
4. **Test in non-production** - Validate permissions before prod use
5. **Limit AssignableScopes** - Restrict to necessary subscriptions/resource groups
6. **Regular reviews** - Audit and update as needed
7. **Version control** - Store JSON definitions in Git

## Scope Management

### Scope Hierarchy

```
Management Group (optional)
└── Subscription
    └── Resource Group
        └── Resource
```

Permissions inherit down the hierarchy. Assignment at higher scope automatically applies to lower scopes.

### Scope Patterns

**Subscription-wide access:**
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role Contributor \
  --scope /subscriptions/{subscription-id}
```

**Resource group access:**
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role Contributor \
  --scope /subscriptions/{sub}/resourceGroups/myRG
```

**Specific resource access:**
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role "Virtual Machine Contributor" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/myVM
```

**Management group access:**
```bash
az role assignment create \
  --assignee jane@contoso.com \
  --role Reader \
  --scope /providers/Microsoft.Management/managementGroups/{management-group-id}
```

### Multi-Scope Strategies

**Environment-based:**
```bash
# Development - full access
az role assignment create \
  --assignee dev-team@contoso.com \
  --role Contributor \
  --scope /subscriptions/{dev-sub}

# Production - limited access
az role assignment create \
  --assignee dev-team@contoso.com \
  --role Reader \
  --scope /subscriptions/{prod-sub}
```

**Application-based:**
```bash
# Frontend team - web resources only
az role assignment create \
  --assignee frontend-team@contoso.com \
  --role "Website Contributor" \
  --scope /subscriptions/{sub}/resourceGroups/frontend-rg

# Backend team - compute and database
az role assignment create \
  --assignee backend-team@contoso.com \
  --role Contributor \
  --scope /subscriptions/{sub}/resourceGroups/backend-rg
```

## Access Reviews and Auditing

### Regular Access Reviews

**List all role assignments:**
```bash
az role assignment list --all --output table > access-review-$(date +%Y%m%d).txt
```

**Find high-privilege assignments:**
```bash
az role assignment list \
  --role Owner \
  --all \
  --query "[].{Principal:principalName, Scope:scope, Type:principalType}" \
  --output table
```

**Find assignments for specific resource type:**
```bash
az role assignment list \
  --all \
  --query "[?contains(scope, 'Microsoft.Compute/virtualMachines')]" \
  --output table
```

**Identify stale assignments** (combine with Entra ID sign-in logs):
```bash
# Get users without sign-in in last 90 days
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/auditLogs/signIns?\$filter=createdDateTime le $(date -u -d '90 days ago' +%Y-%m-%dT%H:%M:%SZ)"
```

### Compliance Reporting

**Generate role assignment report:**
```bash
#!/bin/bash
# role-assignment-report.sh

OUTPUT_FILE="role-assignments-$(date +%Y%m%d).csv"
echo "PrincipalName,PrincipalType,RoleDefinitionName,Scope" > "$OUTPUT_FILE"

az role assignment list --all --query "[].[principalName,principalType,roleDefinitionName,scope]" -o tsv | \
  while IFS=$'\t' read -r principal type role scope; do
    echo "$principal,$type,$role,$scope" >> "$OUTPUT_FILE"
  done

echo "Report generated: $OUTPUT_FILE"
```

**Find role assignments without groups:**
```bash
# List direct user assignments (anti-pattern)
az role assignment list \
  --all \
  --query "[?principalType=='User'].{User:principalName, Role:roleDefinitionName, Scope:scope}" \
  --output table
```

**Audit administrative roles:**
```bash
# Find all Owner and Contributor assignments
for role in Owner Contributor "User Access Administrator"; do
  echo "=== $role ==="
  az role assignment list \
    --role "$role" \
    --all \
    --query "[].{Principal:principalName, Scope:scope}" \
    --output table
done
```

### Automated Compliance Checks

**Check for policy violations:**
```bash
#!/bin/bash
# compliance-check.sh

echo "Checking for direct user assignments (should use groups)..."
DIRECT_USERS=$(az role assignment list --all --query "[?principalType=='User'] | length(@)")
if [ "$DIRECT_USERS" -gt 0 ]; then
  echo "⚠️  Found $DIRECT_USERS direct user assignments"
else
  echo "✓ No direct user assignments"
fi

echo ""
echo "Checking for excessive Owner roles..."
OWNERS=$(az role assignment list --role Owner --all --query "length([])")
if [ "$OWNERS" -gt 5 ]; then
  echo "⚠️  Found $OWNERS Owner assignments (expected < 5)"
else
  echo "✓ Owner assignments within limits: $OWNERS"
fi

echo ""
echo "Checking for subscription-wide Contributor access..."
SUB_CONTRIBUTORS=$(az role assignment list --role Contributor --query "[?contains(scope, '/subscriptions/') && !contains(scope, '/resourceGroups/')] | length(@)")
if [ "$SUB_CONTRIBUTORS" -gt 0 ]; then
  echo "⚠️  Found $SUB_CONTRIBUTORS subscription-wide Contributor assignments"
else
  echo "✓ No subscription-wide Contributor assignments"
fi
```

## Troubleshooting

### Common Issues

**Insufficient privileges to assign roles:**
```
Error: The client does not have authorization to perform action
'Microsoft.Authorization/roleAssignments/write'
```

**Solution:**
- Verify you have Owner or User Access Administrator role at the target scope
- Check: `az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) --all`

**Role assignment not taking effect:**
- Wait 5-10 minutes for propagation
- Have user re-authenticate: `az logout && az login`
- Check for deny assignments: `az deny assignment list`

**Cannot delete role assignment:**
```
Error: Role assignment does not exist
```

**Solution:**
```bash
# List to find exact assignment
az role assignment list --assignee jane@contoso.com --all

# Delete by ID instead of parameters
az role assignment delete --ids {assignment-id}
```

**Custom role scope issues:**
```
Error: The role definition has invalid assignable scopes
```

**Solution:**
- Ensure AssignableScopes includes the target subscription
- Cannot be more restrictive than role definition allows

### Verification Commands

**Check effective permissions:**
```bash
# What can I do at this scope?
az role assignment list \
  --assignee $(az ad signed-in-user show --query id -o tsv) \
  --scope /subscriptions/{sub}/resourceGroups/myRG \
  --include-inherited
```

**Test specific action:**
```bash
# Try the action - will show permission error if not allowed
az vm list --resource-group myRG
```

**List deny assignments:**
```bash
az deny assignment list --scope /subscriptions/{subscription-id}
```

## Best Practices Summary

1. **Use groups, not individual users** - Easier management and auditing
2. **Principle of least privilege** - Grant minimum required permissions
3. **Prefer built-in roles** - Use custom roles only when necessary
4. **Assign at appropriate scope** - Resource group level preferred over subscription
5. **Regular access reviews** - Quarterly review and cleanup
6. **Document role purposes** - Clear descriptions for custom roles
7. **Use managed identities** - Avoid service principals when possible
8. **Monitor privileged roles** - Alert on Owner/Contributor assignments
9. **Implement just-in-time (JIT) access** - For administrative tasks
10. **Version control role definitions** - Track changes in Git

## Related Documentation

- @user-management.md - User, group, and service principal management
- @resource-management.md - Resource lifecycle and organization
- @cli-patterns.md - Advanced CLI patterns for RBAC operations
- @troubleshooting.md - Additional troubleshooting guidance
- @../examples/role-audit.md - Complete role audit workflow
