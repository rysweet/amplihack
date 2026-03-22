#!/usr/bin/env bash
# deploy.sh -- Idempotent Azure deployment for the amplihack distributed hive mind.
#
# Provisions:
#   - Resource group
#   - Azure Container Registry (ACR)
#   - Azure Event Hubs namespace + 3 hubs (hive-events, hive-shards, eval-responses)
#   - EmptyDir volumes for Kuzu (POSIX locks required, Azure Files SMB unsupported)
#   - Container Apps Environment
#   - N Container Apps (ceil(HIVE_AGENT_COUNT / HIVE_AGENTS_PER_APP) apps)
#
# NOTE: Service Bus removed — CBS auth fails in Container Apps. Using Event Hubs.
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
#   HIVE_LOCATION          -- Azure region (default: westus2)
#   HIVE_DEPLOYMENT_PROFILE -- federated-100 | smoke-10 | custom (default: federated-100)
#   HIVE_AGENT_COUNT       -- Total agents (required for custom profile)
#   HIVE_AGENTS_PER_APP    -- Agents per Container App (required for custom profile)
#   HIVE_ACR_NAME          -- ACR name override (auto-generated if empty)
#   HIVE_IMAGE_TAG         -- Docker image tag (default: latest)
#   HIVE_TRANSPORT         -- Transport type (default: azure_event_hubs)
#   HIVE_AGENT_PROMPT_BASE -- Base system prompt for agents
#   HIVE_OTEL_ENABLED      -- Enable OpenTelemetry instrumentation in deployed agents
#   HIVE_OTEL_OTLP_ENDPOINT -- OTLP/HTTP collector endpoint
#   HIVE_OTEL_EXPORTER_HEADERS -- Optional OTLP headers (for auth, etc.)
#   HIVE_OTEL_CONSOLE_EXPORTER -- Emit spans to stdout if no OTLP endpoint is set
#   HIVE_FORCE_RECREATE_EVENT_HUBS -- Force delete/recreate the Event Hubs namespace before deploy
#   HIVE_MEMORY_QUERY_FANOUT -- Max shards queried per distributed retrieval request (default: all agents)
#   HIVE_SHARD_QUERY_TIMEOUT_SECONDS -- Timeout for cross-shard queries (default: disabled for 100-agent profile, otherwise 60s)

set -euo pipefail

# ============================================================
# Configuration
# ============================================================

HIVE_NAME="${HIVE_NAME:-amplihive}"
RESOURCE_GROUP="${HIVE_RESOURCE_GROUP:-hive-mind-rg}"
LOCATION="${HIVE_LOCATION:-westus2}"
FALLBACK_REGIONS="${HIVE_FALLBACK_REGIONS:-eastus,westus3,centralus}"
DEPLOYMENT_PROFILE="${HIVE_DEPLOYMENT_PROFILE:-federated-100}"
IMAGE_TAG="${HIVE_IMAGE_TAG:-latest}"
TRANSPORT="${HIVE_TRANSPORT:-azure_event_hubs}"
MEMORY_BACKEND="${HIVE_MEMORY_BACKEND:-cognitive}"
AGENT_MODEL="${HIVE_AGENT_MODEL:-claude-sonnet-4-6}"
AGENT_PROMPT_BASE="${HIVE_AGENT_PROMPT_BASE:-You are a distributed hive mind agent.}"
ENABLE_DISTRIBUTED_RETRIEVAL="${HIVE_ENABLE_DISTRIBUTED_RETRIEVAL:-true}"
OTEL_OTLP_ENDPOINT="${HIVE_OTEL_OTLP_ENDPOINT:-}"
OTEL_OTLP_PROTOCOL="${HIVE_OTEL_OTLP_PROTOCOL:-http/protobuf}"
OTEL_EXPORTER_HEADERS="${HIVE_OTEL_EXPORTER_HEADERS:-}"
OTEL_SERVICE_NAMESPACE="${HIVE_OTEL_SERVICE_NAMESPACE:-amplihack}"
OTEL_CONSOLE_EXPORTER="${HIVE_OTEL_CONSOLE_EXPORTER:-true}"
FORCE_RECREATE_EVENT_HUBS="${HIVE_FORCE_RECREATE_EVENT_HUBS:-false}"

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

