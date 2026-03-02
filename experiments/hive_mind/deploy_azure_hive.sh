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
            --allow-blob-public-access false \
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

    # Always regenerate the Dockerfile to pick up changes
    if true; then
        _info "Generating Dockerfile at ${dockerfile}..."
        cat > "${dockerfile}" << 'DOCKERFILE_EOF'
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install core Python dependencies
# Install from feature branch which includes hive_mind modules
RUN pip install --no-cache-dir \
    "amplihack @ git+https://github.com/rysweet/amplihack.git@feat/hive-mind-experiments" \
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

    # Always regenerate agent_runner.py to pick up changes
    local runner="${REPO_ROOT}/experiments/hive_mind/agent_runner.py"
    if true; then
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
    """Initialize the hive graph and event bus connections."""
    global _hive, _event_bus

    sys.path.insert(0, "/app/hive_mind_core")
    sys.path.insert(0, "/app")
    from hive_graph import InMemoryHiveGraph
    from event_bus import create_event_bus

    _hive = InMemoryHiveGraph(hive_id=f"hive-{AGENT_ID}")
    _hive.register_agent(AGENT_ID, domain=AGENT_DOMAIN)
    logger.info("Hive initialized: agent=%s domain=%s", AGENT_ID, AGENT_DOMAIN)

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


def _publish_fact(content: str, concept: str, confidence: float) -> None:
    """Publish a FACT_PROMOTED event to the event bus so all agents receive it."""
    if _event_bus is None:
        return
    import uuid as _uuid
    from event_bus import BusEvent
    evt = BusEvent(
        event_id=_uuid.uuid4().hex,
        event_type="FACT_PROMOTED",
        source_agent=AGENT_ID,
        timestamp=time.time(),
        payload={"content": content, "concept": concept, "confidence": confidence},
    )
    try:
        _event_bus.publish(evt)
    except Exception:
        logger.exception("Failed to publish FACT_PROMOTED event")


@app.post("/learn")
def learn(req: LearnRequest):
    """Store a fact locally and publish to event bus for distribution."""
    if _hive is None:
        raise HTTPException(status_code=503, detail="Hive not initialized")
    from hive_graph import HiveFact
    fid = _hive.promote_fact(AGENT_ID, HiveFact(
        fact_id="", content=req.content, concept=req.concept,
        confidence=req.confidence,
    ))
    _publish_fact(req.content, req.concept, req.confidence)
    return {"status": "stored", "agent_id": AGENT_ID, "concept": req.concept, "fact_id": fid}


@app.post("/learn_batch")
def learn_batch(req: FactList):
    """Store multiple facts and publish each to the event bus."""
    if _hive is None:
        raise HTTPException(status_code=503, detail="Hive not initialized")
    from hive_graph import HiveFact
    stored = 0
    for fact in req.facts:
        _hive.promote_fact(AGENT_ID, HiveFact(
            fact_id="", content=fact.content, concept=fact.concept,
            confidence=fact.confidence,
        ))
        _publish_fact(fact.content, fact.concept, fact.confidence)
        stored += 1
    return {"status": "stored", "agent_id": AGENT_ID, "count": stored}


@app.post("/promote")
def promote(req: PromoteRequest):
    """Promote a fact and publish to event bus."""
    if _hive is None:
        raise HTTPException(status_code=503, detail="Hive not initialized")
    from hive_graph import HiveFact
    fid = _hive.promote_fact(AGENT_ID, HiveFact(
        fact_id="", content=req.content, concept=req.concept,
        confidence=req.confidence,
    ))
    _publish_fact(req.content, req.concept, req.confidence)
    return {"agent_id": AGENT_ID, "fact_id": fid, "status": "promoted"}


