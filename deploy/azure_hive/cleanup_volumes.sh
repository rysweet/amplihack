#!/usr/bin/env bash
# cleanup_volumes.sh -- Purge Azure Files persistent volumes for the hive mind.
#
# Deletes all files inside the hive-data Azure File Share, optionally deleting
# the share itself.  The storage account is left intact unless --delete-account
# is passed.
#
# Usage:
#   bash deploy/azure_hive/cleanup_volumes.sh                 # wipe file share contents
#   bash deploy/azure_hive/cleanup_volumes.sh --delete-share  # delete the share itself
#   bash deploy/azure_hive/cleanup_volumes.sh --delete-account # delete storage account
#   bash deploy/azure_hive/cleanup_volumes.sh --dry-run       # show what would be deleted
#
# Environment variable overrides:
#   HIVE_RESOURCE_GROUP  -- Resource group (default: hive-mind-rg)
#   HIVE_STORAGE_ACCOUNT -- Storage account name (auto-detected if empty)
#   HIVE_FILE_SHARE      -- File share name (default: hive-data)

set -euo pipefail

RESOURCE_GROUP="${HIVE_RESOURCE_GROUP:-hive-mind-rg}"
STORAGE_ACCOUNT="${HIVE_STORAGE_ACCOUNT:-}"
FILE_SHARE="${HIVE_FILE_SHARE:-hive-data}"

MODE="wipe"
case "${1:-}" in
  --delete-share)   MODE="delete-share"   ;;
  --delete-account) MODE="delete-account" ;;
  --dry-run)        MODE="dry-run"        ;;
esac

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
die()  { echo "ERROR: $*" >&2; exit 1; }

command -v az >/dev/null 2>&1 || die "Azure CLI (az) is required."

# Auto-detect storage account if not set
if [[ -z "${STORAGE_ACCOUNT}" ]]; then
  STORAGE_ACCOUNT=$(az storage account list \
    --resource-group "${RESOURCE_GROUP}" \
    --query "[?starts_with(name, 'hivesa')].name | [0]" \
    -o tsv 2>/dev/null)
  [[ -n "${STORAGE_ACCOUNT}" ]] || die "Could not detect storage account in ${RESOURCE_GROUP}. Set HIVE_STORAGE_ACCOUNT."
  log "Detected storage account: ${STORAGE_ACCOUNT}"
fi

ACCOUNT_KEY=$(az storage account keys list \
  --account-name "${STORAGE_ACCOUNT}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[0].value" -o tsv 2>/dev/null)

[[ -n "${ACCOUNT_KEY}" ]] || die "Could not retrieve storage account key for ${STORAGE_ACCOUNT}."

if [[ "${MODE}" == "delete-account" ]]; then
  if [[ "${DRY_RUN:-}" == "true" || "${MODE}" == "dry-run" ]]; then
    log "DRY-RUN: would delete storage account ${STORAGE_ACCOUNT}"
    exit 0
  fi
  log "Deleting storage account ${STORAGE_ACCOUNT}..."
  az storage account delete \
    --name "${STORAGE_ACCOUNT}" \
    --resource-group "${RESOURCE_GROUP}" \
    --yes
  log "Storage account deleted."
  exit 0
fi

if [[ "${MODE}" == "delete-share" ]]; then
  if [[ "${MODE}" == "dry-run" ]]; then
    log "DRY-RUN: would delete file share ${FILE_SHARE} in ${STORAGE_ACCOUNT}"
    exit 0
  fi
  log "Deleting file share '${FILE_SHARE}' in ${STORAGE_ACCOUNT}..."
  az storage share delete \
    --name "${FILE_SHARE}" \
    --account-name "${STORAGE_ACCOUNT}" \
    --account-key "${ACCOUNT_KEY}" \
    --output none
  log "File share '${FILE_SHARE}' deleted."
  log "Recreating empty share for future deployments..."
  az storage share create \
    --name "${FILE_SHARE}" \
    --account-name "${STORAGE_ACCOUNT}" \
    --account-key "${ACCOUNT_KEY}" \
    --quota 100 \
    --output none
  log "File share '${FILE_SHARE}' recreated (empty, 100 GiB quota)."
  exit 0
fi

# Default: wipe (delete all files / directories inside the share)
log "Enumerating files in share '${FILE_SHARE}'..."
FILE_COUNT=0
DIR_COUNT=0

while IFS= read -r item; do
  [[ -z "${item}" ]] && continue
  if [[ "${MODE}" == "dry-run" ]]; then
    log "DRY-RUN: would delete: ${item}"
  else
    az storage file delete \
      --path "${item}" \
      --share-name "${FILE_SHARE}" \
      --account-name "${STORAGE_ACCOUNT}" \
      --account-key "${ACCOUNT_KEY}" \
      --output none 2>/dev/null || true
  fi
  (( FILE_COUNT++ )) || true
done < <(az storage file list \
  --share-name "${FILE_SHARE}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${ACCOUNT_KEY}" \
  --query "[?type=='file'].name" -o tsv 2>/dev/null)

while IFS= read -r dir; do
  [[ -z "${dir}" ]] && continue
  if [[ "${MODE}" == "dry-run" ]]; then
    log "DRY-RUN: would delete directory: ${dir}"
  else
    az storage directory delete \
      --name "${dir}" \
      --share-name "${FILE_SHARE}" \
      --account-name "${STORAGE_ACCOUNT}" \
      --account-key "${ACCOUNT_KEY}" \
      --output none 2>/dev/null || true
  fi
  (( DIR_COUNT++ )) || true
done < <(az storage file list \
  --share-name "${FILE_SHARE}" \
  --account-name "${STORAGE_ACCOUNT}" \
  --account-key "${ACCOUNT_KEY}" \
  --query "[?type=='dir'].name" -o tsv 2>/dev/null)

if [[ "${MODE}" == "dry-run" ]]; then
  log "DRY-RUN complete — ${FILE_COUNT} files and ${DIR_COUNT} directories would be removed."
else
  log "Cleanup complete — removed ${FILE_COUNT} files and ${DIR_COUNT} directories from '${FILE_SHARE}'."
fi
