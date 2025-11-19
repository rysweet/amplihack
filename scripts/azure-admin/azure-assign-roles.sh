#!/usr/bin/env bash
#
# Azure Role Assignment Automation Script
#
# Purpose: Assign Owner and User Access Administrator roles to specified accounts
#          at both Subscription and Tenant Root scopes
#
# Usage:
#   ./azure-assign-roles.sh                    # Normal execution
#   DRY_RUN=1 ./azure-assign-roles.sh          # Dry-run mode (no changes)
#   SKIP_CONFIRMATION=1 ./azure-assign-roles.sh # Skip confirmation prompts
#
# Requirements:
#   - Azure CLI (az) installed and authenticated
#   - Account file at /tmp/acct with one username per line
#   - Permissions to assign roles at subscription and tenant root
#
# Exit Codes:
#   0 - All operations successful
#   1 - One or more operations failed
#

set -euo pipefail

# ============================================================================
# CONSTANTS
# ============================================================================

TENANT_ID="c7674d41-af6c-46f5-89a5-d41495d2151e"
SUBSCRIPTION_ID="c190c55a-9ab2-4b1e-92c4-cc8b1a032285"
UPN_DOMAIN="DefenderATEVET12.onmicrosoft.com"
ROLES=("Owner" "User Access Administrator")
SCOPES=(
  "/subscriptions/${SUBSCRIPTION_ID}"
  "/"
)
ACCOUNTS_FILE="/tmp/acct"

# Logging
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOG_FILE="/tmp/azure-role-assignments-${TIMESTAMP}.log"

# Statistics
TOTAL_OPERATIONS=0
SUCCESSFUL_OPERATIONS=0
SKIPPED_OPERATIONS=0
FAILED_OPERATIONS=0

# Flags
DRY_RUN="${DRY_RUN:-0}"
SKIP_CONFIRMATION="${SKIP_CONFIRMATION:-0}"

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_success() {
    log "SUCCESS" "$@"
}

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

check_az_cli() {
    log_info "Checking Azure CLI installation..."
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI (az) is not installed"
        log_error "Install from: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
        return 1
    fi

    local az_version
    az_version=$(az version --query '"azure-cli"' -o tsv 2>/dev/null || echo "unknown")
    log_info "Azure CLI version: ${az_version}"
    return 0
}

check_authentication() {
    log_info "Checking Azure CLI authentication..."

    if ! az account show &> /dev/null; then
        log_error "Not authenticated with Azure CLI"
        log_error "Run: az login --tenant ${TENANT_ID}"
        return 1
    fi

    local current_user
    current_user=$(az account show --query user.name -o tsv)
    local current_tenant
    current_tenant=$(az account show --query tenantId -o tsv)
    local current_subscription
    current_subscription=$(az account show --query id -o tsv)

    log_info "Authenticated as: ${current_user}"
    log_info "Current tenant: ${current_tenant}"
    log_info "Current subscription: ${current_subscription}"

    if [[ "${current_tenant}" != "${TENANT_ID}" ]]; then
        log_warn "Current tenant (${current_tenant}) does not match target tenant (${TENANT_ID})"
        log_warn "Consider running: az login --tenant ${TENANT_ID}"
    fi

    if [[ "${current_subscription}" != "${SUBSCRIPTION_ID}" ]]; then
        log_warn "Current subscription (${current_subscription}) does not match target (${SUBSCRIPTION_ID})"
        log_info "Setting subscription to ${SUBSCRIPTION_ID}..."
        az account set --subscription "${SUBSCRIPTION_ID}"
    fi

    return 0
}

validate_accounts_file() {
    log_info "Validating accounts file: ${ACCOUNTS_FILE}"

    if [[ ! -f "${ACCOUNTS_FILE}" ]]; then
        log_error "Accounts file not found: ${ACCOUNTS_FILE}"
        return 1
    fi

    if [[ ! -r "${ACCOUNTS_FILE}" ]]; then
        log_error "Accounts file not readable: ${ACCOUNTS_FILE}"
        return 1
    fi

    local line_count
    line_count=$(grep -c . "${ACCOUNTS_FILE}" || echo 0)
    log_info "Found ${line_count} accounts in file"

    if [[ "${line_count}" -eq 0 ]]; then
        log_error "Accounts file is empty"
        return 1
    fi

    return 0
}

validate_azure_ad_account() {
    local username="$1"
    local upn="${username}@${UPN_DOMAIN}"

    log_info "Validating Azure AD account: ${upn}"

    if az ad user show --id "${upn}" &> /dev/null; then
        log_success "Account exists: ${upn}"
        return 0
    else
        log_error "Account not found in Azure AD: ${upn}"
        return 1
    fi
}

