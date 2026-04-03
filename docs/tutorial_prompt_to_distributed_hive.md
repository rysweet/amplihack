# From Prompt to 100 Distributed Agents in Azure

A step-by-step guide that takes you from a single agent prompt to a
100-agent distributed hive mind running in Azure Container Apps. Each step
builds on the previous one, with working code and real CLI commands you can
run today.

**Real Azure resources used in this tutorial:**

| Resource              | Name                    |
| --------------------- | ----------------------- |
| Resource Group        | `hive-mind-rg`          |
| Container Registry    | `hivacrhivemind`        |
| Service Bus Namespace | `hive-sb-dj2qo2w7vu5zi` |

---

## Step 1: Write Your Agent Prompt

Every hive mind starts with a prompt that defines what your agent knows and
cares about. Write a system prompt describing your agent's domain and purpose.

```python
# prompts/security_analyst.py
SYSTEM_PROMPT = """You are a cloud security analyst for a distributed infrastructure.
You monitor server events, detect anomalies, and correlate findings across systems.

When you learn new facts:
- Extract entities (servers, IPs, ports, users, incidents)
- Note temporal context (timestamps, event sequences)
- Identify relationships (which servers communicate, which users have access)

When answering questions:
- Ground every answer in facts you have learned
- State confidence levels when uncertain
- Note if a question requires information you may not have seen
"""
```

Save this as `prompts/security_analyst.py`. You will pass it to the Memory
facade in Step 2.

---

## Step 2: Create Local Memory via Memory Facade (Zero Config)

The `Memory` facade requires zero configuration to get started. It defaults
to a local `cognitive` backend backed by a Kuzu graph database. No network,
no YAML, no environment variables required.

```python
from amplihack.memory import Memory

# Zero-config local memory — works out of the box
mem = Memory("security-analyst-1")
```

Under the hood this resolves to:

- `topology = "single"` (no network)
- `backend = "cognitive"` (Kuzu graph DB)
- `storage_path = ~/.amplihack/agents/security-analyst-1/`
- `kuzu_buffer_pool_mb = 256`

The storage path is created automatically on first use. The Kuzu database
persists between runs.

```python
# Verify the memory is alive
print(mem._agent_name)  # "security-analyst-1"
mem.close()             # Always close to flush the Kuzu buffer
```

---

## Step 3: remember() and recall() Locally

The entire API is two methods: `remember()` stores a fact, `recall()` retrieves
relevant facts for a query.

```python
from amplihack.memory import Memory

mem = Memory("security-analyst-1")

# remember() ingests raw text and extracts structured facts via LLM
mem.remember(
    "Server prod-db-01 runs PostgreSQL 15.5 on 10.0.1.5:5432. "
    "It has 64 GB RAM and 16 vCPUs. Last patched 2026-01-15 for CVE-2025-1234."
)

mem.remember(
    "Security incident INC-2026-0012: Brute-force SSH detected on prod-db-01 "
    "from 203.0.113.17. Firewall rule FW-101 added to block source IP. "
    "Incident resolved 2026-01-20."
)

mem.remember(
    "Server prod-web-01 runs Nginx 1.26 on 10.0.2.10:443. "
    "Serves the public API behind Azure Front Door."
)

# recall() finds relevant facts using hybrid vector + keyword search
facts = mem.recall("PostgreSQL incident prod-db-01")
for fact in facts:
    print(f"[{fact.get('confidence', 0):.0%}] {fact.get('content', fact)}")

# Ask a specific question
facts = mem.recall("What servers were involved in security incidents?")
for fact in facts:
    print(fact)

mem.close()
```

**What happens inside `remember()`:**

1. LLM extracts structured facts as JSON (`context`, `fact_text`, `confidence`)
2. Facts are stored in the local Kuzu graph DB
3. Temporal metadata is extracted (timestamps, sequences)
4. A concept map is generated to link related facts

**What happens inside `recall()`:**

1. Hybrid retrieval: vector similarity (BAAI/bge-base-en-v1.5) + keyword overlap
2. Results scored: `0.5 * semantic + 0.3 * confirmations + 0.2 * source_trust`
3. Top-K facts returned, sorted by score

