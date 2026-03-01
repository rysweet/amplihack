#!/usr/bin/env bash
# deploy_azure_hive.sh -- Idempotent Azure deployment for the 20-agent Hive Mind evaluation.
#
# Provisions Azure infrastructure (Container Apps, Service Bus, Storage, ACR)
# and deploys 20 domain agents + 1 adversarial agent as individual Container Apps.
#
# Follows the haymaker-workload-starter patterns:
#   - Consumption tier Container Apps (near-zero idle cost)
#   - Basic ACR with admin-enabled for image pull
#   - Log Analytics for centralized logging
#   - Idempotent creation (safe to run repeatedly)
#
# Usage:
#   bash experiments/hive_mind/deploy_azure_hive.sh            # Deploy infra + agents
#   bash experiments/hive_mind/deploy_azure_hive.sh --eval     # Run evaluation only
#   bash experiments/hive_mind/deploy_azure_hive.sh --cleanup  # Tear down everything
#   bash experiments/hive_mind/deploy_azure_hive.sh --status   # Show deployment status
#
# Prerequisites:
#   - Azure CLI authenticated:  az login
#   - GitHub CLI authenticated: gh auth login
#   - ANTHROPIC_API_KEY env var set
#   - Active Azure subscription selected
#
# Environment variable overrides:
#   HIVE_RESOURCE_GROUP   -- Resource group name (default: hive-mind-eval-rg)
#   HIVE_LOCATION         -- Azure region (default: eastus)
#   HIVE_AGENT_COUNT      -- Number of domain agents (default: 20)
#   HIVE_ACR_NAME         -- ACR name override (default: auto-generated)
#   HIVE_IMAGE_TAG        -- Docker image tag (default: latest)

set -euo pipefail

# ============================================================
# Configuration
# ============================================================

RESOURCE_GROUP="${HIVE_RESOURCE_GROUP:-hive-mind-eval-rg}"
LOCATION="${HIVE_LOCATION:-eastus}"
AGENT_COUNT="${HIVE_AGENT_COUNT:-20}"
IMAGE_TAG="${HIVE_IMAGE_TAG:-latest}"

# Derived names -- deterministic from subscription to ensure idempotency.
# ACR names must be globally unique (3-50 alphanumeric chars only).
SUB_ID=$(az account show --query id -o tsv 2>/dev/null || echo "")
SUB_HASH=$(echo "${SUB_ID}" | md5sum | cut -c1-6)
ACR_NAME="${HIVE_ACR_NAME:-hivemindacr${SUB_HASH}}"
SERVICE_BUS_NS="hive-events-${SUB_HASH}"
STORAGE_ACCOUNT="hivemind${SUB_HASH}"
FILE_SHARE_NAME="agent-databases"
LOG_ANALYTICS_NAME="hive-logs-${SUB_HASH}"
CONTAINER_ENV_NAME="hive-mind-env"
IMAGE_NAME="hive-mind-agent"

# 10 domains x 2 agents each = 20 domain agents
DOMAINS=("biology" "chemistry" "physics" "math" "compsci" "history" "geography" "economics" "psychology" "engineering")

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# ============================================================
# Logging helpers
# ============================================================

_log()  { echo "[$(date +%H:%M:%S)] $*"; }
_info() { _log "INFO:  $*"; }
_warn() { _log "WARN:  $*"; }
_err()  { _log "ERROR: $*" >&2; }
_ok()   { _log "OK:    $*"; }

# ============================================================
# Step 1: Prerequisites
# ============================================================

check_prereqs() {
    _info "Checking prerequisites..."
    local failed=0

    # Azure CLI
    if ! command -v az &>/dev/null; then
        _err "Azure CLI (az) not found. Install: https://aka.ms/install-azure-cli"
        failed=1
    elif ! az account show &>/dev/null; then
        _err "Azure CLI not authenticated. Run: az login"
        failed=1
    else
        _ok "Azure CLI authenticated (subscription: ${SUB_ID})"
    fi

    # Subscription ID must be non-empty
    if [[ -z "${SUB_ID}" ]]; then
        _err "No Azure subscription selected. Run: az account set --subscription <id>"
        failed=1
    fi

    # Docker
    if ! command -v docker &>/dev/null; then
        _err "Docker not found. Install: https://docs.docker.com/get-docker/"
        failed=1
    else
        _ok "Docker available"
    fi

    # ANTHROPIC_API_KEY
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
        _err "ANTHROPIC_API_KEY not set. Export it: export ANTHROPIC_API_KEY=sk-..."
        failed=1
    else
        _ok "ANTHROPIC_API_KEY set (${#ANTHROPIC_API_KEY} chars)"
    fi

    # jq
    if ! command -v jq &>/dev/null; then
        _err "jq not found. Install: sudo apt-get install jq"
        failed=1
    else
        _ok "jq available"
    fi

    if [[ ${failed} -ne 0 ]]; then
        _err "Prerequisites check failed. Fix the issues above and retry."
        exit 1
    fi

    _info "All prerequisites satisfied."
    echo
}

# ============================================================
# Step 2: Resource Group (idempotent)
# ============================================================

