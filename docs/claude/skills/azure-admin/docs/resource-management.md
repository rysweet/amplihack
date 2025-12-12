# Resource Management in Azure

Comprehensive guide to managing Azure resources, resource groups, subscriptions, and infrastructure as code.

## Table of Contents

1. [Resource Hierarchy](#resource-hierarchy)
2. [Resource Groups](#resource-groups)
3. [Resource Operations](#resource-operations)
4. [Infrastructure as Code](#infrastructure-as-code)
5. [Resource Tagging](#resource-tagging)
6. [Resource Locks](#resource-locks)
7. [Resource Move Operations](#resource-move-operations)

## Resource Hierarchy

Azure organizes resources in a hierarchical structure:

```
Management Groups (optional)
└── Subscriptions (billing boundary)
    └── Resource Groups (logical container)
        └── Resources (VMs, storage, networks, etc.)
```

### Management Groups

Group multiple subscriptions for policy and compliance management.

```bash
# Create management group
az account management-group create \
  --name "ProductionManagementGroup" \
  --display-name "Production Management Group"

# Add subscription to management group
az account management-group subscription add \
  --name "ProductionManagementGroup" \
  --subscription {subscription-id}

# List management groups
az account management-group list --output table

# Show management group hierarchy
az account management-group show \
  --name "ProductionManagementGroup" \
  --expand --recurse
```

### Subscriptions

```bash
# List subscriptions
az account list --output table

# Show current subscription
az account show

# Set active subscription
az account set --subscription "My Subscription"

# Get subscription ID
az account show --query id -o tsv

# List available locations
az account list-locations --query "[].{Name:name, DisplayName:displayName}" --output table
```

## Resource Groups

Resource groups are fundamental containers for managing related Azure resources.

### Creating Resource Groups

```bash
# Basic creation
az group create --name myResourceGroup --location eastus

# With tags
az group create \
  --name myResourceGroup \
  --location eastus \
  --tags Environment=Production Department=IT CostCenter=12345

# Multiple resource groups (for multi-region)
for region in eastus westus centralus; do
  az group create --name "myapp-${region}-rg" --location "$region"
done
```

### Listing and Querying Resource Groups

```bash
# List all resource groups
az group list --output table

# Filter by location
az group list --query "[?location=='eastus']" --output table

# Filter by tag
az group list --query "[?tags.Environment=='Production']" --output table

# Show resources in group
az resource list --resource-group myResourceGroup --output table

# Count resources per group
az group list --query "[].{Name:name, Count:length(resources)}"
```

### Updating Resource Groups

```bash
# Add/update tags
az group update \
  --name myResourceGroup \
  --tags Environment=Production Owner=jane@contoso.com

# Add tags without removing existing
az group update \
  --name myResourceGroup \
  --set tags.NewTag=NewValue
```

### Deleting Resource Groups

```bash
# Delete resource group (deletes ALL resources inside)
az group delete --name myResourceGroup --yes --no-wait

# Delete with confirmation
az group delete --name myResourceGroup

# Delete multiple resource groups
for rg in myRG1 myRG2 myRG3; do
  az group delete --name "$rg" --yes --no-wait
done

# Check deletion status
az group exists --name myResourceGroup
```

### Resource Group Best Practices

1. **Organize by lifecycle** - Resources that share the same lifecycle belong together
2. **One application per group** - Group all resources for a single application
3. **Environment separation** - Separate dev, test, prod into different groups
4. **Consistent naming** - Use naming convention: `{app}-{env}-{region}-rg`
5. **Tag everything** - Apply tags for cost tracking, ownership, environment
6. **Use locks** - Protect production resource groups from accidental deletion
7. **Same region preference** - Resources in same region as group for better management

## Resource Operations

### Listing Resources

```bash
# List all resources in subscription
az resource list --output table

# List resources in resource group
az resource list --resource-group myResourceGroup --output table

# Filter by resource type
az resource list --resource-type "Microsoft.Compute/virtualMachines" --output table

# Filter by location
az resource list --location eastus --output table

# Filter by tag
az resource list --tag Environment=Production --output table

# Get specific resource
az resource show \
  --resource-group myResourceGroup \
  --name myVM \
  --resource-type "Microsoft.Compute/virtualMachines"
```

### Creating Resources

```bash
# Create virtual network
az network vnet create \
  --resource-group myResourceGroup \
  --name myVNet \
  --address-prefix 10.0.0.0/16 \
  --subnet-name default \
  --subnet-prefix 10.0.1.0/24

# Create storage account
az storage account create \
  --name mystorageaccount \
  --resource-group myResourceGroup \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2

# Create virtual machine
az vm create \
  --resource-group myResourceGroup \
  --name myVM \
  --image Ubuntu2204 \
  --size Standard_B2s \
  --admin-username azureuser \
  --generate-ssh-keys
```

### Updating Resources

```bash
# Update VM size
az vm resize \
  --resource-group myResourceGroup \
  --name myVM \
  --size Standard_D4s_v3

# Update storage account tier
az storage account update \
  --name mystorageaccount \
  --resource-group myResourceGroup \
  --sku Standard_GRS

# Update resource tags
az resource tag \
  --tags Environment=Production CostCenter=12345 \
  --ids /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/myVM
```

### Deleting Resources

```bash
# Delete virtual machine
az vm delete --resource-group myResourceGroup --name myVM --yes

# Delete multiple resources
for vm in vm1 vm2 vm3; do
  az vm delete --resource-group myResourceGroup --name "$vm" --yes --no-wait
done

# Delete all resources of a type
az resource list \
  --resource-group myResourceGroup \
  --resource-type "Microsoft.Compute/virtualMachines" \
  --query "[].id" -o tsv | \
  xargs -I {} az resource delete --ids {}
```

## Infrastructure as Code

### ARM Templates

ARM templates are JSON files that define infrastructure declaratively.

**Basic template structure:**
```json
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "location": {
      "type": "string",
      "defaultValue": "[resourceGroup().location]"
    }
  },
  "resources": [
    {
      "type": "Microsoft.Storage/storageAccounts",
      "apiVersion": "2023-01-01",
      "name": "mystorageaccount",
      "location": "[parameters('location')]",
      "sku": {
        "name": "Standard_LRS"
      },
      "kind": "StorageV2"
    }
  ],
  "outputs": {
    "storageAccountId": {
      "type": "string",
      "value": "[resourceId('Microsoft.Storage/storageAccounts', 'mystorageaccount')]"
    }
  }
}
```

**Deploy ARM template:**
```bash
az deployment group create \
  --resource-group myResourceGroup \
  --template-file template.json \
  --parameters location=eastus

# With parameter file
az deployment group create \
  --resource-group myResourceGroup \
  --template-file template.json \
  --parameters @parameters.json

# Validate before deploying
az deployment group validate \
  --resource-group myResourceGroup \
  --template-file template.json

# What-if analysis
az deployment group what-if \
  --resource-group myResourceGroup \
  --template-file template.json
```

### Bicep

Bicep is a domain-specific language (DSL) for deploying Azure resources with cleaner syntax than ARM templates.

**Basic Bicep file:**
```bicep
param location string = resourceGroup().location
param storageAccountName string = 'mystorageaccount'
param storageSku string = 'Standard_LRS'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: storageSku
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
  }
}

output storageAccountId string = storageAccount.id
output primaryEndpoint string = storageAccount.properties.primaryEndpoints.blob
```

**Multi-resource Bicep example:**
```bicep
param location string = resourceGroup().location
param vmName string
param vmSize string = 'Standard_B2s'
param adminUsername string

resource vnet 'Microsoft.Network/virtualNetworks@2023-05-01' = {
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

resource nic 'Microsoft.Network/networkInterfaces@2023-05-01' = {
  name: '${vmName}-nic'
  location: location
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          subnet: {
            id: vnet.properties.subnets[0].id
          }
          privateIPAllocationMethod: 'Dynamic'
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
    osProfile: {
      computerName: vmName
      adminUsername: adminUsername
      linuxConfiguration: {
        disablePasswordAuthentication: true
        ssh: {
          publicKeys: [
            {
              path: '/home/${adminUsername}/.ssh/authorized_keys'
              keyData: loadTextContent('~/.ssh/id_rsa.pub')
            }
          ]
        }
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: nic.id
        }
      ]
    }
    storageProfile: {
      imageReference: {
        publisher: 'Canonical'
        offer: '0001-com-ubuntu-server-jammy'
        sku: '22_04-lts-gen2'
        version: 'latest'
      }
      osDisk: {
        createOption: 'FromImage'
        managedDisk: {
          storageAccountType: 'Premium_LRS'
        }
      }
    }
  }
}
```

**Bicep CLI operations:**
```bash
# Install/update Bicep
az bicep install
az bicep upgrade
az bicep version

# Build Bicep to ARM template
az bicep build --file main.bicep

# Decompile ARM template to Bicep
az bicep decompile --file template.json

# Deploy Bicep file
az deployment group create \
  --resource-group myResourceGroup \
  --template-file main.bicep \
  --parameters vmName=myVM adminUsername=azureuser

# Validate Bicep
az deployment group validate \
  --resource-group myResourceGroup \
  --template-file main.bicep
```

### Bicep Modules

Organize reusable infrastructure patterns:

**storage-module.bicep:**
```bicep
param location string
param storageAccountName string
param storageSku string = 'Standard_LRS'

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: storageSku
  }
  kind: 'StorageV2'
}

output storageAccountId string = storageAccount.id
```

**main.bicep (using module):**
```bicep
param location string = resourceGroup().location

module storage 'storage-module.bicep' = {
  name: 'storageDeployment'
  params: {
    location: location
    storageAccountName: 'mystorageaccount'
    storageSku: 'Standard_GRS'
  }
}

output storageId string = storage.outputs.storageAccountId
```

## Resource Tagging

Tags enable organization, cost tracking, and automation.

### Tagging Strategy

**Common tag schemas:**
```json
{
  "Environment": "Production|Development|Test",
  "CostCenter": "IT|Engineering|Marketing",
  "Owner": "email@contoso.com",
  "Application": "CustomerPortal|InternalTools",
  "Criticality": "High|Medium|Low",
  "Compliance": "PCI-DSS|HIPAA|SOC2",
  "BackupPolicy": "Daily|Weekly|None",
  "MaintenanceWindow": "Saturday 2-4am UTC",
  "ExpirationDate": "2025-12-31"
}
```

### Applying Tags

```bash
# Tag resource group
az group update \
  --name myResourceGroup \
  --tags Environment=Production CostCenter=IT Owner=admin@contoso.com

# Tag resource
az resource tag \
  --tags Environment=Production Application=WebApp \
  --ids /subscriptions/{sub}/resourceGroups/{rg}/providers/Microsoft.Compute/virtualMachines/myVM

# Bulk tag resources in resource group
az resource list --resource-group myResourceGroup --query "[].id" -o tsv | \
  xargs -I {} az resource tag --tags Environment=Production --ids {}

# Copy tags from resource group to resources
RG_TAGS=$(az group show --name myResourceGroup --query tags -o json)
az resource list --resource-group myResourceGroup --query "[].id" -o tsv | \
  xargs -I {} az resource tag --tags "$RG_TAGS" --ids {}
```

### Querying by Tags

```bash
# Find resources by tag
az resource list --tag Environment=Production --output table

# Find resources with multiple tag criteria
az resource list \
  --query "[?tags.Environment=='Production' && tags.Criticality=='High']" \
  --output table

# List all tag keys/values
az tag list --output table
```

## Resource Locks

Locks prevent accidental deletion or modification of resources.

### Lock Types

- **CanNotDelete**: Can read and modify, but cannot delete
- **ReadOnly**: Can only read, no modifications or deletions

### Applying Locks

```bash
# Lock resource group
az lock create \
  --name DontDeleteLock \
  --lock-type CanNotDelete \
  --resource-group myResourceGroup

# Lock specific resource
az lock create \
  --name ReadOnlyLock \
  --lock-type ReadOnly \
  --resource-group myResourceGroup \
  --resource-name myVM \
  --resource-type Microsoft.Compute/virtualMachines

# Lock at subscription level
az lock create \
  --name SubscriptionLock \
  --lock-type CanNotDelete \
  --resource-group myResourceGroup
```

### Managing Locks

```bash
# List locks
az lock list --resource-group myResourceGroup --output table

# Show lock details
az lock show --name DontDeleteLock --resource-group myResourceGroup

# Delete lock
az lock delete --name DontDeleteLock --resource-group myResourceGroup
```

## Resource Move Operations

Move resources between resource groups or subscriptions.

### Move Between Resource Groups

```bash
# Get resource IDs to move
RESOURCE_IDS=$(az resource list --resource-group sourceRG --query "[].id" -o tsv)

# Move resources
az resource move \
  --destination-group targetRG \
  --ids $RESOURCE_IDS

# Move specific resources
az resource move \
  --destination-group targetRG \
  --ids /subscriptions/{sub}/resourceGroups/sourceRG/providers/Microsoft.Compute/virtualMachines/myVM
```

### Move Between Subscriptions

```bash
az resource move \
  --destination-group targetRG \
  --destination-subscription-id {target-subscription-id} \
  --ids {resource-ids}
```

### Move Limitations

Not all resources support move operations. Check compatibility:
```bash
az rest --method POST \
  --url "https://management.azure.com/subscriptions/{sub}/resourceGroups/{rg}/validateMoveResources?api-version=2021-04-01" \
  --body '{"resources": ["{resource-id}"], "targetResourceGroup": "{target-rg-id}"}'
```

## Related Documentation

- @user-management.md - Identity and access management
- @role-assignments.md - RBAC for resources
- @cli-patterns.md - Advanced CLI patterns for resource management
- @devops-automation.md - Infrastructure as code in CI/CD
- @cost-optimization.md - Resource cost management
- @../examples/environment-setup.md - Complete environment provisioning