---

## Step 4: Scale to Multiple Agents with shared_hive

Add a second agent and connect them through a shared `DistributedHiveGraph`.
Both agents learn different facts. Either agent can recall facts learned by
the other because all facts flow through the shared hive.

```python
from pathlib import Path
from amplihack.memory import Memory
from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
    DistributedHiveGraph,
)

# Create a shared DHT-backed hive (handles up to 100+ agents)
shared_hive = DistributedHiveGraph(
    hive_id="security-ops-hive",
    replication_factor=3,    # Each fact copied to 3 shards
    query_fanout=5,          # Query up to 5 shards per request
    gossip_enabled=True,
)

# Agent A: Infrastructure specialist
agent_a = Memory(
    "infra-analyst",
    topology="distributed",
    shared_hive=shared_hive,
)

# Agent B: Security incident analyst
agent_b = Memory(
    "incident-analyst",
    topology="distributed",
    shared_hive=shared_hive,
)

# Agent A learns infrastructure facts
agent_a.remember(
    "Server prod-db-01 (10.0.1.5) upgraded to PostgreSQL 15.5. "
    "Patch for CVE-2025-1234 applied. 3 read replicas: prod-db-02, 03, 04."
)

# Agent B learns security facts
agent_b.remember(
    "CVE-2025-1234 affects PostgreSQL instances. APT-29 actively exploiting. "
    "All unpatched PostgreSQL 15.x instances at risk."
)

# Cross-agent recall: Agent B can answer infra questions
facts = agent_b.recall("Is prod-db-01 patched for CVE-2025-1234?")
print("Agent B (incident analyst) answers infra question:")
for fact in facts:
    print(f"  {fact}")

# Cross-agent recall: Agent A can answer threat intel questions
facts = agent_a.recall("What CVEs are being actively exploited?")
print("\nAgent A (infra analyst) answers threat intel question:")
for fact in facts:
    print(f"  {fact}")

agent_a.close()
agent_b.close()
```

The `DistributedHiveGraph` distributes facts across agent shards via consistent
hashing (DHT). Each agent holds only its shard (`O(F/N)` memory per agent
instead of `O(F)` total), making it suitable for 100+ agent deployments.

---

## Step 5: Configure for Distributed via memory.yaml and Env Vars

For teams and production deployments, configure the memory stack declaratively
instead of passing parameters in code. Create `~/.amplihack/memory.yaml`:

```yaml
# ~/.amplihack/memory.yaml
topology: distributed
backend: cognitive
kuzu_buffer_pool_mb: 512
replication_factor: 3
query_fanout: 5
gossip_enabled: true
gossip_rounds: 3

# Azure Service Bus for cross-container fact propagation
memory_transport: azure_service_bus
memory_connection_string: "Endpoint=sb://hive-sb-dj2qo2w7vu5zi.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=<key>"
```

Or set environment variables (override YAML values):

```bash
export AMPLIHACK_MEMORY_TOPOLOGY=distributed
export AMPLIHACK_MEMORY_BACKEND=cognitive
export AMPLIHACK_MEMORY_TRANSPORT=azure_service_bus
export AMPLIHACK_MEMORY_CONNECTION_STRING="Endpoint=sb://hive-sb-dj2qo2w7vu5zi.servicebus.windows.net/;..."
export AMPLIHACK_MEMORY_KUZU_BUFFER_MB=512
export AMPLIHACK_MEMORY_REPLICATION_FACTOR=3
export AMPLIHACK_MEMORY_QUERY_FANOUT=5
export AMPLIHACK_MEMORY_GOSSIP_ENABLED=true
```

With this configuration, `Memory("my-agent")` automatically uses the
distributed topology and Azure Service Bus — no code changes needed:

```python
from amplihack.memory import Memory

# Config comes from memory.yaml or env vars
mem = Memory("security-analyst-42")
mem.remember("Server prod-web-03 is under high load: CPU 95%, MEM 88%.")
facts = mem.recall("servers under high load")
mem.close()
```