create_resource_group() {
    _info "Creating resource group '${RESOURCE_GROUP}' in '${LOCATION}'..."

    az group create \
        --name "${RESOURCE_GROUP}" \
        --location "${LOCATION}" \
        --tags purpose=hive-mind-eval created-by=deploy-azure-hive \
        -o none

    _ok "Resource group '${RESOURCE_GROUP}' ready."
    echo
}

# ============================================================
# Step 3: Log Analytics Workspace (idempotent)
# ============================================================

create_log_analytics() {
    _info "Creating Log Analytics workspace '${LOG_ANALYTICS_NAME}'..."

    local exists
    exists=$(az monitor log-analytics workspace show \
        --resource-group "${RESOURCE_GROUP}" \
        --workspace-name "${LOG_ANALYTICS_NAME}" \
        --query name -o tsv 2>/dev/null || echo "")

    if [[ -n "${exists}" ]]; then
        _ok "Log Analytics workspace already exists."
    else
        az monitor log-analytics workspace create \
            --resource-group "${RESOURCE_GROUP}" \
            --workspace-name "${LOG_ANALYTICS_NAME}" \
            --location "${LOCATION}" \
            --retention-time 30 \
            -o none
        _ok "Log Analytics workspace created."
    fi

    # Export workspace ID and key for Container Apps Environment
    LOG_WORKSPACE_ID=$(az monitor log-analytics workspace show \
        --resource-group "${RESOURCE_GROUP}" \
        --workspace-name "${LOG_ANALYTICS_NAME}" \
        --query customerId -o tsv)
    LOG_WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys \
        --resource-group "${RESOURCE_GROUP}" \
        --workspace-name "${LOG_ANALYTICS_NAME}" \
        --query primarySharedKey -o tsv)

    echo
}

# ============================================================
# Step 4: Azure Service Bus (idempotent)
# ============================================================

