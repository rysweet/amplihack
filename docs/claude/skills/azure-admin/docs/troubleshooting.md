# Azure Troubleshooting Guide

Common issues and solutions for Azure administration tasks.

## Table of Contents

1. [Authentication and Authorization](#authentication-and-authorization)
2. [Resource Operations](#resource-operations)
3. [Networking Issues](#networking-issues)
4. [Deployment Failures](#deployment-failures)
5. [CLI and Tooling Problems](#cli-and-tooling-problems)
6. [Performance Issues](#performance-issues)

## Authentication and Authorization

### Login Failures

**Problem**: `az login` fails or times out

**Solutions**:
```bash
# 1. Use device code flow
az login --use-device-code

# 2. Clear cached credentials
az logout
az account clear
rm -rf ~/.azure/

# 3. Login with specific tenant
az login --tenant {tenant-id}

# 4. Verify system time (authentication uses time-based tokens)
date  # Ensure clock is accurate

# 5. Check network/proxy settings
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080
```

### Permission Denied Errors

**Problem**: "Insufficient privileges" or "Authorization failed"

**Diagnosis**:
```bash
# Check your role assignments
az role assignment list \
  --assignee $(az ad signed-in-user show --query id -o tsv) \
  --all \
  --output table

# Check subscription context
az account show

# Verify resource provider registration
az provider list --query "[?registrationState=='NotRegistered']" --output table
```

**Solutions**:
```bash
# 1. Register required resource providers
az provider register --namespace Microsoft.Compute
az provider register --namespace Microsoft.Storage

# 2. Verify you're in the correct subscription
az account set --subscription "My Subscription"

# 3. Request appropriate role from subscription administrator
# Minimum roles needed:
# - Reader: View resources
# - Contributor: Create/manage resources
# - Owner: Full access including role assignments
```

### Token Expiration

**Problem**: "Authentication token has expired"

**Solution**:
```bash
# Refresh authentication
az login --use-device-code

# For service principal
az login --service-principal \
  --username {app-id} \
  --password {secret} \
  --tenant {tenant-id}
```

### Multi-Tenant Issues

**Problem**: Cannot access resources in different tenants

**Solution**:
```bash
# List available tenants
az account tenant list

# Login with specific tenant
az login --tenant {tenant-id}

# Switch between tenants
az account set --subscription {subscription-in-other-tenant}
```

## Resource Operations

### Resource Not Found

**Problem**: "Resource not found" or "ResourceGroupNotFound"

**Diagnosis**:
```bash
# Check if resource exists
az resource show --ids {resource-id}

# List all resources with similar name
az resource list --name {partial-name}

# Check if in correct subscription
az account show

# Search across all subscriptions
az account list --query "[].{Name:name, ID:id}" -o table
for sub in $(az account list --query "[].id" -o tsv); do
  echo "Checking subscription: $sub"
  az resource list --subscription "$sub" --name {resource-name}
done
```

### Resource Locked

**Problem**: "Cannot delete resource due to lock"

**Diagnosis and Solution**:
```bash
# List locks on resource
az lock list --resource-group myRG

# Show specific lock
az lock show --name LockName --resource-group myRG

# Delete lock (requires appropriate permissions)
az lock delete --name LockName --resource-group myRG

# Delete lock on specific resource
az lock delete \
  --name LockName \
  --resource-group myRG \
  --resource-name myVM \
  --resource-type Microsoft.Compute/virtualMachines
```

### Quota Exceeded

**Problem**: "QuotaExceeded" or "OperationNotAllowed"

**Diagnosis**:
```bash
# Check current quota usage
az vm list-usage --location eastus --output table

# Check specific resource quota
az network vnet list-usage \
  --ids /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Network/virtualNetworks/{vnet}
```

**Solution**:
- Request quota increase via Azure Portal > Subscription > Usage + quotas
- Or create support ticket for quota increase
- Consider using different VM sizes or regions with available capacity

### Resource Provider Not Registered

**Problem**: "ResourceProviderNotRegistered"

**Solution**:
```bash
# List all resource providers and their registration status
az provider list --query "[].{Namespace:namespace, State:registrationState}" --output table

# Register specific provider
az provider register --namespace Microsoft.Compute

# Check registration status
az provider show --namespace Microsoft.Compute --query registrationState

# Wait for registration to complete (can take a few minutes)
az provider show --namespace Microsoft.Compute --query registrationState -o tsv | \
  while read state; do
    if [ "$state" == "Registered" ]; then
      echo "✓ Provider registered"
      break
    fi
    echo "Waiting for registration... (current state: $state)"
    sleep 10
  done
```

## Networking Issues

### Cannot Connect to VM

**Problem**: SSH or RDP connection fails

**Diagnosis**:
```bash
# Check VM is running
az vm show --resource-group myRG --name myVM --query powerState

# Check NSG rules
az network nsg list --resource-group myRG --output table
az network nsg rule list --resource-group myRG --nsg-name myNSG --output table

# Check public IP
az vm show --resource-group myRG --name myVM --show-details --query publicIps -o tsv

# Test connectivity
nc -zv {public-ip} 22  # SSH
nc -zv {public-ip} 3389  # RDP
```

**Solutions**:
```bash
# 1. Verify VM is running
az vm start --resource-group myRG --name myVM

# 2. Add NSG rule for SSH/RDP
az network nsg rule create \
  --resource-group myRG \
  --nsg-name myNSG \
  --name AllowSSH \
  --priority 1000 \
  --source-address-prefixes '*' \
  --destination-port-ranges 22 \
  --access Allow \
  --protocol Tcp

# 3. Check if public IP exists
az network public-ip list --resource-group myRG --output table

# 4. Use Azure Bastion or Serial Console
az network bastion list --resource-group myRG
```

### DNS Resolution Failures

**Problem**: Cannot resolve Azure DNS names

**Diagnosis**:
```bash
# Test DNS resolution
nslookup myresource.azurewebsites.net

# Check DNS servers
cat /etc/resolv.conf  # Linux
ipconfig /all  # Windows
```

**Solution**:
```bash
# Verify private DNS zone configuration
az network private-dns zone list --output table

# Check DNS record sets
az network private-dns record-set list \
  --resource-group myRG \
  --zone-name myzone.local
```

## Deployment Failures

### Bicep/ARM Template Errors

**Problem**: Template deployment fails

**Diagnosis**:
```bash
# View deployment operations
az deployment group show \
  --resource-group myRG \
  --name myDeployment \
  --query properties.error

# List all deployment operations
az deployment operation group list \
  --resource-group myRG \
  --name myDeployment \
  --query "[?properties.provisioningState=='Failed']"

# Get detailed error messages
az deployment operation group list \
  --resource-group myRG \
  --name myDeployment \
  --query "[].{Operation:properties.targetResource.resourceType, Error:properties.statusMessage}" \
  --output table
```

**Common Issues and Solutions**:

**1. Validation Errors:**
```bash
# Validate template before deploying
az deployment group validate \
  --resource-group myRG \
  --template-file main.bicep \
  --parameters @parameters.json

# Build Bicep to see compilation errors
az bicep build --file main.bicep
```

**2. Resource Name Conflicts:**
```bash
# Check if resource name already exists
az resource list --name {resource-name}

# Use unique names with deployment name or timestamp
param uniqueSuffix string = uniqueString(resourceGroup().id)
name: 'mystorage${uniqueSuffix}'
```

**3. Parameter Type Mismatches:**
```json
// Ensure parameters match expected types
{
  "parameters": {
    "vmSize": {
      "value": "Standard_B2s"  // String, not number
    },
    "instanceCount": {
      "value": 3  // Number, not string
    }
  }
}
```

### Deployment Timeout

**Problem**: Deployment times out

**Diagnosis**:
```bash
# Check deployment status
az deployment group show \
  --resource-group myRG \
  --name myDeployment \
  --query properties.provisioningState
```

**Solution**:
```bash
# Use --no-wait for long-running deployments
az deployment group create \
  --resource-group myRG \
  --template-file main.bicep \
  --no-wait

# Check status later
az deployment group show \
  --resource-group myRG \
  --name myDeployment
```

## CLI and Tooling Problems

### Azure CLI Command Fails

**Problem**: `az` command returns errors or unexpected results

**Diagnosis**:
```bash
# Check Azure CLI version
az --version

# Enable debug output
az vm list --debug

# Check for CLI bugs or known issues
az --version  # Note version
# Check: https://github.com/Azure/azure-cli/issues
```

**Solutions**:
```bash
# 1. Update Azure CLI
az upgrade

# 2. Clear CLI cache
rm -rf ~/.azure/

# 3. Reinstall extensions
az extension list
az extension remove --name {extension-name}
az extension add --name {extension-name}

# 4. Verify JSON syntax (common issue)
az vm create --parameters @params.json  # Ensure valid JSON
python -m json.tool params.json  # Validate JSON
```

### JMESPath Query Errors

**Problem**: `--query` returns unexpected results or errors

**Diagnosis**:
```bash
# Test query incrementally
az vm list --query "[]"  # All items
az vm list --query "[].name"  # Just names
az vm list --query "[?location=='eastus']"  # With filter

# Use jq for debugging (output to JSON first)
az vm list --output json | jq '.[] | select(.location=="eastus")'
```

**Common Issues**:
- Incorrect syntax: `[?location=eastus]` should be `[?location=='eastus']`
- Wrong operator: `&&` (and) vs `||` (or)
- Nested property access: Use `.` notation

### Bicep CLI Issues

**Problem**: `az bicep` commands fail

**Solutions**:
```bash
# Install/update Bicep
az bicep install
az bicep upgrade

# Verify installation
az bicep version

# Clear Bicep cache
rm -rf ~/.azure/bicep/

# Reinstall manually
az bicep uninstall
az bicep install
```

## Performance Issues

### Slow CLI Commands

**Problem**: Azure CLI commands are slow

**Solutions**:
```bash
# 1. Use specific queries to reduce data transfer
az vm list --query "[].{Name:name, Location:location}"  # Faster
az vm list  # Returns all data, slower

# 2. Filter at API level
az vm list --resource-group myRG  # Faster
az vm list  # Queries all resource groups, slower

# 3. Use --output tsv for scripting (faster parsing)
az vm list --query "[].name" -o tsv

# 4. Enable caching
export AZURE_CLI_DISABLE_CONNECTION_VERIFICATION=1  # Use with caution

# 5. Parallel operations with xargs
az vm list --query "[].id" -o tsv | xargs -P 5 -I {} az vm start --ids {}
```

### Timeout Errors

**Problem**: Operations timeout

**Solutions**:
```bash
# Use --no-wait for long operations
az vm create --no-wait

# Increase timeout (if available)
export AZURE_CLI_TIMEOUT=600  # 10 minutes

# Check operation status
az vm show --resource-group myRG --name myVM --query provisioningState
```

## Debugging Workflow

When encountering issues, follow this systematic approach:

1. **Identify the Error**:
   ```bash
   # Capture full error message
   az vm create ... 2>&1 | tee error.log
   ```

2. **Enable Debug Mode**:
   ```bash
   az vm create --debug ... 2>&1 | tee debug.log
   ```

3. **Verify Prerequisites**:
   - Correct subscription?
   - Sufficient permissions?
   - Resource providers registered?
   - No resource locks?

4. **Check Azure Status**:
   - Azure status: https://status.azure.com
   - Service health in Azure Portal

5. **Search for Known Issues**:
   - Azure CLI issues: https://github.com/Azure/azure-cli/issues
   - Stack Overflow: https://stackoverflow.com/questions/tagged/azure-cli
   - Microsoft Q&A: https://learn.microsoft.com/answers/topics/azure.html

6. **Contact Support**:
   ```bash
   # Create support ticket
   az support tickets create \
     --ticket-name "MyIssue" \
     --title "Brief description" \
     --description "Detailed description with error messages" \
     --problem-classification "/providers/Microsoft.Support/services/{service}/problemClassifications/{classification}" \
     --severity minimal
   ```

## Getting Help

```bash
# Command help
az vm --help
az vm create --help

# Search for commands
az find "create vm"

# Interactive mode
az interactive

# Version info
az --version

# Report bug
az feedback
```

## Related Documentation

- @user-management.md - Identity-related troubleshooting
- @role-assignments.md - RBAC permission issues
- @resource-management.md - Resource operation issues
- @cli-patterns.md - CLI scripting patterns
- @mcp-integration.md - MCP troubleshooting