# ============================================================================
# ROLE ASSIGNMENT FUNCTIONS
# ============================================================================

check_role_assignment_exists() {
    local upn="$1"
    local role="$2"
    local scope="$3"

    # Query for existing role assignment
    local assignment
    assignment=$(az role assignment list \
        --assignee "${upn}" \
        --role "${role}" \
        --scope "${scope}" \
        --query '[0].id' \
        -o tsv 2>/dev/null || echo "")

    if [[ -n "${assignment}" ]]; then
        return 0  # Assignment exists
    else
        return 1  # Assignment does not exist
    fi
}

assign_role() {
    local upn="$1"
    local role="$2"
    local scope="$3"

    TOTAL_OPERATIONS=$((TOTAL_OPERATIONS + 1))

    local scope_name
    if [[ "${scope}" == "/" ]]; then
        scope_name="Tenant Root"
    else
        scope_name="Subscription"
    fi

    log_info "Assigning role '${role}' to '${upn}' at scope '${scope_name}' (${scope})"

    # Check if assignment already exists (idempotency)
    if check_role_assignment_exists "${upn}" "${role}" "${scope}"; then
        log_info "Role assignment already exists, skipping"
        SKIPPED_OPERATIONS=$((SKIPPED_OPERATIONS + 1))
        return 0
    fi

    # Dry-run mode
    if [[ "${DRY_RUN}" == "1" ]]; then
        log_info "[DRY-RUN] Would assign role '${role}' to '${upn}' at scope '${scope}'"
        SKIPPED_OPERATIONS=$((SKIPPED_OPERATIONS + 1))
        return 0
    fi

    # Perform role assignment
    if az role assignment create \
        --assignee "${upn}" \
        --role "${role}" \
        --scope "${scope}" \
        >> "${LOG_FILE}" 2>&1; then
        log_success "Successfully assigned role '${role}' to '${upn}' at scope '${scope_name}'"
        SUCCESSFUL_OPERATIONS=$((SUCCESSFUL_OPERATIONS + 1))
        return 0
    else
        log_error "Failed to assign role '${role}' to '${upn}' at scope '${scope_name}'"
        FAILED_OPERATIONS=$((FAILED_OPERATIONS + 1))
        return 1
    fi
}

# ============================================================================
# MAIN EXECUTION FUNCTIONS
# ============================================================================

