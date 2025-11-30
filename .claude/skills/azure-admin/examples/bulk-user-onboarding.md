# Bulk User Onboarding Workflow

Complete automated workflow for onboarding multiple users to Azure with proper access controls, group assignments, and notifications.

## Scenario

Onboard 15 new engineers to the Azure environment with:
- Entra ID user accounts
- Security group membership (Engineering Team)
- RBAC role assignments (Contributor on dev resource groups, Reader on prod)
- MFA enforcement
- Welcome email with credentials
- Compliance and audit trail

## Prerequisites

- Global Administrator or User Administrator role in Entra ID
- Owner or User Access Administrator role on target subscriptions/resource groups
- Azure CLI installed and authenticated
- CSV file with user data
- Email configuration (optional, for notifications)

## Step 1: Prepare User Data

Create `users.csv`:
```csv
DisplayName,UserPrincipalName,Password,GivenName,Surname,Department,JobTitle,ManagerEmail
Jane Doe,jane.doe@contoso.com,TempPass123!,Jane,Doe,Engineering,Senior Software Engineer,john.smith@contoso.com
John Smith,john.smith@contoso.com,TempPass456!,John,Smith,Engineering,Engineering Manager,alice.johnson@contoso.com
Alice Johnson,alice.johnson@contoso.com,TempPass789!,Alice,Johnson,Engineering,Staff Engineer,john.smith@contoso.com
Bob Williams,bob.williams@contoso.com,TempPass012!,Bob,Williams,Engineering,DevOps Engineer,jane.doe@contoso.com
Carol Brown,carol.brown@contoso.com,TempPass345!,Carol,Brown,Engineering,Cloud Architect,alice.johnson@contoso.com
```

## Step 2: Create Security Groups

```bash
#!/bin/bash
# create-security-groups.sh

# Engineering Team group
az ad group create \
  --display-name "Engineering Team" \
  --mail-nickname "engineering" \
  --description "All engineering team members"

# Platform Engineering subgroup
az ad group create \
  --display-name "Platform Engineering" \
  --mail-nickname "platform-eng" \
  --description "Platform engineering team members"

# Store group IDs
ENG_GROUP_ID=$(az ad group show --group "Engineering Team" --query id -o tsv)
PLATFORM_GROUP_ID=$(az ad group show --group "Platform Engineering" --query id -o tsv)

echo "Engineering Team ID: $ENG_GROUP_ID"
echo "Platform Engineering ID: $PLATFORM_GROUP_ID"
```

## Step 3: Bulk Create Users