case "${DEPLOYMENT_PROFILE}" in
  federated-100)
    PROFILE_AGENT_COUNT="100"
    PROFILE_AGENTS_PER_APP="5"
    ;;
  smoke-10)
    PROFILE_AGENT_COUNT="10"
    PROFILE_AGENTS_PER_APP="1"
    ;;
  custom)
    PROFILE_AGENT_COUNT=""
    PROFILE_AGENTS_PER_APP=""
    ;;
  *)
    die "Unknown HIVE_DEPLOYMENT_PROFILE='${DEPLOYMENT_PROFILE}'. Use federated-100, smoke-10, or custom."
    ;;
esac

if [[ "${DEPLOYMENT_PROFILE}" == "custom" ]]; then
  AGENT_COUNT="${HIVE_AGENT_COUNT:-}"
  AGENTS_PER_APP="${HIVE_AGENTS_PER_APP:-}"
  [[ -n "${AGENT_COUNT}" ]] || die "HIVE_AGENT_COUNT is required when HIVE_DEPLOYMENT_PROFILE=custom."
  [[ -n "${AGENTS_PER_APP}" ]] || die "HIVE_AGENTS_PER_APP is required when HIVE_DEPLOYMENT_PROFILE=custom."
else
  AGENT_COUNT="${HIVE_AGENT_COUNT:-${PROFILE_AGENT_COUNT}}"
  AGENTS_PER_APP="${HIVE_AGENTS_PER_APP:-${PROFILE_AGENTS_PER_APP}}"
  if [[ "${AGENT_COUNT}" != "${PROFILE_AGENT_COUNT}" || "${AGENTS_PER_APP}" != "${PROFILE_AGENTS_PER_APP}" ]]; then
    die "Profile '${DEPLOYMENT_PROFILE}' expects HIVE_AGENT_COUNT=${PROFILE_AGENT_COUNT} and HIVE_AGENTS_PER_APP=${PROFILE_AGENTS_PER_APP}. Use HIVE_DEPLOYMENT_PROFILE=custom for non-profile values."
  fi
fi

if [[ -n "${HIVE_OTEL_ENABLED:-}" ]]; then
  OTEL_ENABLED="${HIVE_OTEL_ENABLED}"
elif [[ -n "${OTEL_OTLP_ENDPOINT}" || "${OTEL_CONSOLE_EXPORTER,,}" == "true" ]]; then
  OTEL_ENABLED="true"
else
  OTEL_ENABLED="false"
fi

if [[ -n "${HIVE_MEMORY_QUERY_FANOUT:-}" ]]; then
  MEMORY_QUERY_FANOUT="${HIVE_MEMORY_QUERY_FANOUT}"
else
  MEMORY_QUERY_FANOUT="${AGENT_COUNT}"
fi

if [[ -n "${HIVE_SHARD_QUERY_TIMEOUT_SECONDS:-}" ]]; then
  SHARD_QUERY_TIMEOUT_SECONDS="${HIVE_SHARD_QUERY_TIMEOUT_SECONDS}"
elif [[ "${AGENT_COUNT}" -ge 100 ]]; then
  SHARD_QUERY_TIMEOUT_SECONDS="0"
else
  SHARD_QUERY_TIMEOUT_SECONDS="60"
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
# Clean deploy: tear down ALL existing Container Apps
# ============================================================
# Every deploy is from scratch — no mixing old and new revisions.
# Bicep cannot guarantee in-place updates clear stale code, so we
# delete all apps first and let Bicep recreate them fresh.