display_summary() {
    local accounts=()

    # Read accounts from file
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "${line}" ]] && continue
        [[ "${line}" =~ ^[[:space:]]*# ]] && continue

        # Trim whitespace
        line=$(echo "${line}" | xargs)
        [[ -z "${line}" ]] && continue

        accounts+=("${line}")
    done < "${ACCOUNTS_FILE}"

    local num_accounts="${#accounts[@]}"
    local num_roles="${#ROLES[@]}"
    local num_scopes="${#SCOPES[@]}"
    local total_assignments=$((num_accounts * num_roles * num_scopes))

    echo ""
    echo "=========================================================================="
    echo "AZURE ROLE ASSIGNMENT SUMMARY"
    echo "=========================================================================="
    echo ""
    echo "Tenant ID:       ${TENANT_ID}"
    echo "Subscription ID: ${SUBSCRIPTION_ID}"
    echo "UPN Domain:      ${UPN_DOMAIN}"
    echo ""
    echo "Accounts (${num_accounts}):"
    for account in "${accounts[@]}"; do
        echo "  - ${account}@${UPN_DOMAIN}"
    done
    echo ""
    echo "Roles (${num_roles}):"
    for role in "${ROLES[@]}"; do
        echo "  - ${role}"
    done
    echo ""
    echo "Scopes (${num_scopes}):"
    for scope in "${SCOPES[@]}"; do
        if [[ "${scope}" == "/" ]]; then
            echo "  - Tenant Root (/)"
        else
            echo "  - Subscription (${scope})"
        fi
    done
    echo ""
    echo "Total Role Assignments: ${total_assignments}"
    echo ""
    echo "Log File: ${LOG_FILE}"

    if [[ "${DRY_RUN}" == "1" ]]; then
        echo ""
        echo "MODE: DRY-RUN (no changes will be made)"
    fi

    echo "=========================================================================="
    echo ""
}

confirm_tenant_root_assignments() {
    if [[ "${SKIP_CONFIRMATION}" == "1" ]]; then
        log_info "Skipping confirmation (SKIP_CONFIRMATION=1)"
        return 0
    fi

    if [[ "${DRY_RUN}" == "1" ]]; then
        log_info "Skipping confirmation (DRY_RUN=1)"
        return 0
    fi

    echo ""
    echo "=========================================================================="
    echo "WARNING: TENANT ROOT SCOPE ASSIGNMENTS"
    echo "=========================================================================="
    echo ""
    echo "This script will assign roles at the TENANT ROOT (/) scope, which grants"
    echo "permissions across ALL subscriptions and management groups in the tenant."
    echo ""
    echo "This is a highly privileged operation and should only be performed by"
    echo "authorized administrators."
    echo ""
    read -p "Do you want to proceed? (yes/no): " -r
    echo ""

    if [[ ! "${REPLY}" =~ ^[Yy][Ee][Ss]$ ]]; then
        log_warn "User declined to proceed with tenant root assignments"
        echo "Operation cancelled by user."
        exit 0
    fi

    log_info "User confirmed tenant root assignments"
}

process_accounts() {
    local accounts=()
    local failed_validations=()

    # Read and validate accounts
    log_info "Reading accounts from ${ACCOUNTS_FILE}..."
    while IFS= read -r line; do
        # Skip empty lines and comments
        [[ -z "${line}" ]] && continue
        [[ "${line}" =~ ^[[:space:]]*# ]] && continue

        # Trim whitespace
        line=$(echo "${line}" | xargs)
        [[ -z "${line}" ]] && continue

        accounts+=("${line}")
    done < "${ACCOUNTS_FILE}"

    log_info "Found ${#accounts[@]} accounts to process"

    # Validate all accounts exist in Azure AD
    log_info "Validating accounts in Azure AD..."
    for account in "${accounts[@]}"; do
        if ! validate_azure_ad_account "${account}"; then
            failed_validations+=("${account}")
        fi
    done

    if [[ "${#failed_validations[@]}" -gt 0 ]]; then
        log_error "Failed to validate ${#failed_validations[@]} accounts:"
        for account in "${failed_validations[@]}"; do
            log_error "  - ${account}@${UPN_DOMAIN}"
        done
        log_error "Aborting due to validation failures"
        return 1
    fi

    log_success "All accounts validated successfully"

    # Process role assignments for each account
    log_info "Starting role assignment process..."
    echo ""

    for account in "${accounts[@]}"; do
        local upn="${account}@${UPN_DOMAIN}"

        echo "----------------------------------------------------------------------"
        log_info "Processing account: ${upn}"
        echo "----------------------------------------------------------------------"

        for role in "${ROLES[@]}"; do
            for scope in "${SCOPES[@]}"; do
                assign_role "${upn}" "${role}" "${scope}" || true
            done
        done

        echo ""
    done

    return 0
}

display_final_summary() {
    echo ""
    echo "=========================================================================="
    echo "EXECUTION SUMMARY"
    echo "=========================================================================="
    echo ""
    echo "Total Operations:      ${TOTAL_OPERATIONS}"
    echo "Successful:            ${SUCCESSFUL_OPERATIONS}"
    echo "Skipped (existing):    ${SKIPPED_OPERATIONS}"
    echo "Failed:                ${FAILED_OPERATIONS}"
    echo ""
    echo "Log File: ${LOG_FILE}"
    echo ""

    if [[ "${FAILED_OPERATIONS}" -gt 0 ]]; then
        echo "STATUS: COMPLETED WITH ERRORS"
        echo ""
        echo "Review the log file for details on failed operations."
    elif [[ "${DRY_RUN}" == "1" ]]; then
        echo "STATUS: DRY-RUN COMPLETED"
        echo ""
        echo "No changes were made. Run without DRY_RUN=1 to apply changes."
    else
        echo "STATUS: ALL OPERATIONS SUCCESSFUL"
    fi

    echo "=========================================================================="
    echo ""
}

main() {
    log_info "=========================================="
    log_info "Azure Role Assignment Script Started"
    log_info "=========================================="
    log_info "Log file: ${LOG_FILE}"

    # Validation Phase
    log_info "Starting validation phase..."

    if ! check_az_cli; then
        exit 1
    fi

    if ! check_authentication; then
        exit 1
    fi

    if ! validate_accounts_file; then
        exit 1
    fi

    log_success "Validation phase completed"

    # Display summary of planned changes
    display_summary

    # Confirm tenant root assignments
    confirm_tenant_root_assignments

    # Execution Phase
    log_info "Starting execution phase..."

    if ! process_accounts; then
        log_error "Execution phase failed"
        display_final_summary
        exit 1
    fi

    log_success "Execution phase completed"

    # Display final summary
    display_final_summary

    # Determine exit code
    if [[ "${FAILED_OPERATIONS}" -gt 0 ]]; then
        exit 1
    else
        exit 0
    fi
}

# ============================================================================
# ENTRY POINT
# ============================================================================

main "$@"