```bash
#!/bin/bash
# bulk-create-users.sh

set -euo pipefail

CSV_FILE="users.csv"
LOG_FILE="user-creation-$(date +%Y%m%d-%H%M%S).log"
SUMMARY_FILE="user-summary-$(date +%Y%m%d-%H%M%S).txt"

# Counters
CREATED_COUNT=0
FAILED_COUNT=0
TOTAL_COUNT=0

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "Starting bulk user creation"
log "CSV file: $CSV_FILE"

# Create summary header
cat > "$SUMMARY_FILE" <<EOF
Azure User Onboarding Summary
Generated: $(date)
========================================

EOF

# Process CSV (skip header)
tail -n +2 "$CSV_FILE" | while IFS=, read -r display_name upn password given_name surname department job_title manager_email; do
  TOTAL_COUNT=$((TOTAL_COUNT + 1))
  log "Processing: $display_name ($upn)"

  # Check if user already exists
  if az ad user show --id "$upn" &>/dev/null; then
    log "⚠️  User already exists: $upn"
    echo "SKIPPED: $upn (already exists)" >> "$SUMMARY_FILE"
    continue
  fi

  # Create user
  USER_CREATE_OUTPUT=$(az ad user create \
    --display-name "$display_name" \
    --user-principal-name "$upn" \
    --password "$password" \
    --given-name "$given_name" \
    --surname "$surname" \
    --department "$department" \
    --job-title "$job_title" \
    --force-change-password-next-sign-in true \
    2>&1)

  if [ $? -eq 0 ]; then
    log "✓ Successfully created: $upn"
    echo "CREATED: $upn" >> "$SUMMARY_FILE"
    CREATED_COUNT=$((CREATED_COUNT + 1))

    # Get user object ID
    USER_ID=$(az ad user show --id "$upn" --query id -o tsv)

    # Add to Engineering Team group
    ENG_GROUP_ID=$(az ad group show --group "Engineering Team" --query id -o tsv)
    az ad group member add --group "$ENG_GROUP_ID" --member-id "$USER_ID" 2>&1 | tee -a "$LOG_FILE"
    log "✓ Added $upn to Engineering Team"

    # Set manager (if specified)
    if [ -n "$manager_email" ]; then
      MANAGER_ID=$(az ad user show --id "$manager_email" --query id -o tsv 2>/dev/null || echo "")
      if [ -n "$MANAGER_ID" ]; then
        # Note: Setting manager requires Microsoft Graph API
        az rest --method PUT \
          --url "https://graph.microsoft.com/v1.0/users/$USER_ID/manager/\$ref" \
          --body "{\"@odata.id\": \"https://graph.microsoft.com/v1.0/users/$MANAGER_ID\"}" \
          2>&1 | tee -a "$LOG_FILE"
        log "✓ Set manager for $upn: $manager_email"
      fi
    fi

    # Rate limiting
    sleep 2
  else
    log "✗ Failed to create: $upn"
    log "Error: $USER_CREATE_OUTPUT"
    echo "FAILED: $upn - $USER_CREATE_OUTPUT" >> "$SUMMARY_FILE"
    FAILED_COUNT=$((FAILED_COUNT + 1))
  fi
done

# Write summary
cat >> "$SUMMARY_FILE" <<EOF

Summary:
--------
Total processed: $TOTAL_COUNT
Successfully created: $CREATED_COUNT
Failed: $FAILED_COUNT

Logs: $LOG_FILE
EOF

log "Bulk user creation complete"
log "Created: $CREATED_COUNT, Failed: $FAILED_COUNT"
log "Summary: $SUMMARY_FILE"

cat "$SUMMARY_FILE"
```

## Step 4: Assign RBAC Roles

```bash
#!/bin/bash
# assign-rbac-roles.sh

set -euo pipefail

ENG_GROUP_ID=$(az ad group show --group "Engineering Team" --query id -o tsv)

# Development resource groups - Contributor access
DEV_RESOURCE_GROUPS=("app1-dev-rg" "app2-dev-rg" "platform-dev-rg")

for rg in "${DEV_RESOURCE_GROUPS[@]}"; do
  echo "Assigning Contributor role to Engineering Team on $rg..."

  if az group exists --name "$rg" | grep -q "false"; then
    echo "⚠️  Resource group $rg does not exist, skipping"
    continue
  fi

  az role assignment create \
    --assignee "$ENG_GROUP_ID" \
    --role Contributor \
    --resource-group "$rg"

  if [ $? -eq 0 ]; then
    echo "✓ Assigned Contributor to $rg"
  else
    echo "✗ Failed to assign Contributor to $rg"
  fi
done

# Production resource groups - Reader access
PROD_RESOURCE_GROUPS=("app1-prod-rg" "app2-prod-rg" "platform-prod-rg")

for rg in "${PROD_RESOURCE_GROUPS[@]}"; do
  echo "Assigning Reader role to Engineering Team on $rg..."

  if az group exists --name "$rg" | grep -q "false"; then
    echo "⚠️  Resource group $rg does not exist, skipping"
    continue
  fi

  az role assignment create \
    --assignee "$ENG_GROUP_ID" \
    --role Reader \
    --resource-group "$rg"

  if [ $? -eq 0 ]; then
    echo "✓ Assigned Reader to $rg"
  else
    echo "✗ Failed to assign Reader to $rg"
  fi
done

echo ""
echo "RBAC role assignments complete"
echo ""
echo "Summary:"
az role assignment list --assignee "$ENG_GROUP_ID" --all --output table
```

