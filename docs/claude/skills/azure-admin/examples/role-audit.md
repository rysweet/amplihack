# RBAC Compliance Audit Workflow

Comprehensive audit of Azure RBAC role assignments for compliance, security, and access reviews.

## Scenario

Perform quarterly access review to:
- List all Owner and Contributor role assignments
- Identify direct user assignments (should use groups)
- Find stale assignments (users without recent sign-ins)
- Detect overprivileged access
- Generate compliance report for management

## Complete Audit Script

```bash
#!/bin/bash
# rbac-compliance-audit.sh

set -euo pipefail

REPORT_FILE="rbac-audit-$(date +%Y%m%d).html"
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)

# HTML Report Header
cat > "$REPORT_FILE" <<EOF
<!DOCTYPE html>
<html>
<head>
  <title>RBAC Compliance Audit</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 20px; }
    h1 { color: #0078d4; }
    h2 { color: #106ebe; border-bottom: 2px solid #0078d4; padding-bottom: 5px; }
    table { border-collapse: collapse; width: 100%; margin: 20px 0; }
    th { background-color: #0078d4; color: white; padding: 10px; text-align: left; }
    td { border: 1px solid #ddd; padding: 8px; }
    tr:nth-child(even) { background-color: #f2f2f2; }
    .warning { background-color: #fff4ce; }
    .critical { background-color: #fde7e9; }
    .good { background-color: #dff6dd; }
    .summary { background-color: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0; }
  </style>
</head>
<body>
  <h1>RBAC Compliance Audit Report</h1>
  <p><strong>Subscription:</strong> $SUBSCRIPTION_NAME</p>
  <p><strong>Subscription ID:</strong> $SUBSCRIPTION_ID</p>
  <p><strong>Date Generated:</strong> $(date)</p>
  <hr>
EOF

# Function to add section to report
add_section() {
  echo "<h2>$1</h2>" >> "$REPORT_FILE"
}

add_table_start() {
  echo "<table><tr>$1</tr>" >> "$REPORT_FILE"
}

add_table_row() {
  echo "<tr class='$2'>$1</tr>" >> "$REPORT_FILE"
}

add_table_end() {
  echo "</table>" >> "$REPORT_FILE"
}

echo "Starting RBAC compliance audit..."

# 1. High-Privilege Role Assignments
echo "Auditing high-privilege roles..."
add_section "1. High-Privilege Role Assignments (Owner, Contributor)"

OWNER_ASSIGNMENTS=$(az role assignment list --role Owner --all --query "[]" -o json)
CONTRIBUTOR_ASSIGNMENTS=$(az role assignment list --role Contributor --all --query "[]" -o json)

OWNER_COUNT=$(echo "$OWNER_ASSIGNMENTS" | jq 'length')
CONTRIBUTOR_COUNT=$(echo "$CONTRIBUTOR_ASSIGNMENTS" | jq 'length')

echo "<p>Found <strong>$OWNER_COUNT</strong> Owner assignments and <strong>$CONTRIBUTOR_COUNT</strong> Contributor assignments.</p>" >> "$REPORT_FILE"

add_table_start "<th>Principal</th><th>Type</th><th>Role</th><th>Scope</th>"

echo "$OWNER_ASSIGNMENTS" | jq -r '.[] | "\(.principalName)|\(.principalType)|\(.roleDefinitionName)|\(.scope)"' | \
while IFS='|' read -r principal type role scope; do
  CSS_CLASS="critical"
  add_table_row "<td>$principal</td><td>$type</td><td>$role</td><td>$scope</td>" "$CSS_CLASS"
done

echo "$CONTRIBUTOR_ASSIGNMENTS" | jq -r '.[] | "\(.principalName)|\(.principalType)|\(.roleDefinitionName)|\(.scope)"' | \
while IFS='|' read -r principal type role scope; do
  CSS_CLASS="warning"
  add_table_row "<td>$principal</td><td>$type</td><td>$role</td><td>$scope</td>" "$CSS_CLASS"
done

add_table_end

# 2. Direct User Assignments (Anti-Pattern)
echo "Checking for direct user assignments..."
add_section "2. Direct User Assignments (Should Use Groups)"

DIRECT_USER_ASSIGNMENTS=$(az role assignment list --all --query "[?principalType=='User']" -o json)
DIRECT_USER_COUNT=$(echo "$DIRECT_USER_ASSIGNMENTS" | jq 'length')

if [ "$DIRECT_USER_COUNT" -gt 0 ]; then
  echo "<p class='warning'>⚠️ Found <strong>$DIRECT_USER_COUNT</strong> direct user assignments (recommended: use groups instead)</p>" >> "$REPORT_FILE"

  add_table_start "<th>User</th><th>Role</th><th>Scope</th>"

  echo "$DIRECT_USER_ASSIGNMENTS" | jq -r '.[] | "\(.principalName)|\(.roleDefinitionName)|\(.scope)"' | \
  while IFS='|' read -r user role scope; do
    add_table_row "<td>$user</td><td>$role</td><td>$scope</td>" "warning"
  done

  add_table_end
else
  echo "<p class='good'>✓ No direct user assignments found. All access is via groups.</p>" >> "$REPORT_FILE"
fi

# 3. Subscription-Wide Access
echo "Checking subscription-wide access..."
add_section "3. Subscription-Wide Access"

SUB_WIDE_ASSIGNMENTS=$(az role assignment list \
  --all \
  --query "[?contains(scope, '/subscriptions/$SUBSCRIPTION_ID') && !contains(scope, '/resourceGroups/')]" \
  -o json)

SUB_WIDE_COUNT=$(echo "$SUB_WIDE_ASSIGNMENTS" | jq 'length')

echo "<p>Found <strong>$SUB_WIDE_COUNT</strong> subscription-wide role assignments.</p>" >> "$REPORT_FILE"

add_table_start "<th>Principal</th><th>Type</th><th>Role</th>"

echo "$SUB_WIDE_ASSIGNMENTS" | jq -r '.[] | "\(.principalName)|\(.principalType)|\(.roleDefinitionName)"' | \
while IFS='|' read -r principal type role; do
  CSS_CLASS="warning"
  if [ "$role" == "Owner" ]; then
    CSS_CLASS="critical"
  fi
  add_table_row "<td>$principal</td><td>$type</td><td>$role</td>" "$CSS_CLASS"
done

add_table_end

# 4. Service Principal Review
echo "Reviewing service principals..."
add_section "4. Service Principal Access"

SP_ASSIGNMENTS=$(az role assignment list --all --query "[?principalType=='ServicePrincipal']" -o json)
SP_COUNT=$(echo "$SP_ASSIGNMENTS" | jq 'length')

echo "<p>Found <strong>$SP_COUNT</strong> service principal role assignments.</p>" >> "$REPORT_FILE"

add_table_start "<th>Service Principal</th><th>Role</th><th>Scope</th>"

echo "$SP_ASSIGNMENTS" | jq -r '.[] | "\(.principalName)|\(.roleDefinitionName)|\(.scope)"' | \
while IFS='|' read -r sp role scope; do
  add_table_row "<td>$sp</td><td>$role</td><td>$scope</td>" ""
done

add_table_end

# 5. Custom Role Assignments
echo "Reviewing custom roles..."
add_section "5. Custom Role Assignments"

CUSTOM_ROLE_ASSIGNMENTS=$(az role assignment list --all --query "[?roleDefinitionName != 'Owner' && roleDefinitionName != 'Contributor' && roleDefinitionName != 'Reader']" -o json | jq '[.[] | select(.roleDefinitionName | startswith("Custom") or contains("custom"))]')
CUSTOM_COUNT=$(echo "$CUSTOM_ROLE_ASSIGNMENTS" | jq 'length')

if [ "$CUSTOM_COUNT" -gt 0 ]; then
  echo "<p>Found <strong>$CUSTOM_COUNT</strong> custom role assignments.</p>" >> "$REPORT_FILE"

  add_table_start "<th>Principal</th><th>Custom Role</th><th>Scope</th>"

  echo "$CUSTOM_ROLE_ASSIGNMENTS" | jq -r '.[] | "\(.principalName)|\(.roleDefinitionName)|\(.scope)"' | \
  while IFS='|' read -r principal role scope; do
    add_table_row "<td>$principal</td><td>$role</td><td>$scope</td>" ""
  done

  add_table_end
else
  echo "<p>No custom role assignments found.</p>" >> "$REPORT_FILE"
fi

# Summary
add_section "Summary and Recommendations"

cat >> "$REPORT_FILE" <<EOF
<div class="summary">
  <h3>Summary Statistics</h3>
  <ul>
    <li>Total Owner assignments: $OWNER_COUNT</li>
    <li>Total Contributor assignments: $CONTRIBUTOR_COUNT</li>
    <li>Direct user assignments: $DIRECT_USER_COUNT</li>
    <li>Subscription-wide assignments: $SUB_WIDE_COUNT</li>
    <li>Service principal assignments: $SP_COUNT</li>
    <li>Custom role assignments: $CUSTOM_COUNT</li>
  </ul>

  <h3>Recommendations</h3>
  <ul>
EOF

if [ "$DIRECT_USER_COUNT" -gt 0 ]; then
  echo "    <li>⚠️ Convert direct user assignments to group-based access</li>" >> "$REPORT_FILE"
fi

if [ "$OWNER_COUNT" -gt 5 ]; then
  echo "    <li>⚠️ Review Owner role assignments (currently $OWNER_COUNT, recommended < 5)</li>" >> "$REPORT_FILE"
fi

if [ "$SUB_WIDE_COUNT" -gt 10 ]; then
  echo "    <li>⚠️ Reduce subscription-wide access (prefer resource group level)</li>" >> "$REPORT_FILE"
fi

cat >> "$REPORT_FILE" <<EOF
    <li>✓ Conduct quarterly access reviews</li>
    <li>✓ Remove assignments for users who have left the organization</li>
    <li>✓ Validate service principal access is still required</li>
    <li>✓ Ensure all assignments have business justification</li>
  </ul>
</div>
EOF

# Close HTML
cat >> "$REPORT_FILE" <<EOF
  <hr>
  <p><em>Generated by rbac-compliance-audit.sh</em></p>
</body>
</html>
EOF

echo ""
echo "✓ RBAC compliance audit complete"
echo "Report saved to: $REPORT_FILE"
echo ""
echo "Summary:"
echo "- Owner assignments: $OWNER_COUNT"
echo "- Contributor assignments: $CONTRIBUTOR_COUNT"
echo "- Direct user assignments: $DIRECT_USER_COUNT"
echo "- Subscription-wide assignments: $SUB_WIDE_COUNT"
```