The `NetworkGraphStore` wraps the local store and publishes
`network_graph.create_node` events to Service Bus. Other agents subscribe
and replicate the write locally, enabling cross-container fact sharing.

---

## Step 6: Create Hive Config with amplihack-hive create

Use the `amplihack-hive` CLI to declare the desired hive topology in a YAML
manifest. The controller reconciles actual state to match the manifest.

```bash
# Create a new hive manifest for 10 agents across 2 groups
amplihack-hive create \
  --name security-ops-hive \
  --agents 10 \
  --groups 2 \
  --transport azure_service_bus \
  --connection-string "$AMPLIHACK_MEMORY_CONNECTION_STRING" \
  --output hive-config.yaml
```

This generates `hive-config.yaml`:

```yaml
# hive-config.yaml
apiVersion: amplihack.io/v1
kind: HiveManifest
metadata:
  name: security-ops-hive
  namespace: default
spec:
  topology: federated
  transport:
    type: azure_service_bus
    connection_string: "Endpoint=sb://hive-sb-dj2qo2w7vu5zi.servicebus.windows.net/;..."
  hive_store:
    type: distributed
    replication_factor: 3
    query_fanout: 5
    gossip_enabled: true
    broadcast_threshold: 0.9
  groups:
    - id: group-0
      domain: security
      agent_count: 5
    - id: group-1
      domain: infrastructure
      agent_count: 5
  gateway:
    enabled: true
    port: 8090
```

Apply the manifest to converge the local system:

```bash
amplihack-hive apply --file hive-config.yaml
```

The `HiveController` reads the manifest and creates the federation tree:
root hive → group hives → agents. High-confidence facts (≥ 0.9) auto-broadcast
across groups. All facts are reachable via `query_federated()`.

---

## Step 7: Add Agents with Prompts and Optional Kuzu DBs

Define individual agent specs in the manifest. Each agent can have its own
prompt variant and an optional Kuzu database path for persistent local memory.

```yaml
# hive-config.yaml (extended with agent specs)
spec:
  agents:
    - id: soc-agent-0
      domain: security
      group: group-0
      prompt_variant: 4 # Expert: full domain context
      kuzu_db_path: /data/soc-0/kuzu # Persistent Kuzu DB (Azure Files)
      env:
        AGENT_ROLE: "SOC Tier 1 analyst — triage and initial investigation"

    - id: soc-agent-1
      domain: security
      group: group-0
      prompt_variant: 5 # Expert + multi-step reasoning
      kuzu_db_path: /data/soc-1/kuzu
      env:
        AGENT_ROLE: "SOC Tier 2 analyst — deep forensics and root cause"

    - id: infra-agent-0
      domain: infrastructure
      group: group-1
      prompt_variant: 3 # Structured answers
      kuzu_db_path: /data/infra-0/kuzu
      env:
        AGENT_ROLE: "Infrastructure engineer — server state and capacity"

    - id: adversarial-agent
      domain: adversarial
      group: group-1
      prompt_variant: 1 # Minimal — injects noise for testing
      kuzu_db_path: /data/adversary/kuzu
      env:
        AGENT_ROLE: "Adversarial agent — injects false facts for consensus testing"
```

Load the manifest and instantiate agents in Python:

```python
from amplihack.agents.goal_seeking.hive_mind.controller import HiveController

controller = HiveController.from_yaml("hive-config.yaml")
controller.apply()  # Creates all agents, hives, and connections

# Access individual agents
soc_agent = controller.get_agent("soc-agent-0")
soc_agent.learn("INC-2026-0099: Ransomware detected on prod-file-01. Isolated.")

infra_agent = controller.get_agent("infra-agent-0")
infra_agent.recall("Which servers have been isolated?")

controller.close()
```

**Prompt variants:**

| Variant | Style      | Use Case                                  |
| ------- | ---------- | ----------------------------------------- |
| 1       | Minimal    | Testing, adversarial agents               |
| 2       | Basic      | Simple recall tasks                       |
| 3       | Structured | Explicit answer dimensions                |
| 4       | Detailed   | Full domain context                       |
| 5       | Expert     | Multi-step reasoning, memory organization |

