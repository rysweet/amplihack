# User Management in Azure

Comprehensive guide to managing users, groups, service principals, and managed identities in Azure Entra ID (formerly Azure AD).

## Table of Contents

1. [User Lifecycle Management](#user-lifecycle-management)
2. [Group Management](#group-management)
3. [Service Principals](#service-principals)
4. [Managed Identities](#managed-identities)
5. [Authentication Methods](#authentication-methods)
6. [Security Best Practices](#security-best-practices)

## User Lifecycle Management

### Creating Users

**Interactive Creation:**
```bash
# Basic user creation
az ad user create \
  --display-name "Jane Doe" \
  --user-principal-name jane.doe@contoso.com \
  --password "ComplexP@ssw0rd!" \
  --force-change-password-next-sign-in true

# User with additional properties
az ad user create \
  --display-name "John Smith" \
  --user-principal-name john.smith@contoso.com \
  --password "SecureP@ss123!" \
  --mail-nickname "jsmith" \
  --given-name "John" \
  --surname "Smith" \
  --department "Engineering" \
  --job-title "Software Engineer" \
  --force-change-password-next-sign-in true
```

**Bulk User Creation from CSV:**

Create a CSV file (`users.csv`):
```csv
DisplayName,UserPrincipalName,Password,Department,JobTitle
Jane Doe,jane.doe@contoso.com,TempPass123!,Engineering,Senior Engineer
John Smith,john.smith@contoso.com,TempPass456!,Marketing,Marketing Manager
Alice Johnson,alice.johnson@contoso.com,TempPass789!,Sales,Sales Representative
```

Bash script to process CSV:
```bash
#!/bin/bash
# bulk-user-create.sh

CSV_FILE="users.csv"

# Skip header, read each line
tail -n +2 "$CSV_FILE" | while IFS=, read -r display_name upn password department job_title; do
  echo "Creating user: $display_name ($upn)"

  az ad user create \
    --display-name "$display_name" \
    --user-principal-name "$upn" \
    --password "$password" \
    --department "$department" \
    --job-title "$job_title" \
    --force-change-password-next-sign-in true

  if [ $? -eq 0 ]; then
    echo "✓ Successfully created $upn"
  else
    echo "✗ Failed to create $upn"
  fi
done
```

### Reading User Information

```bash
# Get user by UPN
az ad user show --id jane.doe@contoso.com

# Get user by object ID
az ad user show --id "12345678-1234-1234-1234-123456789012"

# List all users
az ad user list --output table

# Filter users by department
az ad user list --filter "department eq 'Engineering'" --output table

# Get specific properties
az ad user list --query "[].{Name:displayName, Email:userPrincipalName, Department:department}"

# Search users by display name
az ad user list --filter "startswith(displayName,'Jane')" --output table

# Get currently signed-in user
az ad signed-in-user show
```

### Updating Users

```bash
# Update user properties
az ad user update \
  --id jane.doe@contoso.com \
  --set department="Platform Engineering" jobTitle="Staff Engineer"

# Update multiple properties
az ad user update \
  --id john.smith@contoso.com \
  --set department="Product" \
       jobTitle="Product Manager" \
       mobilePhone="+1-555-0123"

# Reset user password
az ad user update \
  --id jane.doe@contoso.com \
  --password "NewSecureP@ss!" \
  --force-change-password-next-sign-in true
```

### Deleting Users

```bash
# Delete single user
az ad user delete --id jane.doe@contoso.com

# Bulk delete (from file)
cat users-to-delete.txt | while read upn; do
  az ad user delete --id "$upn"
  echo "Deleted: $upn"
done

# List deleted users (soft delete, recoverable for 30 days)
az ad user list --query "[?deletionTimestamp != null]"

# Restore deleted user
az rest --method POST \
  --url "https://graph.microsoft.com/v1.0/directory/deletedItems/{user-id}/restore"
```

## Group Management

### Creating Groups

```bash
# Create security group
az ad group create \
  --display-name "Engineering Team" \
  --mail-nickname "engineering"

# Create Microsoft 365 group
az ad group create \
  --display-name "Marketing Team" \
  --mail-nickname "marketing" \
  --group-types "Unified"

# Create group with description
az ad group create \
  --display-name "Cloud Admins" \
  --mail-nickname "cloudadmins" \
  --description "Administrators with cloud infrastructure access"
```

### Managing Group Membership

```bash
# Add user to group
az ad group member add \
  --group "Engineering Team" \
  --member-id $(az ad user show --id jane.doe@contoso.com --query id -o tsv)

# Add multiple users
for upn in jane.doe@contoso.com john.smith@contoso.com alice.johnson@contoso.com; do
  USER_ID=$(az ad user show --id "$upn" --query id -o tsv)
  az ad group member add --group "Engineering Team" --member-id "$USER_ID"
done

# List group members
az ad group member list --group "Engineering Team" --output table

# List group members with details
az ad group member list \
  --group "Engineering Team" \
  --query "[].{Name:displayName, Email:userPrincipalName, Type:objectType}"

# Remove user from group
az ad group member remove \
  --group "Engineering Team" \
  --member-id $(az ad user show --id jane.doe@contoso.com --query id -o tsv)

# Check if user is member
az ad group member check \
  --group "Engineering Team" \
  --member-id $(az ad user show --id jane.doe@contoso.com --query id -o tsv)
```

### Group Ownership

```bash
# Add group owner
az ad group owner add \
  --group "Engineering Team" \
  --owner-object-id $(az ad user show --id jane.doe@contoso.com --query id -o tsv)

# List group owners
az ad group owner list --group "Engineering Team"

# Remove group owner
az ad group owner remove \
  --group "Engineering Team" \
  --owner-object-id $(az ad user show --id jane.doe@contoso.com --query id -o tsv)
```

## Service Principals

Service principals are identities for applications and services to authenticate to Azure.

### Creating Service Principals

```bash
# Create with automatic role assignment
az ad sp create-for-rbac \
  --name "myAppServicePrincipal" \
  --role Contributor \
  --scopes /subscriptions/{subscription-id}

# Output (SAVE THESE CREDENTIALS):
# {
#   "appId": "12345678-1234-1234-1234-123456789012",
#   "displayName": "myAppServicePrincipal",
#   "password": "generated-secret",
#   "tenant": "tenant-id"
# }

# Create without role assignment (assign later)
az ad sp create-for-rbac --name "myBasicSP" --skip-assignment

# Create with custom role at resource group scope
az ad sp create-for-rbac \
  --name "myCustomSP" \
  --role "Virtual Machine Contributor" \
  --scopes /subscriptions/{sub-id}/resourceGroups/{rg-name}

# Create with certificate authentication
az ad sp create-for-rbac \
  --name "myCertSP" \
  --create-cert \
  --cert "myCert" \
  --keyvault "myKeyVault"
```

### Managing Service Principal Credentials

```bash
# Reset service principal credentials
az ad sp credential reset --id {app-id}

# Add new credential (for rotation)
az ad sp credential reset --id {app-id} --append

# List service principal credentials
az ad sp credential list --id {app-id}

# Delete specific credential
az ad sp credential delete --id {app-id} --key-id {credential-key-id}

# Create certificate credential
az ad sp credential reset \
  --id {app-id} \
  --create-cert \
  --cert "newCert" \
  --keyvault "myKeyVault"
```

### Service Principal Operations

```bash
# List all service principals
az ad sp list --all --output table

# Find service principal by display name
az ad sp list --display-name "myAppServicePrincipal"

# Show service principal details
az ad sp show --id {app-id}

# Delete service principal
az ad sp delete --id {app-id}

# Grant API permissions to service principal
az ad app permission add \
  --id {app-id} \
  --api 00000003-0000-0000-c000-000000000000 \
  --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope

# Grant admin consent
az ad app permission admin-consent --id {app-id}
```

### Service Principal Best Practices

1. **Use Managed Identities when possible** - No credential management required
2. **Rotate credentials regularly** - Every 90 days maximum
3. **Use certificate authentication** - More secure than secrets
4. **Store credentials securely** - Use Azure Key Vault
5. **Least privilege** - Assign minimum required permissions
6. **Separate service principals** - One per application/environment
7. **Monitor usage** - Track sign-ins and API calls
8. **Document ownership** - Tag with team/application information

## Managed Identities

Managed identities provide Azure resources with an identity in Entra ID without managing credentials.

### Types of Managed Identities

**System-Assigned Identity:**
- Tied to resource lifecycle
- Deleted automatically when resource is deleted
- Cannot be shared across resources
- Simple to enable

**User-Assigned Identity:**
- Independent lifecycle
- Can be shared across multiple resources
- Survives resource deletion
- More flexible

### Enabling System-Assigned Identities

```bash
# Enable on VM
az vm identity assign --name myVM --resource-group myRG

# Enable on App Service
az webapp identity assign --name myAppService --resource-group myRG

# Enable on Function App
az functionapp identity assign --name myFunctionApp --resource-group myRG

# Enable on Container Instance
az container create \
  --name myContainer \
  --resource-group myRG \
  --image nginx \
  --assign-identity

# Enable on AKS (kubelet identity)
az aks update \
  --name myAKSCluster \
  --resource-group myRG \
  --enable-managed-identity
```

### Creating and Assigning User-Assigned Identities

```bash
# Create user-assigned identity
az identity create \
  --name myManagedIdentity \
  --resource-group myRG

# Get identity resource ID
IDENTITY_ID=$(az identity show \
  --name myManagedIdentity \
  --resource-group myRG \
  --query id -o tsv)

# Assign to VM
az vm identity assign \
  --name myVM \
  --resource-group myRG \
  --identities "$IDENTITY_ID"

# Assign to App Service
az webapp identity assign \
  --name myAppService \
  --resource-group myRG \
  --identities "$IDENTITY_ID"

# Assign to multiple resources
for vm in vm1 vm2 vm3; do
  az vm identity assign \
    --name "$vm" \
    --resource-group myRG \
    --identities "$IDENTITY_ID"
done
```

### Granting Permissions to Managed Identities

```bash
# Get managed identity principal ID
PRINCIPAL_ID=$(az vm show \
  --name myVM \
  --resource-group myRG \
  --query identity.principalId -o tsv)

# Grant Key Vault access
az keyvault set-policy \
  --name myKeyVault \
  --object-id "$PRINCIPAL_ID" \
  --secret-permissions get list

# Grant Storage account access
az role assignment create \
  --assignee "$PRINCIPAL_ID" \
  --role "Storage Blob Data Reader" \
  --scope /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Storage/storageAccounts/{storage}

# Grant SQL database access
az sql server ad-admin set \
  --resource-group myRG \
  --server-name mySqlServer \
  --display-name myVM \
  --object-id "$PRINCIPAL_ID"
```

### Using Managed Identities in Code

**Azure SDK (Python):**
```python
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# DefaultAzureCredential automatically uses managed identity when running in Azure
credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://mykeyvault.vault.azure.net/", credential=credential)

secret = client.get_secret("mySecret")
print(secret.value)
```

**Azure CLI within Azure resource:**
```bash
# Automatically uses managed identity when run from Azure VM/App Service
az login --identity

# Use specific user-assigned identity
az login --identity --username {client-id}

# Access resources
az storage blob list --account-name mystorageaccount --container-name mycontainer
```

## Authentication Methods

### Multi-Factor Authentication (MFA)

```bash
# Check user MFA status (via Microsoft Graph API)
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/users/{user-id}/authentication/methods"

# Require MFA for specific group (via Conditional Access)
# This requires Azure Portal or Microsoft Graph API - not directly via CLI
```

### Conditional Access

Conditional access policies control access based on conditions (location, device, risk level).

**Common Policies:**
- Require MFA for all users
- Block legacy authentication
- Require compliant devices
- Require approved client apps
- Block access from specific countries

Conditional Access policies are managed through Azure Portal or Microsoft Graph API.

### Password Policies

```bash
# View password policies
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/domains/{domain-name}/passwordPolicy"

# Update user password with expiration
az ad user update \
  --id jane.doe@contoso.com \
  --password "NewP@ssw0rd!" \
  --force-change-password-next-sign-in true
```

## Security Best Practices

### Principle of Least Privilege
- Assign minimum required permissions
- Use built-in roles before creating custom roles
- Regularly review and revoke unnecessary access
- Implement just-in-time (JIT) access for administrative tasks

### Identity Lifecycle Management
1. **Onboarding**: Provision accounts, assign groups, grant access
2. **Ongoing**: Regular access reviews, permission audits
3. **Role Changes**: Update permissions based on job changes
4. **Offboarding**: Disable accounts immediately, revoke access, backup data

### Monitoring and Auditing
```bash
# View sign-in logs (requires appropriate permissions)
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/auditLogs/signIns"

# View directory audit logs
az rest --method GET \
  --url "https://graph.microsoft.com/v1.0/auditLogs/directoryAudits"
```

### Credential Management
- Never store credentials in code
- Use Azure Key Vault for secrets
- Rotate service principal credentials every 90 days
- Use managed identities instead of service principals when possible
- Enable MFA for all users, especially admins
- Use certificate-based authentication over secrets

### Emergency Access Accounts
Create "break-glass" accounts for emergency access:
- Cloud-only accounts (not synchronized from on-premises)
- Excluded from conditional access policies
- Credentials stored securely offline
- Monitored for any usage
- Reviewed quarterly

## Related Documentation

- @role-assignments.md - RBAC role assignment patterns
- @cli-patterns.md - Advanced CLI scripting for identity operations
- @troubleshooting.md - Common identity issues and solutions
- @../examples/bulk-user-onboarding.md - Complete bulk onboarding workflow
