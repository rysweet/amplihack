#!/usr/bin/env bash
# deploy.sh -- Idempotent Azure deployment for the amplihack distributed hive mind.
#
# Provisions:
#   - Resource group
#   - Azure Container Registry (ACR)
#   - Azure Service Bus namespace + topic + subscriptions
#   - Azure Storage Account + File Share (for Kuzu persistence)
#   - Container Apps Environment
#   - N Container Apps (ceil(HIVE_AGENT_COUNT / 5) apps, 5 agents each)
#
# Follows patterns from haymaker-workload-starter and experiments/hive_mind/deploy_azure_hive.sh.
#
# Usage:
#   bash deploy/azure_hive/deploy.sh                 # Deploy everything
#   bash deploy/azure_hive/deploy.sh --build-only    # Build + push image only
#   bash deploy/azure_hive/deploy.sh --infra-only    # Provision infra only
#   bash deploy/azure_hive/deploy.sh --cleanup       # Tear down resource group
#   bash deploy/azure_hive/deploy.sh --status        # Show deployment status
#
# Prerequisites:
#   - Azure CLI authenticated: az login
#   - Docker daemon running (for image build)
#   - ANTHROPIC_API_KEY env var set
#
# Environment variable overrides:
#   HIVE_NAME              -- Hive name (default: amplihive)
#   HIVE_RESOURCE_GROUP    -- Resource group (default: hive-mind-rg)
#   HIVE_LOCATION          -- Azure region (default: eastus)
#   HIVE_AGENT_COUNT       -- Total agents (default: 5)
#   HIVE_AGENTS_PER_APP    -- Agents per Container App (default: 5)
#   HIVE_ACR_NAME          -- ACR name override (auto-generated if empty)
#   HIVE_IMAGE_TAG         -- Docker image tag (default: latest)
#   HIVE_TRANSPORT         -- Transport type (default: azure_service_bus)
#   HIVE_AGENT_PROMPT_BASE -- Base system prompt for agents

set -euo pipefail

# ============================================================
# Configuration
# ============================================================

HIVE_NAME="${HIVE_NAME:-amplihive}"
RESOURCE_GROUP="${HIVE_RESOURCE_GROUP:-hive-mind-rg}"
LOCATION="${HIVE_LOCATION:-eastus}"
AGENT_COUNT="${HIVE_AGENT_COUNT:-5}"
AGENTS_PER_APP="${HIVE_AGENTS_PER_APP:-5}"
IMAGE_TAG="${HIVE_IMAGE_TAG:-latest}"
TRANSPORT="${HIVE_TRANSPORT:-azure_service_bus}"
AGENT_PROMPT_BASE="${HIVE_AGENT_PROMPT_BASE:-You are a distributed hive mind agent.}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ============================================================
# Argument parsing
# ============================================================

MODE="all"
case "${1:-}" in
  --build-only)  MODE="build"   ;;
  --infra-only)  MODE="infra"   ;;
  --cleanup)     MODE="cleanup" ;;
  --status)      MODE="status"  ;;
esac

# ============================================================
# Helpers
# ============================================================

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "$1 is required but not installed."
}

# ============================================================
# Cleanup
# ============================================================

if [[ "$MODE" == "cleanup" ]]; then
  log "Deleting resource group ${RESOURCE_GROUP}..."
  az group delete --name "${RESOURCE_GROUP}" --yes --no-wait
  log "Cleanup initiated (deletion runs in background)."
  exit 0
fi

# ============================================================
# Status
# ============================================================

if [[ "$MODE" == "status" ]]; then
  log "Deployment status for hive '${HIVE_NAME}' in ${RESOURCE_GROUP}:"
  az containerapp list \
    --resource-group "${RESOURCE_GROUP}" \
    --query "[?starts_with(name, '${HIVE_NAME}')].{name:name,status:properties.runningStatus,replicas:properties.template.scale.minReplicas}" \
    --output table 2>/dev/null || echo "Resource group not found or no Container Apps deployed."
  exit 0
fi

# ============================================================
# Prerequisites
# ============================================================

require_cmd az
[[ -n "${ANTHROPIC_API_KEY:-}" ]] || die "ANTHROPIC_API_KEY env var is required."

