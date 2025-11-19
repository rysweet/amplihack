# Azure Admin Tools

Scripts for managing Azure AD accounts and role assignments.

## Tools

### 1. create-azure-users.sh

Creates Azure AD user accounts with temporary passwords.

**Usage:**
```bash
./create-azure-users.sh
```

**Features:**
- Creates users with temporary passwords
- Forces password change on first login
- Configurable domain suffix
- Success/failure logging

**Edit the script to configure:**
- `DOMAIN` - Azure AD domain (default: DefenderATEVET12.onmicrosoft.com)
- `TEMP_PASSWORD` - Initial password for new users
- `ACCOUNTS` - Array of usernames to create

### 2. azure-assign-roles.sh

Assigns Azure roles to multiple accounts at subscription and tenant root scopes.

**Usage:**
```bash
# Dry-run mode (no changes)
DRY_RUN=1 ./azure-assign-roles.sh

# Execute assignments
./azure-assign-roles.sh

# Skip confirmation prompts
SKIP_CONFIRMATION=1 ./azure-assign-roles.sh
```

**Features:**
- Bulk role assignment automation
- Idempotent (safe to re-run)
- Dry-run mode for testing
- Comprehensive error handling
- Audit logging to /tmp/azure-role-assignments-*.log
- Account validation before assignment

**Configuration:**
Edit the script constants section to configure:
- `TENANT_ID` - Azure tenant ID
- `SUBSCRIPTION_ID` - Azure subscription ID
- `UPN_DOMAIN` - Domain suffix for user accounts
- `ROLES` - Array of roles to assign
- `SCOPES` - Array of scopes for assignments
- `ACCOUNTS_FILE` - Path to file containing usernames (one per line)

## Example Workflow

1. **Create accounts file:**
```bash
cat > /tmp/acct << EOF
user1
user2
user3
EOF
```

2. **Create Azure AD users (if they don't exist):**
```bash
./create-azure-users.sh
```

3. **Test role assignments (dry-run):**
```bash
DRY_RUN=1 ./azure-assign-roles.sh
```

4. **Execute role assignments:**
```bash
./azure-assign-roles.sh
```

5. **Verify assignments:**
```bash
az role assignment list --assignee user1@domain.com -o table
```

## Requirements

- Azure CLI installed and authenticated
- Appropriate permissions:
  - User Administrator role (for creating users)
  - User Access Administrator role at tenant root (for role assignments)
- Account list file at configured path

## Security Notes

- **Temporary passwords** should be changed immediately on first login
- **Role assignments** grant extensive privileges - use carefully
- **Audit logs** are created in /tmp/ - review after execution
- **Tenant root scope** provides access across all subscriptions

## Troubleshooting

**Account not found:**
- Ensure account exists in Azure AD
- Check UPN format matches domain configuration

**Permission denied:**
- Verify authenticated user has sufficient privileges
- For tenant root assignments, User Access Administrator at / scope required

**Role already exists:**
- Script is idempotent - re-running will skip existing assignments
- Check logs for "SKIPPED" messages

## Log Files

Role assignment operations are logged to:
```
/tmp/azure-role-assignments-YYYYMMDD-HHMMSS.log
```

Log includes:
- All operations attempted
- Success/failure status for each assignment
- Account validation results
- Execution summary
