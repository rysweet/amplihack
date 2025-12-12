# Azure CLI Patterns and Best Practices

Advanced patterns for Azure CLI scripting, querying, and automation.

## Table of Contents

1. [JMESPath Query Patterns](#jmespath-query-patterns)
2. [Batch Operations](#batch-operations)
3. [Error Handling](#error-handling)
4. [Output Formatting](#output-formatting)
5. [Scripting Best Practices](#scripting-best-practices)
6. [Performance Optimization](#performance-optimization)

## JMESPath Query Patterns

JMESPath is the query language used by Azure CLI for filtering and transforming output.

### Basic Filtering

```bash
# Select specific fields
az vm list --query "[].{Name:name, Location:location, RG:resourceGroup}"

# Filter by property value
az vm list --query "[?location=='eastus']"

# Multiple conditions (AND)
az vm list --query "[?location=='eastus' && powerState=='VM running']"

# Multiple conditions (OR) - use logical operators
az vm list --query "[?location=='eastus' || location=='westus']"

# Negate condition
az vm list --query "[?powerState!='VM deallocated']"
```

### String Operations

```bash
# Contains substring
az resource list --query "[?contains(name, 'prod')]"

# Starts with
az resource list --query "[?starts_with(name, 'vm-')]"

# Ends with
az resource list --query "[?ends_with(name, '-prod')]"

# Case-insensitive matching (convert to lowercase)
az resource list --query "[?contains(to_lower(name), 'production')]"
```

### Array Operations

```bash
# Get first element
az vm list --query "[0]"

# Get last element
az vm list --query "[-1]"

# Get elements by index range
az vm list --query "[0:5]"  # First 5 elements

# Length/count
az vm list --query "length([])"

# Filter and count
az vm list --query "length([?location=='eastus'])"

# Map/projection with array
az vm list --query "[].{Name:name, Tags:tags.Environment}"
```

### Nested Property Access

```bash
# Access nested properties
az vm list --query "[].{Name:name, OS:storageProfile.osDisk.osType}"

# Access array elements in nested objects
az vm list --query "[].{Name:name, NICs:networkProfile.networkInterfaces[].id}"

# Flatten nested arrays
az vm list --query "[].networkProfile.networkInterfaces[].id | []"
```

### Sorting and Limiting

```bash
# Sort ascending
az vm list --query "sort_by([], &name)"

# Sort descending
az vm list --query "reverse(sort_by([], &name))"

# Sort by multiple keys
az vm list --query "sort_by([], &[location, name])"

# Sort by numeric property
az vm list --query "sort_by([], &to_number(properties.hardwareProfile.vmSize))"

# Limit results (first 10)
az vm list --query "[0:10]"
```

### Aggregations

```bash
# Count by property
az vm list --query "group_by([], &location) | keys(@)"

# Sum (requires jmespath-terminal extension or scripting)
az consumption usage list --query "sum([].quantity)"

# Max value
az vm list --query "max_by([], &properties.hardwareProfile.vmSize)"

# Min value
az vm list --query "min_by([], &name)"
```

### Complex Queries

```bash
# Combine multiple operations
az vm list --query "[?location=='eastus'] | [?powerState=='VM running'] | sort_by([], &name) | [].{Name:name, RG:resourceGroup}"

# Conditional output
az vm list --query "[].{Name:name, Status:powerState || 'Unknown'}"

# Type conversion
az vm list --query "[].{Name:name, SizeCode:to_number(properties.hardwareProfile.vmSize[-1:])}"

# Merge properties from different levels
az vm list --query "[].{Name:name, Location:location, Tags:tags, VMSize:properties.hardwareProfile.vmSize}"
```

## Batch Operations

### Parallel Processing

```bash
# Process items in parallel with xargs
az vm list --query "[].id" -o tsv | \
  xargs -I {} -P 5 az vm start --ids {}

# -P 5 means 5 parallel processes
# Adjust based on API rate limits and system resources
```

### Bulk Resource Operations

```bash
#!/bin/bash
# bulk-tag-resources.sh

RESOURCE_GROUP="myResourceGroup"
TAG_KEY="Environment"
TAG_VALUE="Production"

# Get all resource IDs
RESOURCE_IDS=$(az resource list \
  --resource-group "$RESOURCE_GROUP" \
  --query "[].id" -o tsv)

# Tag each resource
echo "$RESOURCE_IDS" | while read -r resource_id; do
  echo "Tagging: $resource_id"
  az resource tag \
    --tags "$TAG_KEY=$TAG_VALUE" \
    --ids "$resource_id"
done
```

### Bulk User Creation

```bash
#!/bin/bash
# bulk-create-users.sh

CSV_FILE="users.csv"
LOG_FILE="user-creation-$(date +%Y%m%d-%H%M%S).log"

# Process CSV (skip header)
tail -n +2 "$CSV_FILE" | while IFS=, read -r display_name upn password department; do
  echo "Creating: $display_name ($upn)" | tee -a "$LOG_FILE"

  az ad user create \
    --display-name "$display_name" \
    --user-principal-name "$upn" \
    --password "$password" \
    --department "$department" \
    --force-change-password-next-sign-in true \
    2>&1 | tee -a "$LOG_FILE"

  if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "✓ Success: $upn" | tee -a "$LOG_FILE"
  else
    echo "✗ Failed: $upn" | tee -a "$LOG_FILE"
  fi

  # Rate limiting
  sleep 1
done

echo "User creation complete. Log: $LOG_FILE"
```

### Bulk Role Assignment

```bash
#!/bin/bash
# bulk-assign-roles.sh

GROUP_NAME="Engineering Team"
ROLE="Contributor"
RESOURCE_GROUPS=("app1-rg" "app2-rg" "app3-rg")

# Get group object ID
GROUP_ID=$(az ad group show --group "$GROUP_NAME" --query id -o tsv)

if [ -z "$GROUP_ID" ]; then
  echo "Error: Group '$GROUP_NAME' not found"
  exit 1
fi

# Assign role to each resource group
for rg in "${RESOURCE_GROUPS[@]}"; do
  echo "Assigning $ROLE to $GROUP_NAME in $rg..."

  az role assignment create \
    --assignee "$GROUP_ID" \
    --role "$ROLE" \
    --resource-group "$rg"

  if [ $? -eq 0 ]; then
    echo "✓ Assigned to $rg"
  else
    echo "✗ Failed for $rg"
  fi
done
```

## Error Handling

### Basic Error Checking

```bash
#!/bin/bash

# Check command success
if az vm start --name myVM --resource-group myRG; then
  echo "VM started successfully"
else
  echo "Failed to start VM"
  exit 1
fi

# Capture exit code
az vm show --name myVM --resource-group myRG
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  echo "VM exists"
elif [ $EXIT_CODE -eq 3 ]; then
  echo "VM not found"
else
  echo "Unexpected error: $EXIT_CODE"
  exit 1
fi
```

### Retry Logic

```bash
#!/bin/bash
# retry-command.sh

retry_command() {
  local max_attempts=3
  local delay=5
  local attempt=1
  local cmd="$@"

  while [ $attempt -le $max_attempts ]; do
    echo "Attempt $attempt/$max_attempts: $cmd"

    if $cmd; then
      echo "✓ Command succeeded"
      return 0
    else
      echo "✗ Command failed"
      if [ $attempt -lt $max_attempts ]; then
        echo "Retrying in ${delay}s..."
        sleep $delay
        delay=$((delay * 2))  # Exponential backoff
      fi
    fi

    attempt=$((attempt + 1))
  done

  echo "Command failed after $max_attempts attempts"
  return 1
}

# Usage
retry_command az vm start --name myVM --resource-group myRG
```

### Validation Before Execution

```bash
#!/bin/bash
# validate-before-deploy.sh

RESOURCE_GROUP="myResourceGroup"
TEMPLATE_FILE="template.bicep"

# Check if resource group exists
if ! az group exists --name "$RESOURCE_GROUP" | grep -q "true"; then
  echo "Error: Resource group '$RESOURCE_GROUP' does not exist"
  exit 1
fi

# Validate template
echo "Validating template..."
if ! az deployment group validate \
  --resource-group "$RESOURCE_GROUP" \
  --template-file "$TEMPLATE_FILE"; then
  echo "Template validation failed"
  exit 1
fi

# Check what-if
echo "Checking deployment changes..."
az deployment group what-if \
  --resource-group "$RESOURCE_GROUP" \
  --template-file "$TEMPLATE_FILE"

# Confirm with user
read -p "Proceed with deployment? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
  echo "Deployment cancelled"
  exit 0
fi

# Deploy
echo "Deploying..."
az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file "$TEMPLATE_FILE"
```

## Output Formatting

### Table Output

```bash
# Default table format
az vm list --output table

# Custom table columns
az vm list \
  --query "[].{Name:name, Location:location, Status:powerState}" \
  --output table

# Sorted table
az vm list \
  --query "sort_by([], &name) | [].{Name:name, Location:location}" \
  --output table
```

### JSON Output

```bash
# Pretty JSON
az vm show --name myVM --resource-group myRG --output json

# Compact JSON
az vm show --name myVM --resource-group myRG --output json | jq -c

# Save to file
az vm list --output json > vms.json

# Process with jq
az vm list --output json | jq '.[] | select(.location=="eastus")'
```

### TSV Output for Scripting

```bash
# Tab-separated values (easy to parse)
az vm list --query "[].{Name:name, RG:resourceGroup}" --output tsv

# Process with while loop
az vm list --query "[].name" -o tsv | while read vm_name; do
  echo "Processing: $vm_name"
  # Do something with $vm_name
done

# Direct to xargs
az vm list --query "[].id" -o tsv | xargs -I {} az vm start --ids {}
```

### YAML Output

```bash
# Human-readable YAML
az vm show --name myVM --resource-group myRG --output yaml

# Multiple resources
az vm list --output yaml > vms.yaml
```

## Scripting Best Practices

### Script Template

```bash
#!/bin/bash
set -euo pipefail  # Exit on error, undefined variables, pipe failures
IFS=$'\n\t'        # Better word splitting

# Script configuration
readonly SCRIPT_NAME=$(basename "$0")
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly LOG_FILE="${SCRIPT_DIR}/${SCRIPT_NAME%.sh}-$(date +%Y%m%d-%H%M%S).log"

# Logging function
log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Error handler
error_exit() {
  log "ERROR: $1"
  exit 1
}

# Cleanup function
cleanup() {
  log "Cleaning up..."
  # Add cleanup logic here
}
trap cleanup EXIT

# Main logic
main() {
  log "Starting $SCRIPT_NAME"

  # Your Azure operations here
  az vm list --output table >> "$LOG_FILE" 2>&1

  log "Script completed successfully"
}

main "$@"
```

### Parameter Validation

```bash
#!/bin/bash

# Required parameters
RESOURCE_GROUP="${1:-}"
VM_NAME="${2:-}"

if [ -z "$RESOURCE_GROUP" ] || [ -z "$VM_NAME" ]; then
  echo "Usage: $0 <resource-group> <vm-name>"
  exit 1
fi

# Validate resource group exists
if ! az group exists --name "$RESOURCE_GROUP" | grep -q "true"; then
  echo "Error: Resource group '$RESOURCE_GROUP' not found"
  exit 1
fi

# Validate VM exists
if ! az vm show --name "$VM_NAME" --resource-group "$RESOURCE_GROUP" >/dev/null 2>&1; then
  echo "Error: VM '$VM_NAME' not found in resource group '$RESOURCE_GROUP'"
  exit 1
fi

echo "✓ Parameters validated"
```

### Idempotent Operations

```bash
#!/bin/bash
# create-resource-group.sh - Idempotent

RESOURCE_GROUP="myResourceGroup"
LOCATION="eastus"

# Check if resource group exists
if az group exists --name "$RESOURCE_GROUP" | grep -q "true"; then
  echo "Resource group '$RESOURCE_GROUP' already exists"
else
  echo "Creating resource group '$RESOURCE_GROUP'..."
  az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
  echo "✓ Resource group created"
fi
```

## Performance Optimization

### Reduce API Calls

```bash
# Inefficient: Multiple API calls
for vm in $(az vm list --query "[].name" -o tsv); do
  az vm show --name "$vm" --resource-group myRG
done

# Efficient: Single API call with query
az vm list --resource-group myRG --query "[].{Name:name, Location:location, Status:powerState}"
```

### Use --no-wait for Long Operations

```bash
# Start multiple VMs without waiting
for vm in vm1 vm2 vm3; do
  az vm start --name "$vm" --resource-group myRG --no-wait
done

# Check status later
az vm list --resource-group myRG --query "[].{Name:name, Status:powerState}"
```

### Cache Reusable Data

```bash
#!/bin/bash

# Cache subscription ID (avoid repeated API calls)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

# Cache resource group list
RESOURCE_GROUPS=$(az group list --query "[].name" -o tsv)

# Use cached data
echo "Operating on subscription: $SUBSCRIPTION_ID"
for rg in $RESOURCE_GROUPS; do
  echo "Processing: $rg"
  # Operations using $rg
done
```

### Parallel Execution with Background Jobs

```bash
#!/bin/bash

# Start multiple operations in background
for vm in vm1 vm2 vm3; do
  (
    az vm start --name "$vm" --resource-group myRG
    echo "✓ Started: $vm"
  ) &
done

# Wait for all background jobs to complete
wait

echo "All VMs started"
```

## Related Documentation

- @user-management.md - CLI patterns for identity operations
- @resource-management.md - CLI patterns for resource operations
- @role-assignments.md - CLI patterns for RBAC operations
- @mcp-integration.md - When to use MCP vs CLI
- @troubleshooting.md - Debugging CLI issues