log "Checking for existing Container Apps to tear down..."
EXISTING_APPS=$(az containerapp list \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[?starts_with(name, '${HIVE_NAME}')].name" \
  -o tsv 2>/dev/null || true)

if [[ -n "${EXISTING_APPS}" ]]; then
  log "Tearing down existing Container Apps (clean deploy)..."
  for APP_NAME in ${EXISTING_APPS}; do
    log "  Deleting ${APP_NAME}..."
    az containerapp delete \
      --name "${APP_NAME}" \
      --resource-group "${RESOURCE_GROUP}" \
      --yes --no-wait 2>/dev/null || true
  done
  # Wait for all deletions to complete
  log "Waiting for Container App deletions to complete..."
  for APP_NAME in ${EXISTING_APPS}; do
    while az containerapp show --name "${APP_NAME}" --resource-group "${RESOURCE_GROUP}" &>/dev/null; do
      sleep 5
    done
  done
  log "All existing Container Apps deleted."
fi

# ============================================================
# Event Hubs reset for immutable partition changes
# ============================================================

DESIRED_EH_PARTITIONS="${AGENT_COUNT}"
if [[ "${DESIRED_EH_PARTITIONS}" -gt 28 ]]; then
  DESIRED_EH_PARTITIONS=32
else
  DESIRED_EH_PARTITIONS=$((DESIRED_EH_PARTITIONS + 4))
fi

EH_NAMESPACE_NAME="$(az eventhubs namespace list \
  --resource-group "${RESOURCE_GROUP}" \
  --query "[?starts_with(name, 'hive-eh-')].name | [0]" \
  -o tsv 2>/dev/null || true)"

RESET_EVENT_HUBS=false
RESET_REASON=""

if [[ "${FORCE_RECREATE_EVENT_HUBS,,}" == "true" && -n "${EH_NAMESPACE_NAME}" ]]; then
  RESET_EVENT_HUBS=true
  RESET_REASON="forced by HIVE_FORCE_RECREATE_EVENT_HUBS=true"
elif [[ -n "${EH_NAMESPACE_NAME}" ]]; then
  for HUB_NAME in "hive-events-${HIVE_NAME}" "hive-shards-${HIVE_NAME}" "eval-responses-${HIVE_NAME}"; do
    CURRENT_PARTITIONS="$(az eventhubs eventhub show \
      --resource-group "${RESOURCE_GROUP}" \
      --namespace-name "${EH_NAMESPACE_NAME}" \
      --name "${HUB_NAME}" \
      --query partitionCount \
      -o tsv 2>/dev/null || true)"
    if [[ -n "${CURRENT_PARTITIONS}" && "${CURRENT_PARTITIONS}" != "null" && "${CURRENT_PARTITIONS}" -lt "${DESIRED_EH_PARTITIONS}" ]]; then
      RESET_EVENT_HUBS=true
      RESET_REASON="hub ${HUB_NAME} has ${CURRENT_PARTITIONS} partition(s), needs ${DESIRED_EH_PARTITIONS}"
      break
    fi
  done
fi

if [[ "${RESET_EVENT_HUBS}" == "true" && -n "${EH_NAMESPACE_NAME}" ]]; then
  log "Recreating Event Hubs namespace ${EH_NAMESPACE_NAME} (${RESET_REASON})..."
  az eventhubs namespace delete \
    --name "${EH_NAMESPACE_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --output none
  log "Waiting for Event Hubs namespace deletion to complete..."
  while az eventhubs namespace show --name "${EH_NAMESPACE_NAME}" --resource-group "${RESOURCE_GROUP}" --output none &>/dev/null; do
    sleep 5
  done
  log "Event Hubs namespace ${EH_NAMESPACE_NAME} deleted."
fi

# ============================================================
# Provision infrastructure via Bicep
# ============================================================

DEPLOY_MAX_RETRIES="${HIVE_DEPLOY_RETRIES:-3}"
DEPLOY_REGIONS="${LOCATION},${FALLBACK_REGIONS}"
DEPLOY_SUCCEEDED=false

IFS=',' read -ra _REGIONS <<< "${DEPLOY_REGIONS}"
for _region in "${_REGIONS[@]}"; do
  _region=$(echo "${_region}" | tr -d ' ')
  DEPLOY_RETRY_DELAY=30

  # Update resource group location if switching regions
  if [[ "${_region}" != "${LOCATION}" ]]; then
    log "Primary region ${LOCATION} failed. Trying fallback region: ${_region}"
    LOCATION="${_region}"
  fi

  for _deploy_attempt in $(seq 1 "${DEPLOY_MAX_RETRIES}"); do
    log "Deploying Bicep to ${RESOURCE_GROUP} in ${_region} (attempt ${_deploy_attempt}/${DEPLOY_MAX_RETRIES})..."
    DEPLOY_OUTPUT=$(az deployment group create \
      --resource-group "${RESOURCE_GROUP}" \
      --template-file "${SCRIPT_DIR}/main.bicep" \
      --parameters \
        hiveName="${HIVE_NAME}" \
        location="${_region}" \
        agentCount="${AGENT_COUNT}" \
        agentsPerApp="${AGENTS_PER_APP}" \
        image="${IMAGE}" \
        acrName="${ACR_NAME}" \
        anthropicApiKey="${ANTHROPIC_API_KEY}" \
        memoryTransport="${TRANSPORT}" \
        memoryBackend="${MEMORY_BACKEND}" \
        agentModel="${AGENT_MODEL}" \
        agentPromptBase="${AGENT_PROMPT_BASE}" \
        enableDistributedRetrieval="${ENABLE_DISTRIBUTED_RETRIEVAL}" \
        memoryQueryFanout="${MEMORY_QUERY_FANOUT}" \
        shardQueryTimeoutSeconds="${SHARD_QUERY_TIMEOUT_SECONDS}" \
        deploymentProfile="${DEPLOYMENT_PROFILE}" \
        enableOpenTelemetry="${OTEL_ENABLED}" \
        otelOtlpEndpoint="${OTEL_OTLP_ENDPOINT}" \
        otelOtlpProtocol="${OTEL_OTLP_PROTOCOL}" \
        otelExporterHeaders="${OTEL_EXPORTER_HEADERS}" \
        otelServiceNamespace="${OTEL_SERVICE_NAMESPACE}" \
        otelConsoleExporter="${OTEL_CONSOLE_EXPORTER}" \
      --output json 2>&1) && { DEPLOY_SUCCEEDED=true; break 2; }

    if [[ "${_deploy_attempt}" -lt "${DEPLOY_MAX_RETRIES}" ]]; then
      log "Attempt ${_deploy_attempt} failed. Retrying in ${DEPLOY_RETRY_DELAY}s..."
      log "Error: $(echo "${DEPLOY_OUTPUT}" | grep -o '"message":"[^"]*"' | head -1)"
      sleep "${DEPLOY_RETRY_DELAY}"
      DEPLOY_RETRY_DELAY=$((DEPLOY_RETRY_DELAY * 2))
    else
      log "All ${DEPLOY_MAX_RETRIES} attempts failed in ${_region}."
      # Clean up partial deployment before trying next region
      log "Cleaning up partial resources in ${_region}..."
      az containerapp env delete -n "hive-env-${HIVE_NAME}" -g "${RESOURCE_GROUP}" --yes 2>/dev/null || true
    fi
  done
done

if [[ "${DEPLOY_SUCCEEDED}" != "true" ]]; then
  log "Deployment failed in all regions: ${DEPLOY_REGIONS}"
  echo "${DEPLOY_OUTPUT}" >&2
  exit 1
fi

log "Bicep deployment complete (region: ${LOCATION})."

# Extract Event Hubs namespace name for reference
EH_NAMESPACE=$(echo "${DEPLOY_OUTPUT}" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print(d.get('properties',{}).get('outputs',{}).get('ehNamespaceName',{}).get('value',''))" 2>/dev/null || echo "")

# ============================================================
# Summary
# ============================================================

APP_COUNT=$(( (AGENT_COUNT + AGENTS_PER_APP - 1) / AGENTS_PER_APP ))

log "============================================"
log "Hive '${HIVE_NAME}' deployment complete!"
log "  Profile:        ${DEPLOYMENT_PROFILE}"
log "  Agents:         ${AGENT_COUNT}"
log "  Container Apps: ${APP_COUNT} (${AGENTS_PER_APP} agents each)"
log "  ACR:            ${ACR_LOGIN_SERVER}"
log "  Transport:      ${TRANSPORT} (azure_event_hubs)"
log "  OTel Enabled:   ${OTEL_ENABLED}"
[[ -n "${OTEL_OTLP_ENDPOINT}" ]] && log "  OTLP Endpoint:  ${OTEL_OTLP_ENDPOINT}"
[[ -n "${OTEL_OTLP_PROTOCOL}" ]] && log "  OTLP Protocol:  ${OTEL_OTLP_PROTOCOL}"
log "  EH Input Hub:   hive-events-${HIVE_NAME}"
log "  EH Shards Hub:  hive-shards-${HIVE_NAME}"
log "  EH Eval Hub:    eval-responses-${HIVE_NAME}"
[[ -n "${EH_NAMESPACE}" ]] && log "  EH Namespace:   ${EH_NAMESPACE}"
log "============================================"
log "View app status: bash deploy/azure_hive/deploy.sh --status"
log "Teardown:        bash deploy/azure_hive/deploy.sh --cleanup"
