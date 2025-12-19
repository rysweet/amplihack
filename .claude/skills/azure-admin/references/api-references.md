# Azure API and SDK References

Comprehensive reference for Azure REST APIs, SDKs, and programmatic access.

## REST API Documentation

### Core Management APIs

**Azure Resource Manager (ARM) REST API**

- Base URL: `https://management.azure.com/`
- Documentation: https://learn.microsoft.com/rest/api/resources/
- API Version: 2021-04-01 (stable)

**Common Operations:**

```bash
# List subscriptions
GET https://management.azure.com/subscriptions?api-version=2020-01-01

# List resource groups
GET https://management.azure.com/subscriptions/{subscriptionId}/resourcegroups?api-version=2021-04-01

# Create resource group
PUT https://management.azure.com/subscriptions/{subscriptionId}/resourcegroups/{resourceGroupName}?api-version=2021-04-01

# Delete resource group
DELETE https://management.azure.com/subscriptions/{subscriptionId}/resourcegroups/{resourceGroupName}?api-version=2021-04-01
```

### Microsoft Graph API

**Base URL:** `https://graph.microsoft.com/v1.0/` or `/beta/`
**Documentation:** https://learn.microsoft.com/graph/api/overview

**Identity and Access:**

```bash
# List users
GET https://graph.microsoft.com/v1.0/users

# Create user
POST https://graph.microsoft.com/v1.0/users

# Get user
GET https://graph.microsoft.com/v1.0/users/{user-id}

# List groups
GET https://graph.microsoft.com/v1.0/groups

# List group members
GET https://graph.microsoft.com/v1.0/groups/{group-id}/members

# List role assignments (directory roles)
GET https://graph.microsoft.com/v1.0/directoryRoles
```

### Service-Specific APIs

**Compute (Virtual Machines)**

- Documentation: https://learn.microsoft.com/rest/api/compute/

```bash
# List VMs
GET https://management.azure.com/subscriptions/{subscriptionId}/providers/Microsoft.Compute/virtualMachines?api-version=2023-03-01

# Create VM
PUT https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Compute/virtualMachines/{vmName}?api-version=2023-03-01

# Start VM
POST https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Compute/virtualMachines/{vmName}/start?api-version=2023-03-01
```

**Storage**

- Documentation: https://learn.microsoft.com/rest/api/storageservices/

```bash
# List storage accounts
GET https://management.azure.com/subscriptions/{subscriptionId}/providers/Microsoft.Storage/storageAccounts?api-version=2023-01-01

# Create storage account
PUT https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Storage/storageAccounts/{accountName}?api-version=2023-01-01

# List blob containers
GET https://{accountName}.blob.core.windows.net/?comp=list

# Upload blob
PUT https://{accountName}.blob.core.windows.net/{container}/{blob}
```

**Networking**

- Documentation: https://learn.microsoft.com/rest/api/virtualnetwork/

```bash
# List virtual networks
GET https://management.azure.com/subscriptions/{subscriptionId}/providers/Microsoft.Network/virtualNetworks?api-version=2023-05-01

# Create virtual network
PUT https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Network/virtualNetworks/{vnetName}?api-version=2023-05-01

# List network security groups
GET https://management.azure.com/subscriptions/{subscriptionId}/providers/Microsoft.Network/networkSecurityGroups?api-version=2023-05-01
```

**App Service**

- Documentation: https://learn.microsoft.com/rest/api/appservice/

```bash
# List App Service plans
GET https://management.azure.com/subscriptions/{subscriptionId}/providers/Microsoft.Web/serverfarms?api-version=2022-09-01

# Create App Service
PUT https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Web/sites/{name}?api-version=2022-09-01

# List deployment slots
GET https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.Web/sites/{name}/slots?api-version=2022-09-01
```

## Authentication

### Azure AD OAuth 2.0

**Token Endpoint:**

```
https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/token
```

**Authorization Flow (Client Credentials):**

```bash
curl -X POST https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id={client-id}" \
  -d "client_secret={client-secret}" \
  -d "scope=https://management.azure.com/.default" \
  -d "grant_type=client_credentials"
```

**Response:**

```json
{
  "token_type": "Bearer",
  "expires_in": 3599,
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGci..."
}
```

**Using Token:**

```bash
curl -H "Authorization: Bearer {access_token}" \
  https://management.azure.com/subscriptions?api-version=2020-01-01
```