create_service_bus() {
    _info "Creating Service Bus namespace '${SERVICE_BUS_NS}'..."

    local ns_exists
    ns_exists=$(az servicebus namespace show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${SERVICE_BUS_NS}" \
        --query name -o tsv 2>/dev/null || echo "")

    if [[ -n "${ns_exists}" ]]; then
        _ok "Service Bus namespace already exists."
    else
        az servicebus namespace create \
            --resource-group "${RESOURCE_GROUP}" \
            --name "${SERVICE_BUS_NS}" \
            --location "${LOCATION}" \
            --sku Standard \
            -o none
        _ok "Service Bus namespace created."
    fi

    # Create topic "hive-events" (idempotent)
    _info "Creating topic 'hive-events'..."
    local topic_exists
    topic_exists=$(az servicebus topic show \
        --resource-group "${RESOURCE_GROUP}" \
        --namespace-name "${SERVICE_BUS_NS}" \
        --name "hive-events" \
        --query name -o tsv 2>/dev/null || echo "")

    if [[ -n "${topic_exists}" ]]; then
        _ok "Topic 'hive-events' already exists."
    else
        az servicebus topic create \
            --resource-group "${RESOURCE_GROUP}" \
            --namespace-name "${SERVICE_BUS_NS}" \
            --name "hive-events" \
            --default-message-time-to-live "PT1H" \
            -o none
        _ok "Topic 'hive-events' created."
    fi

    # Create per-agent subscriptions (idempotent)
    _info "Creating per-agent subscriptions..."
    local sub_count=0
    for domain in "${DOMAINS[@]}"; do
        for suffix in 1 2; do
            local agent_id="${domain}_${suffix}"
            local sub_exists
            sub_exists=$(az servicebus topic subscription show \
                --resource-group "${RESOURCE_GROUP}" \
                --namespace-name "${SERVICE_BUS_NS}" \
                --topic-name "hive-events" \
                --name "${agent_id}" \
                --query name -o tsv 2>/dev/null || echo "")

            if [[ -z "${sub_exists}" ]]; then
                az servicebus topic subscription create \
                    --resource-group "${RESOURCE_GROUP}" \
                    --namespace-name "${SERVICE_BUS_NS}" \
                    --topic-name "hive-events" \
                    --name "${agent_id}" \
                    --default-message-time-to-live "PT1H" \
                    -o none
            fi
            sub_count=$((sub_count + 1))
        done
    done

    # Adversary subscription
    local adv_exists
    adv_exists=$(az servicebus topic subscription show \
        --resource-group "${RESOURCE_GROUP}" \
        --namespace-name "${SERVICE_BUS_NS}" \
        --topic-name "hive-events" \
        --name "adversary" \
        --query name -o tsv 2>/dev/null || echo "")

    if [[ -z "${adv_exists}" ]]; then
        az servicebus topic subscription create \
            --resource-group "${RESOURCE_GROUP}" \
            --namespace-name "${SERVICE_BUS_NS}" \
            --topic-name "hive-events" \
            --name "adversary" \
            --default-message-time-to-live "PT1H" \
            -o none
    fi
    sub_count=$((sub_count + 1))

    _ok "Service Bus ready (${sub_count} subscriptions)."

    # Get connection string
    SERVICE_BUS_CONN=$(az servicebus namespace authorization-rule keys list \
        --resource-group "${RESOURCE_GROUP}" \
        --namespace-name "${SERVICE_BUS_NS}" \
        --name "RootManageSharedAccessKey" \
        --query primaryConnectionString -o tsv)

    echo
}

# ============================================================
# Step 5: Storage Account + File Share (idempotent)
# ============================================================

create_storage() {
    _info "Creating storage account '${STORAGE_ACCOUNT}'..."

    local sa_exists
    sa_exists=$(az storage account show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${STORAGE_ACCOUNT}" \
        --query name -o tsv 2>/dev/null || echo "")

    if [[ -n "${sa_exists}" ]]; then
        _ok "Storage account already exists."
    else
        az storage account create \
            --resource-group "${RESOURCE_GROUP}" \
            --name "${STORAGE_ACCOUNT}" \
            --location "${LOCATION}" \
            --sku Standard_LRS \
            --kind StorageV2 \
            -o none
        _ok "Storage account created."
    fi

    # Get storage key
    STORAGE_KEY=$(az storage account keys list \
        --resource-group "${RESOURCE_GROUP}" \
        --account-name "${STORAGE_ACCOUNT}" \
        --query "[0].value" -o tsv)

    # Create file share for agent databases (idempotent)
    _info "Creating file share '${FILE_SHARE_NAME}'..."
    local share_exists
    share_exists=$(az storage share exists \
        --account-name "${STORAGE_ACCOUNT}" \
        --account-key "${STORAGE_KEY}" \
        --name "${FILE_SHARE_NAME}" \
        --query exists -o tsv 2>/dev/null || echo "false")

    if [[ "${share_exists}" == "true" ]]; then
        _ok "File share already exists."
    else
        az storage share create \
            --account-name "${STORAGE_ACCOUNT}" \
            --account-key "${STORAGE_KEY}" \
            --name "${FILE_SHARE_NAME}" \
            --quota 10 \
            -o none
        _ok "File share created (10 GiB quota)."
    fi

    # Create per-agent subdirectories (idempotent)
    _info "Ensuring per-agent directories on file share..."
    for domain in "${DOMAINS[@]}"; do
        for suffix in 1 2; do
            local agent_id="${domain}_${suffix}"
            az storage directory create \
                --account-name "${STORAGE_ACCOUNT}" \
                --account-key "${STORAGE_KEY}" \
                --share-name "${FILE_SHARE_NAME}" \
                --name "${agent_id}" \
                -o none 2>/dev/null || true
        done
    done
    az storage directory create \
        --account-name "${STORAGE_ACCOUNT}" \
        --account-key "${STORAGE_KEY}" \
        --share-name "${FILE_SHARE_NAME}" \
        --name "adversary" \
        -o none 2>/dev/null || true

    _ok "Storage ready with per-agent directories."
    echo
}

# ============================================================
# Step 6: Container Registry (idempotent)
# ============================================================

create_acr() {
    _info "Creating Container Registry '${ACR_NAME}'..."

    local acr_exists
    acr_exists=$(az acr show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${ACR_NAME}" \
        --query name -o tsv 2>/dev/null || echo "")

    if [[ -n "${acr_exists}" ]]; then
        _ok "ACR already exists."
    else
        az acr create \
            --resource-group "${RESOURCE_GROUP}" \
            --name "${ACR_NAME}" \
            --sku Basic \
            --admin-enabled true \
            -o none
        _ok "ACR created."
    fi

    # Ensure admin is enabled (idempotent)
    az acr update --name "${ACR_NAME}" --admin-enabled true -o none 2>/dev/null || true

    ACR_LOGIN_SERVER=$(az acr show \
        --name "${ACR_NAME}" \
        --query loginServer -o tsv)
    ACR_USERNAME=$(az acr credential show \
        --name "${ACR_NAME}" \
        --query username -o tsv)
    ACR_PASSWORD=$(az acr credential show \
        --name "${ACR_NAME}" \
        --query "passwords[0].value" -o tsv)

    _ok "ACR ready: ${ACR_LOGIN_SERVER}"
    echo
}

# ============================================================
# Step 7: Build and Push Docker Image
# ============================================================

build_and_push() {
    _info "Building Docker image for hive mind agents..."

    local dockerfile="${REPO_ROOT}/experiments/hive_mind/Dockerfile.hive"
    local image_full="${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}"

    # Generate the Dockerfile if it does not already exist
    if [[ ! -f "${dockerfile}" ]]; then
        _info "Generating Dockerfile at ${dockerfile}..."
        cat > "${dockerfile}" << 'DOCKERFILE_EOF'
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install core Python dependencies
RUN pip install --no-cache-dir \
    "amplihack @ git+https://github.com/rysweet/amplihack.git" \
    "amplihack-memory-lib @ git+https://github.com/rysweet/amplihack-memory-lib.git" \
    azure-servicebus \
    kuzu \
    httpx \
    uvicorn \
    fastapi

# Copy the agent entrypoint and evaluation modules
COPY experiments/hive_mind/ /app/hive_mind/
COPY src/amplihack/agents/goal_seeking/hive_mind/ /app/hive_mind_core/

# Copy the agent runner script
COPY experiments/hive_mind/agent_runner.py /app/agent_runner.py

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

EXPOSE 8080

CMD ["python3", "/app/agent_runner.py"]
DOCKERFILE_EOF
        _ok "Dockerfile generated."
    fi

    # Generate agent_runner.py if it does not already exist
    local runner="${REPO_ROOT}/experiments/hive_mind/agent_runner.py"
    if [[ ! -f "${runner}" ]]; then
        _info "Generating agent_runner.py..."
        cat > "${runner}" << 'RUNNER_EOF'
#!/usr/bin/env python3
"""Hive Mind Agent Runner -- Container entrypoint for Azure Container Apps.

Each container runs exactly one agent. Configuration is provided via environment
variables:

    AGENT_ID              -- unique identifier (e.g. "biology_1")
    AGENT_DOMAIN          -- knowledge domain (e.g. "biology")
    SERVICE_BUS_CONN_STR  -- Azure Service Bus connection string
    DATA_DIR              -- mounted directory for the agent's Kuzu database
    ANTHROPIC_API_KEY     -- for LLM-based operations

The agent:
  1. Starts a FastAPI health/query endpoint on :8080
  2. Connects to the shared Service Bus topic for event distribution
  3. Waits for LEARN commands (facts posted to /learn via HTTP)
  4. Promotes top facts via the hive event bus
  5. Answers questions via /query HTTP endpoint
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("agent_runner")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

AGENT_ID = os.environ.get("AGENT_ID", "unknown")
AGENT_DOMAIN = os.environ.get("AGENT_DOMAIN", "general")
SERVICE_BUS_CONN_STR = os.environ.get("SERVICE_BUS_CONN_STR", "")
DATA_DIR = os.environ.get("DATA_DIR", "/data")

# ---------------------------------------------------------------------------
# Hive Mind setup (lazy -- initialized at startup)
# ---------------------------------------------------------------------------

_hive = None
_event_bus = None


def _init_hive():
    """Initialize the Kuzu hive mind and event bus connections."""
    global _hive, _event_bus

    # Import hive mind modules
    sys.path.insert(0, "/app/hive_mind_core")
    sys.path.insert(0, "/app/hive_mind")

    from kuzu_hive import KuzuHiveMind
    from event_bus import create_event_bus

    db_path = os.path.join(DATA_DIR, AGENT_ID, "hive.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    _hive = KuzuHiveMind(db_path=db_path)
    _hive.register_agent(AGENT_ID, domain=AGENT_DOMAIN)
    logger.info("Hive mind initialized: agent=%s domain=%s db=%s", AGENT_ID, AGENT_DOMAIN, db_path)

    # Connect event bus
    if SERVICE_BUS_CONN_STR:
        _event_bus = create_event_bus(
            "azure",
            connection_string=SERVICE_BUS_CONN_STR,
            topic_name="hive-events",
        )
        _event_bus.subscribe(AGENT_ID)
        logger.info("Connected to Azure Service Bus event bus")
    else:
        _event_bus = create_event_bus("local")
        _event_bus.subscribe(AGENT_ID)
        logger.info("Using local event bus (no SERVICE_BUS_CONN_STR)")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(title=f"Hive Agent: {AGENT_ID}", version="1.0.0")


class LearnRequest(BaseModel):
    concept: str
    content: str
    confidence: float = 0.9


class PromoteRequest(BaseModel):
    concept: str
    content: str
    confidence: float = 0.9


class QueryRequest(BaseModel):
    query: str
    limit: int = 10
    mode: str = "hive"  # "local" or "hive"


class FactList(BaseModel):
    facts: list[LearnRequest]


@app.get("/health")
def health():
    """Health check endpoint for Container Apps probes."""
    return {
        "status": "healthy",
        "agent_id": AGENT_ID,
        "domain": AGENT_DOMAIN,
        "hive_ready": _hive is not None,
    }


@app.post("/learn")
def learn(req: LearnRequest):
    """Store a fact in the agent's local memory."""
    if _hive is None:
        raise HTTPException(status_code=503, detail="Hive not initialized")
    _hive.store_fact(AGENT_ID, req.concept, req.content, req.confidence)
    return {"status": "stored", "agent_id": AGENT_ID, "concept": req.concept}


@app.post("/learn_batch")
def learn_batch(req: FactList):
    """Store multiple facts at once."""
    if _hive is None:
        raise HTTPException(status_code=503, detail="Hive not initialized")
    stored = 0
    for fact in req.facts:
        _hive.store_fact(AGENT_ID, fact.concept, fact.content, fact.confidence)
        stored += 1
    return {"status": "stored", "agent_id": AGENT_ID, "count": stored}


@app.post("/promote")
def promote(req: PromoteRequest):
    """Promote a fact from local to hive-level knowledge."""
    if _hive is None:
        raise HTTPException(status_code=503, detail="Hive not initialized")
    result = _hive.promote_fact(AGENT_ID, req.concept, req.content, req.confidence)
    return {"agent_id": AGENT_ID, **result}


@app.post("/query")
def query(req: QueryRequest):
    """Query agent memory (local or hive-wide)."""
    if _hive is None:
        raise HTTPException(status_code=503, detail="Hive not initialized")

    if req.mode == "local":
        results = _hive.query_local(AGENT_ID, req.query, limit=req.limit)
    else:
        results = _hive.query_all(AGENT_ID, req.query, limit=req.limit)

    return {"agent_id": AGENT_ID, "mode": req.mode, "results": results}


@app.get("/stats")
def stats():
    """Return hive statistics for this agent."""
    if _hive is None:
        raise HTTPException(status_code=503, detail="Hive not initialized")
    return {"agent_id": AGENT_ID, "stats": _hive.get_stats()}


# ---------------------------------------------------------------------------
# Event bus polling (background thread)
# ---------------------------------------------------------------------------


def _poll_events():
    """Background thread: poll Service Bus for incoming hive events."""
    if _event_bus is None:
        return
    logger.info("Event polling thread started for agent %s", AGENT_ID)
    while True:
        try:
            events = _event_bus.poll(AGENT_ID)
            for event in events:
                logger.info(
                    "Received event: type=%s from=%s",
                    event.event_type,
                    event.source_agent,
                )
                if event.event_type == "FACT_PROMOTED":
                    payload = event.payload
                    _hive.store_fact(
                        AGENT_ID,
                        payload.get("concept", "shared"),
                        payload.get("content", ""),
                        payload.get("confidence", 0.5),
                    )
        except Exception:
            logger.exception("Error polling events")
        time.sleep(2)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("Starting hive agent: id=%s domain=%s", AGENT_ID, AGENT_DOMAIN)
    _init_hive()

    # Start event polling in background
    poll_thread = threading.Thread(target=_poll_events, daemon=True, name="event-poll")
    poll_thread.start()

    # Run HTTP server
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
RUNNER_EOF
        _ok "agent_runner.py generated."
    fi

    # Login and build
    az acr login --name "${ACR_NAME}"
    docker build -t "${image_full}" -f "${dockerfile}" "${REPO_ROOT}"
    docker push "${image_full}"

    # Tag as latest for convenience
    if [[ "${IMAGE_TAG}" != "latest" ]]; then
        docker tag "${image_full}" "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest"
        docker push "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest"
    fi

    _ok "Image pushed: ${image_full}"
    echo
}

# ============================================================
# Step 8: Container Apps Environment (idempotent)
# ============================================================

create_container_env() {
    _info "Creating Container Apps Environment '${CONTAINER_ENV_NAME}'..."

    local env_exists
    env_exists=$(az containerapp env show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${CONTAINER_ENV_NAME}" \
        --query name -o tsv 2>/dev/null || echo "")

    if [[ -n "${env_exists}" ]]; then
        _ok "Container Apps Environment already exists."
    else
        az containerapp env create \
            --resource-group "${RESOURCE_GROUP}" \
            --name "${CONTAINER_ENV_NAME}" \
            --location "${LOCATION}" \
            --logs-workspace-id "${LOG_WORKSPACE_ID}" \
            --logs-workspace-key "${LOG_WORKSPACE_KEY}" \
            -o none
        _ok "Container Apps Environment created."
    fi

    # Add Azure Files storage to the environment (idempotent)
    _info "Configuring Azure Files storage mount..."
    az containerapp env storage set \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${CONTAINER_ENV_NAME}" \
        --storage-name "agentdata" \
        --azure-file-account-name "${STORAGE_ACCOUNT}" \
        --azure-file-account-key "${STORAGE_KEY}" \
        --azure-file-share-name "${FILE_SHARE_NAME}" \
        --access-mode ReadWrite \
        -o none 2>/dev/null || true

    _ok "Container Apps Environment ready with storage mount."
    echo
}

# ============================================================
# Step 9: Deploy Agent Container Apps
# ============================================================

deploy_single_agent() {
    local agent_id="$1"
    local agent_domain="$2"
    local app_name="hive-agent-${agent_id//_/-}"  # underscores to hyphens for Azure
    local image_full="${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}"

    local app_exists
    app_exists=$(az containerapp show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${app_name}" \
        --query name -o tsv 2>/dev/null || echo "")

    if [[ -n "${app_exists}" ]]; then
        # Update existing container app with latest image and env vars
        az containerapp update \
            --resource-group "${RESOURCE_GROUP}" \
            --name "${app_name}" \
            --image "${image_full}" \
            --set-env-vars \
                "AGENT_ID=${agent_id}" \
                "AGENT_DOMAIN=${agent_domain}" \
                "SERVICE_BUS_CONN_STR=${SERVICE_BUS_CONN}" \
                "DATA_DIR=/mnt/agentdata" \
                "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}" \
            -o none 2>/dev/null || true
        _ok "  Updated: ${app_name}"
    else
        az containerapp create \
            --resource-group "${RESOURCE_GROUP}" \
            --name "${app_name}" \
            --environment "${CONTAINER_ENV_NAME}" \
            --image "${image_full}" \
            --registry-server "${ACR_LOGIN_SERVER}" \
            --registry-username "${ACR_USERNAME}" \
            --registry-password "${ACR_PASSWORD}" \
            --target-port 8080 \
            --ingress internal \
            --min-replicas 1 \
            --max-replicas 1 \
            --cpu 0.5 \
            --memory 1.0Gi \
            --env-vars \
                "AGENT_ID=${agent_id}" \
                "AGENT_DOMAIN=${agent_domain}" \
                "SERVICE_BUS_CONN_STR=${SERVICE_BUS_CONN}" \
                "DATA_DIR=/mnt/agentdata" \
                "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}" \
            -o none
        _ok "  Created: ${app_name}"
    fi
}

deploy_agents() {
    _info "Deploying ${AGENT_COUNT} domain agents + 1 adversary..."

    local deployed=0
    for domain in "${DOMAINS[@]}"; do
        for suffix in 1 2; do
            local agent_id="${domain}_${suffix}"
            deploy_single_agent "${agent_id}" "${domain}"
            deployed=$((deployed + 1))
            _info "  Progress: ${deployed}/$((AGENT_COUNT + 1))"
        done
    done

    # Adversary agent
    deploy_single_agent "adversary" "adversary"
    deployed=$((deployed + 1))

    _ok "All ${deployed} agent containers deployed."
    echo
}

# ============================================================
# Step 10: Wait for Agents to be Ready
# ============================================================

wait_for_agents() {
    _info "Waiting for all agents to become healthy..."

    local max_attempts=40
    local all_ready=false

    for attempt in $(seq 1 ${max_attempts}); do
        local ready_count=0
        local total=0

        for domain in "${DOMAINS[@]}"; do
            for suffix in 1 2; do
                total=$((total + 1))
                local app_name="hive-agent-${domain}-${suffix}"
                local status
                status=$(az containerapp show \
                    --resource-group "${RESOURCE_GROUP}" \
                    --name "${app_name}" \
                    --query "properties.runningStatus" -o tsv 2>/dev/null || echo "Unknown")
                if [[ "${status}" == "Running" ]]; then
                    ready_count=$((ready_count + 1))
                fi
            done
        done

        # Adversary
        total=$((total + 1))
        local adv_status
        adv_status=$(az containerapp show \
            --resource-group "${RESOURCE_GROUP}" \
            --name "hive-agent-adversary" \
            --query "properties.runningStatus" -o tsv 2>/dev/null || echo "Unknown")
        if [[ "${adv_status}" == "Running" ]]; then
            ready_count=$((ready_count + 1))
        fi

        _info "  Attempt ${attempt}/${max_attempts}: ${ready_count}/${total} agents running"

        if [[ ${ready_count} -eq ${total} ]]; then
            all_ready=true
            break
        fi
        sleep 15
    done

    if [[ "${all_ready}" == "true" ]]; then
        _ok "All agents are running."
    else
        _warn "Not all agents are running. Proceeding anyway -- some agents may still be starting."
    fi
    echo
}

# ============================================================
# Step 11: Run Evaluation
# ============================================================

run_eval() {
    _info "Running hive mind evaluation against deployed agents..."

    # Collect FQDNs for all agent apps
    declare -A AGENT_URLS

    for domain in "${DOMAINS[@]}"; do
        for suffix in 1 2; do
            local agent_id="${domain}_${suffix}"
            local app_name="hive-agent-${domain}-${suffix}"
            local fqdn
            fqdn=$(az containerapp show \
                --resource-group "${RESOURCE_GROUP}" \
                --name "${app_name}" \
                --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
            if [[ -n "${fqdn}" ]]; then
                AGENT_URLS["${agent_id}"]="https://${fqdn}"
            else
                _warn "No FQDN for ${app_name} -- skipping"
            fi
        done
    done

    # Adversary
    local adv_fqdn
    adv_fqdn=$(az containerapp show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "hive-agent-adversary" \
        --query "properties.configuration.ingress.fqdn" -o tsv 2>/dev/null || echo "")
    if [[ -n "${adv_fqdn}" ]]; then
        AGENT_URLS["adversary"]="https://${adv_fqdn}"
    fi

    local agent_count=${#AGENT_URLS[@]}
    _info "Found ${agent_count} agent endpoints."

    if [[ ${agent_count} -eq 0 ]]; then
        _err "No agent endpoints found. Ensure agents are deployed with ingress enabled."
        exit 1
    fi

    # Phase 1: Health check all agents
    _info "Phase 1: Health checks..."
    local healthy=0
    for agent_id in "${!AGENT_URLS[@]}"; do
        local url="${AGENT_URLS[${agent_id}]}/health"
        local status
        status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${url}" 2>/dev/null || echo "000")
        if [[ "${status}" == "200" ]]; then
            healthy=$((healthy + 1))
        else
            _warn "  ${agent_id}: unhealthy (HTTP ${status})"
        fi
    done
    _ok "  ${healthy}/${agent_count} agents healthy."

    # Phase 2: Send learning content to each domain agent
    _info "Phase 2: Teaching agents their domain facts..."
    # Use the domain facts from the eval script as a reference.
    # For the deployment eval, we send a subset (5 facts per agent) via HTTP.
    for agent_id in "${!AGENT_URLS[@]}"; do
        if [[ "${agent_id}" == "adversary" ]]; then
            continue
        fi
        local url="${AGENT_URLS[${agent_id}]}/learn"
        local domain
        domain=$(echo "${agent_id}" | sed 's/_[0-9]*$//')

        # Send a representative fact for the domain
        curl -s -X POST "${url}" \
            -H "Content-Type: application/json" \
            -d "{\"concept\": \"${domain}\", \"content\": \"Representative ${domain} knowledge for agent ${agent_id}\", \"confidence\": 0.95}" \
            --max-time 10 >/dev/null 2>&1 || true
    done
    _ok "  Learning content distributed."

    # Phase 3: Promote facts
    _info "Phase 3: Promoting facts via hive..."
    for agent_id in "${!AGENT_URLS[@]}"; do
        if [[ "${agent_id}" == "adversary" ]]; then
            continue
        fi
        local url="${AGENT_URLS[${agent_id}]}/promote"
        local domain
        domain=$(echo "${agent_id}" | sed 's/_[0-9]*$//')

        curl -s -X POST "${url}" \
            -H "Content-Type: application/json" \
            -d "{\"concept\": \"${domain}\", \"content\": \"Representative ${domain} knowledge for agent ${agent_id}\", \"confidence\": 0.95}" \
            --max-time 10 >/dev/null 2>&1 || true
    done
    _ok "  Facts promoted."

    # Phase 4: Wait for propagation
    _info "Phase 4: Waiting 30s for Service Bus propagation..."
    sleep 30

    # Phase 5: Cross-domain queries
    _info "Phase 5: Cross-domain query evaluation..."
    local queries_total=0
    local queries_passed=0

    # Query biology agent about chemistry (cross-domain)
    local bio_url="${AGENT_URLS[biology_1]:-}"
    if [[ -n "${bio_url}" ]]; then
        local resp
        resp=$(curl -s -X POST "${bio_url}/query" \
            -H "Content-Type: application/json" \
            -d '{"query": "What do you know about chemistry?", "limit": 5, "mode": "hive"}' \
            --max-time 15 2>/dev/null || echo '{"results":[]}')
        queries_total=$((queries_total + 1))
        local result_count
        result_count=$(echo "${resp}" | jq '.results | length' 2>/dev/null || echo "0")
        if [[ "${result_count}" -gt 0 ]]; then
            queries_passed=$((queries_passed + 1))
            _ok "  biology_1 -> chemistry: ${result_count} results (PASS)"
        else
            _warn "  biology_1 -> chemistry: 0 results (FAIL)"
        fi
    fi

    # Query economics agent about physics (cross-domain)
    local econ_url="${AGENT_URLS[economics_1]:-}"
    if [[ -n "${econ_url}" ]]; then
        local resp
        resp=$(curl -s -X POST "${econ_url}/query" \
            -H "Content-Type: application/json" \
            -d '{"query": "What do you know about physics?", "limit": 5, "mode": "hive"}' \
            --max-time 15 2>/dev/null || echo '{"results":[]}')
        queries_total=$((queries_total + 1))
        local result_count
        result_count=$(echo "${resp}" | jq '.results | length' 2>/dev/null || echo "0")
        if [[ "${result_count}" -gt 0 ]]; then
            queries_passed=$((queries_passed + 1))
            _ok "  economics_1 -> physics: ${result_count} results (PASS)"
        else
            _warn "  economics_1 -> physics: 0 results (FAIL)"
        fi
    fi

    # Self-domain query (should always work)
    local chem_url="${AGENT_URLS[chemistry_1]:-}"
    if [[ -n "${chem_url}" ]]; then
        local resp
        resp=$(curl -s -X POST "${chem_url}/query" \
            -H "Content-Type: application/json" \
            -d '{"query": "What do you know about chemistry?", "limit": 5, "mode": "local"}' \
            --max-time 15 2>/dev/null || echo '{"results":[]}')
        queries_total=$((queries_total + 1))
        local result_count
        result_count=$(echo "${resp}" | jq '.results | length' 2>/dev/null || echo "0")
        if [[ "${result_count}" -gt 0 ]]; then
            queries_passed=$((queries_passed + 1))
            _ok "  chemistry_1 -> chemistry (local): ${result_count} results (PASS)"
        else
            _warn "  chemistry_1 -> chemistry (local): 0 results (FAIL)"
        fi
    fi

    # Phase 6: Collect stats
    _info "Phase 6: Collecting agent statistics..."
    for agent_id in "${!AGENT_URLS[@]}"; do
        local url="${AGENT_URLS[${agent_id}]}/stats"
        local stats_resp
        stats_resp=$(curl -s --max-time 10 "${url}" 2>/dev/null || echo '{}')
        local local_facts
        local_facts=$(echo "${stats_resp}" | jq '.stats.total_local_facts // 0' 2>/dev/null || echo "0")
        local hive_facts
        hive_facts=$(echo "${stats_resp}" | jq '.stats.total_hive_facts // 0' 2>/dev/null || echo "0")
        echo "  ${agent_id}: local=${local_facts} hive=${hive_facts}"
    done

    # Summary
    echo
    echo "========================================"
    echo "  EVALUATION SUMMARY"
    echo "========================================"
    echo "  Agents deployed:    ${agent_count}"
    echo "  Agents healthy:     ${healthy}/${agent_count}"
    echo "  Queries tested:     ${queries_total}"
    echo "  Queries passed:     ${queries_passed}/${queries_total}"
    echo "  Resource group:     ${RESOURCE_GROUP}"
    echo "  Service Bus:        ${SERVICE_BUS_NS}"
    echo "  Storage Account:    ${STORAGE_ACCOUNT}"
    echo "  Container Registry: ${ACR_NAME}"
    echo "========================================"
    echo
}

# ============================================================
# Step 12: Show Status
# ============================================================

show_status() {
    _info "Deployment status for '${RESOURCE_GROUP}'..."

    # Check resource group
    local rg_exists
    rg_exists=$(az group exists --name "${RESOURCE_GROUP}" 2>/dev/null || echo "false")
    if [[ "${rg_exists}" != "true" ]]; then
        _warn "Resource group '${RESOURCE_GROUP}' does not exist."
        return
    fi

    echo
    echo "=== Resource Group ==="
    az group show --name "${RESOURCE_GROUP}" --query "{name:name, location:location, provisioningState:properties.provisioningState}" -o table 2>/dev/null || true

    echo
    echo "=== Container Apps ==="
    az containerapp list --resource-group "${RESOURCE_GROUP}" \
        --query "[].{Name:name, Status:properties.runningStatus, Image:properties.template.containers[0].image}" \
        -o table 2>/dev/null || echo "  No container apps found."

    echo
    echo "=== Service Bus ==="
    az servicebus namespace show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${SERVICE_BUS_NS}" \
        --query "{name:name, status:status, sku:sku.name}" \
        -o table 2>/dev/null || echo "  No Service Bus namespace found."

    echo
    echo "=== Container Registry ==="
    az acr show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${ACR_NAME}" \
        --query "{name:name, loginServer:loginServer, sku:sku.name}" \
        -o table 2>/dev/null || echo "  No ACR found."

    echo
    echo "=== Storage ==="
    az storage account show \
        --resource-group "${RESOURCE_GROUP}" \
        --name "${STORAGE_ACCOUNT}" \
        --query "{name:name, kind:kind, sku:sku.name}" \
        -o table 2>/dev/null || echo "  No storage account found."

    echo
}

# ============================================================
# Step 13: Cleanup (--cleanup flag)
# ============================================================

cleanup() {
    _warn "This will DELETE the entire resource group '${RESOURCE_GROUP}' and ALL its resources."
    _warn "Resources: Container Apps, Service Bus, Storage Account, ACR, Log Analytics"
    echo

    read -r -p "Type 'yes' to confirm deletion: " confirm
    if [[ "${confirm}" != "yes" ]]; then
        _info "Cleanup cancelled."
        return
    fi

    _info "Deleting resource group '${RESOURCE_GROUP}'..."
    az group delete \
        --name "${RESOURCE_GROUP}" \
        --yes \
        --no-wait

    _ok "Resource group deletion initiated (runs in background)."
    _info "Monitor with: az group show --name '${RESOURCE_GROUP}' --query provisioningState -o tsv"

    # Clean up generated files
    local dockerfile="${REPO_ROOT}/experiments/hive_mind/Dockerfile.hive"
    local runner="${REPO_ROOT}/experiments/hive_mind/agent_runner.py"
    if [[ -f "${dockerfile}" ]]; then
        rm -f "${dockerfile}"
        _ok "Removed ${dockerfile}"
    fi
    if [[ -f "${runner}" ]]; then
        rm -f "${runner}"
        _ok "Removed ${runner}"
    fi

    echo
    _ok "Cleanup complete."
}

# ============================================================
# Main: parse flags and execute
# ============================================================

main() {
    echo "============================================================"
    echo "  Hive Mind Azure Deployment"
    echo "============================================================"
    echo "  Resource Group:     ${RESOURCE_GROUP}"
    echo "  Location:           ${LOCATION}"
    echo "  Domain Agents:      ${AGENT_COUNT}"
    echo "  ACR Name:           ${ACR_NAME}"
    echo "  Service Bus NS:     ${SERVICE_BUS_NS}"
    echo "  Storage Account:    ${STORAGE_ACCOUNT}"
    echo "============================================================"
    echo

    local action="${1:-deploy}"

    case "${action}" in
        --eval|-e)
            check_prereqs
            # Load Service Bus connection string
            SERVICE_BUS_CONN=$(az servicebus namespace authorization-rule keys list \
                --resource-group "${RESOURCE_GROUP}" \
                --namespace-name "${SERVICE_BUS_NS}" \
                --name "RootManageSharedAccessKey" \
                --query primaryConnectionString -o tsv 2>/dev/null || echo "")
            run_eval
            ;;
        --cleanup|-c)
            cleanup
            ;;
        --status|-s)
            show_status
            ;;
        deploy|--deploy|-d)
            check_prereqs
            create_resource_group
            create_log_analytics
            create_service_bus
            create_storage
            create_acr
            build_and_push
            create_container_env
            deploy_agents
            wait_for_agents
            echo "============================================================"
            echo "  DEPLOYMENT COMPLETE"
            echo "============================================================"
            echo
            echo "  Run evaluation:"
            echo "    bash experiments/hive_mind/deploy_azure_hive.sh --eval"
            echo
            echo "  Check status:"
            echo "    bash experiments/hive_mind/deploy_azure_hive.sh --status"
            echo
            echo "  Cleanup (delete all resources):"
            echo "    bash experiments/hive_mind/deploy_azure_hive.sh --cleanup"
            echo
            ;;
        *)
            echo "Usage: bash experiments/hive_mind/deploy_azure_hive.sh [--deploy|--eval|--status|--cleanup]"
            echo
            echo "  --deploy, -d   Provision infra and deploy agents (default)"
            echo "  --eval, -e     Run evaluation against deployed agents"
            echo "  --status, -s   Show deployment status"
            echo "  --cleanup, -c  Delete all resources"
            exit 1
            ;;
    esac
}

main "$@"
