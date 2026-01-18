# Cost Optimization in Azure

Comprehensive guide to managing and optimizing Azure costs through monitoring, rightsizing, and governance.

## Table of Contents

1. [Cost Management Basics](#cost-management-basics)
2. [Cost Analysis and Reporting](#cost-analysis-and-reporting)
3. [Optimization Strategies](#optimization-strategies)
4. [Budgets and Alerts](#budgets-and-alerts)
5. [Azure Policy for Cost Governance](#azure-policy-for-cost-governance)
6. [Automation](#automation)

## Cost Management Basics

### Understanding Azure Costs

Azure costs consist of:

- **Compute**: VMs, App Services, Functions, Containers
- **Storage**: Blob, Files, Disks, managed disks
- **Networking**: Data transfer, VPN Gateway, Load Balancer
- **Databases**: SQL Database, Cosmos DB, managed instances
- **Additional Services**: Monitoring, backup, DevOps

### Cost Factors

1. **Resource Type**: Different SKUs have different pricing
2. **Region**: Costs vary by Azure region
3. **Usage**: Pay-per-use vs. reserved capacity
4. **Data Transfer**: Egress charges apply
5. **Licensing**: Bring your own license (BYOL) savings

### Viewing Current Costs

```bash
# Show current month costs
az consumption usage list \
  --start-date $(date -u -d '1 month ago' +%Y-%m-%d) \
  --end-date $(date -u +%Y-%m-%d) \
  --output table

# Cost by resource group
az costmanagement query \
  --type ActualCost \
  --dataset-aggregation name=Cost,function=Sum \
  --dataset-grouping name=ResourceGroup,type=Dimension \
  --timeframe MonthToDate

# Cost by resource type
az costmanagement query \
  --type ActualCost \
  --dataset-aggregation name=Cost,function=Sum \
  --dataset-grouping name=ResourceType,type=Dimension \
  --timeframe MonthToDate
```

## Cost Analysis and Reporting

### Generate Cost Report

```bash
#!/bin/bash
# cost-report.sh

OUTPUT_FILE="cost-report-$(date +%Y%m%d).csv"
START_DATE=$(date -u -d '30 days ago' +%Y-%m-%d)
END_DATE=$(date -u +%Y-%m-%d)

echo "Generating cost report for $START_DATE to $END_DATE..."

# Get costs by resource group
az costmanagement query \
  --type ActualCost \
  --dataset-aggregation name=Cost,function=Sum \
  --dataset-grouping name=ResourceGroup,type=Dimension \
  --timeframe Custom \
  --timePeriod from="$START_DATE" to="$END_DATE" \
  --query "properties.rows" -o json | \
  jq -r '.[] | [.[0], .[1], .[2]] | @csv' > "$OUTPUT_FILE"

echo "Report saved to: $OUTPUT_FILE"

# Display top 10 most expensive resource groups
echo ""
echo "Top 10 Most Expensive Resource Groups:"
sort -t',' -k2 -rn "$OUTPUT_FILE" | head -10 | column -t -s','
```

### Cost by Tag

```bash
# Analyze costs by tag (e.g., Environment tag)
az costmanagement query \
  --type ActualCost \
  --dataset-aggregation name=Cost,function=Sum \
  --dataset-grouping name=Tag,type=Dimension \
  --dataset-filter '{
    "and": [
      {
        "dimensions": {
          "name": "TagKey",
          "operator": "In",
          "values": ["Environment"]
        }
      }
    ]
  }' \
  --timeframe MonthToDate
```

### Forecast Future Costs

```bash
# Forecast costs for next 30 days
az costmanagement forecast \
  --type ActualCost \
  --dataset-aggregation name=Cost,function=Sum \
  --timeframe Custom \
  --timePeriod from=$(date -u +%Y-%m-%d) to=$(date -u -d '+30 days' +%Y-%m-%d)
```

## Optimization Strategies

### 1. Right-Size Virtual Machines

**Identify Oversized VMs:**

```bash
# List VMs with CPU < 10% average utilization
az monitor metrics list \
  --resource {vm-resource-id} \
  --metric "Percentage CPU" \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --interval PT1H \
  --aggregation Average \
  --query "value[].timeseries[].data[].average | avg(@)"
```

**Resize VM:**

```bash
# List available sizes
az vm list-sizes --location eastus --output table

# Resize VM (deallocates first)
az vm resize \
  --resource-group myRG \
  --name myVM \
  --size Standard_B2s
```

### 2. Reserved Instances

Reserved instances provide up to 72% savings for 1-year or 3-year commitments.

```bash
# View available reserved instance SKUs
az reservations catalog show \
  --subscription-id {subscription-id} \
  --reserved-resource-type VirtualMachines \
  --location eastus

# Calculate savings from reserved instances
# (Use Azure Portal for reservation purchases)
```

### 3. Spot VMs

Spot VMs offer up to 90% savings for fault-tolerant workloads.

```bash
# Create spot VM
az vm create \
  --resource-group myRG \
  --name mySpotVM \
  --image Ubuntu2204 \
  --priority Spot \
  --max-price 0.05 \
  --eviction-policy Deallocate
```

### 4. Auto-Shutdown for Dev/Test VMs

```bash
# Enable auto-shutdown at 7 PM UTC
az vm auto-shutdown \
  --resource-group myRG \
  --name myVM \
  --time 1900 \
  --location eastus

# Disable auto-shutdown
az vm auto-shutdown --resource-group myRG --name myVM --location eastus --time ""
```

### 5. Delete Unused Resources

**Find Orphaned Disks:**

```bash
# List unattached managed disks
az disk list --query "[?diskState=='Unattached'].{Name:name, RG:resourceGroup, Size:diskSizeGb, SKU:sku.name}" --output table

# Delete unattached disks
az disk list --query "[?diskState=='Unattached'].id" -o tsv | \
  xargs -I {} az disk delete --ids {} --yes
```

**Find Orphaned NICs:**

```bash
# List unattached network interfaces
az network nic list --query "[?virtualMachine==null].{Name:name, RG:resourceGroup}" --output table

# Delete unattached NICs
az network nic list --query "[?virtualMachine==null].id" -o tsv | \
  xargs -I {} az network nic delete --ids {} --yes
```

**Find Orphaned Public IPs:**

```bash
# List unassociated public IPs
az network public-ip list --query "[?ipConfiguration==null].{Name:name, RG:resourceGroup}" --output table

# Delete unassociated public IPs
az network public-ip list --query "[?ipConfiguration==null].id" -o tsv | \
  xargs -I {} az network public-ip delete --ids {} --yes
```

### 6. Storage Cost Optimization

**Move to Cool/Archive Tiers:**

```bash
# Set blob access tier to Cool
az storage blob set-tier \
  --account-name mystorageaccount \
  --container-name mycontainer \
  --name myblob \
  --tier Cool

# Lifecycle management policy (JSON)
az storage account management-policy create \
  --account-name mystorageaccount \
  --policy @policy.json

# policy.json example:
{
  "rules": [
    {
      "enabled": true,
      "name": "move-to-cool",
      "type": "Lifecycle",
      "definition": {
        "actions": {
          "baseBlob": {
            "tierToCool": {
              "daysAfterModificationGreaterThan": 30
            },
            "tierToArchive": {
              "daysAfterModificationGreaterThan": 90
            },
            "delete": {
              "daysAfterModificationGreaterThan": 365
            }
          }
        },
        "filters": {
          "blobTypes": ["blockBlob"]
        }
      }
    }
  ]
}
```

### 7. Scale Down Non-Production Resources

```bash
#!/bin/bash
# scale-down-dev.sh - Scale down dev environments

# App Service Plans
az appservice plan list --query "[?tags.Environment=='Development'].{Name:name, RG:resourceGroup}" -o tsv | \
  while read -r name rg; do
    az appservice plan update --name "$name" --resource-group "$rg" --sku B1
    echo "✓ Scaled down App Service Plan: $name"
  done

# SQL Databases
az sql db list --query "[?tags.Environment=='Development'].{Name:name, Server:serverName, RG:resourceGroup}" -o tsv | \
  while read -r name server rg; do
    az sql db update --name "$name" --server "$server" --resource-group "$rg" --service-objective S0
    echo "✓ Scaled down SQL Database: $name"
  done
```

## Budgets and Alerts

### Create Budget

```bash
# Create monthly budget
az consumption budget create \
  --budget-name "MonthlyBudget" \
  --amount 1000 \
  --category Cost \
  --time-grain Monthly \
  --start-date $(date -u +%Y-%m-01T00:00:00Z) \
  --end-date $(date -u -d '+1 year' +%Y-%m-01T00:00:00Z) \
  --resource-group myRG

# Create budget with email notification at 80% and 100%
az consumption budget create \
  --budget-name "MonthlyBudgetWithAlerts" \
  --amount 1000 \
  --category Cost \
  --time-grain Monthly \
  --start-date $(date -u +%Y-%m-01T00:00:00Z) \
  --notifications '[
    {
      "enabled": true,
      "operator": "GreaterThan",
      "threshold": 80,
      "contactEmails": ["admin@contoso.com"],
      "contactRoles": ["Owner", "Contributor"]
    },
    {
      "enabled": true,
      "operator": "GreaterThan",
      "threshold": 100,
      "contactEmails": ["admin@contoso.com", "finance@contoso.com"],
      "contactRoles": ["Owner"]
    }
  ]'
```

### List Budgets

```bash
# List all budgets
az consumption budget list --output table

# Show budget details
az consumption budget show --budget-name "MonthlyBudget"
```

### Cost Alerts

```bash
# Create action group for cost alerts
az monitor action-group create \
  --name "CostAlertActionGroup" \
  --resource-group myRG \
  --short-name "CostAlert" \
  --email admin email=admin@contoso.com

# Create cost alert rule
az monitor metrics alert create \
  --name "HighCostAlert" \
  --resource-group myRG \
  --scopes /subscriptions/{subscription-id} \
  --condition "total Cost > 1000" \
  --description "Alert when monthly cost exceeds $1000" \
  --action "CostAlertActionGroup"
```

## Azure Policy for Cost Governance

### Enforce Resource SKUs

```json
{
  "properties": {
    "displayName": "Allowed VM SKUs",
    "description": "Restrict VM SKUs to cost-effective options",
    "mode": "Indexed",
    "policyRule": {
      "if": {
        "allOf": [
          {
            "field": "type",
            "equals": "Microsoft.Compute/virtualMachines"
          },
          {
            "not": {
              "field": "Microsoft.Compute/virtualMachines/sku.name",
              "in": ["Standard_B2s", "Standard_B2ms", "Standard_D2s_v3", "Standard_D4s_v3"]
            }
          }
        ]
      },
      "then": {
        "effect": "deny"
      }
    }
  }
}
```

### Require Tags for Cost Tracking

```bash
# Assign built-in policy to require tags
az policy assignment create \
  --name "RequireCostCenterTag" \
  --policy "96670d01-0a4d-4649-9c89-2d3abc0a5025" \
  --params '{
    "tagName": {
      "value": "CostCenter"
    }
  }' \
  --resource-group myRG
```

### Enforce Resource Location (Cost Optimization)

```bash
# Restrict to cost-effective regions
az policy assignment create \
  --name "AllowedLocations" \
  --policy "e56962a6-4747-49cd-b67b-bf8b01975c4c" \
  --params '{
    "listOfAllowedLocations": {
      "value": ["eastus", "eastus2", "centralus"]
    }
  }' \
  --resource-group myRG
```

## Automation

### Scheduled Cost Reports

```bash
#!/bin/bash
# scheduled-cost-report.sh - Run via cron

REPORT_DIR="/reports/azure-costs"
REPORT_FILE="$REPORT_DIR/cost-report-$(date +%Y%m%d).json"
EMAIL="finance@contoso.com"

mkdir -p "$REPORT_DIR"

# Generate cost report
az costmanagement query \
  --type ActualCost \
  --dataset-aggregation name=Cost,function=Sum \
  --dataset-grouping name=ResourceGroup,type=Dimension \
  --timeframe MonthToDate > "$REPORT_FILE"

# Parse and format
TOTAL_COST=$(jq -r '.properties.rows | map(.[0]) | add' "$REPORT_FILE")

# Send email (requires mail utility)
cat <<EOF | mail -s "Azure Monthly Cost Report: \$$TOTAL_COST" "$EMAIL"
Azure cost report for $(date +%B\ %Y)

Total Cost: \$$TOTAL_COST

Top 5 Resource Groups:
$(jq -r '.properties.rows | sort_by(.[0]) | reverse | .[0:5] | .[] | "\(.[1]): $\(.[0])"' "$REPORT_FILE")

Full report attached.
EOF
```

### Auto-Cleanup Old Resources

```bash
#!/bin/bash
# auto-cleanup-old-resources.sh

DAYS_OLD=90
TAG_KEY="ExpirationDate"

echo "Finding resources older than $DAYS_OLD days with expiration dates..."

# Find expired resources
EXPIRED_RESOURCES=$(az resource list \
  --query "[?tags.$TAG_KEY != null && tags.$TAG_KEY < '$(date +%Y-%m-%d)'].id" -o tsv)

if [ -z "$EXPIRED_RESOURCES" ]; then
  echo "No expired resources found"
  exit 0
fi

echo "Found $(echo "$EXPIRED_RESOURCES" | wc -l) expired resources"

# Delete expired resources
echo "$EXPIRED_RESOURCES" | while read -r resource_id; do
  echo "Deleting: $resource_id"
  az resource delete --ids "$resource_id" --verbose
done

echo "Cleanup complete"
```

## Cost Optimization Checklist

- [ ] Review monthly cost reports
- [ ] Identify and delete unused resources (disks, NICs, IPs)
- [ ] Right-size oversized VMs based on utilization metrics
- [ ] Evaluate reserved instances for steady-state workloads
- [ ] Use spot VMs for fault-tolerant batch processing
- [ ] Implement auto-shutdown for dev/test environments
- [ ] Move cold storage to Cool/Archive tiers
- [ ] Consolidate resources to reduce networking costs
- [ ] Review and optimize data transfer patterns
- [ ] Ensure all resources are tagged for cost allocation
- [ ] Set up budgets and cost alerts
- [ ] Enforce cost policies via Azure Policy
- [ ] Regular access reviews to remove unused identities
- [ ] Scale down non-production resources
- [ ] Review licensing (BYOL opportunities)

## Related Documentation

- @resource-management.md - Resource tagging for cost tracking
- @cli-patterns.md - Automation scripts for cost management
- @troubleshooting.md - Cost management API issues
- @../examples/environment-setup.md - Cost-optimized environment templates