## Step 5: Enable MFA (via Conditional Access)

MFA enforcement requires Azure AD Premium P1 or P2 and must be configured through Azure Portal or Microsoft Graph API.

**Manual Steps:**
1. Navigate to Azure Portal > Entra ID > Security > Conditional Access
2. Create new policy: "Require MFA for Engineering Team"
3. Assignments:
   - Users: Include "Engineering Team" group
   - Cloud apps: All cloud apps
4. Access controls:
   - Grant: Require multi-factor authentication
5. Enable policy

**Automated via Microsoft Graph API:**
```bash
# Requires Microsoft Graph permissions
# This is a simplified example - full implementation requires complex JSON policy definition

POLICY_NAME="Require MFA for Engineering Team"
ENG_GROUP_ID=$(az ad group show --group "Engineering Team" --query id -o tsv)

# Create conditional access policy (requires admin consent for permissions)
az rest --method POST \
  --url "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" \
  --body "{
    \"displayName\": \"$POLICY_NAME\",
    \"state\": \"enabled\",
    \"conditions\": {
      \"users\": {
        \"includeGroups\": [\"$ENG_GROUP_ID\"]
      },
      \"applications\": {
        \"includeApplications\": [\"All\"]
      }
    },
    \"grantControls\": {
      \"operator\": \"OR\",
      \"builtInControls\": [\"mfa\"]
    }
  }"
```

## Step 6: Generate Welcome Emails

```bash
#!/bin/bash
# generate-welcome-emails.sh

CSV_FILE="users.csv"
EMAIL_TEMPLATE="welcome-email-template.html"
OUTPUT_DIR="welcome-emails"

mkdir -p "$OUTPUT_DIR"

tail -n +2 "$CSV_FILE" | while IFS=, read -r display_name upn password given_name surname department job_title manager_email; do
  EMAIL_FILE="$OUTPUT_DIR/$(echo $upn | tr '@.' '__').html"

  cat > "$EMAIL_FILE" <<EOF
<!DOCTYPE html>
<html>
<head>
  <title>Welcome to Contoso Azure Environment</title>
</head>
<body>
  <h1>Welcome, $given_name!</h1>

  <p>Your Azure account has been created. Please use the following credentials for your first login:</p>

  <ul>
    <li><strong>Username:</strong> $upn</li>
    <li><strong>Temporary Password:</strong> $password</li>
  </ul>

  <p><strong>IMPORTANT:</strong> You will be required to change your password on first login.</p>

  <h2>Next Steps</h2>
  <ol>
    <li>Login to Azure Portal: <a href="https://portal.azure.com">https://portal.azure.com</a></li>
    <li>Change your temporary password</li>
    <li>Setup Multi-Factor Authentication (MFA)</li>
    <li>Review your assigned resource groups and permissions</li>
  </ol>

  <h2>Your Access</h2>
  <ul>
    <li><strong>Department:</strong> $department</li>
    <li><strong>Job Title:</strong> $job_title</li>
    <li><strong>Manager:</strong> $manager_email</li>
    <li><strong>Security Group:</strong> Engineering Team</li>
    <li><strong>Access Level:</strong> Contributor (dev), Reader (prod)</li>
  </ul>

  <p>If you have questions, contact IT support at itsupport@contoso.com</p>

  <p>Welcome to the team!</p>
</body>
</html>
EOF

  echo "Generated: $EMAIL_FILE"
done

echo ""
echo "Welcome emails generated in: $OUTPUT_DIR"
```

## Step 7: Audit and Verification