## Automated Remediation

```bash
#!/bin/bash
# remediate-direct-users.sh

# Convert direct user assignments to group-based

GROUP_NAME="Engineering Team"
GROUP_ID=$(az ad group show --group "$GROUP_NAME" --query id -o tsv)

# Get all direct user assignments
az role assignment list --all --query "[?principalType=='User']" -o json | \
jq -r '.[] | "\(.principalId)|\(.roleDefinitionName)|\(.scope)"' | \
while IFS='|' read -r user_id role scope; do
  echo "Found direct assignment: User $user_id, Role $role, Scope $scope"

  # Add user to group (if not already)
  az ad group member add --group "$GROUP_ID" --member-id "$user_id" 2>/dev/null || echo "User already in group"

  # Assign role to group if not already assigned
  az role assignment create \
    --assignee "$GROUP_ID" \
    --role "$role" \
    --scope "$scope" 2>/dev/null || echo "Group already has this role"

  # Remove direct user assignment
  read -p "Remove direct assignment for user $user_id? (y/n): " confirm
  if [ "$confirm" == "y" ]; then
    az role assignment delete --assignee "$user_id" --role "$role" --scope "$scope"
    echo "✓ Removed direct assignment"
  fi
done
```

## Related Documentation

- @docs/role-assignments.md - RBAC patterns
- @docs/user-management.md - User and group management
- @docs/cli-patterns.md - Reporting scripts
- @docs/troubleshooting.md - RBAC issues