## SDK References

### Python SDK (azure-sdk-for-python)

**GitHub:** https://github.com/Azure/azure-sdk-for-python
**Documentation:** https://learn.microsoft.com/python/api/overview/azure/

**Installation:**

```bash
# Core management libraries
pip install azure-mgmt-resource
pip install azure-mgmt-compute
pip install azure-mgmt-storage
pip install azure-mgmt-network
pip install azure-mgmt-web
pip install azure-mgmt-authorization

# Identity library
pip install azure-identity
```

**Example Usage:**

```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient

# Authenticate
credential = DefaultAzureCredential()
subscription_id = "your-subscription-id"

# Resource management
resource_client = ResourceManagementClient(credential, subscription_id)

# List resource groups
for rg in resource_client.resource_groups.list():
    print(rg.name)

# Create resource group
resource_client.resource_groups.create_or_update(
    "myResourceGroup",
    {"location": "eastus"}
)

# Compute management
compute_client = ComputeManagementClient(credential, subscription_id)

# List VMs
for vm in compute_client.virtual_machines.list_all():
    print(vm.name)

# Start VM
compute_client.virtual_machines.begin_start(
    "myResourceGroup",
    "myVM"
).result()
```

### JavaScript/TypeScript SDK

**GitHub:** https://github.com/Azure/azure-sdk-for-js
**Documentation:** https://learn.microsoft.com/javascript/api/overview/azure/

**Installation:**

```bash
npm install @azure/identity
npm install @azure/arm-resources
npm install @azure/arm-compute
npm install @azure/arm-storage
npm install @azure/arm-network
```

**Example Usage:**

```typescript
import { DefaultAzureCredential } from "@azure/identity";
import { ResourceManagementClient } from "@azure/arm-resources";
import { ComputeManagementClient } from "@azure/arm-compute";

const credential = new DefaultAzureCredential();
const subscriptionId = "your-subscription-id";

// Resource management
const resourceClient = new ResourceManagementClient(credential, subscriptionId);

// List resource groups
for await (const rg of resourceClient.resourceGroups.list()) {
  console.log(rg.name);
}

// Create resource group
await resourceClient.resourceGroups.createOrUpdate("myResourceGroup", {
  location: "eastus",
});

// Compute management
const computeClient = new ComputeManagementClient(credential, subscriptionId);

// List VMs
for await (const vm of computeClient.virtualMachines.listAll()) {
  console.log(vm.name);
}

// Start VM
await computeClient.virtualMachines.beginStartAndWait("myResourceGroup", "myVM");
```

### .NET SDK

**GitHub:** https://github.com/Azure/azure-sdk-for-net
**Documentation:** https://learn.microsoft.com/dotnet/api/overview/azure/

**Installation:**

```bash
dotnet add package Azure.Identity
dotnet add package Azure.ResourceManager
dotnet add package Azure.ResourceManager.Compute
dotnet add package Azure.ResourceManager.Storage
dotnet add package Azure.ResourceManager.Network
```

**Example Usage:**

```csharp
using Azure.Identity;
using Azure.ResourceManager;
using Azure.ResourceManager.Resources;
using Azure.ResourceManager.Compute;

var credential = new DefaultAzureCredential();
var armClient = new ArmClient(credential);

// Get subscription
var subscription = armClient.GetDefaultSubscription();

// List resource groups
await foreach (var rg in subscription.GetResourceGroups())
{
    Console.WriteLine(rg.Data.Name);
}

// Create resource group
var rgData = new ResourceGroupData("eastus");
await subscription.GetResourceGroups().CreateOrUpdateAsync(
    WaitUntil.Completed,
    "myResourceGroup",
    rgData
);

// List VMs
await foreach (var vm in subscription.GetVirtualMachinesAsync())
{
    Console.WriteLine(vm.Data.Name);
}

// Start VM
var resourceGroup = subscription.GetResourceGroups().Get("myResourceGroup");
var vm = resourceGroup.Value.GetVirtualMachines().Get("myVM");
await vm.Value.PowerOnAsync(WaitUntil.Completed);
```

### Go SDK

**GitHub:** https://github.com/Azure/azure-sdk-for-go
**Documentation:** https://pkg.go.dev/github.com/Azure/azure-sdk-for-go

**Installation:**