---

## Step 8: Deploy to Azure via deploy.sh

Run the idempotent deploy script to provision all Azure infrastructure and
deploy your agents as Container Apps.

```bash
# Set required env vars
export ANTHROPIC_API_KEY="your-api-key-here"   # pragma: allowlist secret
export HIVE_RESOURCE_GROUP="hive-mind-rg"
export HIVE_LOCATION="eastus"
export HIVE_AGENT_COUNT=100

# Deploy everything (safe to run repeatedly — idempotent)
bash experiments/hive_mind/deploy_azure_hive.sh
```

**What gets provisioned in `hive-mind-rg`:**

| Resource           | Name                    | Details                                   |
| ------------------ | ----------------------- | ----------------------------------------- |
| Resource Group     | `hive-mind-rg`          | `eastus`                                  |
| Container Registry | `hivacrhivemind`        | Basic SKU, admin enabled                  |
| Service Bus        | `hive-sb-dj2qo2w7vu5zi` | Standard SKU, `hive-events` topic         |
| Storage Account    | Azure Files             | `agent-databases` share, Kuzu persistence |
| Container Apps Env | `hive-mind-env`         | Consumption tier                          |
| Container Apps     | 100 agent containers    | 2.0 CPU / 4.0 GiB each                    |
| Log Analytics      | `hive-logs-*`           | Centralized logging                       |

**Manual Azure CLI commands for custom deployments:**

```bash
# Create resource group
az group create \
  --name hive-mind-rg \
  --location eastus

# Create container registry
az acr create \
  --resource-group hive-mind-rg \
  --name hivacrhivemind \
  --sku Basic \
  --admin-enabled true

# Build and push agent image
az acr build \
  --registry hivacrhivemind \
  --image hive-mind-agent:latest \
  --file experiments/hive_mind/Dockerfile.hive \
  .

# Create Service Bus namespace and topic
az servicebus namespace create \
  --resource-group hive-mind-rg \
  --name hive-sb-dj2qo2w7vu5zi \
  --sku Standard

az servicebus topic create \
  --resource-group hive-mind-rg \
  --namespace-name hive-sb-dj2qo2w7vu5zi \
  --name hive-events

# Get Service Bus connection string
az servicebus namespace authorization-rule keys list \
  --resource-group hive-mind-rg \
  --namespace-name hive-sb-dj2qo2w7vu5zi \
  --name RootManageSharedAccessKey \
  --query primaryConnectionString -o tsv

# Create Container Apps environment
az containerapp env create \
  --name hive-mind-env \
  --resource-group hive-mind-rg \
  --location eastus

# Deploy one agent container (repeat for each agent)
az containerapp create \
  --name soc-agent-0 \
  --resource-group hive-mind-rg \
  --environment hive-mind-env \
  --image hivacrhivemind.azurecr.io/hive-mind-agent:latest \
  --registry-server hivacrhivemind.azurecr.io \
  --cpu 2.0 --memory 4.0Gi \
  --min-replicas 1 --max-replicas 1 \
  --env-vars \
    AGENT_ID=soc-agent-0 \
    AGENT_DOMAIN=security \
    AMPLIHACK_MEMORY_TOPOLOGY=distributed \
    AMPLIHACK_MEMORY_TRANSPORT=azure_service_bus \
    "AMPLIHACK_MEMORY_CONNECTION_STRING=Endpoint=sb://hive-sb-dj2qo2w7vu5zi.servicebus.windows.net/;..." \
    ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY"
```

---

## Step 9: Monitor and Manage with status, logs, stop

Use Azure CLI and the deploy script to monitor and manage your running agents.

### Check deployment status

```bash
# High-level status via deploy script
bash experiments/hive_mind/deploy_azure_hive.sh --status

# List all container apps in the resource group
az containerapp list \
  --resource-group hive-mind-rg \
  --query "[].{name:name, status:properties.runningStatus}" \
  --output table

# Check a specific agent's replica status
az containerapp replica list \
  --name soc-agent-0 \
  --resource-group hive-mind-rg \
  --output table
```

### Stream logs