```bash
#!/bin/bash
# verify-onboarding.sh

CSV_FILE="users.csv"
VERIFICATION_REPORT="verification-report-$(date +%Y%m%d).txt"

cat > "$VERIFICATION_REPORT" <<EOF
User Onboarding Verification Report
Generated: $(date)
========================================

EOF

tail -n +2 "$CSV_FILE" | while IFS=, read -r display_name upn password rest; do
  echo "Verifying: $upn"

  # Check user exists
  if az ad user show --id "$upn" &>/dev/null; then
    echo "✓ User exists: $upn" | tee -a "$VERIFICATION_REPORT"

    # Get user details
    USER_INFO=$(az ad user show --id "$upn" --query "{DisplayName:displayName, Department:department, JobTitle:jobTitle}" -o json)
    echo "  $USER_INFO" | tee -a "$VERIFICATION_REPORT"

    # Check group membership
    USER_ID=$(az ad user show --id "$upn" --query id -o tsv)
    GROUPS=$(az ad user get-member-groups --id "$USER_ID" --query "[]" -o json)
    echo "  Groups: $GROUPS" | tee -a "$VERIFICATION_REPORT"

    # Check role assignments
    ROLES=$(az role assignment list --assignee "$USER_ID" --all --query "[].{Role:roleDefinitionName, Scope:scope}" -o json)
    echo "  Role Assignments: $ROLES" | tee -a "$VERIFICATION_REPORT"
  else
    echo "✗ User NOT found: $upn" | tee -a "$VERIFICATION_REPORT"
  fi

  echo "" | tee -a "$VERIFICATION_REPORT"
done

echo "Verification complete. Report: $VERIFICATION_REPORT"
cat "$VERIFICATION_REPORT"
```

## Complete Workflow Script

```bash
#!/bin/bash
# complete-onboarding-workflow.sh

set -euo pipefail

echo "======================================"
echo "Azure Bulk User Onboarding Workflow"
echo "======================================"
echo ""

# Step 1: Create security groups
echo "Step 1: Creating security groups..."
./create-security-groups.sh

# Step 2: Create users
echo ""
echo "Step 2: Creating users from CSV..."
./bulk-create-users.sh

# Step 3: Assign RBAC roles
echo ""
echo "Step 3: Assigning RBAC roles..."
./assign-rbac-roles.sh

# Step 4: MFA (manual or via API)
echo ""
echo "Step 4: MFA enforcement"
echo "⚠️  Manual step required: Configure Conditional Access policy in Azure Portal"
read -p "Press Enter after MFA policy is configured..."

# Step 5: Generate welcome emails
echo ""
echo "Step 5: Generating welcome emails..."
./generate-welcome-emails.sh

# Step 6: Verification
echo ""
echo "Step 6: Verifying onboarding..."
./verify-onboarding.sh

echo ""
echo "======================================"
echo "Onboarding workflow complete!"
echo "======================================"
```

## Rollback Script (If Needed)

```bash
#!/bin/bash
# rollback-onboarding.sh

CSV_FILE="users.csv"

echo "⚠️  WARNING: This will delete all users listed in $CSV_FILE"
read -p "Are you sure? Type 'DELETE' to confirm: " confirm

if [ "$confirm" != "DELETE" ]; then
  echo "Rollback cancelled"
  exit 0
fi

tail -n +2 "$CSV_FILE" | while IFS=, read -r display_name upn rest; do
  echo "Deleting user: $upn"

  if az ad user show --id "$upn" &>/dev/null; then
    az ad user delete --id "$upn"
    echo "✓ Deleted: $upn"
  else
    echo "⚠️  User not found: $upn"
  fi
done

echo "Rollback complete"
```

## Best Practices

1. **Test First**: Run on non-production tenant or with 1-2 test users
2. **Validate CSV**: Check for duplicates, invalid emails, etc.
3. **Backup Data**: Export existing users before bulk operations
4. **Rate Limiting**: Include delays between API calls (already in scripts)
5. **Error Handling**: Review logs for any failures
6. **Audit Trail**: Keep all logs and reports for compliance
7. **Secure Credentials**: Store temporary passwords securely, send via secure channels
8. **MFA Enforcement**: Enable before users access production
9. **Documentation**: Provide clear onboarding documentation to new users
10. **Regular Reviews**: Quarterly access reviews for all users

## Related Documentation

- @docs/user-management.md - User creation and management
- @docs/role-assignments.md - RBAC best practices
- @docs/cli-patterns.md - Batch operations and scripting
- @docs/troubleshooting.md - Common issues and solutions