# ============================================================
# Resource group
# ============================================================

log "Ensuring resource group ${RESOURCE_GROUP} in ${LOCATION}..."
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --output none

# ============================================================
# Container Registry
# ============================================================

# Auto-generate ACR name if not set (must be globally unique, alphanumeric only)
if [[ -z "${HIVE_ACR_NAME:-}" ]]; then
  SUFFIX=$(echo "${RESOURCE_GROUP}" | tr -cd 'a-z0-9' | head -c 8)
  ACR_NAME="hivacr${SUFFIX}"
else
  ACR_NAME="${HIVE_ACR_NAME}"
fi

log "Ensuring ACR ${ACR_NAME}..."
az acr create \
  --name "${ACR_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --sku Basic \
  --admin-enabled true \
  --output none 2>/dev/null || true

ACR_LOGIN_SERVER=$(az acr show \
  --name "${ACR_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query loginServer -o tsv)

IMAGE="${ACR_LOGIN_SERVER}/${HIVE_NAME}:${IMAGE_TAG}"

# ============================================================
# Build and push Docker image
# ============================================================

if [[ "$MODE" == "all" || "$MODE" == "build" ]]; then
  if command -v docker >/dev/null 2>&1; then
    log "Building Docker image locally..."
    docker build --file "${SCRIPT_DIR}/Dockerfile" --tag "${IMAGE}" "${REPO_ROOT}"
    log "Pushing image to ACR..."
    az acr login --name "${ACR_NAME}"
    docker push "${IMAGE}"
  else
    log "Docker not available, using ACR remote build..."
    az acr build \
      --registry "${ACR_NAME}" \
      --image "${HIVE_NAME}:${IMAGE_TAG}" \
      --file "${SCRIPT_DIR}/Dockerfile" \
      "${REPO_ROOT}" \
      --no-logs 2>/dev/null || \
    az acr build \
      --registry "${ACR_NAME}" \
      --image "${HIVE_NAME}:${IMAGE_TAG}" \
      --file "${SCRIPT_DIR}/Dockerfile" \
      "${REPO_ROOT}"
  fi
  log "Image available: ${IMAGE}"
fi

[[ "$MODE" == "build" ]] && exit 0

# ============================================================
# Provision infrastructure via Bicep
# ============================================================

log "Deploying Bicep template to ${RESOURCE_GROUP}..."
DEPLOY_OUTPUT=$(az deployment group create \
  --resource-group "${RESOURCE_GROUP}" \
  --template-file "${SCRIPT_DIR}/main.bicep" \
  --parameters \
    hiveName="${HIVE_NAME}" \
    agentCount="${AGENT_COUNT}" \
    agentsPerApp="${AGENTS_PER_APP}" \
    image="${IMAGE}" \
    acrName="${ACR_NAME}" \
    anthropicApiKey="${ANTHROPIC_API_KEY}" \
    memoryTransport="${TRANSPORT}" \
    agentPromptBase="${AGENT_PROMPT_BASE}" \
  --output json)

log "Bicep deployment complete."

# Extract Service Bus connection string for reference
SB_FQDN=$(echo "${DEPLOY_OUTPUT}" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(d.get('properties',{}).get('outputs',{}).get('sbNamespaceFqdn',{}).get('value',''))" 2>/dev/null || echo "")

# ============================================================
# Summary
# ============================================================

APP_COUNT=$(( (AGENT_COUNT + AGENTS_PER_APP - 1) / AGENTS_PER_APP ))

log "============================================"
log "Hive '${HIVE_NAME}' deployment complete!"
log "  Agents:         ${AGENT_COUNT}"
log "  Container Apps: ${APP_COUNT} (${AGENTS_PER_APP} agents each)"
log "  ACR:            ${ACR_LOGIN_SERVER}"
log "  Transport:      ${TRANSPORT}"
[[ -n "${SB_FQDN}" ]] && log "  Service Bus:    ${SB_FQDN}"
log "============================================"
log "View app status: bash deploy/azure_hive/deploy.sh --status"
log "Teardown:        bash deploy/azure_hive/deploy.sh --cleanup"