```bash
# Stream logs from a specific agent
az containerapp logs show \
  --name soc-agent-0 \
  --resource-group hive-mind-rg \
  --follow

# Query Log Analytics for cross-agent logs
az monitor log-analytics query \
  --workspace hive-logs-dj2qo2w7vu5zi \
  --analytics-query "
    ContainerAppConsoleLogs_CL
    | where ContainerAppName_s startswith 'soc-agent'
    | where Log_s contains 'FACT_PROMOTED'
    | project TimeGenerated, ContainerAppName_s, Log_s
    | order by TimeGenerated desc
    | limit 50
  " \
  --output table
```

### Monitor Service Bus

```bash
# Check Service Bus topic message counts
az servicebus topic show \
  --resource-group hive-mind-rg \
  --namespace-name hive-sb-dj2qo2w7vu5zi \
  --name hive-events \
  --query "{activeMessages:countDetails.activeMessageCount, transferMessages:countDetails.transferMessageCount}" \
  --output table

# List all subscriptions (one per agent)
az servicebus topic subscription list \
  --resource-group hive-mind-rg \
  --namespace-name hive-sb-dj2qo2w7vu5zi \
  --topic-name hive-events \
  --query "[].name" \
  --output tsv
```

### Stop and restart agents

```bash
# Scale an agent to 0 replicas (stop without deleting)
az containerapp update \
  --name soc-agent-0 \
  --resource-group hive-mind-rg \
  --min-replicas 0 \
  --max-replicas 0

# Restart an agent
az containerapp update \
  --name soc-agent-0 \
  --resource-group hive-mind-rg \
  --min-replicas 1 \
  --max-replicas 1

# Tear down everything
bash experiments/hive_mind/deploy_azure_hive.sh --cleanup
# or manually:
az group delete --name hive-mind-rg --yes --no-wait
```

---

## Step 10: Feed Content and Verify Cross-Agent Recall

With 100 agents running in Azure, feed content via the HTTP API that each
agent exposes and verify that facts learned by one agent are accessible from
another via Service Bus propagation.

### Feed content to agents

Each container runs an HTTP server (`agent_runner.py`) with two endpoints:

```bash
# Get the URL of a deployed agent
SOC_URL=$(az containerapp show \
  --name soc-agent-0 \
  --resource-group hive-mind-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv)

INFRA_URL=$(az containerapp show \
  --name infra-agent-0 \
  --resource-group hive-mind-rg \
  --query "properties.configuration.ingress.fqdn" -o tsv)

# Feed a security fact to the SOC agent
curl -X POST "https://${SOC_URL}/learn" \
  -H "Content-Type: application/json" \
  -d '{"content": "CRITICAL: Zero-day RCE in OpenSSL 3.4.x (CVE-2026-9999). All prod servers must patch within 24h. prod-db-01 and prod-web-01 confirmed vulnerable."}'

# Feed an infrastructure fact to the infra agent
curl -X POST "https://${INFRA_URL}/learn" \
  -H "Content-Type: application/json" \
  -d '{"content": "prod-db-01 patched to OpenSSL 3.4.1 at 2026-03-06T14:30Z. prod-web-01 patch scheduled for 2026-03-06T18:00Z."}'
```

### Verify cross-agent recall

After Service Bus propagates the `FACT_PROMOTED` event (typically 1-3 seconds):

```bash
# Ask the INFRA agent about the security incident (cross-agent recall)
curl -X POST "https://${INFRA_URL}/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Which servers are vulnerable to CVE-2026-9999 and have they been patched?"}'

# Expected: infra agent knows about the CVE from the SOC agent via Service Bus
# {
#   "answer": "prod-db-01 was confirmed vulnerable to CVE-2026-9999 and has been patched
#              to OpenSSL 3.4.1 as of 2026-03-06T14:30Z. prod-web-01 remains vulnerable
#              with a patch scheduled for 2026-03-06T18:00Z.",
#   "sources": ["soc-agent-0", "infra-agent-0"],
#   "confidence": 0.92
# }

# Ask the SOC agent about the patch status (cross-agent recall)
curl -X POST "https://${SOC_URL}/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "Has prod-db-01 been patched for the OpenSSL zero-day?"}'

# Expected: SOC agent knows the patch status from the infra agent via Service Bus
```