@app.post("/query")
def query(req: QueryRequest):
    """Query agent memory (local facts + facts received via event bus)."""
    if _hive is None:
        raise HTTPException(status_code=503, detail="Hive not initialized")

    results = _hive.query_facts(req.query, limit=req.limit)
    return {
        "agent_id": AGENT_ID,
        "mode": req.mode,
        "results": [
            {"content": f.content, "concept": f.concept, "confidence": f.confidence}
            for f in results
        ],
    }


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
                    from hive_graph import HiveFact
                    payload = event.payload
                    _hive.promote_fact(AGENT_ID, HiveFact(
                        fact_id="",
                        content=payload.get("content", ""),
                        concept=payload.get("concept", "shared"),
                        confidence=payload.get("confidence", 0.5),
                    ))
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
            --ingress external \
            --min-replicas 1 \
            --max-replicas 1 \
            --cpu 2.0 \
            --memory 4.0Gi \
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

    # Phase 2: Send domain-specific facts to each agent
    _info "Phase 2: Teaching agents domain-specific facts..."
    local facts_sent=0

    # Domain facts: 5 keyword-rich facts per domain (matched to DOMAINS array)
    declare -A DOMAIN_FACTS
    DOMAIN_FACTS[biology]='[
      {"concept":"genetics","content":"DNA double helix stores genetic information in nucleotide base pairs","confidence":0.95},
      {"concept":"evolution","content":"Natural selection drives evolution through survival of the fittest organisms","confidence":0.9},
      {"concept":"cells","content":"Mitochondria are the powerhouse organelles producing ATP energy in cells","confidence":0.92},
      {"concept":"ecology","content":"Photosynthesis converts sunlight carbon dioxide and water into glucose oxygen","confidence":0.88},
      {"concept":"anatomy","content":"The human brain contains approximately 86 billion neurons connected by synapses","confidence":0.91}
    ]'
    DOMAIN_FACTS[chemistry]='[
      {"concept":"reactions","content":"Chemical reactions involve breaking and forming molecular bonds between atoms","confidence":0.93},
      {"concept":"periodic_table","content":"The periodic table organizes elements by atomic number and electron configuration","confidence":0.95},
      {"concept":"organic","content":"Organic chemistry studies carbon compounds including hydrocarbons and polymers","confidence":0.9},
      {"concept":"acids","content":"pH scale measures hydrogen ion concentration from acidic to basic alkaline solutions","confidence":0.88},
      {"concept":"thermodynamics","content":"Exothermic reactions release heat energy while endothermic reactions absorb heat","confidence":0.91}
    ]'
    DOMAIN_FACTS[physics]='[
      {"concept":"mechanics","content":"Newton laws of motion describe force mass acceleration relationships in classical mechanics","confidence":0.95},
      {"concept":"relativity","content":"Einstein special relativity shows energy equals mass times speed of light squared","confidence":0.94},
      {"concept":"quantum","content":"Quantum mechanics describes particle wave duality and uncertainty at atomic scale","confidence":0.92},
      {"concept":"thermodynamics","content":"Entropy always increases in isolated systems according to second law thermodynamics","confidence":0.9},
      {"concept":"electromagnetism","content":"Maxwell equations unify electric magnetic fields into electromagnetic radiation waves","confidence":0.93}
    ]'
    DOMAIN_FACTS[math]='[
      {"concept":"calculus","content":"Calculus derivatives measure instantaneous rate of change of continuous functions","confidence":0.95},
      {"concept":"algebra","content":"Linear algebra studies vector spaces matrices and linear transformations","confidence":0.93},
      {"concept":"statistics","content":"Bayes theorem calculates conditional probability using prior likelihood evidence","confidence":0.91},
      {"concept":"geometry","content":"Pythagorean theorem states hypotenuse squared equals sum of other sides squared","confidence":0.94},
      {"concept":"topology","content":"Topology studies geometric properties preserved under continuous deformation stretching","confidence":0.88}
    ]'
    DOMAIN_FACTS[compsci]='[
      {"concept":"algorithms","content":"Binary search algorithm finds elements in sorted arrays with logarithmic time complexity","confidence":0.95},
      {"concept":"databases","content":"SQL relational databases use tables indexes joins for structured data storage queries","confidence":0.93},
      {"concept":"networking","content":"TCP protocol ensures reliable ordered delivery of data packets across networks","confidence":0.91},
      {"concept":"security","content":"Public key cryptography uses asymmetric encryption with RSA or elliptic curves","confidence":0.92},
      {"concept":"ai","content":"Neural networks learn patterns through backpropagation gradient descent optimization","confidence":0.9}
    ]'
    DOMAIN_FACTS[history]='[
      {"concept":"ancient","content":"Ancient Rome republic expanded into vast empire spanning Mediterranean Europe Africa","confidence":0.92},
      {"concept":"medieval","content":"Medieval feudal system organized society into lords vassals serfs on agricultural estates","confidence":0.9},
      {"concept":"renaissance","content":"Renaissance period revived classical Greek Roman art science philosophy in Europe","confidence":0.91},
      {"concept":"industrial","content":"Industrial revolution transformed manufacturing with steam engines factories mass production","confidence":0.93},
      {"concept":"modern","content":"World War Two reshaped global politics creating United Nations and Cold War era","confidence":0.94}
    ]'
    DOMAIN_FACTS[geography]='[
      {"concept":"continents","content":"Seven continents are Africa Antarctica Asia Australia Europe North South America","confidence":0.95},
      {"concept":"oceans","content":"Pacific Ocean is largest deepest ocean covering more area than all land combined","confidence":0.93},
      {"concept":"climate","content":"Climate zones range from tropical equatorial to polar arctic based on latitude temperature","confidence":0.91},
      {"concept":"tectonics","content":"Tectonic plates float on mantle causing earthquakes volcanoes mountain formation","confidence":0.92},
      {"concept":"rivers","content":"Amazon River carries most water volume while Nile is longest river in Africa","confidence":0.9}
    ]'
    DOMAIN_FACTS[economics]='[
      {"concept":"markets","content":"Supply and demand curves determine equilibrium price quantity in competitive markets","confidence":0.94},
      {"concept":"macro","content":"GDP measures total economic output of goods services produced in a country annually","confidence":0.93},
      {"concept":"monetary","content":"Central banks control money supply interest rates to manage inflation unemployment","confidence":0.92},
      {"concept":"trade","content":"Comparative advantage theory explains why nations benefit from international trade specialization","confidence":0.9},
      {"concept":"finance","content":"Stock markets enable trading equity shares providing capital to businesses and returns to investors","confidence":0.91}
    ]'
    DOMAIN_FACTS[psychology]='[
      {"concept":"cognitive","content":"Cognitive psychology studies mental processes including memory attention perception reasoning","confidence":0.93},
      {"concept":"behavioral","content":"Classical conditioning associates neutral stimulus with response as Pavlov demonstrated with dogs","confidence":0.91},
      {"concept":"developmental","content":"Piaget stages describe cognitive development from sensorimotor to formal operational thinking","confidence":0.9},
      {"concept":"social","content":"Social psychology examines how group dynamics conformity and persuasion influence behavior","confidence":0.92},
      {"concept":"clinical","content":"Cognitive behavioral therapy treats depression anxiety by changing negative thought patterns","confidence":0.91}
    ]'
    DOMAIN_FACTS[engineering]='[
      {"concept":"structural","content":"Civil engineering designs bridges buildings using steel concrete to withstand loads forces","confidence":0.93},
      {"concept":"electrical","content":"Electrical circuits use resistors capacitors transistors to control current voltage signals","confidence":0.92},
      {"concept":"mechanical","content":"Mechanical engineering applies thermodynamics fluid mechanics to design engines machines","confidence":0.91},
      {"concept":"software","content":"Software engineering follows agile waterfall methodologies for development testing deployment","confidence":0.9},
      {"concept":"materials","content":"Materials science studies properties of metals ceramics polymers composites for engineering applications","confidence":0.92}
    ]'

    for agent_id in "${!AGENT_URLS[@]}"; do
        if [[ "${agent_id}" == "adversary" ]]; then
            continue
        fi
        local url="${AGENT_URLS[${agent_id}]}/learn_batch"
        local domain
        domain=$(echo "${agent_id}" | sed 's/_[0-9]*$//')

        local facts_json="${DOMAIN_FACTS[${domain}]:-}"
        if [[ -z "${facts_json}" ]]; then
            continue
        fi

        local resp
        resp=$(curl -s -X POST "${url}" \
            -H "Content-Type: application/json" \
            -d "{\"facts\": ${facts_json}}" \
            --max-time 15 2>/dev/null || echo '{"count":0}')
        local count
        count=$(echo "${resp}" | jq '.count // 0' 2>/dev/null || echo "0")
        facts_sent=$((facts_sent + count))
    done
    _ok "  ${facts_sent} facts distributed across agents."

    # Phase 3: No separate promote needed — learn stores directly in hive
    _info "Phase 3: Facts already stored in each agent's hive (InMemoryHiveGraph)."
    _ok "  Skipping separate promote step (learn == promote for InMemoryHiveGraph)."

    # Phase 4: No propagation wait needed — each agent has its own local hive
    # Cross-domain queries test the Service Bus event propagation indirectly
    _info "Phase 4: No propagation delay needed (in-process hive graphs)."

    # Phase 5: Comprehensive query evaluation
    _info "Phase 5: Running evaluation queries..."
    local queries_total=0
    local queries_passed=0
    local results_json="[]"

    # --- Self-domain queries (should always pass) ---
    _info "  Category: Self-domain retrieval..."
    declare -A SELF_QUERIES
    SELF_QUERIES[biology_1]="DNA genetics nucleotide"
    SELF_QUERIES[chemistry_1]="chemical reactions molecular bonds"
    SELF_QUERIES[physics_1]="Newton force mass acceleration"
    SELF_QUERIES[math_1]="calculus derivatives functions"
    SELF_QUERIES[compsci_1]="algorithm binary search sorted"
    SELF_QUERIES[history_1]="ancient Rome republic empire"
    SELF_QUERIES[geography_1]="continents Africa Asia Europe"
    SELF_QUERIES[economics_1]="supply demand price market"
    SELF_QUERIES[psychology_1]="cognitive memory attention"
    SELF_QUERIES[engineering_1]="structural bridges buildings steel"

    for agent_id in "${!SELF_QUERIES[@]}"; do
        local url="${AGENT_URLS[${agent_id}]:-}"
        if [[ -z "${url}" ]]; then continue; fi
        local query="${SELF_QUERIES[${agent_id}]}"
        local resp
        resp=$(curl -s -X POST "${url}/query" \
            -H "Content-Type: application/json" \
            -d "{\"query\": \"${query}\", \"limit\": 5}" \
            --max-time 15 2>/dev/null || echo '{"results":[]}')
        queries_total=$((queries_total + 1))
        local result_count
        result_count=$(echo "${resp}" | jq '.results | length' 2>/dev/null || echo "0")
        local domain
        domain=$(echo "${agent_id}" | sed 's/_[0-9]*$//')
        if [[ "${result_count}" -gt 0 ]]; then
            queries_passed=$((queries_passed + 1))
            _ok "    ${agent_id} self-query (${domain}): ${result_count} results"
        else
            _warn "    ${agent_id} self-query (${domain}): 0 results (FAIL)"
        fi
        results_json=$(echo "${results_json}" | jq ". + [{\"agent\": \"${agent_id}\", \"type\": \"self\", \"domain\": \"${domain}\", \"query\": \"${query}\", \"results\": ${result_count}}]")
    done

    # --- Cross-domain queries (test if any propagation happened) ---
    _info "  Category: Cross-domain retrieval..."
    declare -A CROSS_QUERIES
    # Query agent about a DIFFERENT domain's facts
    CROSS_QUERIES[biology_1]="chemical reactions bonds atoms"
    CROSS_QUERIES[chemistry_1]="Newton force acceleration physics"
    CROSS_QUERIES[physics_1]="DNA genetics biology cells"
    CROSS_QUERIES[math_1]="algorithm database SQL networking"
    CROSS_QUERIES[economics_1]="quantum mechanics particle wave"

    for agent_id in "${!CROSS_QUERIES[@]}"; do
        local url="${AGENT_URLS[${agent_id}]:-}"
        if [[ -z "${url}" ]]; then continue; fi
        local query="${CROSS_QUERIES[${agent_id}]}"
        local resp
        resp=$(curl -s -X POST "${url}/query" \
            -H "Content-Type: application/json" \
            -d "{\"query\": \"${query}\", \"limit\": 5}" \
            --max-time 15 2>/dev/null || echo '{"results":[]}')
        queries_total=$((queries_total + 1))
        local result_count
        result_count=$(echo "${resp}" | jq '.results | length' 2>/dev/null || echo "0")
        local domain
        domain=$(echo "${agent_id}" | sed 's/_[0-9]*$//')
        if [[ "${result_count}" -gt 0 ]]; then
            queries_passed=$((queries_passed + 1))
            _ok "    ${agent_id} cross-query: ${result_count} results"
        else
            _info "    ${agent_id} cross-query: 0 results (expected — isolated hives)"
        fi
        results_json=$(echo "${results_json}" | jq ". + [{\"agent\": \"${agent_id}\", \"type\": \"cross\", \"domain\": \"${domain}\", \"query\": \"${query}\", \"results\": ${result_count}}]")
    done

    # --- Needle-in-haystack queries (specific fact retrieval) ---
    _info "  Category: Needle-in-haystack precision..."
    declare -A NEEDLE_QUERIES
    NEEDLE_QUERIES[biology_1]="mitochondria ATP energy powerhouse"
    NEEDLE_QUERIES[physics_1]="Einstein relativity energy mass light"
    NEEDLE_QUERIES[compsci_1]="TCP reliable ordered packets network"

    for agent_id in "${!NEEDLE_QUERIES[@]}"; do
        local url="${AGENT_URLS[${agent_id}]:-}"
        if [[ -z "${url}" ]]; then continue; fi
        local query="${NEEDLE_QUERIES[${agent_id}]}"
        local resp
        resp=$(curl -s -X POST "${url}/query" \
            -H "Content-Type: application/json" \
            -d "{\"query\": \"${query}\", \"limit\": 3}" \
            --max-time 15 2>/dev/null || echo '{"results":[]}')
        queries_total=$((queries_total + 1))
        local result_count
        result_count=$(echo "${resp}" | jq '.results | length' 2>/dev/null || echo "0")
        # Check if the specific target fact is in results
        local found_needle="false"
        if echo "${resp}" | jq -r '.results[].content' 2>/dev/null | grep -qi "mitochondria\|einstein\|TCP"; then
            found_needle="true"
        fi
        if [[ "${found_needle}" == "true" ]]; then
            queries_passed=$((queries_passed + 1))
            _ok "    ${agent_id} needle: found specific fact"
        else
            _warn "    ${agent_id} needle: target fact not found (${result_count} results)"
        fi
        results_json=$(echo "${results_json}" | jq ". + [{\"agent\": \"${agent_id}\", \"type\": \"needle\", \"query\": \"${query}\", \"results\": ${result_count}, \"found_target\": ${found_needle}}]")
    done

    # Phase 6: Collect stats from all agents
    _info "Phase 6: Collecting agent statistics..."
    local stats_json="[]"
    for agent_id in "${!AGENT_URLS[@]}"; do
        local url="${AGENT_URLS[${agent_id}]}/stats"
        local stats_resp
        stats_resp=$(curl -s --max-time 10 "${url}" 2>/dev/null || echo '{}')
        local fact_count
        fact_count=$(echo "${stats_resp}" | jq '.stats.fact_count // .stats.active_facts // 0' 2>/dev/null || echo "0")
        local agent_count_stat
        agent_count_stat=$(echo "${stats_resp}" | jq '.stats.agent_count // 0' 2>/dev/null || echo "0")
        echo "  ${agent_id}: facts=${fact_count} agents=${agent_count_stat}"
        stats_json=$(echo "${stats_json}" | jq ". + [{\"agent_id\": \"${agent_id}\", \"fact_count\": ${fact_count}, \"agent_count\": ${agent_count_stat}}]")
    done

    # Save results to JSON file
    local results_file="${REPO_ROOT}/experiments/hive_mind/eval_results_azure.json"
    local self_passed
    self_passed=$(echo "${results_json}" | jq '[.[] | select(.type == "self" and .results > 0)] | length')
    local self_total
    self_total=$(echo "${results_json}" | jq '[.[] | select(.type == "self")] | length')
    local cross_passed
    cross_passed=$(echo "${results_json}" | jq '[.[] | select(.type == "cross" and .results > 0)] | length')
    local cross_total
    cross_total=$(echo "${results_json}" | jq '[.[] | select(.type == "cross")] | length')
    local needle_passed
    needle_passed=$(echo "${results_json}" | jq '[.[] | select(.type == "needle" and .found_target == true)] | length')
    local needle_total
    needle_total=$(echo "${results_json}" | jq '[.[] | select(.type == "needle")] | length')

    jq -n \
        --arg date "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        --arg rg "${RESOURCE_GROUP}" \
        --arg location "${LOCATION}" \
        --argjson agents "${agent_count}" \
        --argjson healthy "${healthy}" \
        --argjson total "${queries_total}" \
        --argjson passed "${queries_passed}" \
        --argjson self_passed "${self_passed}" \
        --argjson self_total "${self_total}" \
        --argjson cross_passed "${cross_passed}" \
        --argjson cross_total "${cross_total}" \
        --argjson needle_passed "${needle_passed}" \
        --argjson needle_total "${needle_total}" \
        --argjson queries "${results_json}" \
        --argjson stats "${stats_json}" \
        '{
            date: $date,
            resource_group: $rg,
            location: $location,
            agents_deployed: $agents,
            agents_healthy: $healthy,
            summary: {
                total_queries: $total,
                total_passed: $passed,
                self_domain: { passed: $self_passed, total: $self_total },
                cross_domain: { passed: $cross_passed, total: $cross_total },
                needle_in_haystack: { passed: $needle_passed, total: $needle_total }
            },
            queries: $queries,
            agent_stats: $stats
        }' > "${results_file}"
    _ok "  Results saved to ${results_file}"

    # Summary
    echo
    echo "========================================"
    echo "  EVALUATION SUMMARY"
    echo "========================================"
    echo "  Date:               $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "  Agents deployed:    ${agent_count}"
    echo "  Agents healthy:     ${healthy}/${agent_count}"
    echo "  ---"
    echo "  Self-domain:        ${self_passed}/${self_total}"
    echo "  Cross-domain:       ${cross_passed}/${cross_total}"
    echo "  Needle-in-haystack: ${needle_passed}/${needle_total}"
    echo "  ---"
    echo "  Total queries:      ${queries_passed}/${queries_total}"
    echo "  Resource group:     ${RESOURCE_GROUP}"
    echo "========================================"
    echo
    echo "  Full results: ${results_file}"
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