```bash
go get github.com/Azure/azure-sdk-for-go/sdk/azidentity
go get github.com/Azure/azure-sdk-for-go/sdk/resourcemanager/resources/armresources
go get github.com/Azure/azure-sdk-for-go/sdk/resourcemanager/compute/armcompute
```

**Example Usage:**

```go
package main

import (
    "context"
    "github.com/Azure/azure-sdk-for-go/sdk/azidentity"
    "github.com/Azure/azure-sdk-for-go/sdk/resourcemanager/resources/armresources"
    "github.com/Azure/azure-sdk-for-go/sdk/resourcemanager/compute/armcompute"
)

func main() {
    cred, _ := azidentity.NewDefaultAzureCredential(nil)
    subscriptionID := "your-subscription-id"

    // Resource groups client
    rgClient, _ := armresources.NewResourceGroupsClient(subscriptionID, cred, nil)

    // List resource groups
    pager := rgClient.NewListPager(nil)
    for pager.More() {
        page, _ := pager.NextPage(context.Background())
        for _, rg := range page.Value {
            println(*rg.Name)
        }
    }

    // Create resource group
    rgClient.CreateOrUpdate(context.Background(), "myResourceGroup", armresources.ResourceGroup{
        Location: to.Ptr("eastus"),
    }, nil)

    // VMs client
    vmClient, _ := armcompute.NewVirtualMachinesClient(subscriptionID, cred, nil)

    // List VMs
    vmPager := vmClient.NewListAllPager(nil)
    for vmPager.More() {
        page, _ := vmPager.NextPage(context.Background())
        for _, vm := range page.Value {
            println(*vm.Name)
        }
    }

    // Start VM
    vmClient.BeginStart(context.Background(), "myResourceGroup", "myVM", nil)
}
```

## Azure Resource Graph API

**Query resources at scale using KQL (Kusto Query Language)**

**Documentation:** https://learn.microsoft.com/azure/governance/resource-graph/

**REST API:**

```bash
POST https://management.azure.com/providers/Microsoft.ResourceGraph/resources?api-version=2021-03-01

{
  "subscriptions": ["{subscription-id}"],
  "query": "Resources | where type =~ 'Microsoft.Compute/virtualMachines' | project name, location, resourceGroup"
}
```

**Python SDK:**

```python
from azure.mgmt.resourcegraph import ResourceGraphClient
from azure.mgmt.resourcegraph.models import QueryRequest

graph_client = ResourceGraphClient(credential)

query = QueryRequest(
    subscriptions=[subscription_id],
    query="Resources | where type =~ 'Microsoft.Compute/virtualMachines' | project name, location"
)

response = graph_client.resources(query)
for row in response.data:
    print(row)
```

## Cost Management API

**Documentation:** https://learn.microsoft.com/rest/api/cost-management/

**Query Costs:**

```bash
POST https://management.azure.com/subscriptions/{subscriptionId}/providers/Microsoft.CostManagement/query?api-version=2023-03-01

{
  "type": "ActualCost",
  "timeframe": "MonthToDate",
  "dataset": {
    "granularity": "Daily",
    "aggregation": {
      "totalCost": {
        "name": "Cost",
        "function": "Sum"
      }
    },
    "grouping": [
      {
        "type": "Dimension",
        "name": "ResourceGroup"
      }
    ]
  }
}
```

## Monitoring and Logging APIs

**Azure Monitor REST API**

- Documentation: https://learn.microsoft.com/rest/api/monitor/

**Log Analytics Query API:**

```bash
POST https://api.loganalytics.io/v1/workspaces/{workspace-id}/query

{
  "query": "AzureActivity | where TimeGenerated > ago(1d) | summarize count() by OperationName"
}
```

## Rate Limits and Throttling

**ARM API Limits:**

- Read requests: 12,000 per hour
- Write requests: 1,200 per hour

**Best Practices:**

- Implement exponential backoff for retries
- Cache responses when possible
- Use batch operations
- Monitor for 429 (Too Many Requests) status codes

**Retry Logic Example (Python):**

```python
import time
from azure.core.exceptions import HttpResponseError

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except HttpResponseError as e:
            if e.status_code == 429 and attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                raise
```

## Related Documentation

- @../docs/cli-patterns.md - CLI alternatives to APIs
- @../docs/mcp-integration.md - MCP abstraction over APIs
- @microsoft-learn.md - Learning resources for APIs
- @az-104-guide.md - Certification covering API usage