### Python batch verification

```python
import httpx
import time

SOC_URL = "https://soc-agent-0.your-env.eastus.azurecontainerapps.io"
INFRA_URL = "https://infra-agent-0.your-env.eastus.azurecontainerapps.io"

# Feed facts to different agents
with httpx.Client() as client:
    # SOC agent learns about 5 incidents
    for i in range(5):
        client.post(f"{SOC_URL}/learn", json={
            "content": f"INC-2026-{1000+i}: Security event on prod-server-{i:02d}."
        })

    # Infra agent learns about server state
    for i in range(5):
        client.post(f"{INFRA_URL}/learn", json={
            "content": f"prod-server-{i:02d} is running at 78% capacity, 256GB RAM."
        })

# Wait for Service Bus propagation
time.sleep(5)

# Cross-agent recall verification
with httpx.Client() as client:
    # Infra agent should know about incidents (from SOC via Service Bus)
    resp = client.post(f"{INFRA_URL}/query", json={
        "question": "Which servers have had security incidents?"
    })
    print("Infra agent cross-recall result:", resp.json()["answer"])

    # SOC agent should know about server capacity (from infra via Service Bus)
    resp = client.post(f"{SOC_URL}/query", json={
        "question": "What is the capacity utilization of prod-server-00?"
    })
    print("SOC agent cross-recall result:", resp.json()["answer"])
```

### Run the full eval against deployed agents

```bash
# Run the eval against the deployed Azure agents
bash experiments/hive_mind/deploy_azure_hive.sh --eval

# Or run with custom parameters
python -m amplihack_eval.run \
  --scenario long_horizon \
  --topology distributed \
  --num-agents 100 \
  --hive-resource-group hive-mind-rg \
  --service-bus hive-sb-dj2qo2w7vu5zi \
  --output-dir results/azure-100-agents
```

---

## Summary

| Step | What You Did                                | Key API                                     |
| ---- | ------------------------------------------- | ------------------------------------------- |
| 1    | Wrote an agent prompt                       | Plain text / Python string                  |
| 2    | Created local memory (zero config)          | `Memory("agent-name")`                      |
| 3    | Stored and retrieved facts locally          | `mem.remember()`, `mem.recall()`            |
| 4    | Connected two agents via shared hive        | `DistributedHiveGraph` + `shared_hive=`     |
| 5    | Configured for distributed via YAML/env     | `memory.yaml`, `AMPLIHACK_MEMORY_*`         |
| 6    | Declared hive topology                      | `amplihack-hive create`, `hive-config.yaml` |
| 7    | Added agents with prompts and Kuzu DBs      | `HiveController.from_yaml()`                |
| 8    | Deployed 100 agents to Azure                | `deploy_azure_hive.sh`, `az containerapp`   |
| 9    | Monitored and managed deployment            | `az containerapp logs`, Service Bus metrics |
| 10   | Fed content and verified cross-agent recall | `/learn`, `/query` HTTP endpoints           |

## Azure Resources Quick Reference

```bash
# Resource group
az group show --name hive-mind-rg

# Container registry
az acr show --name hivacrhivemind --resource-group hive-mind-rg

# Service Bus
az servicebus namespace show \
  --name hive-sb-dj2qo2w7vu5zi \
  --resource-group hive-mind-rg

# All container apps
az containerapp list \
  --resource-group hive-mind-rg \
  --query "[].name" --output tsv
```

## Next Steps

- **[ARCHITECTURE.md](hive_mind/ARCHITECTURE.md)** — deep dive into DHT sharding,
  CRDTs, gossip protocol, and RRF retrieval
- **[EVAL.md](hive_mind/EVAL.md)** — evaluation methodology and interpreting results
- **[GETTING_STARTED.md](hive_mind/GETTING_STARTED.md)** — in-process tutorial
  from single agent to federated hive
- **[distributed_hive_mind.md](distributed_hive_mind.md)** — DistributedHiveGraph
  architecture and DHT internals
